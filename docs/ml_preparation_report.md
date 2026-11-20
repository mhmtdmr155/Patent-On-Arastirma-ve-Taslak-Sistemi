# KSÜ Bilgisayar Mühendisliği Bitirme Projesi
# Makine Öğrenmesi Hazırlık, Özellik Çıkarımı ve Etiketleme Altyapısı Raporu (PAT-0404 - PAT-0409)

**Proje:** Yapay Zekâ Destekli Patent Ön Araştırma ve Patent Ön Taslağı Hazırlama Sistemi  
**Görev Kodu:** PAT-0404 (Kapsanan Görevler: PAT-0404, PAT-0405, PAT-0406, PAT-0407, PAT-0408, PAT-0409)  
**Tarih:** 05.11.2026  
**Durum:** Tamamlandı — Bağımsız Denetime Hazır  

---

## 1. Yönetici Özeti ve Temel Mimari

Bu çalışma kapsamında, BM25 birinci aşama bilgi getirme (first-stage retrieval) sonuçlarını yeniden sıralayacak (reranking) denetimli makine öğrenmesi modelinin bilimsel ve metodolojik hazırlık altyapısı inşa edilmiştir.

Sistemin temel felsefesi:
1. **Sıfır Yapay Etiket Prensibi:** Model eğitimi için sentetik/otomatik etiket üretimi kesinlikle reddedilmiş; insan uzman denetimine dayalı nesnel etiketleme süreci tasarlanmıştır.
2. **Seçim Yanlılığı (Selection Bias) Önleme:** İlk denetim raporundaki 140 çiftlik aday kümesi, 20 teknik sorgu ile 8 patentin tam Kartezyen çarpımına genişletilerek 160 çifte çıkarılmıştır. Böylece BM25 skoru sıfır olan (aday dışı kalan) 20 patent-sorgu çifti de denetçiye sunularak birinci aşamanın kaçırdığı potansiyel patentler (false negatives) analiz edilebilir kılınmıştır.
3. **Veri Sızıntısını Önleyen Grup Bazlı Ayrım:** Patent ailesi devam başvurularının aynı kökten gelmesi sebebiyle train/test kümelerine rastgele dağıtılması sonucu oluşacak "aile içi sızıntı" (family leakage), 6 bağımsız `evaluation_group_id` birimi tanımlanarak ve `GroupKFold` çapraz doğrulama uygulanarak matematiksel olarak engellenmiştir.
4. **Yorumlanabilir Sayısal Özellikler:** 7 boyutlu, hedef etiketlerden tamamen bağımsız, normalize edilmiş ve sonlu sayısal özellik vektörü mimarisi oluşturulmuştur.
5. **Model Eğitimi Öncesi Kesin Blokaj (`NOT_READY`):** İnsan etiketleri toplanmadan model eğitimine başlanmasını önleyen 12 önkoşullu denetim mekanizması devreye alınmış; sistemin anlık durumu `NOT_READY` olarak tescil edilmiştir.

---

## 2. Aday Kuyruğu ve Veri Şeması Mühendisliği (PAT-0404)

### 2.1 140 vs 160 Çift Uyuşmazlığının Çözümü
- **Önceki Durum:** BM25 aramasında skoru $> 0.0$ olan adaylar filtrelendiğinde 140 çift elde ediliyordu. Ancak bu durum, BM25'in sıfır skor verdiği 20 çifti denetim havuzundan dışlayarak "hayatta kalma yanlılığı" (survivorship bias) yaratıyordu.
- **Düzeltme:** 20 sorgu $\times$ 8 patent = 160 çiftlik tam Kartezyen uzay `data/annotations/labeling_queue.csv` dosyasında oluşturulmuştur.
- **Dağılım:**
  - `bm25_candidate == True` (Skor $> 0.0$): 140 kayıt (BM25 rank 1..8)
  - `bm25_candidate == False` (Skor $== 0.0000$): 20 kayıt (BM25 rank 0, kanıt pasajı boş)

