"""
Birim ve Entegrasyon Testleri (PAT-0005 & PAT-0006)
Uygulama Mantığı, Doğrulama, Durum Yönetimi ve Statik Güvenlik Analizi
"""

import ast
import os
from streamlit.testing.v1 import AppTest
from app import clean_components, validate_invention_data

# app.py dosyasının mutlak yolu
APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


# ==============================================================================
# 1. BİRİM TESTLERİ (Unit Tests): clean_components
# ==============================================================================

def test_clean_components_normal() -> None:
    """T7: Bileşen temizleme normal virgüllü metinle çalışır."""
    raw = "Toprak nem sensörü, Mikrodenetleyici, Solenoid vana"
    result = clean_components(raw)
    assert result == ["Toprak nem sensörü", "Mikrodenetleyici", "Solenoid vana"]


def test_clean_components_newlines_and_spaces() -> None:
    """T7: Bileşen temizleme yeni satır, boşluk ve yinelenen boş elemanları temizler."""
    raw = "Toprak nem sensörü, , Mikrodenetleyici,\nSolenoid vana\n\n  Röle modülü  "
    result = clean_components(raw)
    assert result == ["Toprak nem sensörü", "Mikrodenetleyici", "Solenoid vana", "Röle modülü"]


def test_clean_components_empty_and_whitespace() -> None:
    """T8: Boş veya yalnızca boşluk içeren bileşen girişleri boş liste döndürür."""
    assert clean_components("") == []
    assert clean_components("   ") == []
    assert clean_components(", , , \n \n") == []


# ==============================================================================
# 2. BİRİM TESTLERİ: validate_invention_data
# ==============================================================================

def test_validate_invention_data_valid() -> None:
    """Geçerli tüm alanlar doldurulduğunda doğrulama başarılı olmalı."""
    is_valid, errors, data = validate_invention_data(
        title="Sensör Tabanlı Sulama Kontrolü",
        technical_problem="Gereksiz su tüketiminin azaltılması.",
        proposed_solution="Toprak nemine göre sulamanın kontrol edilmesi.",
        components_raw="Toprak nem sensörü, Mikrodenetleyici, Solenoid vana",
        working_steps="Sensör verisi okunur ve vana kontrol edilir.",
    )
    assert is_valid is True
    assert errors == {}
    assert data is not None
    assert data["title"] == "Sensör Tabanlı Sulama Kontrolü"
    assert len(data["components"]) == 3


def test_validate_invention_data_empty_fields() -> None:
    """T8: Boş veya yalnızca boşluk içeren alanlar doğrulanamaz."""
    is_valid, errors, data = validate_invention_data(
        title="",
        technical_problem="   ",
        proposed_solution="",
        components_raw=" , , ",
        working_steps="",
    )
    assert is_valid is False
    assert data is None
    assert "title" in errors
    assert "technical_problem" in errors
    assert "proposed_solution" in errors
    assert "components" in errors
    assert "working_steps" in errors


def test_validate_invention_data_partial_missing() -> None:
    """Kısmi eksik alanlarda yalnızca ilgili alanlar için hata dönmeli."""
    is_valid, errors, data = validate_invention_data(
        title="Başlık Var",
        technical_problem="",
        proposed_solution="Çözüm Var",
        components_raw="Bileşen 1",
        working_steps="",
    )
    assert is_valid is False
    assert "technical_problem" in errors
    assert "working_steps" in errors
    assert "title" not in errors


# ==============================================================================
# 3. ENTEGRASYON VE STREAMLIT APPTEST TESTLERİ
# ==============================================================================

def test_app_initial_state() -> None:
    """T9: Uygulama ilk açıldığında Session State varsayılan değerlerle tanımlanır."""
    at = AppTest.from_file(APP_PATH)
    at.run()
    assert at.session_state["current_invention"] is None
    assert at.session_state["current_query"] == ""
    assert at.session_state["search_results"] == []
    assert at.session_state["comparison_data"] == {}
    assert at.session_state["generated_draft"] is None
    assert at.session_state["edited_draft"] is None
    assert at.session_state["selected_ranking_method"] == "BM25"


