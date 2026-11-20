# Patent Veri Kaynakları Karşılaştırmalı Fizibilite Raporu

Bu belge; bitirme projesinde (Katman 1 ve Katman 2) kullanılacak 50–200 patentlik gerçek patent veri havuzunun oluşturulması amacıyla incelenen açık, resmi ve akademik patent veri kaynaklarının teknik fizibilite analizini sunar.

---

## 1. Araştırmanın Amacı ve Kapsamı
Projenin amacı doğrultusunda, patent ön araştırması (BM25 arama motoru), scikit-learn Logistic Regression ile yeniden sıralama ve RAG ile dört bölümlü patent ön taslağı hazırlama adımlarında **gerçek patent metinleri** kullanılacaktır. 

Sistemin ihtiyaç duyduğu zorunlu veri alanları:
1. Yayın / Patent Numarası (`patent_id` / `publication_number`)
2. Buluş Başlığı (`title`)
3. Buluş Özeti (`abstract`)
4. Ayrıntılı Açıklama (`description`) veya Mevcut Teknik (`background`)
5. Patent Sınıflandırma Kodları (CPC / IPC)
6. Başvuru / Yayın Tarihleri (`filing_date`, `publication_date`)

---

## 2. İncelenen Veri Kaynakları ve Resmi Erişim Adresleri

1. **HUPD (Harvard USPTO Patent Dataset):**
   - Resmi Web Sitesi: `https://patentdataset.org/`
   - Hugging Face Deposu: `https://huggingface.co/datasets/HUPD/hupd`
2. **USPTO Bulk Data Storage System (BDSS) / XML:**
   - Açık Veri Portalı: `https://data.uspto.gov/bulkdata/datasets`
   - XML Kaynakları: `https://www.uspto.gov/learning-and-resources/xml-resources`
3. **PatentsView (USPTO Destekli Platform):**
   - Resmi Web Sitesi: `https://patentsview.org/`
   - API Dokümantasyonu: `https://search.patentsview.org/docs/`
4. **Google Patents Public Datasets / BigQuery:**
   - GitHub Arşivi: `https://github.com/google/patents-public-data`
   - BigQuery Dokümanı: `https://docs.cloud.google.com/bigquery/public-data`
   - Web Arayüzü: `https://patents.google.com/`

---

## 3. Karşılaştırmalı Değerlendirme Tablosu

| Kriter / Özellik | HUPD (Harvard USPTO) | USPTO Resmi XML (BDSS) | PatentsView API | Google Patents (BigQuery) |
| :--- | :--- | :--- | :--- | :--- |
| **Kurum / Sağlayıcı** | Harvard Üniversitesi / USPTO verisi | ABD Patent ve Marka Ofisi (USPTO) | USPTO & Amerikan Girişimcilik Enstitüsü | Google Cloud / Google Patents |
| **Erişim Yöntemi** | Hugging Face Datasets / Doğrudan İndirme | HTTPS Doğrudan İndirme (ZIP/TAR) | REST API (`/api/v1/patent/`) / Toplu TSV | Google BigQuery SQL / Web |
| **Kimlik Doğrulama / API Key** | Gerektirmez (HF API veya doğrudan URL) | **ÖNEMLİ KISIT:** USPTO 1 Mayıs 2026 duyurusuna göre 18 Haziran 2026 itibarıyla Open Data Portal için kullanıcı kaydı zorunlu hale gelmektedir (BDSS API'leri anahtar istemektedir). | **ZORUNLU API KEY** (`X-Api-Key`) | **GCP Hesabı & Proje Zorunlu** |
| **Maliyet / Ücret Durumu** | Ücretsiz (Açık Akademik) | Ücretsiz (Kamu Malı - Public Domain) | Ücretsiz (Kayıt ve anahtar şartı) | Sorgu kotası aşılırsa ücretli (1 TB/ay kota) |
| **Lisans Türü** | **ÇELİŞKİLİ:** Web sitesinde `CC BY-NC-SA 4.0`, Hugging Face'te `CC BY-SA 4.0` | Kamu Malı (US Public Domain) | CC BY 4.0 / Açık Kamu Verisi | Veri açık, altyapı ticari GCP kurallarına tabi |
| **Dosya Biçimleri** | JSON / Arrow (HF Dataset) / Tar | XML (W3C Patent Grant DTD / Schema) | JSON (API) / TSV (Toplu veri) | BigQuery Tabloları / SQL çıktıları |
| **Tam Metin Kapsamı** | **VAR** (`abstract`, `description`, `background`, `claims`) | **VAR** (XML etiketleri içinde tam metin) | API'de **YOK** (Yalnızca özet/başlık/istem; açıklama dev TSV'lerde) | **VAR** (`publications` tablosunda tam metin) |
| **İndirme / Arşiv Boyutu** | **ÇOK BÜYÜK:** `all-years.tar` 61,8 GB (açılmışı >360 GB); `sample` 388 MB | **BÜYÜK:** Haftalık arşivler 100–500 MB (Zipli) | API: Hafif JSON; Toplu TSV: 10–50 GB | Sorgu bazlı gigabayt/terabayt tarama |
| **Teknik Kapsam / Alan** | USPTO başvuruları (2004–2018) | Tüm yayınlanan patentler (Haftalık güncel) | ABD patentleri (1976–günümüz) | Dünya geneli (ABD, EPO, WIPO vb.) |
| **Öğrenci Projesi Uygunluğu** | **Koşullu / Riskli** (Dev dosya boyutu, lisans çelişkisi) | **Orta / Uygulanabilir** (XML parse gerektirir, hafif haftalık batch) | **Düşük** (API key zorunlu, tam açıklama yok) | **Düşük / Riskli** (GCP hesabı, billing riski, arşivlenmiş repo) |

