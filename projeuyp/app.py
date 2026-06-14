from datetime import date, datetime
from pathlib import Path

import cv2
import pandas as pd
import streamlit as st

try:
    from projeuyp.services import (
        STANDARDS,
        build_prediction_provider,
        build_sensor_provider,
        check_value,
        get_phase_data,
    )
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from projeuyp.services import (
        STANDARDS,
        build_prediction_provider,
        build_sensor_provider,
        check_value,
        get_phase_data,
    )

try:
    from ultralytics import YOLO

    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

st.set_page_config(page_title="Eko-Üretim MES", layout="wide", initial_sidebar_state="expanded")

# --- VERİ TABANI SİMÜLASYONU İLKLENDİRME ---
if "lines" not in st.session_state:
    st.session_state.lines = {
        "Hat-01": {"status": "Boş"},
        "Hat-02": {"status": "Boş"},
        "Hat-03": {"status": "Boş"},
        "Hat-04": {"status": "Boş"},
    }

if "active_productions" not in st.session_state:
    st.session_state.active_productions = {}

if "archive" not in st.session_state:
    st.session_state.archive = []

if "alerts" not in st.session_state:
    st.session_state.alerts = []

if "notifications" not in st.session_state:
    st.session_state.notifications = []

if "prod_counter" not in st.session_state:
    st.session_state.prod_counter = 101

if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}


STANDARTLAR = STANDARDS
SENSOR_PROVIDER = build_sensor_provider()
PREDICTION_PROVIDER = build_prediction_provider()


if "active_productions" not in st.session_state:
    st.session_state.active_productions = {}
if "archive" not in st.session_state:
    st.session_state.archive = []
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "notifications" not in st.session_state:
    st.session_state.notifications = []
if "prod_counter" not in st.session_state:
    st.session_state.prod_counter = 101
if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}


@st.cache_resource
def load_yolo_model():
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / "models" / "best.pt",
        base_dir / "best.pt",
        base_dir.parent / "Görüntü İşleme" / "models" / "best.pt",
    ]
    for path in candidates:
        if path.exists():
            try:
                return YOLO(str(path)), str(path)
            except Exception as exc:
                return f"HATA: {exc}", str(path)
    return None, "Bulunamadı"


def render_kat_sensorleri(ideal):
    kat_sekmeleri = st.tabs(["1. Kat", "2. Kat", "3. Kat", "4. Kat"])
    ilk_kat_verisi = None
    for i, kat in enumerate(kat_sekmeleri):
        with kat:
            s_data = SENSOR_PROVIDER.read(ideal)
            if i == 0:
                ilk_kat_verisi = s_data
            st.caption(f"Veri Okuma Döngüsü Saati: {datetime.now().strftime('%H:%M:%S')}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    f"**pH:** {check_value(s_data['ph'], ideal['ph'][0], ideal['ph'][1])}",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"**Bağıl Nem (%):** {check_value(s_data['hum'], ideal['hum'][0], ideal['hum'][1])}",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"**Işık (PPFD):** {check_value(s_data['light'], ideal['light'][0], ideal['light'][1])}",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"**EC (mS/cm):** {check_value(s_data['ec'], ideal['ec'][0], ideal['ec'][1])}",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"**Ortam Sıcaklığı (°C):** {check_value(s_data['temp'], ideal['temp'][0], ideal['temp'][1])}",
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f"**CO2 Seviyesi (ppm):** {check_value(s_data['co2'], ideal['co2'][0], ideal['co2'][1])}",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"**Su Sıcaklığı (°C):** {check_value(s_data['water_temp'], ideal['water_temp'][0], ideal['water_temp'][1])}",
                    unsafe_allow_html=True,
                )
    return ilk_kat_verisi