def test_app_empty_form_submission() -> None:
    """T4: Form boşken kaydet butonuna basıldığında state bozulmaz, hata bildirilir."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.button[0].click()
    at.run()

    assert at.session_state["current_invention"] is None
    assert at.session_state["form_feedback_type"] == "error"
    assert len(at.error) > 0


def test_app_valid_form_submission_and_persistence() -> None:
    """T9: Geçerli form gönderimi buluşu kaydeder ve rerun sırasında veriyi korur."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input[0].input("Sensör Tabanlı Sulama Kontrolü")
    at.text_area[0].input("Gereksiz su tüketiminin azaltılması.")
    at.text_area[1].input("Toprak nemine göre sulamanın kontrol edilmesi.")
    at.text_area[2].input("Toprak nem sensörü, Mikrodenetleyici, Solenoid vana")
    at.text_area[3].input("Sensör verisi okunur ve tanımlanmış eşiklere göre vana kontrol edilir.")

    at.button[0].click()
    at.run()

    inv = at.session_state["current_invention"]
    assert inv is not None
    assert inv["title"] == "Sensör Tabanlı Sulama Kontrolü"
    assert inv["components"] == ["Toprak nem sensörü", "Mikrodenetleyici", "Solenoid vana"]
    assert at.session_state["form_feedback_type"] == "success"

    # Yeniden çalıştırmada (rerun) state korunmalı
    at.run()
    assert at.session_state["current_invention"]["title"] == "Sensör Tabanlı Sulama Kontrolü"


def test_app_invention_change_clears_current_query_and_results() -> None:
    """T1 & T2: Buluş değiştiğinde current_query ve dört bağımlı sonuç alanı temizlenir."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 1. Buluşu kaydet
    at.text_input[0].input("Buluş 1")
    at.text_area[0].input("Problem 1")
    at.text_area[1].input("Çözüm 1")
    at.text_area[2].input("Bileşen A, Bileşen B")
    at.text_area[3].input("Adım 1, Adım 2")
    at.button[0].click()
    at.run()

    # Bağımlı state alanlarını ve sorguyu simüle et
    at.session_state["current_query"] = "eski arama sorgusu"
    at.session_state["search_results"] = [{"patent_id": "TR2026/001"}]
    at.session_state["comparison_data"] = {"similarity": 0.85}
    at.session_state["generated_draft"] = {"summary": "Taslak 1"}
    at.session_state["edited_draft"] = {"summary": "Düzenlenen 1"}

    # 2. Farklı bir buluş kaydet
    at.text_input[0].input("Buluş 2 - Güncellenmiş")
    at.text_area[0].input("Problem 2")
    at.text_area[1].input("Çözüm 2")
    at.text_area[2].input("Bileşen C")
    at.text_area[3].input("Adım 3")
    at.button[0].click()
    at.run()

    # Buluş değiştiği için current_query ve tüm bağımlı sonuçlar temizlenmiş olmalı
    assert at.session_state["current_invention"]["title"] == "Buluş 2 - Güncellenmiş"
    assert at.session_state["current_query"] == ""
    assert at.session_state["search_results"] == []
    assert at.session_state["comparison_data"] == {}
    assert at.session_state["generated_draft"] is None
    assert at.session_state["edited_draft"] is None


def test_app_same_invention_resubmission_does_not_clear() -> None:
    """T3: Aynı buluş tekrar kaydedildiğinde arama sonuçları ve sorgu korunur."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 1. Buluşu kaydet
    at.text_input[0].input("Aynı Buluş")
    at.text_area[0].input("Aynı Problem")
    at.text_area[1].input("Aynı Çözüm")
    at.text_area[2].input("Parça 1, Parça 2")
    at.text_area[3].input("Adım 1")
    at.button[0].click()
    at.run()

    # Sonuçları ve sorguyu simüle et
    at.session_state["current_query"] = "aktif sorgu"
    at.session_state["search_results"] = [{"patent_id": "TR2026/002"}]

    # 2. Aynı bilgileri tekrar kaydet
    at.button[0].click()
    at.run()

    # Aynı buluş tekrar kaydedildiğinde veriler temizlenmemeli
    assert at.session_state["current_query"] == "aktif sorgu"
    assert at.session_state["search_results"] == [{"patent_id": "TR2026/002"}]


