# Patent İlgililik Etiketleme Kılavuzu (PAT-0402)

Bu doküman, Yapay Zekâ Destekli Patent Ön Araştırma Sistemi'nde kullanılacak makine öğrenmesi yeniden sıralama modelinin eğitimi ve test edilmesi için **insan denetçiler tarafından yürütülecek etiketleme protokolünü** tanımlar.

---

## 1. Temel İlke ve Hukuki Ayrım

Etiketleme işlemi kesinlikle bir **patentlenebilirlik, yenilik (novelty) veya patent ihlali (infringement)** kararı DEĞİLDİR.

Etiketlemenin yegâne amacı:
> *"Verilen bir teknik arama sorgusu ile patent dokümanının ifşa ettiği teknik çözüm arasındaki mühendislik ilgililik düzeyini 3 dereceli ölçekte nesnel olarak belirlemektir."*

---

## 2. Üç Seviyeli İlgililik Ölçeği

| Etiket Değeri | Seviye Adı | Kısa Tanım | Karar Kriteri |
|:---:|---|---|---|
| **0** | **İlgisiz** *(Irrelevant)* | Teknik olarak alakasız veya tesadüfi kelime eşleşmesi | Patent, sorgunun çözmek istediği teknik problemi ele almaz. Sorgudaki kelimeler patentte sadece yan unsur, genel benzetme veya arka plan cümlesi olarak geçmektedir. |
| **1** | **Kısmen İlgili** *(Partially Relevant)* | Genel alan veya alt bileşen benzerliği | Patent aynı geniş teknik alandadır (örn. sulama kontrolü) veya sorgudaki bileşenlerden birini (örn. kablosuz ağ geçidi) içerir; ancak sorgunun odaklandığı özgün mekanizmayı (örn. rezonans frekanslı nem ölçümü) doğrudan sunmaz. |
| **2** | **Doğrudan İlgili** *(Directly Relevant)* | Birebir teknik odak ve temel mekanizma örtüşmesi | Patent, sorguda belirtilen teknik problemi ve temel çözüm mekanizmasını doğrudan tarifnamesinde veya özetinde ayrıntılı olarak açıklamaktadır. |

---

## 3. Karar Verirken Ayrılması Gereken Üç Durum

Bir denetçi etiket verirken şu üç olguyu birbirinden kesinlikle ayırmalıdır:

1. **Yüzeysel Kelime Örtüşmesi (Lexical Overlap):**
   - Bir kelimenin patentte geçmesi o patentin ilgili olduğunu kanıtlamaz.
   - *Örnek:* "sensor" kelimesi US11064664B2'de geçer; ancak patent nem sensörünün kendisini değil, bulut tabanlı vana kontrol algoritmasını anlatır. Bu durum etiketi 2 yapmaz.
2. **Teknik İşlev Benzerliği (Functional Equivalence):**
   - Patent farklı kelimeler kullansa bile aynı fiziksel ilkeyi uyguluyorsa ilgilidir.
   - *Örnek:* "resonant RLC circuit" sorgusu için US9804113B2'nin LC tank devresiyle empedans ölçümü yapması işlevsel olarak doğrudan ilgilidir (Etiket: 2).
3. **Uygulama Alanı Benzerliği (Domain Context):**
   - Tıbbi bir alanda sıvı ölçümü yapan bir sensör, tarımsal sulama sorgusu için kısmen ilgili (1) veya ilgisiz (0) olarak sınıflandırılmalıdır.

---

## 4. Somut Örnekler ve Karar Gerekçeleri

### Örnek 1: Sorgu = `"series RLC circuit"`
- **US9804113B2 (Soil moisture sensor):**
  - *İçerik:* Seri RLC rezonans devresi ve frekans kayması ile toprak dielektrik katsayısı ölçümü.
  - **Etiket: 2 (Doğrudan İlgili)**
  - *Gerekçe:* Sorgunun teknik özü patentin ana buluş konusudur.
- **US7836910B2 (Soil moisture sensor and controller):**
  - *İçerik:* Kapasitif sensör ve zamanlayıcı devresi; ancak seri RLC rezonans mimarisi ana odak değildir.
  - **Etiket: 1 (Kısmen İlgili)**
  - *Gerekçe:* Toprak nem sensörüdür fakat rezonans devresi yerine osilatör/zamanlama kullanır.
- **US11064664B2 (Methods and systems for irrigation control):**
  - *İçerik:* Sulama yönetim sunucusu ve vana kontrolörleri. RLC devresi açıklanmaz.
  - **Etiket: 0 (İlgisiz)**
  - *Gerekçe:* Teknik odak tamamen ağ ve yazılım mimarisidir.

### Örnek 2: Sorgu = `"remote monitoring gateway"`
- **US11064664B2 (Methods and systems for irrigation control):**
  - *İçerik:* Baz istasyonu/ağ geçidi (gateway), kablosuz düğümler ve uzak sunucu iletişimi.
  - **Etiket: 2 (Doğrudan İlgili)**
- **US9241451B2 (Methods and systems for irrigation control):**
  - *İçerik:* Kablosuz ağ düğümleri ve baz istasyonu ile uzaktan izleme.
  - **Etiket: 2 (Doğrudan İlgili)**
- **US9804113B2 (Soil moisture sensor):**
  - *İçerik:* Yalnızca tekil sensör probu. Ağ geçidi veya uzak sunucu bağlantısı içermez.
  - **Etiket: 0 (İlgisiz)**

---

## 5. İnsan Değerlendirme Protokolü (Human Review Protocol)

1. **Bağımsız İnceleme:** Etiketler alanında uzman veya eğitim almış insan denetçiler tarafından verilir.
2. **Sentetik Etiket Yasağı:** Model eğitiminde LLM veya yapay zekâ tarafından otomatik üretilen uydurma etiketler "doğrulanmış insan etiketi" sayılamaz.
3. **Başlangıç Durumu:** Hazırlanan etiketleme tablosunda (`data/annotations/labeling_queue.csv`) `human_relevance_label` sütunu başlangıçta **BOŞ** bırakılır ve `review_status` değeri `PENDING_HUMAN_REVIEW` olarak atanır.

