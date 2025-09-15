import streamlit as st
import hashlib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import gdown, tempfile, os
from pathlib import Path

st.set_page_config(page_title="MNC Insurance Actuarial Website", layout="wide")

# ===================== GOOGLE DRIVE CONFIG =====================
# Ambil FILE_ID dari link:
# Contoh link: https://drive.google.com/file/d/1EUvHNcgg5rqznMFKA9lRmUSSX9eYqw0B/view?usp=sharing
# FILE_ID = "1EUvHNcgg5rqznMFKA9lRmUSSX9eYqw0B"
FILE_ID = "1EUvHNcgg5rqznMFKA9lRmUSSX9eYqw0B"

def load_df_from_gdrive_gdown() -> pd.DataFrame:
    """
    Download file Parquet dari Google Drive menggunakan gdown,
    lalu baca ke pandas. Pastikan file Drive diset 'Anyone with the link - Viewer'.
    """
    tmpdir = tempfile.mkdtemp()
    out_path = os.path.join(tmpdir, "data.parquet")
    # gdown akan handle konfirmasi download untuk file besar
    gdown.download(id=FILE_ID, output=out_path, quiet=True)
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError("Unduhan dari Google Drive gagal atau file kosong.")
    return pd.read_parquet(out_path, engine="pyarrow")

# ===================== USER AUTH (hash blake2b) =====================
USERS = {
    # username_hashed : password_hashed (keduanya blake2b.hexdigest())
    "568622d8836e4856d75132f68bc2cdb16ee788ad6b72f74bc264f9757d8a54ded1c02cf2bb37b59420bc9f43dcd297b9a828d5f673d9a977b68b724650b1442a":
    "db1bc89118ae73eea00e2de5868a96cd25a80c3eb6cd62639a921ba5abfc1b6bee91783fc1a1167dc3e14966c56a23237eb635dfb4529f3ddbe533c9b8d609f4"
}

def b2b_hex(s: str) -> str:
    return hashlib.blake2b(s.encode("utf-8")).hexdigest()

# ===================== HEADER =====================
st.title("MNC Insurance Actuarial Website")
st.markdown(
    """
    <p style='color:gray; font-size:14px;'>
    Aplikasi ini masih dalam tahap pengembangan, bug, kritik, dan saran dapat disampaikan ke 
    <a href="mailto:henry.sihombing@mnc-insurance.com">henry.sihombing@mnc-insurance.com</a>
    </p>
    <hr style="border:1px solid #bbb; margin:20px 0;">
    """,
    unsafe_allow_html=True
)

# ===================== SESSION STATE =====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ===================== LOGIN =====================
if not st.session_state.logged_in:
    username_input = st.text_input("Masukkan Username")
    password_input = st.text_input("Masukkan Password", type="password")

    if st.button("Login", type="primary"):
        username_hashed = b2b_hex(username_input)
        password_hashed = b2b_hex(password_input)

        if username_hashed in USERS and USERS[username_hashed] == password_hashed:
            st.session_state.logged_in = True
            st.success("Login berhasil!")
            st.rerun()
        else:
            st.error("! Username atau password salah")

# ===================== MAIN (SETELAH LOGIN) =====================
else:
    # Sidebar: logout
    with st.sidebar:
        st.caption("📁 Data source: Google Drive via gdown")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    st.subheader("Optimum Share and CoR Calculator")

    # --- Load data SETELAH login ---
    try:
        df = load_df_from_gdrive_gdown()
    except Exception as e:
        st.error("Gagal memuat data dari Google Drive. Pastikan:\n"
                 "- FILE_ID benar\n"
                 "- Share: 'Anyone with the link - Viewer'\n"
                 "- File benar-benar format Parquet")
        st.exception(e)
        st.stop()

    # --- Validasi kolom yang diperlukan ---
    required_cols = {"RISK CODE", "TSI RANGE", "ADJ NET LR", "Suggested Share", "Buffer 15%"}
    missing = required_cols - set(df.columns.astype(str))
    if missing:
        st.error(f"Kolom wajib tidak ditemukan: {missing}")
        st.stop()

    # --- UI Filter ---
    risk_selected = st.selectbox(
        "Pilih RISK CODE",
        options=sorted(df["RISK CODE"].dropna().unique())
    )

    tsi_options = df.loc[df["RISK CODE"] == risk_selected, "TSI RANGE"].dropna().unique()
    tsi_selected = st.selectbox(
        "Pilih TSI RANGE",
        options=sorted(tsi_options)
    )

    # --- Ambil baris terpilih ---
    row = df[
        (df["RISK CODE"] == risk_selected) &
        (df["TSI RANGE"] == tsi_selected)
    ]

    if not row.empty:
        adj_net_lr = float(row["ADJ NET LR"].values[0])            # 0–1
        suggested_share = float(row["Suggested Share"].values[0])  # 0–1
        buffer_15 = float(row["Buffer 15%"].values[0])             # 0–1

        st.markdown(
            f"""
            ### Adjusted Share
            - Share to Retain: **{suggested_share*100:.2f}%**  
            - Share with 15% Buffer: **{buffer_15*100:.2f}%**

            ### Simulated Risk Profile
            - NET Loss Ratio: **{adj_net_lr*100:.2f}%**
            """
        )

        if suggested_share > 0:
            col1, col2 = st.columns(2)
            with col1:
                komisi_ojk = st.number_input(
                    "Masukkan Komisi OJK (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    format="%.2f"
                )
            with col2:
                ovr = st.number_input(
                    "Masukkan OVR (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    format="%.2f"
                )

            if st.button("Calculate CoR", type="primary"):
                OPEX = 15.0
                cor = adj_net_lr*100 + komisi_ojk + ovr + OPEX

                if cor < 100:
                    st.success(f"📊 CoR = **{cor:.2f}%**")
                else:
                    st.markdown(
                        f"<span style='color:#e11d48; font-weight:bold;'>📊 CoR = {cor:.2f}%</span>",
                        unsafe_allow_html=True
                    )

                # ----- Waterfall Chart -----
                st.subheader("Expected UW Result")

                base = 100.0
                values = [
                    -adj_net_lr*100,   # Net LR
                    -komisi_ojk,       # Komisi OJK
                    -ovr,              # OVR
                    -OPEX              # OPEX
                ]
                labels = ["Gross Premium", "Net Loss Ratio", "Komisi OJK", "OVR", "OPEX", "Profit/Loss"]
                measures = ["absolute", "relative", "relative", "relative", "relative", "total"]

                final_val = base + sum(values)
                total_color = "green" if final_val >= 0 else "red"

                fig = go.Figure(go.Waterfall(
                    name="CoR Breakdown",
                    orientation="v",
                    measure=measures,
                    x=labels,
                    text=[f"{base:.2f}%"] + [f"{v:.2f}%" for v in values] + [f"{final_val:.2f}%"],
                    y=[base] + values + [None],  # None untuk total (Plotly hitung otomatis)
                    connector={"line": {"color": "rgb(120,120,120)"}},
                    decreasing={"marker": {"color": "red"}},
                    increasing={"marker": {"color": "blue"}},
                    totals={"marker": {"color": total_color}},
                ))
                fig.update_layout(margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("This risk code is not recommended!")
    else:
        st.warning("Kombinasi RISK CODE & TSI RANGE tidak ditemukan di data.")