def test_app_invalid_submission_preserves_existing_invention() -> None:
    """T4: Geçersiz form gönderimi mevcut kayıtlı buluşu ve bağımlı verileri bozmaz."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # Geçerli buluş kaydet
    at.text_input[0].input("Geçerli Buluş")
    at.text_area[0].input("Geçerli Problem")
    at.text_area[1].input("Geçerli Çözüm")
    at.text_area[2].input("Bileşen 1")
    at.text_area[3].input("Adım 1")
    at.button[0].click()
    at.run()

    at.session_state["current_query"] = "korunacak sorgu"
    at.session_state["search_results"] = [{"patent_id": "TR2026/999"}]

    # Başlığı boşaltıp geçersiz form gönder
    at.text_input[0].input("")
    at.button[0].click()
    at.run()

    # Hata üretilmeli ancak mevcut geçerli buluş ve sonuçlar bozulmamalı
    assert at.session_state["form_feedback_type"] == "error"
    assert at.session_state["current_invention"]["title"] == "Geçerli Buluş"
    assert at.session_state["current_query"] == "korunacak sorgu"
    assert at.session_state["search_results"] == [{"patent_id": "TR2026/999"}]


def test_app_reset_button_clears_visible_form_fields() -> None:
    """T5: 'Yeni Buluş Girişi (Formu Temizle)' butonu 5 görünür alanın tamamını boşaltır."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input[0].input("Silinecek Buluş")
    at.text_area[0].input("Silinecek Problem")
    at.text_area[1].input("Silinecek Çözüm")
    at.text_area[2].input("Sensör, Vana")
    at.text_area[3].input("Adım 1")
    at.button[0].click()
    at.run()

    assert at.session_state["current_invention"] is not None

    reset_buttons = [b for b in at.button if "Temizle" in b.label]
    assert len(reset_buttons) == 1

    reset_buttons[0].click()
    at.run()

    # Session State sıfırlanmalı
    assert at.session_state["current_invention"] is None
    assert at.session_state["current_query"] == ""
    assert at.session_state["search_results"] == []

    # 5 görünür form alanının tamamı boşalmış olmalı
    assert at.text_input[0].value == ""
    assert at.text_area[0].value == ""
    assert at.text_area[1].value == ""
    assert at.text_area[2].value == ""
    assert at.text_area[3].value == ""


def test_app_subsequent_invention_save_after_reset() -> None:
    """T6: Form temizlendikten sonra ikinci bir buluş başarıyla kaydedilebilir."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 1. Buluş
    at.text_input[0].input("İlk Buluş")
    at.text_area[0].input("İlk Problem")
    at.text_area[1].input("İlk Çözüm")
    at.text_area[2].input("Bileşen X")
    at.text_area[3].input("Adım X")
    at.button[0].click()
    at.run()

    # Temizle
    reset_btn = [b for b in at.button if "Temizle" in b.label][0]
    reset_btn.click()
    at.run()

    # 2. Buluş
    at.text_input[0].input("İkinci Buluş")
    at.text_area[0].input("İkinci Problem")
    at.text_area[1].input("İkinci Çözüm")
    at.text_area[2].input("Bileşen Y, Bileşen Z")
    at.text_area[3].input("Adım Y")
    at.button[0].click()
    at.run()

    assert at.session_state["current_invention"]["title"] == "İkinci Buluş"
    assert at.session_state["current_invention"]["components"] == ["Bileşen Y", "Bileşen Z"]
    assert at.session_state["form_feedback_type"] == "success"


def test_scope_and_future_modules_not_implemented() -> None:
    """T10: Gelecek modüllerin statülerinin 'Henüz geliştirilmedi' olduğunu doğrular."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    assert len(at.status) >= 3
    for s in at.status:
        assert "Henüz geliştirilmedi" in s.label

    assert at.session_state["search_results"] == []
    assert at.session_state["comparison_data"] == {}
    assert at.session_state["generated_draft"] is None


