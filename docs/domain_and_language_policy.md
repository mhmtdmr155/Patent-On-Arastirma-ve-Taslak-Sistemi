# Pilot Teknik Alan ve Dil Politikası Şartnamesi (PAT-0104 & PAT-0105)

Bu belge, **Yapay Zekâ Destekli Patent Ön Araştırma ve Patent Ön Taslağı Hazırlama Sistemi** bitirme projesinde uygulanacak pilot teknik alan sınırlarını (PAT-0104) ve çok dilli (Türkçe/İngilizce) veri ve sorgu işleme politikasını (PAT-0105) tanımlar.

---

## BÖLÜM 1: PİLOT TEKNİK ALAN POLİTİKASI (PAT-0104)

### 1.1 Seçilen Pilot Teknik Alan
Projenin pilot teknik alanı:
> **"Sensör Tabanlı Akıllı Sulama ve Toprak Nemi İzleme Sistemleri"**  
> *(Sensor-Based Smart Irrigation and Soil Moisture Monitoring Systems)*

### 1.2 Teknik Alanın Seçilme Gerekçeleri
1. **Zengin ve Erişilebilir Patent Literatürü:** USPTO ve uluslararası patent veri tabanlarında (Google Patents, Espacenet) bu alanda binlerce açık ve tescilli patent mevcuttur.
2. **Donanım ve Yazılım Kesişimi:** Alan hem fiziksel bileşenleri (sensör probu, vana, solenoid, kontrol devresi) hem de algoritmik/yazılımsal adımları (nem eşik değeri kararı, meteorolojik veri analizi, sulama döngü planlaması) barındırır. Bu durum, bitirme projesinin 5 temel giriş alanını (Başlık, Problem, Çözüm, Bileşenler, Yöntem Adımları) tam olarak test etmek için idealdir.
3. **Net ve İyi Tanımlanmış CPC/IPC Sınıflandırması:** İlgili alan standart patent sınıflarına net bir şekilde dağılmıştır.
4. **Akademik Değerlendirme Uygunluğu:** BM25 ve Logistic Regression ile yeniden sıralama (re-ranking) başarımlarını (MRR, MAP, Precision@5) somut ve doğrulanabilir metriklerle ölçmeye elverişlidir.

### 1.3 Kapsam Sınırları ve Dahil/Hariç Tutma Kriterleri

#### A) Dahil Edilen Konular (Inclusion Criteria):
*   Toprak nemi ölçüm aygıtları (kapasitif, rezistif, ultrasonik, zaman alanlı yansıma -TDR-, yüksek frekanslı dielektrik sensörler).
*   Gömülü ve in-ground (toprak altı) kablosuz sensör düğümleri (solar beslemeli, RF/LoRa/BLE haberleşmeli).
*   Mikrodenetleyici veya mikroişlemci tabanlı sulama kontrol üniteleri ve akıllı vana kontrol devreleri.
*   Meteorolojik veriler (sıcaklık, hava nemi, yağış tahmini, evapotranspirasyon) ile zemin nem verilerini harmanlayan akıllı karar algoritmaları.
*   Çok bölgeli (multi-zone) sulama zamanlaması ve su tasarrufu optimizasyon sistemleri.

#### B) Kapsam Sınırında Olan / Dikkatle Ele Alınacak Konular (Boundary Context):
*   **Bina Temeli ve Çevre Zemin Nem Kontrolü:** Örnek olarak tescilli `US12144295B1` patenti, bina temellerinin zemin nemi hareketlerinden ötürü oturmasını ve çatlamasını önlemek için dinamik nem algılama ve akışkan yönlendirme kullanır. Bu sistem, akıllı nem kontrolü genel şemsiyesinde yer almakla birlikte tarımsal/peyzaj sulamasından uygulama amacı bakımından ayrılır. Pilot veri havuzunda bu tür patentler yer alabilir; ancak sorgu alaka düzeyi (relevance) etiketlemesinde bu ayrım açıkça belgelenmelidir.

#### C) Hariç Tutulan Konular (Exclusion Criteria):
*   Makro ölçekli baraj, hidroelektrik santral ve bölgesel ana isale hatları.
*   Kimyasal gübre veya pestisit sentezleme reaksiyonları (kimya patentleri).
*   Traktör mekanik şanzıman veya içten yanmalı motor donanımları.
*   Tarımsal genetik tohum ıslahı patentleri.

### 1.4 İlgili Temel Patent Sınıflandırma Kodları (CPC/IPC)

| CPC Kodu | Resmi Açıklama / Alan Karşılığı | Projedeki Kullanım Amacı |
| :--- | :--- | :--- |
| **`A01G 25/00`** | Sulama düzenleri, bahçe ve tarla sulama sistemleri | Temel tarımsal sulama mimarisi |
| **`A01G 25/16`** | Sulamanın kontrolü (otomatik, sensörlü, zamanlayıcılı) | Akıllı sulama kontrolörleri ve algoritmaları |
| **`A01G 25/167`**| Meteorolojik veya sensör verilerine duyarlı sulama kontrolü | Evapotranspirasyon ve nem sensörlü sulama |
| **`G01N 33/24`** | Toprak analizi ve toprak nemi tayini | Toprak nem sensörleri ve laboratuvar/arazi probları |
| **`G01N 27/00`** | Elektriksel veya elektrokimyasal yöntemlerle malzeme analizi | Rezistif ve kapasitif toprak nem ölçüm devreleri |
| **`F16K 37/00`** | Vana ve musluklarda kontrol, sinyal ve algılama düzenleri | Akıllı solenoid vana kontrol devreleri |
| **`G05B 19/00`** | Programlanabilir kontrol ve otomasyon sistemleri | Sulama karar modülleri ve ağ geçitleri |

