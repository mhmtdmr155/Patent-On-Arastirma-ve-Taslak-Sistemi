# Patent Bilgi Getirimi ve BM25 Arama Tasarımı (PAT-0301)

Bu doküman, Yapay Zekâ Destekli Patent Ön Araştırma ve Patent Ön Taslağı Hazırlama Sistemi'nin 1. Katmanını oluşturan **BM25 Patent Pasaj Arama Motoru**'nun mimari kararlarını, matematiksel gerekçelerini, veri akışını ve entegrasyon sınırlarını ayrıntılandırmaktadır.

---

## 1. Mimari Genel Bakış ve Amaç

Sistemin arama katmanı, kullanıcının girdiği teknik problem, buluş özeti veya teknik sorgu terimleri ile patent korpusundaki doğrulanmış teknik metinleri karşılaştırarak en ilgili patent dokümanlarını ve bu dokümanlar içerisindeki en kritik kanıt pasajlarını tespit eder.

```
+-------------------------------------------------------------+
| Kullanıcı / Buluş Formu (Teknik Sorgu: İngilizce)           |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| Tokenizer (Unicode NFC, [a-z0-9]+(?:[/\-_][a-z0-9]+)*,     |
|            Minimal Stopwords, Teknik Tanımlayıcı Koruması)  |
+-------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------+
| BM25Okapi Pasaj İndeksi (rank_bm25)                        |
| 256 Doğrulanmış Pasaj (Abstract + Description)              |
+-------------------------------------------------------------+
                               |
                               v  Pasaj Skorları (BM25 > 0.0)
+-------------------------------------------------------------+
| Patent Düzeyinde Max-Pooling Birleştirme                   |
| patent_score = max_{c in Chunks(P)} (score(c))             |
+-------------------------------------------------------------+
                               |
                               v  Sıralama: (-score, pub_number)
+-------------------------------------------------------------+
| İlk 20 Farklı Patent Adayı (Deterministik Seçim)            |
+-------------------------------------------------------------+
                               |
                               v  Kullanıcı Sunumu (Top 5)
+-------------------------------------------------------------+
| Kaynaklı İlk 5 Patent Sonucu                               |
| (Başlık, Yayın No, Başvuru No, Skor, En İyi Pasaj,         |
|  İç Konum Belirteci, Kaynak Doküman Konumu, Google URL)     |
+-------------------------------------------------------------+
```

---

## 2. Neden BM25Okapi? (TF-IDF ile Karşılaştırma)

Arama motoru çekirdeğinde klasik TF-IDF yerine **BM25Okapi** algoritması tercih edilmiştir:

1. **Terim Sıklığı Doygunluğu ($k_1 = 1.5$):**
   - Standart TF-IDF yaklaşımında terim frekansı arttıkça skor doğrusal veya logaritmik olarak sınırsız büyür.
   - Patent metinlerinde bir kelime ("sensor", "valve") patentin uzunluğu veya tekrar eden anlatımı nedeniyle onlarca kez geçebilir.
   - BM25'te $k_1$ parametresi terim frekansının marjinal katkısını sınırlar ve doygunluğa ulaştırır.
2. **Belge Uzunluğu Normalizasyonu ($b = 0.75$):**
   - Patentler 2 sayfa özet ile 50 sayfa ayrıntılı tarifname arasında devasa uzunluk farkları gösterir.
   - $b$ parametresi, pasaj uzunluğunun ortalama korpus pasaj uzunluğuna ($L / L_{avg}$) oranına göre uzun pasajları adil biçimde cezalandırarak haksız skor şişmesini engeller.
3. **Deterministik ve Şeffaf Skorlama:**
   - Vektör gömmeleri (dense embeddings) henüz denetlenmemiş bir patent korpusunda semantik kaymaya yol açabilirken, BM25 terim eşleşmesi ile patent vekillerinin alışık olduğu anahtar kelime eşleşmesini doğrulanabilir biçimde sağlar.

---

## 3. Tokenization Stratejisi ve Teknik Tanımlayıcıların Korunması

