# Sistem Mimarisi ve Oturum Durumu (Session State) Tasarımı

## 1. Projenin Amacı ve Temel Vizyonu
Bu projenin amacı; patent ön araştırma sürecini araştırmacılar ve mühendisler için optimize eden, taranan patent dokümanları üzerinde şeffaf metin karşılaştırması ve ilgililik sıralaması gerçekleştiren ve doğrulanmış patent kaynak pasajlarına dayalı dört bölümlü bir patent ön taslağı hazırlayan yapay zekâ destekli bir karar destek sistemi sunmaktır.

Sistem, halüsinasyonu en aza indiren kural tabanlı ve makine öğrenimi tabanlı bilgi erişimi (retrieval) ile hazır büyük dil modellerinin (LLM) kontrollü metin sentezleme gücünü ayrıştırılmış bir mimaride birleştirir.

---

## 2. Geliştirme Sınırları ve Hukuki Kapsam

*   **Hukuki Karar Verilmez:** Sistem; bir buluşun yeniliği, patentlenebilirliği veya ihlal durumu hakkında kesin hukuki bağlayıcılığı olan kararlar üretmez.
*   **İstemler (Claims) Kapsam Dışıdır:** İlk sürümde patent istemleri üretilmeyecektir.
*   **LLM Rolü Sınırlıdır:** Büyük dil modelleri kesinlikle patent arama, veri çıkarma, ML eğitimi, ilgililik sıralaması veya kaynak atfı doğrulama aşamalarında kullanılmaz; yalnızca Katman 1'in getirdiği bağlamı metne dökmek için kullanılır.
*   **Ayrık Mühendislik:** Arama motoru ve yeniden sıralama modelleri tamamen yerel scikit-learn ve rank-bm25 altyapısıyla çalışır.

---

## 3. Üç Temel Çalışma Bileşeni (Katmanlı Mimari)

```text
+-----------------------------------------------------------------------------------+
| KATMAN 1: PATENT ARAŞTIRMA & İLGİLİLİK SIRALAMASI                                |
| - Patent doküman havuzunun hazırlanması ve indekslenmesi                         |
| - rank-bm25 (BM25Okapi) ile ilk 20 aday patentin tespiti                         |
| - scikit-learn (TF-IDF + Logistic Regression) ile adayların yeniden sıralanması   |
| - İlk 5 patentin kaynak pasajlarıyla kullanıcıya şeffaf sunumu                   |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| KATMAN 2: RAG VE DÖRT BÖLÜMLÜ PATENT ÖN TASLAĞI                                  |
| - Buluş girdileri + Katman 1 kaynak pasajları = Doğrulanmış RAG Bağlamı          |
| - Hazır LLM ile kontrollü metin üretimi (İstemler HARİÇ 4 Bölüm):                |
|     1. Buluş Özeti                                                               |
|     2. Teknik Alan                                                               |
|     3. Mevcut Teknik (Önceki Teknik)                                             |
|     4. Ayrıntılı Açıklama                                                        |
| - Kullanıcı arayüzünde taslak inceleme ve yerinde düzenleme                      |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| KATMAN 3: BİLİMSEL DEĞERLENDİRME VE KIYASLAMA                                    |
| - Arama Kıyaslaması: Salt BM25 vs. BM25 + Logistic Regression                    |
| - Taslak Kıyaslaması: Salt LLM (LLM-only) vs. RAG Destekli LLM                   |
| - Tutarlılık, terim örtüşmesi ve kaynak atıf hassasiyet metrikleri               |
+-----------------------------------------------------------------------------------+
```

---

## 4. Kullanıcı Veri Akışı

```text
Kullanıcı Buluş Girdilerini Form Üzerinden Yazar
       |
       v
Form Alanları Doğrulanır (validate_invention_data)
  |-- [Hatalı ise] --> Hata Mesajları Gösterilir, State Değişmez
  |
  +-- [Geçerli ise] -> Buluş Bilgileri Session State'e Kaydedilir (current_invention)
                         |
                         v (Buluş Değişti mi?)
                         |-- [Evet] -> Önceki Arama ve Taslak Verileri Temizlenir
                         |-- [Hayır] -> Mevcut Sonuçlar Korunur
                         |
                         v
                 [GELECEK AŞAMALAR]
                         |
                         v
                 BM25 Arama (İlk 20 Aday)
                         |
                         v
                 ML Modeli ile Yeniden Sıralama (İlk 5 Sonuç)
                         |
                         v
                 Kaynaklı Metin Karşılaştırması
                         |
                         v
                 RAG Bağlamı ve Hazır LLM ile 4 Bölümlü Taslak Üretimi
                         |
                         v
                 Kullanıcı Düzenlemesi ve Sonuç İncelemesi
```

