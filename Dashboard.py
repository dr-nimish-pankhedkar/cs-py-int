import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

st.set_page_config(page_title="CoilSim Digital Twin", layout="wide")
st_autorefresh(interval=30000, key="datarefresh") # 30s refresh for live demo

# --- DATABASE CONNECTION ---
def get_db_data(query):
    user, host, port, dbname = "dtwinuser", "192.168.10.189", "8503", "poc-digital-twin"
    password = st.secrets["db_password"]
    conn_str = f"postgresql://{user}:{urllib.parse.quote_plus(password)}@{host}:{port}/{dbname}"
    engine = create_engine(conn_str)
    return pd.read_sql(query, engine)

# --- DATA RETRIEVAL ---
# Get the most recent task
tasks_df = get_db_data("SELECT * FROM cs_py_int.simulation_tasks ORDER BY created_at DESC LIMIT 1")
hb_df = get_db_data("SELECT * FROM cs_py_int.worker_heartbeat WHERE worker_name = 'CoilSim_Worker_01'")

if not tasks_df.empty:
    latest_task = tasks_df.iloc[0]
    # Get the profile for this specific latest task
    profile_df = get_db_data(f"SELECT * FROM cs_py_int.profile_details WHERE task_id = {latest_task['id']} ORDER BY axial_position")

st.title("🔥 CoilSim 1D | Cracking Furnace Digital Twin")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Reactor Schematic")
    # Dynamic Values for SVG
    cot_val = f"{latest_task['cot_input']:.1f}" if not pd.isna(latest_task['cot_input']) else "---"
    flow_val = f"{latest_task['flow_input']:.0f}" if not pd.isna(latest_task['flow_input']) else "---"
    
    # Simple Furnace SVG
    svg_html = f"""
    <div style="background:#1a1a1a; padding:20px; border-radius:15px; border:2px solid #444;">
        <svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
            <rect x="100" y="50" width="200" height="200" fill="#333" stroke="#ff4b4b" stroke-width="4" />
            <path d="M 120 70 Q 150 90 120 110 Q 150 130 120 150 Q 150 170 120 190" fill="none" stroke="#ff9f43" stroke-width="4" />
            <text x="110" y="40" fill="white" font-size="14" font-family="sans-serif">Cracking Furnace</text>
            <text x="20" y="80" fill="#00d1b2" font-size="12">FEED: {flow_val} kg/h</text>
            <text x="310" y="240" fill="#ff4b4b" font-size="12">COT: {cot_val} °C</text>
        </svg>
    </div>
    """
    components.html(svg_html, height=350)
    
    # Progress Tracker
    st.write(f"**Task ID:** {latest_task['id']} | **Status:** {latest_task['status']}")

with col2:
    st.subheader("Lengthwise Profiles (Live)")
    if not profile_df.empty:
        # Tgas and Conversion Plot
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['tgas'], name="Tgas (°C)", line=dict(color="#ff4b4b")))
        fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['mass_conversion'], name="Conversion (%)", yaxis="y2", line=dict(color="#00d1b2", dash='dash')))
        
        fig.update_layout(
            template="plotly_dark", height=400,
            yaxis=dict(title="Temperature (°C)"),
            yaxis2=dict(title="Conversion (%)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()
# Heartbeat & Health
if not hb_df.empty:
    st.sidebar.markdown(f"**Worker:** {hb_df.iloc[0]['status_message']}")
    st.sidebar.caption(f"Last Pulse: {hb_df.iloc[0]['last_pulse']}")