### 1.5 Tek Teknik Alan Sınırlamasının Riskleri ve Sistemin Genellenebilirliği
*   **Risk:** Sistem yalnızca akıllı sulama terminolojisine aşina olursa, diğer mühendislik alanlarındaki patent sorgularında başarım düşebilir.
*   **Mimari Güvence (Generalizability):**
    1. Sistemin arama çekirdeği (`rank-bm25`) ve yeniden sıralama katmanı (`scikit-learn LogisticRegression`), alana özgü sabit kurallara bağımlı değildir; saf istatistiksel ve öznitelik tabanlı (TF-IDF, kelime örtüşmesi, alan ağırlığı) çalışır.
    2. Gelecekte sisteme farklı bir CPC sınıfına ait (örn. B60W - Taşıt Kontrol Sistemleri) patent veri seti yüklendiğinde, kod tabanında hiçbir yapısal değişiklik yapılması gerekmeyecektir.
    3. Bitirme projesi kapsamında tek bir alana odaklanılmasının asıl nedeni, **akademik deney kalitesini**, veri doğruluğunu ve yerel model eğitiminin tutarlılığını garanti altına almaktır.

---

## BÖLÜM 2: DİL POLİTİKASI VE SORGU STRATEJİSİ (PAT-0105)

### 2.1 Veri Tabanı Dili: İngilizce (English)
*   **Gerekçe:** Dünyadaki en geniş ve kapsamlı açık patent havuzları (USPTO, WIPO, EPO) İngilizce yayınlanmaktadır. Teknik patent dili, istem (claim) yapıları ve hukuki terimler küresel standart olarak İngilizce literatürde olgunlaşmıştır.
*   Pilot patent havuzundaki tüm kayıtların `title`, `abstract`, `description` ve `claims` metinleri **İngilizce** olacaktır.

### 2.2 Kullanıcı Arayüzü ve Girdi Dili: Türkçe (Türkçe Arayüz Desteği)
*   Kullanıcı Streamlit arayüzünde buluş özetini, teknik problemi ve bileşenleri Türkçe olarak girebilir (veya isterse doğrudan İngilizce girebilir).
*   Sistem, yerel kullanıcı deneyimini Türkçe olarak desteklerken, arama motorunun doğruluğunu İngilizce teknik korpus üzerinde maksimize edecektir.

### 2.3 Sorgu Dönüştürme ve Arama Stratejisi
Kullanıcı girdisinin arama motoruna (BM25) iletilmesinde **3 katmanlı deterministik strateji** uygulanır:

```
[Kullanıcı Buluş Girdisi (Türkçe/İngilizce)]
                  │
                  ▼
[1. Deterministik Metin Ön İşleme & Temizleme]
(Küçük harfe dönüştürme, noktalama temizliği, stopword filtreleme)
                  │
                  ▼
[2. Teknik Terim ve Anahtar Kelime Çıkarımı (Domain Lexicon Mapping)]
(Deterministik iki dilli terim eşleme: örn. 'toprak nemi' -> 'soil moisture',
 'akıllı sulama' -> 'smart irrigation', 'vana' -> 'valve')
                  │
                  ▼
[3. Deterministik BM25 Sorgusu (English Keywords)]
(Örn: "soil moisture sensor smart irrigation valve controller")
                  │
                  ▼
[BM25 Sıralaması -> Scikit-Learn Re-Ranking (Katman 1 & 2)]
```

### 2.4 KESİN KURAL: Arama ve Sıralama Katmanlarında LLM Yasağı
*   **Kural:** Patent ön araştırmasında (BM25 sorgusu oluşturma, BM25 skorlama, TF-IDF öznitelik çıkarımı ve Logistic Regression reranking) **KESİNLİKLE HİÇBİR LLM (Gemini, Ollama, OpenAI vb.) KULLANILMAYACAKTIR.**
*   **Bilimsel Gerekçe:** Proje yol haritası (v2.0 + v2.1) ve Katman 1/Katman 2 mimari şartnamesi uyarınca, patent arama ve filtreleme adımları tamamen deterministik, hızlı, CPU üzerinde çalışabilir ve bilimsel olarak kıyaslanabilir olmalıdır. Arama adımında LLM kullanılırsa, projenin "kendi geliştirdiğimiz ML modeli ile sıralama" hedefi geçersiz hale gelir.
*   **LLM'nin Yeri (Katman 2):** Hazır LLM yalnızca ve sadece Katman 2'de (RAG destekli Patent Ön Taslağı hazırlama) devreye girecektir. İlk 5 patentin kaynak metinleri ve kullanıcının buluş bilgileri LLM'ye bağlam (context) olarak verilerek 4 bölümlü taslak üretilecektir. Katman 3 ise bilimsel değerlendirme ve kıyaslama katmanıdır.

