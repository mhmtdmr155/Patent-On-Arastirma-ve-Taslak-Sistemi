"""
Yapay Zekâ Destekli Patent Ön Araştırma ve Patent Ön Taslağı Hazırlama Sistemi
İlk Çalışan Streamlit Uygulaması (PAT-0005)
"""

from typing import Any
import streamlit as st
from src.retrieval.bm25_engine import BM25SearchEngine


def clean_components(raw_input: str) -> list[str]:
    """
    Kullanıcının girdiği bileşen metnini temizler.
    Virgül veya yeni satır ile ayrılmış girdileri ayıklar,
    boşlukları temizler ve sırayı koruyarak boş olmayanları döndürür.
    """
    if not raw_input or not isinstance(raw_input, str):
        return []

    # Hem yeni satır hem virgülle ayırmayı destekle
    normalized = raw_input.replace("\n", ",")
    tokens = normalized.split(",")

    cleaned: list[str] = []
    seen: set[str] = set()

    for item in tokens:
        stripped = item.strip()
        if stripped and stripped not in seen:
            cleaned.append(stripped)
            seen.add(stripped)

    return cleaned


def validate_invention_data(
    title: str,
    technical_problem: str,
    proposed_solution: str,
    components_raw: str,
    working_steps: str,
) -> tuple[bool, dict[str, str], dict[str, Any] | None]:
    """
    Buluş formu alanlarını doğrular.
    Zorunlu alanların dolu olduğunu, yalnızca boşluk içermediğini ve
    en az bir geçerli bileşen bulunduğunu denetler.
    """
    errors: dict[str, str] = {}

    cleaned_title = title.strip() if isinstance(title, str) else ""
    if not cleaned_title:
        errors["title"] = "Buluş başlığı boş bırakılamaz."

    cleaned_problem = technical_problem.strip() if isinstance(technical_problem, str) else ""
    if not cleaned_problem:
        errors["technical_problem"] = "Teknik problem alanı boş bırakılamaz."

    cleaned_solution = proposed_solution.strip() if isinstance(proposed_solution, str) else ""
    if not cleaned_solution:
        errors["proposed_solution"] = "Önerilen çözüm alanı boş bırakılamaz."

    cleaned_components_list = clean_components(components_raw)
    if not cleaned_components_list:
        errors["components"] = "En az bir geçerli temel bileşen girilmelidir."

    cleaned_steps = working_steps.strip() if isinstance(working_steps, str) else ""
    if not cleaned_steps:
        errors["working_steps"] = "Çalışma adımları alanı boş bırakılamaz."

    if errors:
        return False, errors, None

    validated_invention: dict[str, Any] = {
        "title": cleaned_title,
        "technical_problem": cleaned_problem,
        "proposed_solution": cleaned_solution,
        "components": cleaned_components_list,
        "working_steps": cleaned_steps,
    }

    return True, {}, validated_invention