def login():
    st.markdown(
        "<h1 style='text-align: center; color: #2E7D32;'>Eko-Üretim Kontrol Merkezi</h1>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            st.subheader(" Güvenli Kimlik Doğrulama")
            u = st.text_input("Kullanıcı Adı")
            p = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                if u in ["admin", "operator", "yonetici"] and p == "123":
                    st.session_state.auth = {
                        "logged_in": True,
                        "role": u.upper(),
                        "user": u.capitalize(),
                    }
                    st.rerun()
                else:
                    st.error("Geçersiz kullanıcı adı veya şifre!")


def operator_ekrani():
    if st.session_state.notifications:
        for idx, note in enumerate(st.session_state.notifications):
            st.info(f" **1 Yeni Bildiriminiz Var:** {note}")
            if st.button("Bildirimi Kapat", key=f"op_note_{idx}"):
                st.session_state.notifications.pop(idx)
                st.rerun()

    st.title("Saha Operasyon Paneli")
    tab1, tab2, tab3 = st.tabs(["Hat İzleme ", "Geçmiş Analiz", "Genel İşlemler"])

    with tab1:
        active_lines = [
            line for line, value in st.session_state.lines.items() if value["status"] == "Dolu"
        ]
        if not active_lines:
            st.info(
                "Aktif süreç bulunmamaktadır. 'Genel İşlemler' sekmesinden yeni üretim başlatabilirsiniz."
            )
        else:
            sel_line = st.selectbox("İzlenecek Hattı Seçin", active_lines)
            prod = st.session_state.active_productions[sel_line]
            days_passed = (date.today() - prod["start_date"]).days
            ideal = get_phase_data(days_passed)

            st.markdown(
                f"**Üretim ID:** `{prod['prod_id']}` | **Üretim Tanımı:** `{prod['prod_desc']}` | **Gün:** {days_passed}/45 | **Evre:** {ideal['evre']}"
            )

            st.markdown("Sensör Değerleri")

            kat_verisi = render_kat_sensorleri(ideal)

            st.write("")
            try:
                tahmin_kalan = PREDICTION_PROVIDER.predict(kat_verisi)
            except Exception as exc:
                st.warning(f"Hasat tahmini üretilemedi: {exc}")
                tahmin_kalan = None
            if tahmin_kalan is not None:
                st.success(
                    f"{sel_line} hattındaki '{prod['prod_desc']}' ürününün hasadına tahmini **{int(tahmin_kalan)} gün** kalmıştır."
                )
            else:
                st.info(
                    "'trained_model.pkl' yüklenmedi. Model dosyası dizine "
                    "eklendiğinde gün tahmini burada görüntülenecektir."
                )

            st.divider()
            st.subheader("Kalite Kontrol ")
            model, model_durumu = load_yolo_model()
            cam_aktif = st.checkbox("Canlı Sağlık Analiz Kamerasını Aç")
            warning_placeholder = st.empty()
            FRAME_WINDOW = st.image([])

            if cam_aktif:
                cap = cv2.VideoCapture(0)
                while cam_aktif:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    if YOLO_AVAILABLE and model is not None and not isinstance(model, str):
                        results = model(frame, verbose=False)
                        annotated_frame = results[0].plot()
                        if len(results[0].boxes) > 0:
                            warning_placeholder.error(
                                "🚨 UYARI: Bitki dokusunda anomali / hastalık bölgesi tespit edildi!"
                            )
                        else:
                            warning_placeholder.empty()
                    else:
                        annotated_frame = frame.copy()
                        cv2.putText(
                            annotated_frame,
                            "YOLO ENTEGRASYONU AKTIF",
                            (30, 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (0, 255, 0),
                            2,
                        )
                    FRAME_WINDOW.image(
                        cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB),
                        channels="RGB",
                        use_container_width=True,
                    )
                cap.release()

            st.divider()
            st.subheader("Anomali Bildirim Formu")
            with st.form("hata_formu", clear_on_submit=True):
                issue = st.text_area("Hattaki Problemi Açıklayın:")
                if st.form_submit_button("Admin Paneline Gönder", type="primary") and issue:
                    st.session_state.alerts.append(
                        {
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "line": sel_line,
                            "msg": issue,
                            "status": "Yeni",
                        }
                    )
                    st.success("Hata raporlandı.")

    with tab2:
        st.subheader("Geçmiş Veri İnceleme")
        if not st.session_state.archive:
            st.info("Sistem arşivinde henüz tamamlanmış bir üretim kaydı bulunmuyor.")
        else:
            df_arch = pd.DataFrame(st.session_state.archive)
            c_search, c_sort = st.columns([2, 1])
            with c_search:
                q = st.text_input("Kelime ile Ara (Tanım, Hat veya ID):")
            with c_sort:
                s_col = st.selectbox(
                    "Sıralama Kriteri:",
                    ["Başlangıç Tarihi", "Bitiş Tarihi", "Hat", "Üretim Tanımı"],
                )

            if q:
                df_arch = df_arch[
                    df_arch.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)
                ]

            sort_map = {
                "Başlangıç Tarihi": "start_date",
                "Bitiş Tarihi": "end_date",
                "Hat": "line",
                "Üretim Tanımı": "prod_desc",
            }
            df_arch = df_arch.sort_values(by=sort_map[s_col])
            st.dataframe(df_arch, use_container_width=True)

    with tab3:
        r1_c1, r1_c2 = st.columns(2)
        with r1_c1:
            st.subheader("Üretim Başlat")
            with st.form("u_baslat"):
                empty_lines = [
                    line
                    for line, value in st.session_state.lines.items()
                    if value["status"] == "Boş"
                ]
                t_line = st.selectbox("Boş Üretim Hattı Seçin", empty_lines)
                p_desc = st.text_input("Üretim Tanımı (Operatör Açıklaması)")
                if st.form_submit_button("Süreci Tetikle", type="primary") and t_line and p_desc:
                    new_pk = f"PRD-{st.session_state.prod_counter}"
                    st.session_state.active_productions[t_line] = {
                        "prod_id": new_pk,
                        "prod_desc": p_desc,
                        "start_date": date.today(),
                    }
                    st.session_state.lines[t_line]["status"] = "Dolu"
                    st.session_state.prod_counter += 1
                    st.success(f"Başarılı! {new_pk}")
                    st.rerun()

        with r1_c2:
            st.subheader("Üretim Bitir")
            with st.form("u_bitir"):
                active_lines_list = [
                    line
                    for line, value in st.session_state.lines.items()
                    if value["status"] == "Dolu"
                ]
                f_line = st.selectbox("Hasat Edilecek Hattı Seçin", active_lines_list)
                if st.form_submit_button("Hasadı Onayla ve Arşivle", type="primary") and f_line:
                    p_info = st.session_state.active_productions[f_line]
                    st.session_state.archive.append(
                        {
                            "prod_id": p_info["prod_id"],
                            "prod_desc": p_info["prod_desc"],
                            "line": f_line,
                            "start_date": p_info["start_date"],
                            "end_date": date.today(),
                        }
                    )
                    st.session_state.lines[f_line]["status"] = "Boş"
                    del st.session_state.active_productions[f_line]
                    st.success("Süreç bitirildi ve veri tabanına eklendi.")
                    st.rerun()

        st.divider()
        r2_c1, r2_c2 = st.columns(2)
        with r2_c1:
            st.subheader("Hat Başlat")
            with st.form("h_ekle"):
                h_name = st.text_input("Eklenecek Yeni Hat Kodu:")
                if st.form_submit_button("Hattı Devreye Al"):
                    if h_name and h_name not in st.session_state.lines:
                        st.session_state.lines[h_name] = {"status": "Boş"}
                        st.success(f"{h_name} başarıyla sisteme eklendi.")
                        st.rerun()

        with r2_c2:
            st.subheader("Hat Bitir")
            with st.form("h_sil"):
                deletable_lines = [
                    line
                    for line, value in st.session_state.lines.items()
                    if value["status"] == "Boş"
                ]
                h_del = st.selectbox("Kapatılacak Boş Hattı Seçin", deletable_lines)
                if st.form_submit_button("Hattı Kapat"):
                    if h_del:
                        st.session_state.lines[h_del]["status"] = "Pasif"
                        st.success(f"{h_del}'Pasif' moda çekildi.")
                        st.rerun()


