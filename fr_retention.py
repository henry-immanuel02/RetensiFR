import streamlit as st
import hashlib
import numpy as np
import pandas as pd
import plotly.graph_objects as go

url = "https://drive.google.com/file/d/1EUvHNcgg5rqznMFKA9lRmUSSX9eYqw0B/view?usp=sharing"
df = pd.read_parquet(url, engine="pyarrow")

# Simpan user hash di dictionary
users = {
    # username:password (dua-duanya di-hash pakai blake2b.hexdigest())
    '568622d8836e4856d75132f68bc2cdb16ee788ad6b72f74bc264f9757d8a54ded1c02cf2bb37b59420bc9f43dcd297b9a828d5f673d9a977b68b724650b1442a':
    'db1bc89118ae73eea00e2de5868a96cd25a80c3eb6cd62639a921ba5abfc1b6bee91783fc1a1167dc3e14966c56a23237eb635dfb4529f3ddbe533c9b8d609f4'
}

st.title("MNC Insurance Actuarial Website")
st.markdown(
    """
    <p style='color:gray; font-size:14px;'>
    Aplikasi ini masih dalam tahap pengembangan, bug, kritik, dan saran dapat disampaikan ke 
    <a href="mailto:henry.sihombing@mnc-insurance.com">henry.sihombing@mnc-insurance.com</a>
    </p>
    """,
    unsafe_allow_html=True
)
st.markdown(
    """
    <hr style="border:1px solid #bbb; margin:20px 0;">
    """,
    unsafe_allow_html=True
)

# Inisialisasi session_state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Kalau belum login, tampilkan form login
if not st.session_state.logged_in:
    username_input = st.text_input("Masukkan Username")
    password_input = st.text_input("Masukkan Password", type="password")

    if st.button("Login"):
        # Hash input
        username_hashed = hashlib.blake2b(username_input.encode("utf-8")).hexdigest()
        password_hashed = hashlib.blake2b(password_input.encode("utf-8")).hexdigest()

        # Cek ke dictionary
        if username_hashed in users and users[username_hashed] == password_hashed:
            st.session_state.logged_in = True
            st.success("Login berhasil!")
            st.rerun()  # refresh supaya langsung masuk ke halaman berikutnya
        else:
            st.error("! Username atau password salah")



# Kalau sudah login, tampilkan halaman berikutnya
else:
    st.subheader("Optimum Share and CoR Calculator")
    
    # Dropdown pilih Risk Code
    risk_selected = st.selectbox(
        "Pilih RISK CODE",
        options=df["RISK CODE"].unique()
    )

    # Filter TSI berdasarkan risk_selected
    tsi_options = df[df["RISK CODE"] == risk_selected]["TSI RANGE"].unique()

    tsi_selected = st.selectbox(
        "Pilih TSI RANGE",
        options=tsi_options
    )

    # Ambil baris data sesuai pilihan
    row = df[
        (df["RISK CODE"] == risk_selected) &
        (df["TSI RANGE"] == tsi_selected)
    ]

    if not row.empty:
        adj_net_lr = row["ADJ NET LR"].values[0]
        suggested_share = row["Suggested Share"].values[0]
        buffer_15 = row["Buffer 15%"].values[0]

        # Tampilkan informasi
        
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
            # Input tambahan
            komisi_ojk = st.number_input(
                "Masukkan Komisi OJK (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.2f"
            )
            ovr = st.number_input(
                "Masukkan OVR (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
                format="%.2f"
            )

            if st.button("Calculate CoR"):
                cor = adj_net_lr*100 + komisi_ojk + ovr + 15
                if cor < 100:
                    st.success(f"📊 CoR = **{cor:.2f}%**")
                else:
                    st.markdown(
                        f"<span style='color:red; font-weight:bold;'>📊 CoR = {cor:.2f}%</span>",
                        unsafe_allow_html=True
                    )

                # ----- Waterfall Chart -----
                st.subheader("Expected UW Result")

                base = 100
                values = [
                    -adj_net_lr*100,
                    -komisi_ojk,
                    -ovr,
                    -15
                ]

                labels = ["Gross Premium", "Net Loss Ratio", "Komisi OJK", "OVR", "OPEX", "Profit/Loss"]
                measures = ["absolute", "relative", "relative", "relative", "relative", "total"]

                # Tentukan warna akhir (profit/loss)
                final_val = base + sum(values)
                total_color = "green" if final_val > 0 else "red"

                fig = go.Figure(go.Waterfall(
                    name="CoR Breakdown",
                    orientation="v",
                    measure=measures,
                    x=labels,
                    text=[f"{base:.2f}%"] + [f"{v:.2f}%" for v in values] + [f"{final_val:.2f}%"],
                    y=[base] + values + [None],  # None untuk total biar auto dihitung
                    connector={"line":{"color":"rgb(63, 63, 63)"}},
                    decreasing={"marker":{"color":"red"}},
                    increasing={"marker":{"color":"blue"}},
                    totals={"marker":{"color": total_color}}
                ))

                st.plotly_chart(fig, use_container_width=True)

        else:
            st.error("This risk code is not recomended!")

    if st.button("Logout"):
        st.session_state.logged_in = False

        st.rerun()
