import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

# --- 1. PAGE CONFIGURATION & CSS ---
st.set_page_config(page_title="CoilSim Digital Twin", layout="wide")

# 30-second autorefresh for live data feel
st_autorefresh(interval=30000, key="datarefresh") 

# --- 2. DATABASE UTILITY FUNCTION ---
# This function centralizes all DB connection logic using st.secrets
def get_db_data(query):
    try:
        # Pull connection parameters from Streamlit Secrets
        creds = st.secrets
        user = creds["db_user"]
        password = creds["db_password"]
        host = creds["db_host"]
        port = creds["db_port"]
        dbname = creds["db_name"]
        
        # URL-encode password to handle special characters
        encoded_pass = urllib.parse.quote_plus(password)
        
        # Create connection string and SQLAlchemy engine
        conn_str = f"postgresql://{user}:{encoded_pass}@{host}:{port}/{dbname}"
        engine = create_engine(conn_str, connect_args={'connect_timeout': 10})
        
        # Execute query and return as Pandas DataFrame
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"❌ Database Connection Error: {e}")
        # Return empty DataFrame so subsequent logic doesn't crash
        return pd.DataFrame()

# --- 3. DATA RETRIEVAL ---
# Note: Ensure the tables exist in the 'cs_py_int' schema on the external host

# Fetch the single most recent simulation task
tasks_df = get_db_data("SELECT * FROM cs_py_int.simulation_tasks ORDER BY created_at DESC LIMIT 1")

# Fetch the background worker's liveness heartbeat
hb_df = get_db_data("SELECT * FROM cs_py_int.worker_heartbeat WHERE worker_name = 'CoilSim_SQL_Worker_01'")

# --- 4. MAIN UI EXECUTION ---
st.title("🔥 CoilSim 1D | Cracking Furnace Digital Twin")

# --- CONNECTIVITY DEBUGGER (Optional, can be removed after testing) ---
with st.expander("🛠️ Connectivity Debugger", expanded=True):
    st.write(f"**Current Target Host:** `{st.secrets['db_host']}`")
    st.write(f"**Schema:** `cs_py_int`")
    st.write(f"**Rows found in tasks:** {len(tasks_df)}")
    if not tasks_df.empty:
        latest = tasks_df.iloc[0]
        st.write(f"**Latest Task ID:** `{latest['id']}` | **Status:** `{latest['status']}`")

# --- PLACEHOLDER LOGIC ---
# Define defaults to prevent crashes if the database is currently empty
if tasks_df.empty:
    latest = {'id': 'N/A', 'status': 'No Data', 'cot_input': 0.0, 'flow_input': 0.0}
    profile_df = pd.DataFrame()
else:
    latest = tasks_df.iloc[0]
    # Fetch the lengthwise profile data specifically for this latest task ID
    profile_df = get_db_data(f"SELECT * FROM cs_py_int.profile_details WHERE task_id = {latest['id']} ORDER BY axial_position")

# --- MAIN DASHBOARD LAYOUT ---
col1, col2 = st.columns([1, 1.2]) # Left column smaller than right for balanced graphs

