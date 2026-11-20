# Patent Korpusu Veri Kurtarma ve Yeniden Üretim Kılavuzu (DATA RESTORE)

Bu belge, **Yapay Zekâ Destekli Patent Ön Araştırma ve Patent Taslağı Hazırlama Sistemi** projesinde kullanılan 34 patentlik korpus verisinin mimarisini, Git dışı tutulma gerekçesini, yerel yedekten geri yükleme adımlarını ve sıfırdan yeniden üretim (reproducibility) prosedürünü açıklar.

---

## 1. Veri Depolama Politikası ve Git İzolasyonu

Proje kapsamında yer alan patent verileri üç katmandan oluşur:
1. **data/raw/ (Ham Veri):** Google Patents genel ayna sunucusundan indirilen 34 adet resmi HTML dosyası (~22 MB).
2. **data/processed/ (İşlenmiş Veri):** Bölüm duyarlı normalize edilmiş `patents.jsonl` (34 kayıt, ~2.75 MB) ve `chunks.jsonl` (1504 pasaj, ~2.68 MB).
3. **data_manifest.json (Veri Bütünlük Manifestosu):** Tüm işlenmiş ve ham dosyaların SHA-256 özetleri, kayıt sayıları ve doğrulama durumları.

### Neden Git Deposuna Dahil Edilmemiştir?
*   **Depo Boyutu ve Performansı:** 26+ MB ham HTML ve JSONL verilerinin her revizyonda Git geçmişinde birikmesi depoyu şişirir.
*   **Veri Mühendisliği Ayrımı:** Kaynak kod ile veri havuzunun ayrılması (Separation of Concerns).
*   **Yeniden Üretilebilirlik Garantisi:** Kod tabanı (`src/data/pipeline.py`), herhangi bir ortamda ham HTML dosyalarından veya genel ayna sunucusundan veri kümesini %100 deterministik olarak yeniden üretebilmektedir.

---

## 2. Mevcut Yerel Yedekleme Konumu

Mevcut 34 patentlik doğrulanmış korpus, proje çalışma alanının dışında bağımsız yerel yedek konumuna kopyalanmıştır:

*   **Yerel Yedekleme Dizini:** `C:\Users\mehme\Desktop\Patent_Bitirm_Data_Backup`
*   **Yedeklenen Dosya Sayısı:** 38 dosya (34 raw HTML + `raw_manifest.json` + `patents.jsonl` + `chunks.jsonl` + `data_manifest.json`)
*   **Toplam Boyut:** 27,663,077 bayt (26.38 MB)
*   **Bütünlük Manifestosu:** `C:\Users\mehme\Desktop\Patent_Bitirm_Data_Backup\backup_manifest.json`

> [!WARNING]
> **Felaket Kurtarma Uyarısı:** Aynı bilgisayardaki yerel yedek, tek başına tam bir felaket kurtarma (disaster recovery) güvencesi sağlamaz. Disk arızası riskine karşı verilerin ikinci bir bağımsız harici diske veya güvenli bulut alanına (Google Drive / OneDrive) arşivlenmesi önerilir.

---

## 3. Veri Geri Yükleme Yöntemleri

### Yöntem A: Yerel Yedekten Hızlı Geri Yükleme (Önerilen)
Yerel yedek klasörü mevcutsa aşağıdaki PowerShell komutuyla saniyeler içinde geri yükleyebilirsiniz:

```powershell
# Proje kök dizininde çalıştırın:
Copy-Item -Path "C:\Users\mehme\Desktop\Patent_Bitirm_Data_Backup\data\*" -Destination "data\" -Recurse -Force
Copy-Item -Path "C:\Users\mehme\Desktop\Patent_Bitirm_Data_Backup\data_manifest.json" -Destination "data_manifest.json" -Force
```

### Yöntem B: Ham HTML'lerden Deterministik Yeniden Üretim
Eğer `data/raw/` klasöründe HTML dosyaları mevcutsa, işlenmiş JSONL dosyaları ve pasaj indeksleri boru hattı üzerinden doğrudan üretilir:

```powershell
.\.venv\Scripts\python.exe scripts/reprocess_corpus_d01.py
```

Bu işlem:
1. 34 patentin tamamını okur.
2. `PatentRecord` ve `PatentChunk` şemalarına göre doğrular.
3. 28 sızıntısız değerlendirme grubunu (`evaluation_group_id`) atar.
4. `data/processed/patents.jsonl` (34 kayıt) ve `data/processed/chunks.jsonl` (1504 pasaj) dosyalarını yazar.
5. `data_manifest.json` ve `docs/data_quality_report.md` dosyalarını günceller.

### Yöntem C: Sıfırdan Google Patents Üzerinden Yeniden Çekme
Ham HTML dosyaları dahi bulunmadığında, `scripts/patent_source_probe.py` betiği polite delay (1.0 sn gecikme) ve MAX_DOWNLOAD_BYTES + 1 kesilme korumasıyla 34 patenti indirir:

```powershell
.\.venv\Scripts\python.exe scripts/patent_source_probe.py --download-all
.\.venv\Scripts\python.exe scripts/reprocess_corpus_d01.py
```

---

## 4. Bütünlük ve Test Doğrulaması

Veri geri yüklendikten sonra bütünlük kontrolü ve regresyon testleri aşağıdaki komutlarla çalıştırılır:

```powershell
# 1. Manifest ve SHA-256 doğrulama testleri
.\.venv\Scripts\python.exe -m pytest tests/test_data_integrity.py tests/test_data_pipeline.py -v

# 2. Tüm proje testleri (200 test)
.\.venv\Scripts\python.exe -m pytest -v
```

Tüm testler `%100 PASSED` sonucunu vermelidir.