---

## 4. Detaylı Kaynak Analizleri ve Riskler

### A) HUPD (Harvard USPTO Patent Dataset) Fizibilitesi
*   **Boyut Riski:** HUPD deposundaki `all-years.tar` arşivi **61,8 GB** sıkıştırılmış boyuta sahiptir ve yerel diske açıldığında **360 GB'ın üzerinde** alan gerektirmektedir. Mevcut geliştirme makinesinde serbest disk alanı ~132 GB olduğundan tam veri setinin indirilmesi imkânsızdır ve sistem çökmesine yol açar.
*   **Örnek (Sample) Boyutu:** Resmi Hugging Face deposundaki en küçük alt küme olan `sample-jan-2016.tar.gz` (Ocak 2016 başvuruları) **388 MB** sıkıştırılmış boyuttadır. Bu görevdeki 2 MB tekil / 10 MB toplam indirme sınırını aşmaktadır.
*   **Lisans Çelişkisi:** HUPD resmi sitesinde (`patentdataset.org`) veri setinin **CC BY-NC-SA 4.0** (Ticari Olmayan) lisansıyla korunduğu belirtilirken, Hugging Face reposunda **CC BY-SA 4.0** etiketi yer almaktadır. Lisans şartlarındaki bu uyumsuzluk resmi olarak netleşene kadar HUPD'nin ticari/açık yayın uyumluluğu belirsiz kabul edilmelidir.
*   **Veri Alanı Zenginliği:** 34 yapılandırılmış alan sunması ve `background`, `description`, `abstract` alanlarını temiz metin olarak barındırması en büyük avantajıdır.

### B) USPTO Resmi Bulk Data (BDSS / XML)
*   **Lisans:** ABD hükümet eseri olarak kamu malıdır (Public Domain). Hiçbir telif veya ticari kısıt içermez.
*   **Erişim ve Kritik Güncel Kısıt:** USPTO tarafından 1 Mayıs 2026 tarihinde yapılan resmî duyuruya (`https://www.uspto.gov/about-us/news-updates/uspto-open-data-portal-require-registration-access-beginning-june-18-2026`) göre, 18 Haziran 2026 tarihinden itibaren Open Data Portal üzerinden verilere erişim için **zorunlu kullanıcı kaydı ve hesap girişi** gerekecektir. Ayrıca yeni BDSS API'leri API anahtarı talep edebilmektedir.
*   **Proje Kısıtı Uyumu:** Güvenlik kurallarımız gereği sisteme API anahtarı eklenmesi veya hesap açılması yasak olduğundan, doğrudan Open Data Portal API'leri yerine herkese açık kamu aynaları (Google Patents kamu HTML görünümü) veya kimlik doğrulamasız doğrudan indirme arşivleri tercih edilmelidir.
*   **Format:** XML (XML formatı başlık, özet, buluşun arka planı -background- ve ayrıntılı açıklama etiketlerini kesin ve standart biçimde içerir).
*   **Risk:** Haftalık tek bir arşiv 100 MB ile 500 MB arasında değişebilir. Tüm haftayı indirmek yerine, Python akışlı (streaming) okuma ile sadece ilk 50–100 patentin XML dokümanını ayıklamak mümkündür.