def initialize_session_state() -> None:
    """
    Session State anahtarlarını başlangıç değerleriyle tanımlar.
    Mevcut state değerlerini ezmez.
    """
    defaults: dict[str, Any] = {
        "current_invention": None,
        "current_query": "",
        "search_results": [],
        "comparison_data": {},
        "generated_draft": None,
        "edited_draft": None,
        "selected_ranking_method": "BM25",
        "generation_settings": {"language": "tr"},
        "form_feedback_msg": None,
        "form_feedback_type": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_resource
def get_search_engine() -> BM25SearchEngine:
    """
    BM25 arama motorunu tekil (cached) nesne olarak yükler.
    """
    return BM25SearchEngine()


def reset_invention_state() -> None:
    """
    Yeni buluş girişi için aktif buluş ve bağımlı sonuç alanlarını sıfırlar.
    """
    st.session_state["current_invention"] = None
    st.session_state["current_query"] = ""
    st.session_state["search_results"] = []
    st.session_state["comparison_data"] = {}
    st.session_state["generated_draft"] = None
    st.session_state["edited_draft"] = None
    st.session_state["form_feedback_msg"] = "Buluş formu temizlendi. Yeni buluş bilgilerini girebilirsiniz."
    st.session_state["form_feedback_type"] = "info"


def save_invention(
    title: str,
    technical_problem: str,
    proposed_solution: str,
    components_raw: str,
    working_steps: str,
) -> bool:
    """
    Form girdilerini doğrular ve geçerliyse Session State'e kaydeder.
    Eğer buluş içeriği değişmişse önceki arama ve taslak sonuçlarını temizler.
    """
    is_valid, errors, validated_data = validate_invention_data(
        title=title,
        technical_problem=technical_problem,
        proposed_solution=proposed_solution,
        components_raw=components_raw,
        working_steps=working_steps,
    )

    if not is_valid:
        error_msgs = "\n".join(f"• {msg}" for msg in errors.values())
        st.session_state["form_feedback_msg"] = f"Lütfen formdaki eksik alanları tamamlayınız:\n{error_msgs}"
        st.session_state["form_feedback_type"] = "error"
        return False

    previous_invention = st.session_state.get("current_invention")

    # Eğer kaydedilen buluş öncekine göre değiştiyse bağımlı verileri temizle
    if previous_invention != validated_data:
        st.session_state["current_query"] = ""
        st.session_state["search_results"] = []
        st.session_state["comparison_data"] = {}
        st.session_state["generated_draft"] = None
        st.session_state["edited_draft"] = None

    st.session_state["current_invention"] = validated_data
    st.session_state["form_feedback_msg"] = f"Buluş bilgileri başarıyla kaydedildi: \"{validated_data['title']}\""
    st.session_state["form_feedback_type"] = "success"
    return True


def render_ui() -> None:
    """
    Streamlit kullanıcı arayüzünü oluşturur.
    """
    st.set_page_config(
        page_title="Patent Ön Araştırma Sistemi",
        page_icon="📄",
        layout="wide",
    )

    initialize_session_state()

    st.title("Yapay Zekâ Destekli Patent Ön Araştırma ve Patent Ön Taslağı Hazırlama Sistemi")
    st.caption("Buluş bilgilerinizi girerek patent ön araştırması ve ön taslak süreci için ilk adımı oluşturabilirsiniz.")

    st.info(
        "📌 **Bilgilendirme:** Bu sürüm ilk çalışan aşama olup buluş bilgilerinin girişini, doğrulanmasını "
        "ve oturumda (Session State) güvenle saklanmasını sağlar. Patent arama motoru (BM25), makine öğrenimi "
        "sıralaması ve RAG taslak üretim modülleri sonraki aşamalarda sisteme entegre edilecektir."
    )

    # Bildirim mesajı varsa göster
    if st.session_state.get("form_feedback_msg"):
        fb_type = st.session_state.get("form_feedback_type", "info")
        msg = st.session_state["form_feedback_msg"]
        if fb_type == "success":
            st.success(msg)
        elif fb_type == "error":
            st.error(msg)
        else:
            st.info(msg)

    # İki sütunlu düzen: Sol tarafta form, sağ tarafta kaydedilen buluş özeti
    col_form, col_summary = st.columns([1.1, 0.9], gap="large")

    current_inv = st.session_state.get("current_invention")

    with col_form:
        st.subheader("1. Buluş Bilgileri Giriş Formu")

        # Mevcut kayıtlı değerler varsa form alanlarına başlangıç değeri ver
        default_title = current_inv.get("title", "") if current_inv else ""
        default_problem = current_inv.get("technical_problem", "") if current_inv else ""
        default_solution = current_inv.get("proposed_solution", "") if current_inv else ""
        default_components = ", ".join(current_inv.get("components", [])) if current_inv else ""
        default_steps = current_inv.get("working_steps", "") if current_inv else ""

        with st.form(key="invention_form", clear_on_submit=False):
            title_input = st.text_input(
                label="Buluş Başlığı *",
                value=default_title,
                placeholder="Örnek: Sensör Tabanlı Sulama Kontrolü",
                help="Buluşun teknik amacını belirten kısa ve net başlık.",
            )

            problem_input = st.text_area(
                label="Teknik Problem *",
                value=default_problem,
                placeholder="Örnek: Tarımsal alanlarda kontrolsüz ve gereksiz su tüketiminin azaltılması.",
                help="Buluşun çözmeyi amaçladığı temel teknik zorluk.",
                height=100,
            )

            solution_input = st.text_area(
                label="Önerilen Çözüm *",
                value=default_solution,
                placeholder="Örnek: Toprak nemine ve sıcaklık verisine göre sulamanın otomatik kontrol edilmesi.",
                help="Teknik probleme getirilen somut mühendislik çözümü.",
                height=100,
            )

            components_input = st.text_area(
                label="Temel Bileşenler (Virgül veya yeni satır ile ayırınız) *",
                value=default_components,
                placeholder="Örnek: Toprak nem sensörü, Mikrodenetleyici, Solenoid vana, Röle modülü",
                help="Buluşu meydana getiren donanım, yazılım veya yapısal parçalar.",
                height=90,
            )

            steps_input = st.text_area(
                label="Çalışma Adımları *",
                value=default_steps,
                placeholder="Örnek: 1. Sensör verisi okunur. 2. Mikrodenetleyici eşik değerle kıyaslar. 3. Vana tetiklenir.",
                help="Bileşenlerin birlikte nasıl çalıştığını adım adım açıklayınız.",
                height=110,
            )

            submit_btn = st.form_submit_button(
                label="Buluş Bilgilerini Kaydet",
                use_container_width=True,
                type="primary",
            )

            if submit_btn:
                save_invention(
                    title=title_input,
                    technical_problem=problem_input,
                    proposed_solution=solution_input,
                    components_raw=components_input,
                    working_steps=steps_input,
                )
                st.rerun()

        # Yeni buluş başlatma butonu
        if current_inv is not None:
            if st.button("Yeni Buluş Girişi (Formu Temizle)", use_container_width=True):
                reset_invention_state()
                st.rerun()

    with col_summary:
        st.subheader("2. Oturumda Kayıtlı Buluş Bilgileri")

        if current_inv is not None:
            st.markdown(f"### 📋 {current_inv['title']}")
            
            with st.container(border=True):
                st.markdown("**Teknik Problem:**")
                st.write(current_inv["technical_problem"])

                st.markdown("**Önerilen Çözüm:**")
                st.write(current_inv["proposed_solution"])

                st.markdown("**Temel Bileşenler:**")
                for comp in current_inv["components"]:
                    st.markdown(f"- {comp}")

                st.markdown("**Çalışma Adımları:**")
                st.write(current_inv["working_steps"])

            st.caption("🔒 Bu bilgiler yalnızca bu oturum süresince bellekte (Session State) tutulmaktadır. Harici bir servise gönderilmez.")
        else:
            st.info("Henüz kaydedilmiş bir buluş bilgisi bulunmamaktadır. Lütfen soldaki formu doldurarak 'Kaydet' butonuna basınız.")

    # Buluş kaydedildiyse BM25 Patent Arama Bölümünü Göster
    if current_inv is not None:
        st.markdown("---")
        st.subheader("2. Patent Ön Araştırması (BM25 Pasaj Arama)")
        st.caption("Kayıtlı buluşunuz için doğrulanmış pilot patent korpusunda (US/EN) BM25 terim eşleşmesi ile pasaj araması yapınız.")

        st.info(
            "⚠️ **Hukuki / Değerlendirme Uyarısı:** Bu arama yalnızca doğrulanmış pilot patent korpusundaki "
            "(Google Patents Public HTML Mirror) metin pasajlarının BM25 terim eşleşmesine dayalı istatistiksel benzerlik sıralamasıdır. "
            "Kesin bir patentlenebilirlik, yenilik (novelty) veya patent ihlali (infringement) analizi niteliği taşımaz."
        )

        col_q, col_btn = st.columns([4, 1], gap="medium")
        with col_q:
            default_q = st.session_state.get("current_query", "")
            query_text = st.text_input(
                label="İngilizce Teknik Arama Sorgusu *",
                value=default_q,
                placeholder="Örnek: soil moisture sensor wireless irrigation controller",
                help="Doğrulanmış patent korpusu İngilizce olduğundan arama terimlerini İngilizce giriniz.",
                key="search_query_input",
            )
        with col_btn:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            search_clicked = st.button(
                label="Patent Ara (BM25)",
                type="primary",
                use_container_width=True,
                key="search_btn",
            )

        if search_clicked:
            cleaned_query = query_text.strip()
            if not cleaned_query:
                st.warning("Lütfen arama yapmak için en az bir teknik terim giriniz.")
                st.session_state["current_query"] = ""
                st.session_state["search_results"] = []
            else:
                st.session_state["current_query"] = cleaned_query
                engine = get_search_engine()
                raw_results = engine.search(cleaned_query, top_k_patents=20)
                st.session_state["search_results"] = [r.to_dict() for r in raw_results[:5]]
                st.rerun()

        results = st.session_state.get("search_results", [])
        if results:
            ranking_method = st.session_state.get("selected_ranking_method", "BM25")
            total_matching = results[0].get("total_matching_patents", len(results)) if results else 0
            displayed_results = results[:5]
            st.markdown(f"### 🎯 Eşleşen Toplam {total_matching} Patent Adayı Arasından İlk {len(displayed_results)} Sonuç (Sıralama: {ranking_method})")
            for idx, res in enumerate(displayed_results, start=1):
                with st.container(border=True):
                    r_header, r_metric = st.columns([4, 1])
                    with r_header:
                        st.markdown(f"**{idx}. [{res['publication_number']}]({res['source_url']}) — {res['title']}**")
                        app_num = res.get("application_number") or "N/A"
                        doc_loc = res.get("source_document_locator") or "section=description"
                        inv_str = ", ".join(res.get("inventors", [])) or "Belirtilmemiş"
                        ass_str = res.get("assignee") or "Belirtilmemiş"
                        st.caption(f"Başvuru No: `{app_num}` | Mucitler: {inv_str} | Hak Sahibi: {ass_str} | Konum: `{doc_loc}`")
                    with r_metric:
                        score_val = res.get("bm25_score", 0.0)
                        st.metric(label="BM25 Skoru", value=f"{score_val:.4f}")

                    section_name = res.get("best_section", "description").upper()
                    chunk_id = res.get("chunk_id", "")
                    internal_loc = res.get("internal_chunk_locator", "")
                    matching_count = len(res.get("top_passages", []))

                    st.markdown(
                        f"**En İlgili Pasaj Bölümü:** `{section_name}` | "
                        f"**İç Konum Belirteci:** `{internal_loc}` | "
                        f"**Eşleşen Pasaj:** {matching_count}"
                    )
                    with st.expander(f"📄 En İyi Pasaj Metnini Görüntüle ({chunk_id})"):
                        st.write(res.get("best_passage", ""))
        elif st.session_state.get("current_query"):
            st.info(f"\"{st.session_state['current_query']}\" sorgusu için korpusta eşleşen ve pozitif skor üreten patent bulunamadı.")

    st.markdown("---")
    st.subheader("3. Sonraki Geliştirme Aşamaları")

    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        st.markdown("#### Katman 1: Patent Arama & Sıralama")
        st.status("BM25 Pasaj Arama Aktif / ML Sıralama Henüz geliştirilmedi (Gelecek Aşama)", state="complete")
        st.caption("BM25Okapi arama motoru devrede. ML Logistic Regression planlandı.")

    with col_m2:
        st.markdown("#### Katman 2: RAG ve Patent Ön Taslağı")
        st.status("Henüz geliştirilmedi (Gelecek Aşama)", state="error")
        st.caption("Doğrulanmış patent pasajları ile 4 bölümlü ön taslak üretimi (İstemler hariç).")

    with col_m3:
        st.markdown("#### Katman 3: Bilimsel Değerlendirme")
        st.status("Henüz geliştirilmedi (Gelecek Aşama)", state="error")
        st.caption("BM25 vs. ML ve Salt LLM vs. RAG karşılaştırmalı başarım analizleri.")


if __name__ == "__main__":
    render_ui()
