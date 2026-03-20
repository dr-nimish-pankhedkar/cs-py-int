import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="CoilSim Digital Twin", layout="wide")

# --- 2. DATABASE UTILITY ---
def get_db_data(query):
    try:
        creds = st.secrets
        encoded_pass = urllib.parse.quote_plus(creds["db_password"])
        conn_str = f"postgresql://{creds['db_user']}:{encoded_pass}@{creds['db_host']}:{creds['db_port']}/{creds['db_name']}"
        engine = create_engine(conn_str, connect_args={'connect_timeout': 10})
        return pd.read_sql(query, engine)
    except Exception:
        return pd.DataFrame()

# --- 3. DATA RETRIEVAL (STRICTLY COMPLETED RUNS) ---
tasks_df = get_db_data("""
    SELECT * FROM cs_py_int.simulation_tasks 
    WHERE status = 'Completed' 
    ORDER BY completed_at DESC LIMIT 1
""")

hb_df = get_db_data("SELECT * FROM cs_py_int.worker_heartbeat WHERE worker_name = 'CoilSim_SQL_Worker_01'")

# --- 4. HEADER ---
if not tasks_df.empty:
    latest = tasks_df.iloc[0]
    last_ts = latest['completed_at'].strftime("%d-%b-%Y %H:%M:%S")
    st.markdown(f"### 🔥 CoilSim 1D Digital Twin | <span style='color:#d32f2f;'>Last Update: {last_ts}</span>", unsafe_allow_html=True)
else:
    st.title("🏭 CoilSim 1D | Digital Twin")

# --- 5. DATA PROCESSING ---
cot_display, flow_display = "---", "---"
profile_df = pd.DataFrame()
yield_df = pd.DataFrame()

if not tasks_df.empty:
    latest = tasks_df.iloc[0]
    tid = latest['id']
    cot_display = f"{latest['cot_input']:.1f}" if pd.notnull(latest['cot_input']) else "---"
    flow_display = f"{latest['flow_input']:.0f}" if pd.notnull(latest['flow_input']) else "---"
    
    profile_df = get_db_data(f"SELECT axial_position, tgas, mass_conversion FROM cs_py_int.profile_details WHERE task_id = {tid} ORDER BY axial_position")
    yield_df = get_db_data(f'SELECT component_name as "Component", yield_value as "Yield" FROM cs_py_int.yield_history WHERE task_id = {tid} ORDER BY yield_value DESC')

# --- 6. MAIN LAYOUT ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Process Schematic")
    
    # NEW SVG: 4-Pass W-Coil with Circular U-Bends (Engineering Front View)
    svg_html = f"""
    <div style="background:#ffffff; padding:20px; border-radius:12px; border:1px solid #ddd; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
        <svg viewBox="0 0 400 350" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto;">
            <defs>
                <marker id="ar" markerWidth="8" markerHeight="8" refX="0" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#d32f2f" /></marker>
                <marker id="ab" markerWidth="8" markerHeight="8" refX="0" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#1976d2" /></marker>
            </defs>
            
            <rect x="60" y="80" width="280" height="210" fill="#fcfcfc" stroke="#999" stroke-width="2" />
            <line x1="60" y1="80" x2="340" y2="80" stroke="#444" stroke-width="4" /> <rect x="100" y="30" width="12" height="260" fill="#f39c12" stroke="#e67e22" stroke-width="1" />
            <path d="M 100 290 Q 130 330 160 290" fill="none" stroke="#e67e22" stroke-width="10" stroke-linecap="round" />
            <rect x="154" y="110" width="12" height="180" fill="#f39c12" stroke="#e67e22" stroke-width="1" />
            <path d="M 160 110 Q 185 70 210 110" fill="none" stroke="#e67e22" stroke-width="10" stroke-linecap="round" />
            <rect x="204" y="110" width="12" height="180" fill="#f39c12" stroke="#e67e22" stroke-width="1" />
            <path d="M 210 290 Q 240 330 270 290" fill="none" stroke="#e67e22" stroke-width="10" stroke-linecap="round" />
            <rect x="264" y="30" width="12" height="260" fill="#f39c12" stroke="#e67e22" stroke-width="1" />

            <line x1="106" y1="10" x2="106" y2="25" stroke="#1976d2" stroke-width="2" marker-end="url(#ab)" />
            <text x="106" y="5" fill="#1976d2" font-size="10" font-family="sans-serif" font-weight="bold" text-anchor="middle">FEED: {flow_display} kg/h</text>
            
            <line x1="270" y1="25" x2="270" y2="5" stroke="#d32f2f" stroke-width="2" marker-end="url(#ar)" />
            <text x="270" y="45" fill="#d32f2f" font-size="10" font-family="sans-serif" font-weight="bold" text-anchor="middle">COT: {cot_display} °C</text>
        </svg>
    </div>
    """
    components.html(svg_html, height=380)

    st.write("---")
    if not yield_df.empty:
        st.subheader(f"🧪 Product Slate (Run #{tid})")
        top_yields = yield_df.head(10).copy().sort_values("Yield", ascending=True)
        fig_y = go.Figure(go.Bar(x=top_yields["Yield"], y=top_yields["Component"], orientation='h',
                                 marker=dict(color=top_yields["Yield"], colorscale='Viridis'),
                                 text=top_yields["Yield"].apply(lambda x: f"{x:.2f}%"), textposition='outside'))
        fig_y.update_layout(template="plotly_white", height=350, margin=dict(l=10, r=40, t=0, b=0), xaxis=dict(visible=False))
        st.plotly_chart(fig_y, use_container_width=True, config={'displayModeBar': False})

with col2:
    st.subheader("Lengthwise Profiles")
    if not profile_df.empty and len(profile_df) > 1:
        try:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['tgas'], name="Tgas (°C)", line=dict(color="#d32f2f", width=3)))
            fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['mass_conversion'], name="Conv (%)", yaxis="y2", line=dict(color="#1976d2", dash='dash', width=3)))
            
            # FIXED PLOTLY CALL: Removed nested titlefont to prevent ValueError
            fig.update_layout(
                template="plotly_white", height=550, margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Axial Position [m]"),
                yaxis=dict(title="Tgas (°C)", titlefont=dict(color="#d32f2f")),
                yaxis2=dict(title="Conv (%)", titlefont=dict(color="#1976d2"), overlaying="y", side="right"),
                legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info("Refreshing graph coordinates...")
    else:
        st.info("📊 Awaiting lengthwise profile data...")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Worker Status")
    if not hb_df.empty:
        st.success("CoilSim Worker: Online")
        st.caption(f"Pulse: {hb_df.iloc[0]['last_pulse'].strftime('%H:%M:%S')}")
    else:
        st.error("Worker: Offline")
