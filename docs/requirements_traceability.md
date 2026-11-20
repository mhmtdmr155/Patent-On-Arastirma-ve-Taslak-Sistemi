# Gereksinim ve Test İzlenebilirlik Matrisi (Requirements Traceability Matrix)

Bu belge, proje yol haritasında (v2.0 + v2.1) tanımlanan gereksinimlerin kaynak kod, test paketleri ve mimari dokümantasyon ile olan karşılıklarını ve güncel gerçekleştirilme durumlarını şeffaf bir şekilde belgeler.

---

## 1. Durum Göstergeleri

*   **Uygulandı ve Test Edildi:** Kod geliştirilmiş, otomatik testlerle doğrulanmış ve kanıtlanmıştır.
*   **Kısmen Uygulandı:** Temel mimari veya arayüz iskeleti hazırlanmış, nihai iş mantığı henüz tamamlanmamıştır.
*   **Planlandı:** Gelecek geliştirme aşamalarında (Katman 1, 2, 3) uygulanacaktır.
*   **Engellendi:** Dış bağımlılık, yetki veya donanım kısıtı nedeniyle ilerletilemeyen maddeler.
*   **Doğrulanamadı:** Testi henüz gerçekleştirilememiş maddeler.

---

## 2. İzlenebilirlik Tablosu

