# Yapay Zekâ Destekli Patent Ön Araştırma ve Patent Taslağı Hazırlama Sistemi

**Proje Sahibi:** Mehmet Demir  
**Kurum:** Kahramanmaraş Sütçü İmam Üniversitesi (KSÜ), Mühendislik ve Mimarlık Fakültesi, Bilgisayar Mühendisliği Bölümü  
**Çalışma Türü:** Lisans Bitirme Projesi (Bireysel Çalışma)  
**Hedef Repository:** `mhmtdmr155/Patent-On-Arastirma-ve-Taslak-Sistemi` (Private)

---

## 1. Proje Amacı ve Hukuki Kapsam Sınırları
Bu bitirme projesinin temel amacı; buluş sahipleri, araştırmacılar ve Ar-Ge mühendisleri için patent ön araştırma sürecini hızlandıran, taranan patent havuzu üzerinden metinsel benzerlik ve ilgililik analizi sunan ve doğrulanmış kaynak pasajlarına dayalı bir patent ön taslağı hazırlayan yapay zekâ destekli bütünleşik bir karar destek sistemi geliştirmektir.

> [!IMPORTANT]
> **Hukuki Kapsam Uyarısı:**
> Bu sistem bir hukuki karar mercii, resmi patent vekili veya patent tescil kurumu değildir. Sistem;
> *   *"Bu buluş kesinlikle yenidir",*
> *   *"Bu buluş kesinlikle patentlenebilir",*
> *   *"Bu patent kesin olarak ihlal edilmiştir"*
> gibi bağlayıcı hukuki veya tescil niteliğinde kararlar **vermez**. Yalnızca Ar-Ge mühendislerine ve araştırmacılara ön araştırma, metinsel benzerlik kıyaslaması ve taslak hazırlama desteği sağlar. Patent istemlerinin (claims) hazırlanması ilk sürümün kapsamı dışındadır.

---

## 2. Üç Temel Çalışma Katmanı

1.  **Katman 1 — Patent Arama, BM25 ve Makine Öğrenimi Yeniden Sıralama:**
    34 patentlik doğrulanmış korpus ve 1504 pasaj chunk'ı üzerinde BM25Okapi leksikal arama motoru ile en ilgili adaylar çıkarılır. İnsan denetimli ilgililik etiketleri (`0`, `1`, `2`) ile eğitilecek scikit-learn tabanlı Logistic Regression modeli, TF-IDF ve metin benzerlik öznitelikleriyle adayları yeniden sıralar. İlk 5 patent şeffaf kaynak pasajları ve atıflarla kullanıcıya sunulur.
2.  **Katman 2 — RAG Destekli Patent Ön Taslağı Üretimi:**
    Kullanıcının girdiği buluş açıklaması ve Katman 1'den elde edilen doğrulanmış patent pasajları bağlam (context) olarak verilerek Retrieval-Augmented Generation (RAG) yaklaşımıyla 4 bölümlü patent ön taslağı üretilir:
    *   *Buluş Özeti*
    *   *Teknik Alan*
    *   *Mevcut Teknik (Önceki Teknik / Arka Plan)*
    *   *Ayrıntılı Açıklama*
3.  **Katman 3 — Bilimsel Değerlendirme ve Kıyaslama:**
    Arama başarımında salt BM25 ile ML reranker modeli; taslak üretiminde ise salt LLM (LLM-only) çıktısı ile RAG destekli LLM çıktısı bilimsel metriklerle kıyaslanır.

---

## 3. Kullanılan Temel Teknolojiler
*   **Programlama Dili:** Python 3.12 (64-bit)
*   **Kullanıcı Arayüzü:** Streamlit
*   **Bilgi Erişimi (Arama Motoru):** rank-bm25 (BM25Okapi) & Unicode Tokenizer
*   **Makine Öğrenimi:** scikit-learn (TF-IDF, Logistic Regression, GroupKFold)
*   **Veri Analizi ve İşleme:** pandas, numpy
*   **Test Altyapısı:** pytest (200 test, %100 başarı)
*   **Sürüm Kontrolü:** Git & GitHub CLI (main dalı, Private repo)