### C) PatentsView API
*   **API Değişikliği:** PatentsView platformu yakın zamanda API v1 mimarisine geçmiş ve **zorunlu API anahtarı (`X-Api-Key`)** uygulaması başlatmıştır.
*   **Eksik Veri:** REST API sorguları (`patent_title`, `patent_abstract`, `patent_date`) sağlamakta ancak **ayrıntılı açıklama (detailed description / background)** alanını API yanıtında döndürmemektedir. Ayrıntılı açıklama yalnızca onlarca gigabaytlık toplu TSV (`g_detail_desc_text`) dosyalarında mevcuttur. Bu nedenle tek başına API olarak yetersizdir.

### D) Google Patents / BigQuery
*   **Altyapı:** `patents-public-data:patents.publications` tablosu dünyanın en geniş patent verisini sunar.
*   **Arşivlenmiş Repo:** Örnek sorguları içeren `google/patents-public-data` GitHub deposu arşivlenmiş ve salt-okunur yapılmıştır.
*   **Maliyet ve Güvenlik Riski:** BigQuery sorguları Google Cloud hesabı, faturalandırma (billing) profili ve kimlik doğrulama gerektirir. Öğrenci bitirme projesinde beklenmedik bulut maliyetlerine yol açma riski bulunmaktadır.

---

## 5. Küçük Ölçekli Gerçek Patent Örnekleri (Doğrulanmış 8 Pilot Kayıt)

Projenin pilot araştırma alanı olarak ele alınan *Akıllı Sulama, Toprak Nemi ve Sensör Sistemleri* alanında kamuya açık Google Patents ve USPTO kayıtlarından `scripts/patent_source_probe.py` aracıyla canlı olarak doğrulanan 8 gerçek patent kaydı aşağıda sunulmuştur. İlk 4 kaydın başvuru numaraları PAT-0006-D01 kapsamında resmi kayıtlarla birebir örtüşecek şekilde düzeltilmiştir. Detaylı teknik envanter için ayrıca bkz: `docs/patent_sample_audit.md`.

### Örnek 1: US 11,457,576 B2
*   **Yayın Numarası (Publication No):** US11457576B2
*   **Başvuru Numarası (Application No):** US 16/690,109 *(PAT-0006-D01 ile düzeltildi; önceki hatalı değer: US 16/689,451)*
*   **Buluş Başlığı (Title):** Intelligent irrigation system
*   **Başvuru Tarihi:** 2019-11-20 | **Tescil/Yayın Tarihi:** 2022-10-04
*   **Kaynak URL:** `https://patents.google.com/patent/US11457576B2/en`
*   **Doğrulanan Alanlar:** Başlık, başvuru numarası, başvuru tarihi, tescil tarihi, özet, CPC sınıfları (`A01G25/16`).
*   **Teknik Odak:** Sensörlerden toplanan meteorolojik ve nem verilerine göre sulama vanalarının otomatik kontrolü.

### Örnek 2: US 11,674,944 B2
*   **Yayın Numarası (Publication No):** US11674944B2
*   **Başvuru Numarası (Application No):** US 17/725,836 *(PAT-0006-D01 ile düzeltildi; önceki hatalı değer: US 17/726,052)*
*   **Buluş Başlığı (Title):** In-ground wireless soil moisture sensor
*   **Başvuru Tarihi:** 2022-04-21 | **Tescil/Yayın Tarihi:** 2023-06-13
*   **Kaynak URL:** `https://patents.google.com/patent/US11674944B2/en`
*   **Doğrulanan Alanlar:** Başlık, başvuru numarası, tarihler, kablosuz toprak altı sensör donanım yapısı, CPC sınıfları (`G01N33/24`).
*   **Teknik Odak:** Ultrasonik algılayıcılar ve solar kapaklı kablosuz toprak altı nem sensörü.

