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
st_autorefresh(interval=30000, key="datarefresh") # 30s refresh for live demo

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
# Get the single most recent completed task
tasks_df = get_db_data("""
    SELECT * FROM cs_py_int.simulation_tasks 
    WHERE status = 'Completed' 
    ORDER BY completed_at DESC LIMIT 1
""")

# Fetch the background worker's heartbeat
hb_df = get_db_data("SELECT * FROM cs_py_int.worker_heartbeat WHERE worker_name = 'CoilSim_SQL_Worker_01'")

st.title("🏭 CoilSim 1D | Cracking Furnace Digital Twin")

# --- PLACEHOLDER LOGIC ---
# Define defaults to prevent crashes if the database is empty
if tasks_df.empty:
    cot_display, flow_display = "---", "---"
    profile_df = pd.DataFrame()
else:
    latest = tasks_df.iloc[0]
    # Fetch the profile for this specific latest task
    profile_df = get_db_data(f"SELECT * FROM cs_py_int.profile_details WHERE task_id = {latest['id']} ORDER BY axial_position")
    
    # Value Formatting for Schematic
    cot_display = f"{latest['cot_input']:.1f}" if not pd.isna(latest['cot_input']) else "---"
    flow_display = f"{latest['flow_input']:.0f}" if not pd.isna(latest['flow_input']) else "---"

# --- MAIN DASHBOARD LAYOUT ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Process Schematic")
    
    # Custom W-Coil SVG (Derived from drawing image_0.png) on White Background
    # The image X-axis represents vertical position, and the Y-axis represents length of coil, providing the informative instructive value for CoilSim 1D Digital Twin.
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
            <text x="200" y="50" fill="#495057" font-size="14" font-family="sans-serif" font-weight="bold" text-anchor="middle">Radiant Section</text>
            
            <path d="M 100 280 
                     L 100 80
                     L 160 240
                     L 220 80
                     L 280 240
                     L 280 40" 
                  fill="none" 
                  stroke="#f39c12" 
                  stroke-width="5" 
                  stroke-linecap="round" 
                  stroke-linejoin="round" />
            
            <line x1="100" y1="310" x2="100" y2="285" stroke="#1976d2" stroke-width="3" marker-end="url(#arrow_blue)" />
            <text x="100" y="315" fill="#1976d2" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">INLET: HC FLOW</text>
            
            <text x="50" y="295" fill="#1976d2" font-size="18" font-family="sans-serif" font-weight="bold">{flow_display} kg/h</text>
            
            <line x1="280" y1="35" x2="280" y2="10" stroke="#d32f2f" stroke-width="3" marker-end="url(#arrow_red)" />
            <text x="280" y="55" fill="#d32f2f" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">OUTLET: COT</text>
            
            <text x="330" y="35" fill="#d32f2f" font-size="18" font-family="sans-serif" font-weight="bold">{cot_display} °C</text>
            
        </svg>
    </div>
    """
    components.html(svg_html, height=380)
    # The "ID Status" section previously located here has been removed per request.

with col2:
    st.subheader("Lengthwise Profiles")
    # THE TRACEBACK FIX: Added conditional check to ensure profile_df is not empty
    if not profile_df.empty:
        # Dual-Y Axis Plotly Chart (White Theme)
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
        
        # Applying the layout settings (This section caused the ValueError when profile_df was empty)
        fig.update_layout(
            template="plotly_white", 
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0,r=0,t=0,b=0),
            xaxis=dict(title="Axial Position [m]", gridcolor="#eee"),
            yaxis=dict(title="Tgas (°C)", gridcolor="#eee", titlefont=dict(color="#d32f2f")),
            # Define secondary y-axis logic (overlaying primary)
            yaxis2=dict(title="Conversion (%)", overlaying="y", side="right", gridcolor="#eee", titlefont=dict(color="#1976d2")),
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Shown if no completed tasks or if the latest task has no profile rows
        st.info("📊 Awaiting lengthwise profile data collection...")

# --- BOTTOM FOOTER / HEARTBEAT ---
st.divider()
with st.sidebar:
    st.header("⚙️ Worker Status")
    if not hb_df.empty:
        hb_row = hb_df.iloc[0]
        st.success(f"CoilSim Worker: Online")
        st.write(f"**Current State:** {hb_row['status_message']}")
        st.caption(f"Last Heartbeat: {hb_row['last_pulse']}")
    else:
        st.error("CoilSim Worker: Offline")
        st.caption("Check server or worker logs.")