### 2.2 CSV Şeması (`data/annotations/labeling_queue.csv`)
| Sütun Adı | Tip | Açıklama |
|---|---|---|
| `pair_id` | str (PK) | Benzersiz çift kimliği (`{query_id}_{publication_number}`) |
| `query_id` | str | Sorgu kimliği (Q01-Q20) |
| `query_text` | str | Arama metni |
| `publication_number` | str | Patent yayın numarası |
| `patent_title` | str | Patent başlığı |
| `source_url` | str | Google Patents resmi URL'si |
| `family_id` | str | Patent devam ailesi kimliği (boş ise bağımsız) |
| `evaluation_group_id` | str | Train/Test bölünmesinde kullanılan 6 bağımsız grup |
| `bm25_score` | float | BM25 eşleşme skoru (4 ondalık) |
| `bm25_rank` | int / empty | Sorgu bazlı BM25 sıralaması (1..8 veya boş) |
| `bm25_candidate` | bool | BM25 tarafından aday olarak getirilip getirilmediği |
| `evidence_chunk_id` | str / empty | En yüksek skorlu kanıt pasajı kimliği |
| `human_relevance_label` | str / empty | İnsan ilgililik kararı (`0`, `1`, `2` veya boş) |
| `reviewer_id` | str / empty | İncelemeyi yapan araştırmacı rumuzu |
| `review_status` | str | `PENDING_HUMAN_REVIEW` veya `REVIEWED` |
| `review_notes` | str / empty | Araştırmacının teknik gerekçe notu |
| `reviewed_at` | str / empty | UTC zaman damgası |

---

## 3. Patent Aileleri ve Değerlendirme Grupları (PAT-0405)

### 3.1 Tekil Kümeleme Yanılgısının Düzeltilmesi
Önceki raporda yapılan incelemede, bağımsız (herhangi bir devam ailesine bağlı olmayan) 4 patentin ortak bir `"SINGLETON"` etiketi altında toplanması, `GroupKFold` algoritmasının bu 4 patenti tek bir süper-aile gibi ele almasına ve yapay küme içi bağımlılık yanılsamasına yol açtığı tespit edilmiştir.

### 3.2 6 Bağımsız Değerlendirme Grubu Mimarisi
8 gerçek patent kaydı, aşağıdaki 6 ayrık değerlendirme grubuna atanmıştır:

1. `FAM_US_DRESSELHAUS_SOIL_01`:
   - `US7836910B2` (Soil moisture sensor and controller)
   - `US8671969B2` (Soil moisture sensor and controller - Continuation)
2. `FAM_US_IRR_WIRELESS_01`:
   - `US9241451B2` (Methods and systems for irrigation control)
   - `US11064664B2` (Methods and systems for irrigation control - Continuation)
3. `SINGLETON_US11457576B2`:
   - `US11457576B2` (Intelligent irrigation system)
4. `SINGLETON_US11674944B2`:
   - `US11674944B2` (In-ground wireless soil moisture sensor)
5. `SINGLETON_US12144295B1`:
   - `US12144295B1` (Smart irrigation system)
6. `SINGLETON_US9804113B2`:
   - `US9804113B2` (Soil moisture sensor)

### 3.3 Aile İçi Sızıntının Önlenmesi Kanıtı
`family_aware_kfold_split(n_splits=3)` fonksiyonu test edilmiş ve şu doğrulamalar yapılmıştır:
- $Train \cap Test = \emptyset$ (Grup düzeyinde kesişim kesinlikle 0).
- `US7836910B2` ve `US8671969B2` hiçbir fold'da train ve test arasına bölünmemiştir.
- `US9241451B2` ve `US11064664B2` hiçbir fold'da train ve test arasına bölünmemiştir.

Ayrıca sorgu genelleştirmesi için `query_aware_kfold_split(n_splits=4)` fonksiyonu da her fold'da 5 sorguyu testte, 15 sorguyu eğitimde tutacak şekilde 0 sızıntıyla çalışmaktadır.

---

## 4. Sayısal Özellik Çıkarımı (PAT-0407 & PAT-0408)

Yeniden sıralama modelinde kullanılmak üzere 7 boyutlu, fiziksel/metinsel karşılığı olan ve yorumlanabilir özellik vektörü tasarlanmıştır (`src/ml/features.py`):

