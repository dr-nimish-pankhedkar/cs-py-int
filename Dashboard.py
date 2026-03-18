import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="CoilSim Digital Twin", layout="wide")
st_autorefresh(interval=30000, key="datarefresh") 

# --- 2. DATABASE UTILITY ---
def get_db_data(query):
    try:
        creds = st.secrets
        encoded_pass = urllib.parse.quote_plus(creds["db_password"])
        conn_str = f"postgresql://{creds['db_user']}:{encoded_pass}@{creds['db_host']}:{creds['db_port']}/{creds['db_name']}"
        engine = create_engine(conn_str, connect_args={'connect_timeout': 10})
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame()

# --- 3. DATA RETRIEVAL ---
tasks_df = get_db_data("SELECT * FROM cs_py_int.simulation_tasks ORDER BY created_at DESC LIMIT 1")
hb_df = get_db_data("SELECT * FROM cs_py_int.worker_heartbeat WHERE worker_name = 'CoilSim_SQL_Worker_01'")

st.title("🔥 CoilSim 1D | Cracking Furnace Digital Twin")

if not tasks_df.empty:
    latest = tasks_df.iloc[0]
    profile_df = get_db_data(f"SELECT * FROM cs_py_int.profile_details WHERE task_id = {latest['id']} ORDER BY axial_position")
    
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("Reactor Schematic")
        cot = f"{latest['cot_input']:.1f}" if latest['cot_input'] else "---"
        flow = f"{latest['flow_input']:.1f}" if latest['flow_input'] else "---"
        
        svg_html = f"""
        <div style="background:#1a1a1a; padding:20px; border-radius:15px; border:2px solid #444;">
            <svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
                <rect x="100" y="50" width="200" height="200" fill="#333" stroke="#ff4b4b" stroke-width="4" />
                <path d="M 120 70 Q 150 90 120 110 Q 150 130 120 150 Q 150 170 120 190" fill="none" stroke="#ff9f43" stroke-width="4" />
                <text x="110" y="40" fill="white" font-size="14" font-family="sans-serif">Cracking Furnace</text>
                <text x="20" y="80" fill="#00d1b2" font-size="12">FEED: {flow} kg/h</text>
                <text x="310" y="240" fill="#ff4b4b" font-size="12">COT: {cot} °C</text>
            </svg>
        </div>
        """
        components.html(svg_html, height=350)
        st.metric("Current Status", latest['status'], delta=f"ID: {latest['id']}")

    with col2:
        st.subheader("Lengthwise Profiles (Live)")
        if not profile_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['tgas'], name="Tgas (°C)", line=dict(color="#ff4b4b")))
            fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['mass_conversion'], name="Conversion (%)", yaxis="y2", line=dict(color="#00d1b2", dash='dash')))
            fig.update_layout(template="plotly_dark", height=400, yaxis=dict(title="Temp (°C)"), yaxis2=dict(title="Conv (%)", overlaying="y", side="right"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Awaiting Profile Data...")

st.divider()
# Sidebar Status
with st.sidebar:
    st.header("⚙️ Worker Status")
    if not hb_df.empty:
        hb = hb_df.iloc[0]
        st.success(f"Worker: Online")
        st.write(f"**State:** {hb['status_message']}")
        st.caption(f"Last Pulse: {hb['last_pulse']}")
    else:
        st.error("Worker: Offline")
