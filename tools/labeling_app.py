"""
İnsan Denetimli Patent İlgililik Etiketleme Arayüzü (PAT-0404).
Yerel Streamlit aracı: Bilimsel ML modeli eğitimi için insan denetçilerin
sorgu-patent çiftlerini inceleyip 0/1/2 ilgililik etiketi vermesini sağlar.
"""

from pathlib import Path
import sys
import streamlit as st

# Proje kök dizinini sys.path'e ekle
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ml.dataset import PatentMLDataset
from src.ml.label_store import LabelStore


def initialize_session_state() -> None:
    """Etiketleme oturumu için state değişkenlerini ilklendirir."""
    if "current_index" not in st.session_state:
        st.session_state["current_index"] = 0
    if "reviewer_id" not in st.session_state:
        st.session_state["reviewer_id"] = "human_evaluator"
    if "notification_msg" not in st.session_state:
        st.session_state["notification_msg"] = None
    if "notification_type" not in st.session_state:
        st.session_state["notification_type"] = "info"


def render_labeling_app() -> None:
    st.set_page_config(
        page_title="Patent İlgililik Etiketleme Aracı (PAT-0404)",
        page_icon="🏷️",
        layout="wide",
    )

    initialize_session_state()

    custom_path = st.session_state.get("custom_queue_path")
    store = LabelStore(queue_path=custom_path)
    dataset = PatentMLDataset(queue_path=custom_path)

    # Üst Başlık ve Bilgilendirme
    st.title("🏷️ İnsan Denetimli Patent İlgililik Etiketleme Arayüzü")
    st.caption("KSÜ Bilgisayar Mühendisliği Bitirme Projesi — PAT-0404 ML Veri Hazırlık Aracı")

    st.info(
        "📌 **Akademik İlke:** Bu etiketleme bir patentlenebilirlik veya ihlal incelemesi DEĞİLDİR. "
        "Yalnızca verilen teknik sorgu ile patent arasındaki mühendislik ilgililik düzeyini "
        "(0: İlgisiz, 1: Kısmen İlgili, 2: Doğrudan İlgili) nesnel olarak belirlemeyi amaçlar."
    )

    # İlerleme ve İstatistikler
    progress = store.get_progress()
    total = progress["total"]
    reviewed = progress["reviewed"]
    pending = progress["pending"]
    pct = progress["percent_complete"]

    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    col_stat1.metric("Toplam Çift", total)
    col_stat2.metric("İncelenen", reviewed)
    col_stat3.metric("Bekleyen", pending)
    col_stat4.metric("Tamamlanma", f"%{pct:.1f}")

    st.progress(pct / 100.0 if total > 0 else 0.0)

    # Bildirim kutusu
    if st.session_state.get("notification_msg"):
        ntype = st.session_state.get("notification_type", "info")
        if ntype == "success":
            st.success(st.session_state["notification_msg"])
        elif ntype == "error":
            st.error(st.session_state["notification_msg"])
        else:
            st.info(st.session_state["notification_msg"])

    # Sol Kenar Çubuğu: Filtreler ve Ayarlar
    with st.sidebar:
        st.subheader("⚙️ Filtreler ve Ayarlar")

        reviewer_input = st.text_input(
            "Denetçi Adı / Kimliği *",
            value=st.session_state["reviewer_id"],
            help="Etiketi kaydeden araştırmacının rumuzu veya kimliği.",
        )
        st.session_state["reviewer_id"] = reviewer_input.strip() or "human_evaluator"

        filter_status = st.radio(
            "İnceleme Durumu Filtresi",
            options=["Tümü", "Yalnızca Bekleyenler", "Yalnızca İncelenenler"],
            index=0,
        )

        all_records = store.load_records()
        queries_list = sorted(list({r["query_id"] for r in all_records}))
        selected_query = st.selectbox("Sorgu Filtresi", options=["Tüm Sorgular"] + queries_list)

        patents_list = sorted(list({r["publication_number"] for r in all_records}))
        selected_patent = st.selectbox("Patent Filtresi", options=["Tüm Patentler"] + patents_list)

        st.markdown("---")
        st.markdown("### 📊 Etiket Dağılımı")
        dist = progress["distribution"]
        st.write(f"- **0 (İlgisiz):** {dist['0']}")
        st.write(f"- **1 (Kısmen İlgili):** {dist['1']}")
        st.write(f"- **2 (Doğrudan İlgili):** {dist['2']}")

    # Filtre değişikliğini tespit et ve gerekirse indeksi sıfırla
    filter_sig = f"{filter_status}_{selected_query}_{selected_patent}"
    if st.session_state.get("last_filter_sig") != filter_sig:
        st.session_state["last_filter_sig"] = filter_sig
        st.session_state["current_index"] = 0

    # Filtreleri Uygula
    filtered_records: list[dict] = []
    for r in all_records:
        lbl = str(r.get("human_relevance_label", "")).strip()
        is_reviewed = lbl in {"0", "1", "2"}

        if filter_status == "Yalnızca Bekleyenler" and is_reviewed:
            continue
        if filter_status == "Yalnızca İncelenenler" and not is_reviewed:
            continue
        if selected_query != "Tüm Sorgular" and r["query_id"] != selected_query:
            continue
        if selected_patent != "Tüm Patentler" and r["publication_number"] != selected_patent:
            continue

        filtered_records.append(r)

    if not filtered_records:
        st.warning("Seçilen filtre kriterlerine uygun kayıt bulunamadı.")
        return

    # Geçerli indeksi sınırla
    if st.session_state["current_index"] >= len(filtered_records):
        st.session_state["current_index"] = max(0, len(filtered_records) - 1)

    idx = st.session_state["current_index"]
    current_pair = filtered_records[idx]
    pair_id = current_pair["pair_id"]

    # Üst Navigasyon Bilgisi
    col_nav1, col_nav2 = st.columns([3, 1])
    with col_nav1:
        st.markdown(f"### Kayıt {idx + 1} / {len(filtered_records)} (`{pair_id}`)")
    with col_nav2:
        rev_status = current_pair.get("review_status", "PENDING_HUMAN_REVIEW")
        if rev_status == "REVIEWED":
            st.success(f"DURUM: İNCELENDİ (Etiket: {current_pair.get('human_relevance_label')})")
        else:
            st.warning("DURUM: BEKLİYOR")

    # İki Sütunlu İnceleme Alanı
    col_q, col_p = st.columns([1, 1], gap="large")

    with col_q:
        with st.container(border=True):
            st.markdown(f"#### 🔍 Teknik Arama Sorgusu ({current_pair['query_id']})")
            st.markdown(f"### **`{current_pair['query_text']}`**")

            q_obj = dataset.get_query(current_pair["query_id"])
            if q_obj:
                st.caption(f"Teknik Odak: `{q_obj.get('technical_focus')}` | Kaynak Türü: `{q_obj.get('source_type')}`")

            st.markdown("---")
            st.markdown("#### ⚙️ BM25 Çıkarım İstatistikleri")
            bm_score = float(current_pair.get("bm25_score", 0.0))
            bm_rank = current_pair.get("bm25_rank") or "Sıralama Dışı"
            is_cand = current_pair.get("bm25_candidate") == "True" or current_pair.get("bm25_candidate") is True

            col_b1, col_b2, col_b3 = st.columns(3)
            col_b1.metric("BM25 Skoru", f"{bm_score:.4f}")
            col_b2.metric("BM25 Sırası", bm_rank)
            col_b3.metric("Aday Durumu", "Aday (Skor > 0)" if is_cand else "Aday Değil (Skor = 0)")

            st.markdown(f"**Değerlendirme Grubu:** `{current_pair.get('evaluation_group_id')}`")
            fam_str = current_pair.get("family_id") or "Bağımsız (Singleton)"
            st.markdown(f"**Patent Ailesi:** `{fam_str}`")

    with col_p:
        with st.container(border=True):
            pub_num = current_pair["publication_number"]
            p_title = current_pair["patent_title"]
            s_url = current_pair["source_url"]

            st.markdown(f"#### 📄 [{pub_num}]({s_url}) — {p_title}")

            p_obj = dataset.get_patent(pub_num)
            if p_obj:
                app_num = p_obj.get("application_number", "N/A")
                invs = ", ".join(p_obj.get("inventors", [])) or "Belirtilmemiş"
                ass = p_obj.get("assignee") or "Belirtilmemiş"
                st.caption(f"Başvuru No: `{app_num}` | Mucitler: {invs} | Hak Sahibi: {ass}")

                st.markdown("**Resmi Patent Özeti (Abstract):**")
                st.write(p_obj.get("abstract", "Özet bulunamadı."))

                # Varsa kanıt pasajı
                ev_chunk_id = current_pair.get("evidence_chunk_id")
                if ev_chunk_id:
                    c_obj = dataset.get_chunk(ev_chunk_id)
                    if c_obj:
                        with st.expander(f"📑 En Yüksek Skorlu Pasajı Görüntüle ({ev_chunk_id})", expanded=True):
                            st.write(c_obj.get("text", ""))
                            st.caption(f"Bölüm: `{c_obj.get('section')}` | Konum: `{c_obj.get('internal_chunk_locator')}`")
                else:
                    st.info("Bu patent için BM25 eşleşen kanıt pasajı üretmemiştir (Skor: 0.0000).")

    # Etiket Verme Bölümü
    st.markdown("---")
    st.subheader("🎯 İlgililik Kararı ve Kayıt")

    existing_lbl = str(current_pair.get("human_relevance_label", "")).strip()
    lbl_index = None
    if existing_lbl == "0":
        lbl_index = 0
    elif existing_lbl == "1":
        lbl_index = 1
    elif existing_lbl == "2":
        lbl_index = 2

    label_options = [
        "0 — İLGİSİZ (Irrelevant: Teknik problem veya temel çözüm mekanizması belirgin şekilde farklı)",
        "1 — KISMEN İLGİLİ (Partially Relevant: Geniş uygulama alanı benziyor, ancak temel çözüm mekanizması tam örtüşmüyor)",
        "2 — DOĞRUDAN İLGİLİ (Directly Relevant: Teknik problem ve temel çözüm mekanizması doğrudan sorguyla ilişkili)",
    ]

    radio_key = f"label_radio_{pair_id}"
    notes_key = f"notes_{pair_id}"

    selected_label_str = st.radio(
        "İlgililik Seviyesi Seçimi *",
        options=label_options,
        index=lbl_index,
        key=radio_key,
        help="Lütfen etiketleme kılavuzundaki (PAT-0402) kriterlere göre seçim yapınız.",
    )

    existing_notes = current_pair.get("review_notes", "") or ""
    notes_input = st.text_area(
        "İnceleme Notu (Opsiyonel)",
        value=existing_notes,
        height=80,
        key=notes_key,
    )

    # Butonlar: Kaydet, Önceki, Sonraki, Sıfırla
    col_btn_prev, col_btn_save, col_btn_next, col_btn_clear = st.columns([1, 2, 1, 1], gap="medium")

    with col_btn_prev:
        if st.button("⬅️ Önceki Kayıt", use_container_width=True, disabled=(idx == 0)):
            st.session_state["current_index"] = max(0, idx - 1)
            st.session_state["notification_msg"] = None
            st.rerun()

    with col_btn_save:
        if st.button("💾 Etiketi Kaydet", type="primary", use_container_width=True):
            if not selected_label_str:
                st.session_state["notification_msg"] = (
                    "⚠️ Lütfen bir ilgililik seviyesi seçiniz (0, 1 veya 2)! "
                    "Seçim yapılmadan kayıt yapılamaz."
                )
                st.session_state["notification_type"] = "error"
                st.rerun()

            chosen_label = selected_label_str.split(" — ")[0]
            success = store.update_label(
                pair_id=pair_id,
                label=chosen_label,
                reviewer_id=st.session_state["reviewer_id"],
                notes=notes_input,
            )
            if success:
                st.session_state["notification_msg"] = f"Kayıt başarıyla kaydedildi: `{pair_id}` -> Etiket: {chosen_label}"
                st.session_state["notification_type"] = "success"
                # Otomatik sonraki kayda ilerle
                if filter_status == "Yalnızca Bekleyenler":
                    if idx >= len(filtered_records) - 1:
                        st.session_state["current_index"] = max(0, len(filtered_records) - 2)
                else:
                    if idx < len(filtered_records) - 1:
                        st.session_state["current_index"] = idx + 1
                st.rerun()
            else:
                st.session_state["notification_msg"] = f"Hata: `{pair_id}` güncellenemedi."
                st.session_state["notification_type"] = "error"
                st.rerun()

    with col_btn_next:
        if st.button("➡️ Sonraki Kayıt", use_container_width=True, disabled=(idx >= len(filtered_records) - 1)):
            st.session_state["current_index"] = min(len(filtered_records) - 1, idx + 1)
            st.session_state["notification_msg"] = None
            st.rerun()

    with col_btn_clear:
        if st.button("🗑️ Etiketi Sıfırla", use_container_width=True):
            store.clear_label(pair_id=pair_id)
            if radio_key in st.session_state:
                del st.session_state[radio_key]
            if notes_key in st.session_state:
                del st.session_state[notes_key]
            st.session_state["notification_msg"] = f"`{pair_id}` etiket kaydı temizlendi (bekliyor durumuna alındı)."
            st.session_state["notification_type"] = "info"
            st.rerun()


if __name__ == "__main__":
    render_labeling_app()

