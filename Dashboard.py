import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. PAGE CONFIGURATION ---
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
# Get the most recent completed task
tasks_df = get_db_data("""
    SELECT * FROM cs_py_int.simulation_tasks 
    WHERE status = 'Completed' 
    ORDER BY completed_at DESC LIMIT 1
""")

hb_df = get_db_data("SELECT * FROM cs_py_int.worker_heartbeat WHERE worker_name = 'CoilSim_SQL_Worker_01'")

st.title("🏭 CoilSim 1D | Cracking Furnace Digital Twin")

# --- DATA PROCESSING ---
latest_task_id = None
cot_display, flow_display = "---", "---"
profile_df = pd.DataFrame()

if not tasks_df.empty:
    latest = tasks_df.iloc[0]
    latest_task_id = latest['id']
    cot_display = f"{latest['cot_input']:.1f}" if pd.notnull(latest['cot_input']) else "---"
    flow_display = f"{latest['flow_input']:.0f}" if pd.notnull(latest['flow_input']) else "---"
    
    # Fetch profile
    profile_df = get_db_data(f"SELECT * FROM cs_py_int.profile_details WHERE task_id = {latest_task_id} ORDER BY axial_position")
    # Clean up any potential NaNs in the profile data to prevent Plotly errors
    if not profile_df.empty:
        profile_df = profile_df.dropna(subset=['axial_position', 'tgas', 'mass_conversion'])

# --- MAIN UI ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Process Schematic")
    
    # Simple Vertical W-Coil (White Background)
    svg_html = f"""
    <div style="background:#ffffff; padding:20px; border-radius:12px; border:1px solid #ddd; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
        <svg viewBox="0 0 400 320" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto;">
            <defs>
                <marker id="arrow_red" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto">
                    <path d="M0,0 L0,6 L9,3 z" fill="#d32f2f" />
                </marker>
                <marker id="arrow_blue" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto">
                    <path d="M0,0 L0,6 L9,3 z" fill="#1976d2" />
                </marker>
            </defs>
            <rect x="80" y="60" width="240" height="200" fill="#f8f9fa" stroke="#6c757d" stroke-width="2" rx="5" />
            
            <path d="M 100 280 L 100 80 L 160 240 L 220 80 L 280 240 L 280 40" 
                  fill="none" stroke="#f39c12" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
            
            <line x1="100" y1="310" x2="100" y2="285" stroke="#1976d2" stroke-width="3" marker-end="url(#arrow_blue)" />
            <text x="100" y="325" fill="#1976d2" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">INLET: {flow_display} kg/h</text>
            
            <line x1="280" y1="35" x2="280" y2="10" stroke="#d32f2f" stroke-width="3" marker-end="url(#arrow_red)" />
            <text x="280" y="55" fill="#d32f2f" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">OUTLET: {cot_display} °C</text>
        </svg>
    </div>
    """
    components.html(svg_html, height=380)

with col2:
    st.subheader("Lengthwise Profiles")
    # STRICT CHECK: Ensure profile_df is not empty and has multiple points
    if not profile_df.empty and len(profile_df) > 1:
        try:
            fig = go.Figure()
            
            # Primary Variable: Gas Temperature (Left Axis, Red Line)
            fig.add_trace(go.Scatter(
                x=profile_df['axial_position'], 
                y=profile_df['tgas'], 
                name="Tgas (°C)", 
                line=dict(color="#d32f2f", width=3)
            ))
            
            # Secondary Variable: Mass Conversion (Right Axis, Blue Dashed Line)
            fig.add_trace(go.Scatter(
                x=profile_df['axial_position'], 
                y=profile_df['mass_conversion'], 
                name="Conv (%)", 
                yaxis="y2", 
                line=dict(color="#1976d2", dash='dash', width=3)
            ))
            
            # FIXED LAYOUT: Moved font settings inside the title dictionary
            fig.update_layout(
                template="plotly_white", 
                height=400,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(
                    title=dict(text="Axial Position [m]"), 
                    gridcolor="#eee"
                ),
                yaxis=dict(
                    title=dict(
                        text="Tgas (°C)", 
                        font=dict(color="#d32f2f") # Corrected path
                    ), 
                    gridcolor="#eee"
                ),
                yaxis2=dict(
                    title=dict(
                        text="Conversion (%)", 
                        font=dict(color="#1976d2") # Corrected path
                    ), 
                    overlaying="y", 
                    side="right", 
                    gridcolor="#eee"
                ),
                legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
            )
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as plot_err:
            st.warning(f"Plotting Error: {plot_err}")
    else:
        st.info("📊 Awaiting data: Run the simulation worker to populate profiles.")
        
# --- SIDEBAR ---
st.divider()
with st.sidebar:
    st.header("⚙️ Worker Status")
    if not hb_df.empty:
        hb_row = hb_df.iloc[0]
        st.success("CoilSim Worker: Online")
        st.caption(f"Last Heartbeat: {hb_row['last_pulse']}")
    else:
        st.error("CoilSim Worker: Offline")