# --- COL 1: SCHEMATIC & STATUS ---
with col1:
    st.subheader("Process Schematic")
    
    # 1. Formatting Display Values
    # Format COT to 1 decimal place, Flow to 0 (integer-like), or show "---" if NULL
    cot_display = f"{latest['cot_input']:.1f}" if not pd.isna(latest['cot_input']) else "---"
    flow_display = f"{latest['flow_input']:.0f}" if not pd.isna(latest['flow_input']) else "---"
    
    # 2. Updated W-Coil SVG Schematic (High-Fidelity)
    # The SVG contains a background furnace box, a distinct W-shaped process coil, 
    # and labels positioning input flow and output temperature.
    svg_html = f"""
    <div style="background:#111; padding:20px; border-radius:15px; border:2px solid #444; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto;">
            <defs>
                <marker id="arrow" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto">
                    <path d="M0,0 L0,6 L9,3 z" fill="#ff4b4b" />
                </marker>
            </defs>
            
            <rect x="100" y="50" width="200" height="200" fill="#222" stroke="#444" stroke-width="3" rx="10" ry="10" />
            <text x="200" y="40" fill="white" font-size="16" font-family="sans-serif" font-weight="bold" text-anchor="middle">Cracking Zone (Radiant Section)</text>
            
            <path d="M 120 70 
                     L 160 210
                     L 200 70
                     L 240 210
                     L 280 70" 
                  fill="none" 
                  stroke="#ff9f43" 
                  stroke-width="6" 
                  stroke-linecap="round" 
                  stroke-linejoin="round"
                  style="filter: drop-shadow(0px 0px 5px rgba(255,159,67,0.5));" />
            
            <line x1="120" y1="20" x2="120" y2="65" stroke="#ff4b4b" stroke-width="4" marker-end="url(#arrow)" />
            <text x="120" y="15" fill="#00d1b2" font-size="14" font-family="sans-serif" font-weight="bold" text-anchor="middle">INLET: HC FLOW</text>
            
            <rect x="10" y="30" width="100" height="40" rx="5" fill="#00d1b2" fill-opacity="0.1" />
            <text x="60" y="55" fill="#00d1b2" font-size="20" font-family="sans-serif" font-weight="bold" text-anchor="middle">{flow_display}</text>
            <text x="60" y="75" fill="#00d1b2" font-size="12" font-family="sans-serif" text-anchor="middle">kg/h</text>
            
            <line x1="280" y1="65" x2="280" y2="20" stroke="#ff4b4b" stroke-width="4" marker-end="url(#arrow)" />
            <text x="280" y="15" fill="#ff4b4b" font-size="14" font-family="sans-serif" font-weight="bold" text-anchor="middle">OUTLET: COT</text>
            
            <rect x="290" y="30" width="100" height="40" rx="5" fill="#ff4b4b" fill-opacity="0.1" />
            <text x="340" y="55" fill="#ff4b4b" font-size="20" font-family="sans-serif" font-weight="bold" text-anchor="middle">{cot_display}</text>
            <text x="340" y="75" fill="#ff4b4b" font-size="12" font-family="sans-serif" text-anchor="middle">°C</text>
            
        </svg>
    </div>
    """
    components.html(svg_html, height=350)
    
    # 3. Task Progress Metrics
    st.write("---")
    m1, m2 = st.columns(2)
    with m1:
        st.metric("Current Run ID", latest['id'])
    with m2:
        # Display status (Completed, Processing, Pending, Error)
        st.metric("Engine Status", latest['status'])

# --- COL 2: DYNAMIC PROFILES ---
with col2:
    st.subheader("Lengthwise Profiles (Live)")
    if not profile_df.empty:
        # Dual-Y Axis Plotly Chart
        fig = go.Figure()
        
        # Primary Variable: Gas Temperature (Left Axis, Red Line)
        fig.add_trace(go.Scatter(
            x=profile_df['axial_position'], 
            y=profile_df['tgas'], 
            name="Gas Temp (°C)", 
            line=dict(color="#ff4b4b", width=3)
        ))
        
        # Secondary Variable: Mass Conversion (Right Axis, Cyan Dashed Line)
        fig.add_trace(go.Scatter(
            x=profile_df['axial_position'], 
            y=profile_df['mass_conversion'], 
            name="Methane Conv (%)", 
            yaxis="y2", 
            line=dict(color="#00d1b2", dash='dash', width=3)
        ))
        
        # Plot Styling (Dark Theme, Transparent Background)
        fig.update_layout(
            template="plotly_dark", 
            height=400,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0,r=0,t=0,b=0),
            xaxis=dict(title="Reactor Length (Axial Position) [m]", gridcolor="#333"),
            yaxis=dict(title="Gas Temperature (°C)", gridcolor="#333", titlefont=dict(color="#ff4b4b")),
            # Define secondary y-axis logic (overlaying primary)
            yaxis2=dict(title="Conversion (%)", overlaying="y", side="right", gridcolor="#333", titlefont=dict(color="#00d1b2")),
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        # Shown if a task exists, but the 'profile_details' table doesn't have data yet
        st.info("📊 Simulation in progress or awaiting profile data data collection for this task...")

# --- BOTTOM FOOTER / HEARTBEAT ---
st.divider()
with st.sidebar:
    st.header("⚙️ Worker Status")
    if not hb_df.empty:
        hb_row = hb_df.iloc[0]
        st.success(f"CoilSim Worker: Online")
        # Display the custom message set by the backend worker script
        st.write(f"**Current State:** {hb_row['status_message']}")
        st.caption(f"Last Heartbeat: {hb_row['last_pulse']}")
    else:
        st.error("CoilSim Worker: Offline")
        st.caption("Check server or worker logs.")