### Örnek 3: US 8,671,969 B2
*   **Yayın Numarası (Publication No):** US8671969B2
*   **Başvuru Numarası (Application No):** US 13/336,709 *(PAT-0006-D01 ile düzeltildi; önceki hatalı değer: US 13/336,448)*
*   **Buluş Başlığı (Title):** Soil moisture sensor and controller
*   **Başvuru Tarihi:** 2011-12-23 | **Tescil/Yayın Tarihi:** 2014-03-18
*   **Kaynak URL:** `https://patents.google.com/patent/US8671969B2/en`
*   **Doğrulanan Alanlar:** Başlık, başvuru numarası, tarihler, vana kesme kontrol devresi, CPC sınıfları (`F16K37/00`, `G01N27/00`).
*   **Teknik Odak:** Toprak içerisine gömülen entegre nem sensörü ve vana kontrol anahtarı.

### Örnek 4: US 12,144,295 B1
*   **Yayın Numarası (Publication No):** US12144295B1
*   **Başvuru Numarası (Application No):** US 18/206,695 *(PAT-0006-D01 ile düzeltildi; önceki hatalı değer: US 18/206,861)*
*   **Buluş Başlığı (Title):** Smart irrigation system
*   **Başvuru Tarihi:** 2023-06-07 | **Tescil/Yayın Tarihi:** 2024-11-19
*   **Kaynak URL:** `https://patents.google.com/patent/US12144295B1/en`
*   **Doğrulanan Alanlar:** Güncel patent tescili, başvuru numarası, başlık, dinamik debi ve nem sensör kontrolleri.
*   **Teknik Odak ve Kapsam Ayrımı:** Bina temeli ve çevre zemin nem kontrolü (*Building foundation and landscaping moisture control*). Bu buluş, bina temellerinin toprak nem seviyelerindeki dalgalanmalar nedeniyle çatlamasını önlemek amacıyla nem ve kirlilik sensörlerine göre suyu dinamik yönlendirir. Doğrudan tarımsal sulama olmamakla birlikte nem algılama ve akıllı vana kontrolü kesişimindedir; alt alan sınırlandırmalarında bu ayrım dikkate alınmalıdır.

### Örnek 5: US 11,064,664 B2
*   **Yayın Numarası (Publication No):** US11064664B2
*   **Başvuru Numarası (Application No):** US 16/933,594
*   **Buluş Başlığı (Title):** Methods and systems for irrigation control
*   **Başvuru Tarihi:** 2020-07-20 | **Tescil/Yayın Tarihi:** 2021-07-20
*   **Kaynak URL:** `https://patents.google.com/patent/US11064664B2/en`
*   **Resmi Özet (Verbatim Abstract):** A wireless system is provided for monitoring environmental, soil, or climate conditions and/or controlling irrigation or climate control systems at an agricultural or landscape site. In some embodiments, the wireless system includes at least one wireless control nodes for monitoring environmental, soil, or climate conditions and/or for controlling one or more irrigation or climate control systems at the site. The wireless system also includes a web based application or a cell phone application and a gateway coupled to a communications network. The communications network is configured to transfer data to and receive remote control commands or queries from an end-user.
*   **Teknik Odak:** Tarımsal/peyzaj sahasında kablosuz sensör düğümleri, ağ geçidi ve web/mobil uygulama ile uzaktan sulama ve çevre izleme sistemi.
*   **Patent Ailesi:** `US9241451B2` ile doğrudan devam (continuation) soyundadır (TR 2008/05998 ortak öncelikli).

### Örnek 6: US 9,241,451 B2
*   **Yayın Numarası (Publication No):** US9241451B2
*   **Başvuru Numarası (Application No):** US 14/466,469
*   **Buluş Başlığı (Title):** Methods and systems for irrigation control
*   **Başvuru Tarihi:** 2014-08-22 | **Tescil/Yayın Tarihi:** 2016-01-26
*   **Kaynak URL:** `https://patents.google.com/patent/US9241451B2/en`
*   **Resmi Özet (Verbatim Abstract):** A wireless system is provided for monitoring environmental, soil, or climate conditions and/or controlling irrigation or climate control systems at an agricultural or landscape site. In some embodiments, the wireless system includes at least one wireless nodes for monitoring environmental, soil, or climate conditions and/or for controlling one or more irrigation or climate control systems at the site. The wireless system also includes a server computer system located remotely from the site. The server computer system is coupled to the node/s over a communications network for receiving data from and controlling operation of the node/s. The server computer system is also coupled to a device operated by an end-user over a communications network for transmitting the data to and receiving remote control commands or queries from the end-user.
*   **Teknik Odak:** Uzak sunucu, kablosuz düğümler ve iletişim ağı üzerinden tarımsal çevre koşullarını izleme ve sulama sistemini uzaktan kontrol etme mimarisi.
*   **Patent Ailesi:** `US11064664B2`'nin ana continuation kaynağıdır.