Patent metinleri standart doğal dil metinlerinden farklı olarak yoğun biçimde teknik birimler, devre elemanları, voltaj değerleri ve patent sınıflandırma kodları içerir:

- **Unicode Normalizasyonu:** Giriş metni `unicodedata.normalize('NFC', text)` ile normalize edilir.
- **Teknik Regex:** `[a-z0-9]+(?:[/\-_][a-z0-9]+)*` deseni kullanılarak:
  - Devre modelleri (`rlc`, `5v`, `100pf`, `3.3v`) korunur.
  - CPC kodları (`a01g25/16`) tek bir token olarak muhafaza edilir.
  - Tireli veya altçizgili teknik kavramlar parçalanmaz.
- **Minimal Stopwords:** Yalnızca 42 temel İngilizce işlevsel sözcük elenir (`the`, `is`, `at`, `which`, `on` vb.). Teknik anlam taşıyabilecek hiçbir kısaltma stopwords listesine dahil edilmemiştir.
- **Çift Yönlü Tutarlılık:** İndekslenen korpus ve arama sorgusu birebir aynı tokenizer ve aynı parametreler (`remove_stopwords=True`) ile işlenir.

---

## 4. Pasaj Düzeyinde İndeksleme ve Bölüm Ayrımı

Patent metinleri tek bir yekpare metin olarak değil, bölüm ve pasaj duyarlı parçalar (chunks) halinde indekslenir (`data/processed/chunks.jsonl`):

- **Kapsam:** Yalnızca `abstract` ve `description` bölümleri indekslenir. Hukuki istemler (`claims`) PAT-0201 kuralları gereği korpustan ve indeksleme kapsamından kesinlikle hariç tutulmuştur.
- **Pasaj Boyutu:** Paragraflar ~1.000 karakterlik pencerelerle yapılandırılmıştır (pilot korpusta 8 patent için toplam 256 pasaj).
- **Konum Belirteçleri:**
  - `internal_chunk_locator`: Sistem içi sıralı belirteç (örn. `abstract_p0`, `description_p14`).
  - `source_document_locator`: Orijinal patent dokümanındaki bölüm (örn. `section=description`).

---

## 5. Pasajdan Patente Max-Pooling Birleştirme

BM25 indeksinde 256 adet pasaj bağımsız birer doküman olarak puanlanır. Ancak kullanıcıya pasaj yığını değil, patent düzeyinde sıralanmış bir liste sunulmalıdır.

### Neden Max-Pooling ($Score_{patent} = \max_{c \in Chunks} Score_{c}$)?
- **Teknik Gerekçe:** Bir buluşun yeniliğini etkileyen patent, genellikle buluşun tüm adımlarını değil, belirli bir teknik özelliğini (örn. "toprak nemine göre eşik değer kıyası") tek bir paragrafında tam olarak ifşa eden patenttir.
- **Ortalama Skorun (Average) Sakıncası:** Ortalama skor kullanılsaydı, 50 sayfalık çok ayrıntılı ve geniş kapsamlı bir patentin diğer ilgisiz paragrafları ortalamayı düşürecek ve patent haksız yere alt sıralara itilecekti.
- **Toplam Skorun (Sum) Sakıncası:** Toplam skor kullanılsaydı, çok uzun patentler sırf çok sayıda pasaj içerdiği için kısa ama tam odaklı patentlerin önüne geçecekti.
- **Sonuç:** Max-pooling, teknik benzerliğin en yoğun olduğu tekil pasajın gücünü patent skoruna yansıtarak en doğru kanıtı öne çıkarır.

---

## 6. Aday Seçimi ve Deterministik Tie-Breaking

1. **Pozitif Skor Filtresi:** Yalnızca $BM25 > 0.0$ olan ve en az bir terim eşleşmesi sağlayan pasajlar toplanır.
2. **Deterministik Sıralama:**
   - Birincil anahtar: BM25 skoru (büyükten küçüğe, `score DESC`).
   - İkincil anahtar (Eşitlik bozucu / Tie-breaker): Yayın numarası alfabetik sıralaması (`publication_number ASC`).
   - Bu sayede aynı skora sahip patentler her çalıştırmada kesinlikle aynı sırada listelenir.