| Gereksinim Kodu | Kategori | Gereksinim Açıklaması | İlgili Dosya / Modül | İlgili Test(ler) | Teknik Kanıt | Güncel Durum | Eksikler / Notlar |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G1.1** | A. Buluş Girişi | 5 Temel Alanın Girişi (Başlık, Problem, Çözüm, Bileşenler, Adımlar) | `app.py` (`render_ui`) | `test_app_valid_form_submission_and_persistence` | `AppTest` form doldurma ve `current_invention` sözlüğü | **Uygulandı ve Test Edildi** | Eksiksiz çalışıyor. |
| **G1.2** | A. Buluş Girişi | Form Veri Doğrulaması (Boşluk, eksik alan, bileşen ayrıştırma) | `app.py` (`validate_invention_data`, `clean_components`) | `test_validate_invention_data_*`, `test_clean_components_*` | pytest birim testleri (6 adet) | **Uygulandı ve Test Edildi** | Hatalar kullanıcıya açık bildirimle sunuluyor. |
| **G1.3** | A. Buluş Girişi | Session State Başlatma ve Veri Saklama | `app.py` (`initialize_session_state`, `save_invention`) | `test_app_initial_state`, `test_app_valid_form_submission_and_persistence` | `at.session_state` anahtar ve tip kontrolleri | **Uygulandı ve Test Edildi** | Rerun sırasında state korunuyor. |
| **G1.4** | A. Buluş Girişi | Buluş Değiştiğinde `current_query` ve Bağımlı Sonuçların Sıfırlanması | `app.py` (`save_invention`) | `test_app_invention_change_clears_current_query_and_results` | `current_query == ""`, `search_results == []`, `generated_draft is None` | **Uygulandı ve Test Edildi** | PAT-0005-D01 kapsamında düzeltildi. |
| **G1.5** | A. Buluş Girişi | Aynı Buluş Tekrar Kaydedildiğinde Sonuçların Korunması | `app.py` (`save_invention`) | `test_app_same_invention_resubmission_does_not_clear` | Eşit veri kaydında `search_results` silinmez | **Uygulandı ve Test Edildi** | Gereksiz veri kaybı önlendi. |
| **G1.6** | A. Buluş Girişi | Geçersiz Form Gönderiminde Mevcut Buluşun Korunması | `app.py` (`save_invention`) | `test_app_invalid_submission_preserves_existing_invention` | Hatalı gönderimde `current_invention` bozulmaz | **Uygulandı ve Test Edildi** | Kullanıcı girdisi güvenceye alındı. |
| **G1.7** | A. Buluş Girişi | "Yeni Buluş Girişi (Formu Temizle)" ile Form ve State Sıfırlama | `app.py` (`reset_invention_state`) | `test_app_reset_button_clears_visible_form_fields`, `test_app_subsequent_invention_save_after_reset` | 5 form alanının `value == ""` olması ve 2. kayıt başarısı | **Uygulandı ve Test Edildi** | Görünür alanlar tamamen boşalıyor. |
| **G2.1** | B. Patent Arama | Gerçek Patent Veri Havuzunun Oluşturulması | `data/` (planlanan) | — | — | **Planlandı** | PAT-0101/0103 fizibilitesi tamamlanınca uygulanacak. |
| **G2.2** | B. Patent Arama | rank-bm25 (BM25Okapi) Arama Motoru İndekslemesi | `src/retrieval/` (planlanan) | — | — | **Planlandı** | BM25 ters indeks oluşturulacak. |
| **G2.3** | B. Patent Arama | İlk 20 Aday Patentin Belirlenmesi | `src/retrieval/` (planlanan) | — | — | **Planlandı** | Skor sıralaması yapılacak. |
| **G2.4** | B. Patent Arama | İlk 5 Patentin Kaynak Pasajlarıyla Gösterimi | `app.py` (planlanan) | — | — | **Planlandı** | Kullanıcıya şeffaf atıf sunulacak. |
| **G3.1** | C. Kendi ML Modeli | Etiketli Sorgu–Patent Veri Seti Hazırlama | `data/` (planlanan) | — | — | **Planlandı** | İlgili / ilgisiz etiketli çiftler oluşturulacak. |
| **G3.2** | C. Kendi ML Modeli | TF-IDF Öznitelik Çıkarımı | `src/ranking/` (planlanan) | — | — | **Planlandı** | scikit-learn TfidfVectorizer kullanılacak. |
| **G3.3** | C. Kendi ML Modeli | Logistic Regression Model Eğitimi ve Kaydı | `src/ranking/` (planlanan) | — | — | **Planlandı** | scikit-learn LogisticRegression eğitilecek. |
| **G3.4** | C. Kendi ML Modeli | BM25 Adaylarının Yeniden Sıralanması (Re-ranking) | `src/ranking/` (planlanan) | — | — | **Planlandı** | Model skoruna göre sıralama güncellenecek. |
| **G4.1** | D. Kaynak Güvenilirliği | Patent Numarası ve Yayın Bilgisi Eşleme | `src/retrieval/` (planlanan) | — | — | **Planlandı** | Gerçek resmi patent metadata kontrolü. |
| **G4.2** | D. Kaynak Güvenilirliği | Kaynak Pasajlarının Yapısal Doğrulanması | `src/retrieval/` (planlanan) | — | — | **Planlandı** | Alıntılanan metnin orijinal patentte varlığı denetlenecek. |
| **G4.3** | D. Kaynak Güvenilirliği | Hukuki Karar Verilmemesi İlkesi | `README.md`, `docs/architecture.md` | — | Dokümantasyon metin analizi | **Uygulandı ve Test Edildi** | Yenilik/ihlal kararı verilmediği açıkça belirtildi. |
| **G5.1** | E. RAG ve Ön Taslak | 4 Bölümlü Ön Taslak Üretimi (Özet, Teknik Alan, Mevcut Teknik, Açıklama) | `src/drafting/` (planlanan) | — | — | **Planlandı** | İstemler hariç 4 bölüm üretilecek. |
| **G5.2** | E. RAG ve Ön Taslak | Hazır LLM'nin Yalnızca Metin Yazımında Kullanılması | `src/drafting/` (planlanan) | — | — | **Planlandı** | Arama ve ML'de LLM kullanılmayacak. |
| **G5.3** | E. RAG ve Ön Taslak | Kullanıcı Tarafından Taslak Düzenleme İmkanı | `app.py` (planlanan) | — | — | **Planlandı** | `edited_draft` alanı üzerinden sunulacak. |
| **G6.1** | F. Bilimsel Kıyaslama | BM25 vs. BM25 + Logistic Regression Kıyaslaması | `src/evaluation/` (planlanan) | — | — | **Planlandı** | MRR/MAP ve Precision@5 metrikleri. |
| **G6.2** | F. Bilimsel Kıyaslama | LLM-only vs. RAG Destekli Taslak Kıyaslaması | `src/evaluation/` (planlanan) | — | — | **Planlandı** | Terim örtüşmesi ve kaynak sadakati ölçümü. |
| **K1** | G. Kalite ve Güvenlik | Uygulama Çalıştırılabilirliği (Streamlit HTTP Server) | `app.py` | `test_app_*`, HTTP Live Probe | HTTP 200 OK yanıtı, 17/17 pytest | **Uygulandı ve Test Edildi** | Canlı sunucu ve AppTest teyit edildi. |
| **K2** | G. Kalite ve Güvenlik | Python 3.12 Ortam Bütünlüğü | `.venv` | `pip check`, `py_compile` | `No broken requirements found.` | **Uygulandı ve Test Edildi** | Python 3.12.10 64-bit doğrulanmıştır. |
| **K3** | G. Kalite ve Güvenlik | Kullanıcı Veri Gizliliği (Dışa Aktarmama, Disk İzolasyonu) | `app.py` | `test_privacy_and_no_disk_leak`, `test_static_code_analysis_no_external_api_calls` | AST analizi (0 yasaklı import), os.listdir kontrolü | **Uygulandı ve Test Edildi** | Kodda harici ağ isteği bulunmuyor. |
| **K4** | G. Kalite ve Güvenlik | Hata Dayanıklılığı ve Kullanıcı Geri Bildirimi | `app.py` | `test_app_empty_form_submission` | `at.error` bildirimleri | **Uygulandı ve Test Edildi** | Hatalı durumlarda arayüz çökmesi engellendi. |
| **K5** | G. Kalite ve Güvenlik | Git ve Dosya Güvenliği | `.gitignore` | `git check-ignore` testleri | .venv, .env, models/ dışlama kuralları | **Uygulandı ve Test Edildi** | Hassas ve büyük dosyalar dışlanmaktadır. |

---

## 3. Özet Durum Sayıları

*   **Toplam Tanımlı Gereksinim:** 28
*   **Uygulandı ve Test Edildi:** 13 (%46.4)
*   **Planlandı (Sonraki Aşamalar):** 15 (%53.6)
*   **Kısmen Uygulandı:** 0
*   **Engellendi / Doğrulanamadı:** 0

