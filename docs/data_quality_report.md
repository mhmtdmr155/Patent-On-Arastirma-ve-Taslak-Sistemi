# Gerçek Patent Veri Havuzu Kalite ve Doğrulama Raporu (PAT-0208)

Bu rapor, **data/processed/patents.jsonl** ve **data/processed/chunks.jsonl** dosyalarında yer alan gerçek patent kayıtlarının ve pasaj parçalarının somut ölçümlerini belgeler.

---

## 1. Genel Korpus Özeti

*   **Toplam Gerçek Patent Kaydı:** 34
*   **Tam Metin Doğrulanan (FULL_TEXT_VERIFIED):** 34
*   **Özet Doğrulanan (ABSTRACT_VERIFIED):** 0
*   **Başarısız Kayıt (FAILED):** 0
*   **Tekrarlanan Yayın Numarası Sayısı:** 0 (Yasak ve engellendi)
*   **Başarısız Kaynak Erişimi:** 0

---

## 2. Alan Bazlı Tamlık Ölçümleri

| Alan Adı | Mevcut Kayıt Sayısı | Eksik Kayıt Sayısı | Tamlık Oranı (%) |
| :--- | :---: | :---: | :---: |
| **Buluş Başlığı (title)** | 34 | 0 | 100.0% |
| **Resmi Özet (abstract - verbatim)** | 34 | 0 | 100.0% |
| **Ayrıntılı Açıklama (description)** | 34 | 0 | 100.0% |
| **Mevcut Teknik / Arka Plan (background)** | 34 | 0 | 100.0% |
| **CPC Sınıflandırma Kodları (cpc_codes)** | 34 | 0 | 100.0% |
| **IPC Sınıflandırma Kodları (ipc_codes)** | 34 | 0 | 100.0% |
| **Başvuru Numarası (application_number)** | 34 | 0 | 100.0% |
| **Patent Ailesi / Devam Bağlantısı** | 9 | 25 | 26.5% |
| **Sınırda Teknik Alan Kaydı (Bina Temeli)** | 1 | - | - |

---

## 3. Bölüm Duyarlı Pasaj (Chunk) İstatistikleri

*   **Toplam Pasaj (Chunk) Sayısı:** 1504
*   **Ortalama Pasaj Uzunluğu:** 266.0 kelime
*   **Boş Pasaj Sayısı:** 0
*   **Bölümlere Göre Pasaj Dağılımı:**
    *   `TITLE`: 34 pasaj
    *   `ABSTRACT`: 34 pasaj
    *   `BACKGROUND`: 76 pasaj
    *   `DESCRIPTION`: 1360 pasaj

---

## 4. Doğrulanmış Patent Ailesi İlişkileri

1.  **Sulama Kontrolü ve Kablosuz İzleme Ailesi (Ersavas et al. / Rain Bird Corp):**
    *   Üyeler: `US8849461B2`, `US9241451B2`, `US10716269B2`, `US11064664B2`
    *   İlişki Türü: Doğrulanmış devam başvurusu zinciri (`continuation_of`, `continuation_lineage`, `has_continuation`)
    *   Google Patents Aile ID: `41495413`
    *   Kanıt: US8849461B2 (App 13/844,248) -> US9241451B2 (App 14/466,469) -> US10716269B2 (App 16/452,397 via US10362739) -> US11064664B2 (App 16/933,594); ortak rüçhan TR 2008/05998.

2.  **Toprak Nemi Sensörü ve Kontrolör Ailesi (Dresselhaus et al. / Rain Bird Corp):**
    *   Üyeler: `US7836910B2`, `US8104498B2`, `US8671969B2`
    *   İlişki Türü: Doğrulanmış devam başvurusu zinciri (`continuation_of`, `has_continuation`)
    *   Google Patents Aile ID: `36615521`
    *   Kanıt: US7836910B2 (App 11/097,061, CIP of 11/027,355) -> US8104498B2 (App 12/910,720, continuation of US7836910B2) -> US8671969B2 (App 13/336,709, continuation of US8104498B2).

3.  **Acclima TDR ve Empedans Toprak Nemi Sensörü Ailesi (Anderson et al. / TDC Inc):**
    *   Üyeler: `US6657443B2`, `US6831468B2`
    *   İlişki Türü: Doğrulanmış devam-içinde-kısmi başvuru (`continuation_in_part_of`, `has_continuation_in_part`)
    *   Google Patents Aile ID'leri: `25483224`, `31999113`
    *   Kanıt: US6831468B2 (App 10/659,645), US6657443B2'nin (App 09/945,528) doğrudan continuation-in-part başvurusudur.

4.  **Bağımsız Tekil Patentler (Singletons):**
    *   25 bağımsız patent: Her biri bağımsız Google Patents aile kimliğine sahip olup korpusta başka devam veya rüçhan üyesi bulunmamaktadır (`SINGLETON_{pub}`).
    *   Toplam Değerlendirme Grubu Sayısı: 28 (3 çoklu aile + 25 bağımsız singleton).

---

## 5. Verinin Bilinen Eksikleri ve Sınırları

1.  **Korpus Ölçeği:** Mevcut korpus 34 gerçek doğrulanmış patent içermektedir (8 pilot + 26 kontrollü genişletme). Bu veri kümesi Katman 1 (BM25 ve Logistic Regression) modelleme altyapısını ve sızıntısız GroupKFold bölmelerini bilimsel olarak destekler.
2.  **Dil Kapsamı:** Tüm patent metinleri İngilizce dilindedir (dil politikası gereği).
3.  **İstemler (Claims):** Proje kapsam kuralları gereği patent istemleri taslak üretiminde kullanılmayacağından bu sürümde chunk indeksine dahil edilmemiştir.
