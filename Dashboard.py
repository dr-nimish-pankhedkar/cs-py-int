import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

st.set_page_config(page_title="CoilSim Digital Twin", layout="wide")
st_autorefresh(interval=10000, key="datarefresh") # 10s for testing

# --- DATABASE CONNECTION ---
def get_db_data(query):
    try:
        user, host, port, dbname = "dtwinuser", "114.143.58.70", "8503", "poc-digital-twin"
        password = st.secrets["db_password"]
        conn_str = f"postgresql://{user}:{urllib.parse.quote_plus(password)}@{host}:{port}/{dbname}"
        engine = create_engine(conn_str, connect_args={'connect_timeout': 5})
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"❌ DB Connection Error: {e}")
        return pd.DataFrame()

# --- DATA RETRIEVAL ---
tasks_df = get_db_data("SELECT * FROM cs_py_int.simulation_tasks ORDER BY created_at DESC LIMIT 1")
hb_df = get_db_data("SELECT * FROM cs_py_int.worker_heartbeat WHERE worker_name = 'CoilSim_Worker_01'")

st.title("🔥 CoilSim 1D | Cracking Furnace Digital Twin")

# --- DEBUG INFO (REMOVE LATER) ---
with st.expander("🛠️ Connectivity Debugger", expanded=True):
    st.write(f"Tasks found in DB: {len(tasks_df)}")
    if not tasks_df.empty:
        st.write(f"Latest Task ID: {tasks_df.iloc[0]['id']} | Status: {tasks_df.iloc[0]['status']}")

if tasks_df.empty:
    st.warning("⚠️ No simulation tasks found in `cs_py_int.simulation_tasks`. Dashboard will show placeholders.")
    # Placeholders for demo if DB is empty
    latest_task = {'id': 'N/A', 'status': 'No Data', 'cot_input': 0.0, 'flow_input': 0.0}
    profile_df = pd.DataFrame()
else:
    latest_task = tasks_df.iloc[0]
    profile_df = get_db_data(f"SELECT * FROM cs_py_int.profile_details WHERE task_id = {latest_task['id']} ORDER BY axial_position")

# --- MAIN UI ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Reactor Schematic")
    cot_val = f"{latest_task['cot_input']:.1f}" if not pd.isna(latest_task['cot_input']) else "---"
    flow_val = f"{latest_task['flow_input']:.0f}" if not pd.isna(latest_task['flow_input']) else "---"
    
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
    st.write(f"**Current Run ID:** {latest_task['id']} | **Status:** {latest_task['status']}")

with col2:
    st.subheader("Lengthwise Profiles (Live)")
    if not profile_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['tgas'], name="Tgas (°C)", line=dict(color="#ff4b4b")))
        fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['mass_conversion'], name="Conversion (%)", yaxis="y2", line=dict(color="#00d1b2", dash='dash')))
        fig.update_layout(template="plotly_dark", height=400, yaxis=dict(title="Temperature (°C)"), yaxis2=dict(title="Conversion (%)", overlaying="y", side="right"), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Awaiting Profile Data for this task ID...")

st.divider()
if not hb_df.empty:
    st.sidebar.markdown(f"**Worker:** {hb_df.iloc[0]['status_message']}")
    st.sidebar.caption(f"Last Pulse: {hb_df.iloc[0]['last_pulse']}")
else:
    st.sidebar.error("❌ Worker Heartbeat Not Found")