---

## 5. Buluş Formu Alanları

Kullanıcıdan toplanan temel alanlar:
1. **Buluş Başlığı (`title`):** Buluşun teknik amacını belirten kısa ve net başlık (`st.text_input`).
2. **Teknik Problem (`technical_problem`):** Buluşun çözmeyi amaçladığı mevcut kısıt veya zorluk (`st.text_area`).
3. **Önerilen Çözüm (`proposed_solution`):** Buluşun teknik probleme getirdiği çözüm yaklaşımı (`st.text_area`).
4. **Temel Bileşenler (`components`):** Buluşu oluşturan teknik parçalar/modüller (virgül veya yeni satırla girilir, `list[str]` olarak parse edilir).
5. **Çalışma Adımları (`working_steps`):** Bileşenlerin birlikte nasıl çalıştığını gösteren operasyonel süreç (`st.text_area`).

---

## 6. Session State Yaklaşımı ve Veri Modeli

Uygulamanın durumu Streamlit `st.session_state` sözlüğü içinde merkezi ve öngörülebilir biçimde yönetilir.

| Durum Anahtarı (Key) | Beklenen Veri Tipi | Başlangıç Değeri | Güncellenme Zamanı | Temizlenme / Sıfırlanma Zamanı | Amacı |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `current_invention` | `dict` veya `None` | `None` | Geçerli form gönderildiğinde (`Kaydet`). | "Yeni Buluş" butonuna tıklandığında. | Aktif olarak işlenen buluşun doğrulanmış verilerini saklar. |
| `current_query` | `str` | `""` | Arama sorgusu oluşturulduğunda. | Buluş değiştiğinde veya yeni buluşta. | BM25 ve ML modeline gönderilecek metin sorgusu. |
| `search_results` | `list[dict]` | `[]` | Katman 1 arama/sıralama tamamlandığında. | Buluş değiştiğinde veya yeni buluşta. | İlk 20 aday ve ilk 5 sıralanmış patent listesi. |
| `comparison_data` | `dict` | `{}` | Karşılaştırma modülü çalıştığında. | Buluş değiştiğinde veya yeni buluşta. | Patent pasajları ile buluş arasındaki metin karşılaştırmaları. |
| `generated_draft` | `dict` veya `None` | `None` | RAG/LLM taslak ürettiğinde. | Buluş değiştiğinde veya yeni buluşta. | Üretilen 4 bölümlü ham taslak metni. |
| `edited_draft` | `dict` veya `None` | `None` | Kullanıcı taslağı düzenlediğinde. | Buluş değiştiğinde veya yeni buluşta. | Kullanıcının arayüzde revize ettiği son taslak. |
| `selected_ranking_method`| `str` | `"BM25"` | Kullanıcı sıralama seçtiğinde. | Yeni buluşta varsayılana döner. | Sıralama tercihi (BM25 vs. BM25+ML). |
| `generation_settings` | `dict` | `{"language": "tr"}` | Ayarlar güncellendiğinde. | Oturum boyunca korunur. | Dil ve üretim hiperparametreleri. |

### `current_invention` Veri Şeması:
```json
{
  "title": "Sensör Tabanlı Sulama Kontrolü",
  "technical_problem": "Gereksiz su tüketiminin azaltılması.",
  "proposed_solution": "Toprak nemine göre sulamanın kontrol edilmesi.",
  "components": [
    "Toprak nem sensörü",
    "Mikrodenetleyici",
    "Solenoid vana"
  ],
  "working_steps": "Sensör verisi okunur ve tanımlanmış eşiklere göre vana kontrol edilir."
}
```

---

## 7. Durum Geçiş Kuralları (State Transition Rules)

1. **Form Gönderimi ve Doğrulama:**
   - Kullanıcı formu doldurup "Buluş Bilgilerini Kaydet" butonuna basar.
   - `validate_invention_data` fonksiyonu zorunlu alanları, boşlukları ve bileşen ayrıştırmasını kontrol eder.
   - Doğrulama başarısız olursa kullanıcıya eksik alanlar bildirilir; `current_invention` eski değerini korur (yanlışlıkla bozulmaz).