def admin_ekrani():
    st.title("Sistem Sorumlusu Kontrol Sayfası")
    st.divider()

    col_sys, col_err = st.columns([1, 1])
    with col_sys:
        st.subheader(" Hat İletişim Durumu ve Sensör Gözlem")
        valid_lines = {k: v for k, v in st.session_state.lines.items() if v["status"] != "Pasif"}
        for h, v in valid_lines.items():
            st.write(f" **{h} Gateway:** Bağlantı Aktif | Durum: `{v['status']}`")

        st.write("")
        all_active = [
            line for line, value in st.session_state.lines.items() if value["status"] == "Dolu"
        ]
        if all_active:
            admin_sel_line = st.selectbox(
                "Sensörlerini Canlı İncelemek İstediğiniz Aktif Hattı Seçin:", all_active
            )
            prod = st.session_state.active_productions[admin_sel_line]
            days = (date.today() - prod["start_date"]).days
            render_kat_sensorleri(get_phase_data(days))

    with col_err:
        st.subheader("Operatör Arıza / Anomali Masası")
        if not st.session_state.alerts:
            st.success("Sistemde müdahale bekleyen arıza bildirimi yok.")
        else:
            for i, a in enumerate(st.session_state.alerts):
                with st.expander(f"Hata Alarmı: {a['line']} - Zaman: {a['time']}", expanded=True):
                    st.error(a["msg"])
                    if st.button("Sorunu Gider ve Operatöre Bildir", key=f"adm_fix_{i}"):
                        st.session_state.notifications.append(
                            f"{a['line']} hattında bildirdiğiniz '{a['msg']}' sorunu Admin tarafından çözülmüştür."
                        )
                        st.session_state.alerts.pop(i)
                        st.rerun()

    st.divider()
    st.subheader("Sistemdeki Tüm Aktif Üretimler")
    render_aktif_tablo()