def test_static_code_analysis_no_external_api_calls() -> None:
    """T11: app.py kodunda harici ağ çağrısı veya onaylanmamış API modülleri bulunmadığını doğrular."""
    with open(APP_PATH, "r", encoding="utf-8") as f:
        source_code = f.read()

    tree = ast.parse(source_code)

    forbidden_modules = {
        "requests",
        "urllib",
        "http.client",
        "httpx",
        "aiohttp",
        "socket",
        "openai",
        "anthropic",
        "google.generativeai",
    }

    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.add(node.module.split(".")[0])

    violating_imports = imported_modules.intersection(forbidden_modules)
    assert violating_imports == set(), f"Yasaklı harici ağ modülleri tespit edildi: {violating_imports}"


def test_privacy_and_no_disk_leak() -> None:
    """T12: Form gönderiminin proje çalışma alanında dosya sızdırmadığını sınırlar dahilinde doğrular."""
    files_before = set(os.listdir("."))

    at = AppTest.from_file(APP_PATH)
    at.run()
    at.text_input[0].input("Gizlilik Testi Buluşu")
    at.text_area[0].input("Gizli Problem")
    at.text_area[1].input("Gizli Çözüm")
    at.text_area[2].input("Gizli Parça")
    at.text_area[3].input("Gizli Adım")
    at.button[0].click()
    at.run()

    files_after = set(os.listdir("."))
    new_files = files_after - files_before

    assert new_files == set(), f"Çalışma alanında yetkisiz dosya oluşturuldu: {new_files}"


# ==============================================================================
# 4. STREAMLIT BM25 ARAMA ENTEGRASYON TESTLERİ (PAT-0301)
# ==============================================================================

def test_search_ui_hidden_initially_and_visible_after_invention_saved() -> None:
    """Buluş kaydedilmeden önce arama arayüzü gizlidir, kaydedildikten sonra görünür."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # Başlangıçta arama girdi ve butonu bulunmamalıdır
    search_btns = [b for b in at.button if "Patent Ara" in b.label]
    assert len(search_btns) == 0

    # Buluş kaydet
    at.text_input[0].input("Sulama Sistemi")
    at.text_area[0].input("Su israfı problemi")
    at.text_area[1].input("Otomatik nem kontrollü sulama")
    at.text_area[2].input("Nem sensörü, Solenoid vana")
    at.text_area[3].input("Sensör okunur, vana açılır")
    at.button[0].click().run()

    # Buluş kaydedildikten sonra arama butonu ve girdi alanı görünür olmalı
    search_btns_after = [b for b in at.button if "Patent Ara" in b.label]
    assert len(search_btns_after) == 1
    assert len(at.text_input) >= 2


def test_search_empty_query_shows_warning() -> None:
    """Boş sorgu ile arama yapıldığında kullanıcı uyarılır ve sonuç listesi boş kalır."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input[0].input("Sulama Sistemi")
    at.text_area[0].input("Su israfı")
    at.text_area[1].input("Otomatik sulama")
    at.text_area[2].input("Sensör")
    at.text_area[3].input("Kontrol")
    at.button[0].click().run()

    search_btn = [b for b in at.button if "Patent Ara" in b.label][0]
    search_btn.click().run()

    assert at.session_state["search_results"] == []
    assert len(at.warning) > 0