| No | Özellik Adı | Formül / Tanım | Değer Aralığı | Amaç / Gerekçe |
|---|---|---|---|---|
| 1 | `bm25_score_raw` | $\max(S_{BM25}, 0.0)$ | $[0.0, \infty)$ | Birinci aşama leksikal ilgi skoru |
| 2 | `bm25_score_query_norm` | $\frac{S_{BM25}}{\max(S_{query\_max}, S_{BM25}, 10^{-6})}$ | $[0.0, 1.0]$ | Sorgu uzunluğundan bağımsız göreceli BM25 gücü |
| 3 | `title_token_overlap` | $\frac{\|T_q \cap T_{title}\|}{\|T_q\|}$ | $[0.0, 1.0]$ | Buluş başlığında sorgu terimlerinin örtüşme oranı |
| 4 | `abstract_token_overlap` | $\frac{\|T_q \cap T_{abstract}\|}{\|T_q\|}$ | $[0.0, 1.0]$ | Resmi patent özetinde sorgu terimlerinin örtüşme oranı |
| 5 | `best_passage_overlap` | $\frac{\|T_q \cap T_{passage}\|}{\|T_q\|}$ | $[0.0, 1.0]$ | En yüksek skorlu pasajdaki terim örtüşmesi |
| 6 | `cpc_domain_match` | $\min(\sum [CPC \in Domain], 5.0)$ | $[0.0, 5.0]$ | Hedef CPC kodları (`A01G`, `G01N`) ile sınıf eşleşmesi |
| 7 | `patent_word_count_norm`| $\frac{\text{Kelimeler}}{\text{Korpus\_Ortalama\_Kelime\_Sayısı}}$ | $(0.0, \infty)$ | Patent detay seviyesi ve açıklama derinliği kontrolü |

### Matematiksel Güvenlik ve Sızıntı Kontrolü
1. **Hedef Bağımsızlığı:** Özellik çıkarım fonksiyonu (`extract_features_for_pair`) imzasında ve gövdesinde insan etiketlerine kesinlikle erişmez.
2. **Sonsuz/NaN İzolasyonu:** Bütün özellikler `math.isfinite` denetiminden geçer; sıfıra bölünme durumları $\epsilon = 10^{-6}$ ve koruma koşulları ile sıfıra çekilir.
3. **TF-IDF Sızıntı İzolasyonu:** Kelime dağarcığı (`TfidfVectorizer`) yalnızca eğitim verisi üzerinde fit edilir; test verisi yalnızca transform edilir (`fit_transform_tfidf_no_leakage`).

---

## 5. İnsan Denetimli Etiketleme Arayüzü ve Güvenli Depolama (PAT-0404)

### 5.1 Yerel Streamlit Etiketleme Aracı (`tools/labeling_app.py`)
Araştırmacıların sorgu-patent çiftlerini nesnel olarak değerlendirmesi için modern ve ergonomik bir yerel web arayüzü geliştirilmiştir:
- **Üst Panel:** Toplam çift (160), İncelenen (0), Bekleyen (160) ve Tamamlanma yüzdesi metrikleri ile ilerleme çubuğu.
- **Filtreler:** İnceleme durumu (Bekleyenler / İncelenenler / Tümü), Sorgu seçimi (Q01-Q20), Patent seçimi.
- **İki Sütunlu Kart Tasarımı:**
  - Sol Sütun: Sorgu metni, teknik odak, kaynak türü, BM25 skoru, sıralaması, adalık durumu, patent ailesi ve değerlendirme grubu.
  - Sağ Sütun: Patent numarası (Google Patents bağlantılı), başlık, başvuru numarası, hak sahibi, mucitler, resmi özet (abstract) ve en yüksek skorlu kanıt pasajı (expander içinde tam metin).
- **Etiketleme Seçimi:** 3 seviyeli radyo düğmesi (0: İlgisiz, 1: Kısmen İlgili, 2: Doğrudan İlgili) ve opsiyonel teknik not kutusu.
- **Eylemler:** "Önceki Kayıt", "Etiketi Kaydet" (otomatik bir sonraki kayda geçer), "Sonraki Kayıt", "Etiketi Sıfırla".