3. **İlk 20 Farklı Patent Adayı (PAT-0304):**
   - Sonuç listesi `min(matching_patents, 20)` kuralı ile sınırlandırılır.
   - Pilot korpusta toplam 8 patent bulunduğundan, 8 patentin tamamı eşleşirse 8 aday döner. Korpus genişletildiğinde üst sınır 20 olarak uygulanır.

---

## 7. Kullanıcı Sunumu ve Kaynak İlişkilendirme (Top 5)

Kullanıcı arayüzüne ilk 5 patent sunulur. Her sonuçta şu kaynak alanları eksiksiz yer alır:
- **Buluş Başlığı:** Resmi patent başlığı.
- **Yayın Numarası:** `US11674944B2` gibi benzersiz yayın kimliği.
- **Başvuru Numarası:** `17/384,105` gibi resmi başvuru numarası.
- **BM25 Skoru:** 4 basamaklı ondalık format (`6.6488`).
- **En İyi Pasaj:** En yüksek skoru üreten ham pasaj metni (genişletilebilir `st.expander` içinde).
- **Pasaj Bölümü ve Konumu:** `DESCRIPTION` veya `ABSTRACT`, `internal_chunk_locator` (`description_p14`).
- **Resmi Kaynak Linki:** Doğrulanmış `https://patents.google.com/patent/{pub}/en` URL'si.

---

## 8. Test ve Sorgu Davranış Matrisi

Sistem 8 farklı test senaryosunda doğrulanmıştır:
1. `soil moisture sensor` -> 5 patent eşleşti, en yüksek skor: `US11674944B2` (6.6488).
2. `wireless irrigation controller` -> 5 patent eşleşti, en yüksek skor: `US11064664B2` (4.1067).
3. `series RLC circuit` -> 5 patent eşleşti, en yüksek skor: `US9804113B2` (14.8953).
4. `automatic irrigation` -> 5 patent eşleşti, en yüksek skor: `US11064664B2` (4.5847).
5. `remote monitoring gateway` -> 5 patent eşleşti, en yüksek skor: `US11064664B2` (6.3679).
6. `quantum blockchain cryptocurrency` -> 0 patent eşleşti (boş liste, uyarı mesajı).
7. `""` (Boş sorgu) -> 0 patent eşleşti (boş liste, girdi uyarısı).
8. `toprak nem sensörü` (Türkçe sorgu) -> Yalnızca tek harfli 'r' parçası nedeniyle `US9804113B2` ile yapay eşleşme. Bu sonuç, arayüzde kullanıcının İngilizce teknik terim girmesi gerektiğine dair politikanın doğruluğunu kanıtlamıştır.

---

## 9. Streamlit Entegrasyonu ve Durum Yönetimi (Session State)

- Arama paneli yalnızca `st.session_state["current_invention"]` mevcut olduğunda görünür.
- Kullanıcı formu temizlediğinde veya yeni bir buluş kaydettiğinde `st.session_state["search_results"]` ve `st.session_state["current_query"]` otomatik olarak sıfırlanır.
- Arayüzde "bu patent buluşu engeller" gibi hukuki veya kesinlik bildiren hiçbir iddia yer almaz; sistemin yalnızca istatistiksel bir terim eşleşmesi sıralaması sunduğu açıkça belirtilir.

---

## 10. Korpus Sınırları ve Gelecek Genişleme Yol Haritası

- **Mevcut Pilot Durumu:** 8 doğrulanmış patent, 256 pasaj, 4.18 MB ham veri. Google Patents Public HTML Mirror üzerinden doğrudan doğrulanmıştır.
- **Sınır:** Pilot korpus donanım ve ağ sınırlarına uymak amacıyla kontrollü tutulmuştur.
- **Gelecek Genişleme:** Bulk aşamada USPTO Open Data Portal (Haziran 2026 sonrası zorunlu kullanıcı kaydı koşuluyla) veya bulk XML arşivleri üzerinden akış (streaming) mimarisiyle 50-100 patente genişletilecektir.