def test_search_matching_query_returns_attributed_results() -> None:
    """Eşleşen teknik sorgu en fazla 5 doğrulanmış patent ve kaynak bilgisi döndürür."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input[0].input("Sulama Sistemi")
    at.text_area[0].input("Su israfı")
    at.text_area[1].input("Otomatik sulama")
    at.text_area[2].input("Sensör")
    at.text_area[3].input("Kontrol")
    at.button[0].click().run()

    # 2. text_input arama sorgusu girişidir
    search_input = [ti for ti in at.text_input if "Arama Sorgusu" in ti.label][0]
    search_input.input("soil moisture sensor")

    search_btn = [b for b in at.button if "Patent Ara" in b.label][0]
    search_btn.click().run()

    results = at.session_state["search_results"]
    assert len(results) == 5
    assert results[0]["publication_number"] in {"US11674944B2", "US9301461B2", "US9804113B2", "US8104498B2"}
    assert results[0]["bm25_score"] > 0
    assert "best_passage" in results[0]
    assert "source_url" in results[0]
    assert results[0]["source_url"].startswith("https://patents.google.com/patent/")


def test_search_non_matching_query_shows_info_message() -> None:
    """Korpusta eşleşmeyen bir sorgu verildiğinde sonuç boş kalır ve bilgi mesajı gösterilir."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input[0].input("Sulama Sistemi")
    at.text_area[0].input("Su israfı")
    at.text_area[1].input("Otomatik sulama")
    at.text_area[2].input("Sensör")
    at.text_area[3].input("Kontrol")
    at.button[0].click().run()

    search_input = [ti for ti in at.text_input if "Arama Sorgusu" in ti.label][0]
    search_input.input("quantum blockchain cryptocurrency")

    search_btn = [b for b in at.button if "Patent Ara" in b.label][0]
    search_btn.click().run()

    results = at.session_state["search_results"]
    assert len(results) == 0
    assert any("bulunamadı" in info.value for info in at.info)


def test_search_results_cleared_when_invention_is_modified() -> None:
    """Buluş içeriği değiştirilip yeniden kaydedildiğinde önceki arama sonuçları temizlenir."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input[0].input("İlk Buluş")
    at.text_area[0].input("Problem 1")
    at.text_area[1].input("Çözüm 1")
    at.text_area[2].input("Bileşen 1")
    at.text_area[3].input("Adım 1")
    at.button[0].click().run()

    search_input = [ti for ti in at.text_input if "Arama Sorgusu" in ti.label][0]
    search_input.input("soil moisture sensor")
    search_btn = [b for b in at.button if "Patent Ara" in b.label][0]
    search_btn.click().run()

    assert len(at.session_state["search_results"]) > 0

    # Buluşu değiştir ve tekrar kaydet
    at.text_input[0].input("İkinci Farklı Buluş")
    at.button[0].click().run()

    assert at.session_state["search_results"] == []
    assert at.session_state["current_query"] == ""


def test_search_results_cleared_on_form_reset() -> None:
    """Form temizle butonuna basıldığında arama sonuçları ve sorgu sıfırlanır, arama alanı gizlenir."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input[0].input("Sıfırlanacak Buluş")
    at.text_area[0].input("Problem")
    at.text_area[1].input("Çözüm")
    at.text_area[2].input("Parça")
    at.text_area[3].input("Adım")
    at.button[0].click().run()

    search_input = [ti for ti in at.text_input if "Arama Sorgusu" in ti.label][0]
    search_input.input("irrigation controller")
    search_btn = [b for b in at.button if "Patent Ara" in b.label][0]
    search_btn.click().run()

    assert len(at.session_state["search_results"]) > 0

    reset_btn = [b for b in at.button if "Temizle" in b.label][0]
    reset_btn.click().run()

    assert at.session_state["search_results"] == []
    assert at.session_state["current_query"] == ""
    assert len([b for b in at.button if "Patent Ara" in b.label]) == 0


def test_search_ui_contains_disclaimer() -> None:
    """Arama bölümünde patentlenebilirlik/hukuki iddia bulunmadığını belirten uyarı yer alır."""
    at = AppTest.from_file(APP_PATH)
    at.run()

    at.text_input[0].input("Uyarı Testi")
    at.text_area[0].input("Problem")
    at.text_area[1].input("Çözüm")
    at.text_area[2].input("Bileşen")
    at.text_area[3].input("Adım")
    at.button[0].click().run()

    assert any("BM25 terim eşleşmesine dayalı" in info.value for info in at.info)
    assert any("Kesin bir patentlenebilirlik" in info.value for info in at.info)