### 5.2 Atomik ve Veri Kaybını Önleyen Disk Depolaması (`src/ml/label_store.py`)
- Windows ve POSIX ortamlarında kısmi yazma ve elektrik/işlem kesintilerinde dosya bozulmasını önlemek için **geçici dosya yazımı ve yerinde takas (`.tmp` -> `os.replace`)** mimarisi uygulanmıştır.
- `update_label`: Yalnızca `0`, `1`, `2` değerlerini kabul eder, inceleyen rumuzunu ve UTC zamanını ekler.
- `clear_label`: Kaydı güvenle `PENDING_HUMAN_REVIEW` durumuna geri döndürür.

---

## 6. Etiket Eşleme ve Sınıf Dengesi Politikası (PAT-0409)

1. **İkili Sınıflandırma Eşlemesi:**
   $$\text{Binary Target} = \begin{cases} 0 & \text{eğer } \text{label} = 0 \text{ (İlgisiz)} \\ 1 & \text{eğer } \text{label} \in \{1, 2\} \text{ (Kısmen veya Doğrudan İlgili)} \end{cases}$$
2. **Kademeli Değerlendirme Korunumu:** NDCG@k ve sıralama metrikleri için ham `0`, `1`, `2` etiketleri veritabanında eksiksiz olarak muhafaza edilir.
3. **Sınıf Dengesizliği Stratejisi:** İnsan etiketlemesi tamamlandığında, `class_weight='balanced'` parametresi veya pozitif/negatif ağırlıklandırma katsayıları kullanılacaktır.

---

## 7. Makine Öğrenmesi Hazırlık Denetimi (Readiness Audit)

`src/ml/readiness.py` modülü altında 12 önkoşul kontrol edilmektedir:

| Kontrol Maddesi | Beklenen | Mevcut Değer | Durum |
|---|---|---|---|
| Asgari İnsan Etiket Sayısı | $\ge 50$ | 0 | ❌ BAŞARISIZ (Eğitim Yasak) |
| Sınıf Çeşitliliği (Pozitif & Negatif) | Her iki sınıf mevcut | Yok | ❌ BAŞARISIZ |
| Kapsanan Sorgu Sayısı | $\ge 5$ | 0 | ❌ BAŞARISIZ |
| Değerlendirme Grubu Sayısı | 6 | 6 | ✅ BAŞARILI |
| Toplam Aday Havuz Boyutu | 160 | 160 | ✅ BAŞARILI |
| Sıfır Sentetik Etiket Güvencesi | 0 sahte etiket | 0 sahte etiket | ✅ BAŞARILI |
| BM25 Aday ve Sıfır Skor Tutarlılığı | 140 / 20 ayrımı | 140 / 20 | ✅ BAŞARILI |
| Özellik Matrisi Sonluluğu | NaN/Inf yok | 0 NaN/Inf | ✅ BAŞARILI |
| Grup Bazlı Sızıntı Kontrolü | 0 sızıntı | 0 sızıntı | ✅ BAŞARILI |
| Sorgu Bazlı Sızıntı Kontrolü | 0 sızıntı | 0 sızıntı | ✅ BAŞARILI |
| TF-IDF Train-Only Fit Güvencesi | 0 test terimi | 0 test terimi | ✅ BAŞARILI |
| Atomik Depolama Güvencesi | `.tmp` kalıntısı yok | Doğrulandı | ✅ BAŞARILI |

### Nihai Hazırlık Kararı: `NOT_READY`
Model eğitimi kesin olarak bloklanmıştır. İnsan etiketleme süreci tamamlanmadan hiçbir scikit-learn modeli eğitilmeyecektir.

---

## 8. Test ve Doğrulama Kanıtları

Projede mevcut test paketleri eksiksiz olarak çalıştırılmış ve 138 testin tamamı başarılı olmuştur:
- `tests/test_labeling.py`: 16 test (Aday kuyruğu bütünlüğü, LabelStore doğrulama, atomik yazma, Streamlit arayüz etkileşimi).
- `tests/test_ml_preparation.py`: 12 test (Özellik çıkarımı sınırları, sızıntısız GroupKFold, TF-IDF izolasyonu, NOT_READY denetimi).
- Diğer regresyon testleri: 110 test (BM25 motoru, veri boru hattı, patent kimlik denetimi, arayüz fonksiyonları).
- **Toplam:** 138 test başarılı, 0 hata, 0 uyarı.