---

## 4. Proje Kurulumu ve Çalıştırma

### 4.1 Sanal Ortam Kurulumu
```powershell
# 1. Sanal ortamı oluşturun ve etkinleştirin
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Bağımlılıkları yükleyin
pip install -r requirements.txt
pip check
```

### 4.2 Veri Geri Yükleme ve Doğrulama
Patent korpusu veri tabanı Git deposu dışında tutulmaktadır. Verilerin geri yüklenmesi veya yeniden üretimi için [docs/DATA_RESTORE.md](file:///docs/DATA_RESTORE.md) kılavuzuna bakın.
Hızlı geri yükleme:
```powershell
.\.venv\Scripts\python.exe scripts/reprocess_corpus_d01.py
```

### 4.3 Uygulamaları Başlatma
*   **Ana Patent Ön Araştırma Uygulaması:**
    ```powershell
    streamlit run app.py
    ```
*   **İnsan Denetimli Etiketleme Aracı:**
    ```powershell
    streamlit run tools/labeling_app.py
    ```

### 4.4 Otomatik Testleri Çalıştırma
```powershell
# Tüm testleri (200 test) çalıştırma:
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 5. Proje Klasör Mimarisi
```text
Patent_Bitirm/
├── .env.example              # Güvenli ortam değişkeni şablonu
├── .gitignore                # Hassas, geçici, veri ve arşiv dışlama kuralları
├── GEMINI.md                 # Antigravity/Gemini kalıcı çalışma kuralları
├── README.md                 # Proje tanıtım ve kılavuz dokümanı
├── app.py                    # Ana Streamlit patent ön araştırma uygulaması
├── data_manifest.json        # 34 patent / 1504 pasaj veri manifestosu
├── sanitized_manifest.txt    # Sanitized doğrulanmış korpus manifestosu
├── requirements.txt          # Doğrudan proje bağımlılıkları
├── requirements-lock.txt     # Kilitli bağımlılık sürümleri
├── artifacts/                # Denetim ve metadata çıktıları (patent_metadata_audit.csv)
├── data/
│   └── annotations/          # queries.csv (etiketleme kuyruğu ve ham veriler Git dışındadır)
├── docs/                     # Sistem mimarisi, kurallar ve teknik raporlar
│   ├── architecture.md       # Sistem mimarisi ve Session State modeli
│   ├── DATA_RESTORE.md       # Veri kurtarma ve yeniden üretim kılavuzu
│   ├── WORKFLOW_RULES.md     # Kalıcı Git ve çalışma akışı protokolü
│   ├── data_quality_report.md # Veri kalite ve tamlık ölçüm raporu
│   ├── domain_and_language_policy.md # İki dilli sorgu politikası
│   ├── ml_preparation_report.md # ML hazırlık ve GroupKFold raporu
│   ├── ml_relevance_design.md   # İlgililik modeli tasarım dokümanı
│   ├── relevance_labeling_guide.md # Etiketleme kuralları kılavuzu
│   └── source_feasibility.md # Patent veri kaynakları fizibilite raporu
├── scripts/                  # Veri işleme, denetim ve yedekleme betikleri
├── src/                      # Temel uygulama modülleri
│   ├── data/                 # Veri boru hattı (schema, chunker, normalizer, family, pipeline)
│   ├── ml/                   # ML hazırlık (dataset, label_store, features, splitting, readiness)
│   └── retrieval/            # BM25 arama motoru ve Unicode tokenizer
├── tests/                    # 14 test dosyası (200 test, %100 PASSED)
└── tools/
    └── labeling_app.py       # Yerel insan denetimli Streamlit etiketleme arayüzü
```

---

## 6. Kalıcı Çalışma Prensipleri
Proje, ChatGPT koordinasyonunda ve Antigravity/Gemini uygulayıcılığında sürdürülmektedir. Ayrıntılı iş akışı kuralları ve gün sonu Git prosedürü için [docs/WORKFLOW_RULES.md](file:///docs/WORKFLOW_RULES.md) belgesini inceleyiniz.