def render_aktif_tablo():
    data = []
    for line, production in st.session_state.active_productions.items():
        days = (date.today() - production["start_date"]).days
        data.append(
            {
                "Veritabanı ID (PK)": production["prod_id"],
                "Üretim Tanımı": production["prod_desc"],
                "Hat": line,
                "Başlangıç Tarihi": production["start_date"],
                "Mevcut Gün": f"{days} / 45",
                "Evre": get_phase_data(days)["evre"],
            }
        )
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    else:
        st.info("Şu an sahada aktif bir üretim bulunmuyor.")


def yonetici_ekrani():
    st.title("Tesis Genel Analiz ve Yönetim Paneli")
    st.divider()

    valid_lines = {k: v for k, v in st.session_state.lines.items() if v["status"] != "Pasif"}
    total_capacity = len(valid_lines)
    active_count = len(st.session_state.active_productions)

    active_errors = len(st.session_state.alerts)
    availability = (active_count - active_errors) / total_capacity if total_capacity > 0 else 0.0
    availability = max(0.0, availability)

    if active_count > 0:
        prog_list = [
            min(100, ((date.today() - v["start_date"]).days / 45) * 100)
            for v in st.session_state.active_productions.values()
        ]
        performance = sum(prog_list) / (active_count * 100)
    else:
        performance = 0.0

    error_lines = len(set([a["line"] for a in st.session_state.alerts]))
    quality = (active_count - error_lines) / active_count if active_count > 0 else 1.0

    calculated_oee = (availability * performance * quality) * 100
    doluluk_orani = (active_count / total_capacity) * 100 if total_capacity > 0 else 0

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Kapasite Doluluk Oranı",
        f"%{doluluk_orani:.1f}",
        f"{active_count} Aktif / {total_capacity} Hat",
    )
    m2.metric("Sistem Kalite İndeksi", f"%{quality*100:.1f}")
    m3.metric("OEE Puanı", f"%{calculated_oee:.1f}")

    st.write("")
    c_g1, c_g2 = st.columns(2)
    with c_g1:
        st.subheader("Üretim Hatlarının Hasat Yaklaşım Yüzdeleri")
        progress_dict = {}
        for line, production in st.session_state.active_productions.items():
            days = (date.today() - production["start_date"]).days
            progress_dict[production["prod_desc"]] = min(100.0, (days / 45) * 100)
        if progress_dict:
            st.bar_chart(pd.Series(progress_dict))
        else:
            st.info("Çizilecek aktif hat verisi yok.")

    with c_g2:
        st.subheader("Tesis Genel Durum Analiz Özeti")
        status_counts = {"Boş": 0, "Dolu": 0, "Pasif": 0}
        for v in st.session_state.lines.values():
            status_counts[v["status"]] = status_counts.get(v["status"], 0) + 1
        st.dataframe(pd.DataFrame([status_counts], index=["Hat Sayısı"]), use_container_width=True)

    st.divider()
    st.subheader("📋 Aktif Üretim Detay Analiz Tablosu")
    render_aktif_tablo()


def main():
    if not st.session_state.auth["logged_in"]:
        login()
    else:
        with st.sidebar:
            st.markdown(f"**Operatör Kimliği:** `{st.session_state.auth['user']}`")
            st.markdown(f"**Sistem Yetki Rolü:** `{st.session_state.auth['role']}`")
            st.write("")
            if st.button("Güvenli Oturumu Kapat", use_container_width=True, type="secondary"):
                st.session_state.auth = {"logged_in": False, "role": None, "user": None}
                st.rerun()

        r = st.session_state.auth["role"]
        if r == "OPERATOR":
            operator_ekrani()
        elif r == "ADMIN":
            admin_ekrani()
        elif r == "YONETICI":
            yonetici_ekrani()


if __name__ == "__main__":
    main()