2. **Buluş Değişiklik Kontrolü (Invalidation):**
   - Form doğrulandığında, yeni veri mevcut `current_invention` ile içeriksel olarak karşılaştırılır.
   - Eğer buluş bilgileri değişmişse; önceki buluşa ait `search_results`, `comparison_data`, `generated_draft` ve `edited_draft` alanları derhal temizlenir (`None` veya `[]`).
   - Eğer form aynı bilgilerle yeniden kaydedilmişse bağımlı sonuçlar gereksiz yere sıfırlanmaz.
3. **Yeni Buluş Başlatma:**
   - "Yeni Buluş Girişi" eylemi tetiklendiğinde tüm state anahtarları başlangıç değerlerine döndürülür ve form alanları temizlenir.

---

## 8. Streamlit Rerun Güvenliği ve Performans

*   **`st.form` Kullanımı:** Form girdileri `st.form(key="invention_form")` bloğu içinde tutulur. Böylece kullanıcı metin yazarken her tuş vuruşunda uygulamanın baştan sona yeniden çalışması (rerun) engellenir; yalnızca "Kaydet" butonuna basıldığında kontrollü tek bir rerun gerçekleşir.
*   **Durum Koruma (`initialize_session_state`):** Oturum anahtarları yalnızca bir defa (mevcut değillerse) tanımlanır. Sayfa yeniden çalıştığında kullanıcının verileri ezilmez.
*   **Gelecekteki Önbellek Stratejisi:**
    - Patent veri seti ve BM25 indeksi ileride `@st.cache_resource` ile belleğe alınacak, her istekte diskten okunmayacaktır.
    - Henüz model ve veri seti bulunmadığından şu an sahte cache tanımlaması yapılmamıştır.

---

## 9. Gelecekteki Modül Sınırları ve Ayrık Mimari

Uygulama dizin yapısı gelecekteki genişlemeye hazır olacak şekilde tasarlanmıştır:
- `app.py`: Streamlit arayüzü, form yönetimi ve state koordinasyonu.
- `src/retrieval/`: BM25 indeksi oluşturma, metin ön işleme ve ilk aday seçimi.
- `src/ranking/`: TF-IDF vektörleştirme, Logistic Regression model yükleme ve yeniden sıralama.
- `src/drafting/`: RAG bağlamı hazırlama ve hazır LLM entegrasyonu (yalnızca taslak üretimi).
- `src/evaluation/`: Karşılaştırmalı bilimsel test ve değerlendirme metrikleri.

---

## 10. Kaynak Doğrulama ve Güvenlik Sınırları

*   **Yapısal Atıf Doğrulaması:** RAG çıktısında kaynak olarak verilen patent doküman numaraları ve pasajları, Katman 1'in getirdiği gerçek dokümanlarla biçimsel olarak eşleştirilir.
*   **Teknik Hakikat Sınırı:** Yapısal atıfın varlığı, üretilen patent ön taslağındaki teknik iddianın fiili veya bilimsel doğruluğunun mutlak garantisi olarak kabul edilemez.

---

## 11. Veri Gizliliği Prensipleri

*   Kullanıcının girdiği buluş bilgileri hiçbir harici üçüncü taraf servisine veya onaylanmamış API'ye iletilmez.
*   İlk aşamada hiçbir kullanıcı girdisi yerel diske veya kalıcı veritabanına yazılmaz; oturum kapatıldığında bellekten silinir.
*   Kullanıcı verileri sistem loglarına açık metin olarak yazılmaz.

---

## 12. Hata Yönetimi ve Test Stratejisi

*   Arayüz ve iş mantığı (business logic) birbirinden ayrıştırılmıştır. Bileşen temizleme (`clean_components`) ve form doğrulama (`validate_invention_data`) işlevleri bağımsız birim testlerle (`pytest`) doğrulanır.
*   Streamlit `AppTest` API'si ile kullanıcı etkileşimleri, form gönderimleri ve state güncellemeleri otomatik olarak test edilir.
*   Mevcut sistemde çalışmayan hiçbir bileşen için aktif buton veya sahte sonuç gösterilmez.

---

## 13. Mevcut Geliştirme Durumu (PAT-0004 & PAT-0005)

*   **Tamamlanan:** Buluş giriş formu, veri doğrulama iş mantığı, Session State başlangıç ve geçiş kuralları, "Yeni Buluş" sıfırlama mekanizması ve otomatik testler.
*   **Gelecek Aşama:** Patent veri setinin hazırlanması, BM25 indekslemesi, Logistic Regression modelinin eğitilmesi ve RAG boru hattının inşası.