### Örnek 7: US 7,836,910 B2
*   **Yayın Numarası (Publication No):** US7836910B2
*   **Başvuru Numarası (Application No):** US 11/097,061
*   **Buluş Başlığı (Title):** Soil moisture sensor and controller
*   **Başvuru Tarihi:** 2005-03-31 | **Tescil/Yayın Tarihi:** 2010-11-23
*   **Kaynak URL:** `https://patents.google.com/patent/US7836910B2/en`
*   **Resmi Özet (Verbatim Abstract):** Moisture sensor devices and methods associated with operation of the moisture sensor devices are disclosed herein. One embodiment includes a moisture sensor to be placed in soil comprising a sensor circuit comprising a probe; and a controller circuit coupled to the sensor circuit; the controller circuit adapted to determine a moisture level of the soil based on an output of the sensor circuit, to compare the moisture level of the soil to a threshold moisture level, and to output a signal to interrupt operation of a valve of an irrigation system when the moisture level is above the threshold moisture level.
*   **Teknik Odak:** Doğrudan vana solenoid hattına seri bağlanan ve eşik aşımında sulamayı donanımsal kesen prob devresi.
*   **Patent Ailesi:** `US8671969B2`'nin doğrudan üst başvurusudur (Dresselhaus et al. soyu).

### Örnek 8: US 9,804,113 B2
*   **Yayın Numarası (Publication No):** US9804113B2
*   **Başvuru Numarası (Application No):** US 14/715,352
*   **Buluş Başlığı (Title):** Soil moisture sensor
*   **Başvuru Tarihi:** 2015-05-18 | **Tescil/Yayın Tarihi:** 2017-10-31
*   **Kaynak URL:** `https://patents.google.com/patent/US9804113B2/en`
*   **Resmi Özet (Verbatim Abstract):** A soil moisture sensor includes a capacitive probe configured to be inserted into soil, a series RLC circuit electrically coupled to the capacitive probe, a microcontroller configured to determine the capacitance value of the soil and determine the moisture content of the soil from the capacitance value of the soil.
*   **Teknik Odak:** Toprağa daldırılan kapasitif prob, seri RLC devresi ve mikrodenetleyici ile toprak sığasını ölçerek nem miktarını belirleyen donanım.
*   **Patent Ailesi:** Bağımsız başvuru (App US14/715,352).

---

## 6. Önerilen Kaynak Stratejisi ve Alternatif Plan

### Öneri 1 (En Güçlü Aday — USPTO Bulk XML Streaming veya Tek Hafta Sınırlı Filtreleme)
*   **Gerekçe:** Kamu malıdır (lisans riski sıfır), ücretsizdir, API anahtarı istemez, doğrudan tam metin (başlık, özet, background, description) içerir.
*   **Uygulama:** Tek bir haftalık XML arşivinden (veya USPTO BDSS API üzerinden) yalnızca belirlenen CPC sınıfına (örn. A01G - Tarım / Sulama) ait 50–100 patent çekilerek yerel JSON/Parquet havuzuna dönüştürülür.

### Alternatif Plan (HUPD Sample Seçici Çıkarım)
*   **Gerekçe:** Temizlenmiş hazır JSON alanları içerir.
*   **Kısıt:** Lisans çelişkisi resmi olarak teyit edilmeli ve 388 MB'lık `sample-jan-2016` arşivinden yalnızca hedef alana ait 50 patent izole edilmelidir.

### Nihai Karar Durumu
*   Bu rapordaki değerlendirmeler bir **teknik öneri ve fizibilite raporudur**.
*   Nihai veri kaynağı seçimi, teknik alan tercihi ve veri dili kararı ChatGPT'nin bağımsız denetimi ve onayı sonrasında (PAT-0104 / PAT-0107 aşamalarında) kesinleştirilecektir.

