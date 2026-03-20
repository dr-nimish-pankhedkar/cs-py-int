import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="CoilSim Digital Twin", layout="wide")

# CSS to hide status widgets and clean up padding
st.markdown("""
    <style>
        [data-testid="stStatusWidget"] { visibility: hidden; }
        .block-container { padding-top: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE UTILITY ---
@st.cache_resource
def get_engine():
    creds = st.secrets
    encoded_pass = urllib.parse.quote_plus(creds["db_password"])
    conn_str = f"postgresql://{creds['db_user']}:{encoded_pass}@{creds['db_host']}:{creds['db_port']}/{creds['db_name']}"
    return create_engine(conn_str, connect_args={'connect_timeout': 10})

def get_db_data(query):
    try:
        engine = get_engine()
        return pd.read_sql(query, engine)
    except Exception:
        return pd.DataFrame()

# --- 3. DYNAMIC FRAGMENT (THE REFRESH ZONE) ---
@st.fragment(run_every="30s")
def update_dashboard():
    # A. Fetch Data
    tasks_df = get_db_data("""
        SELECT * FROM cs_py_int.simulation_tasks 
        WHERE status = 'Completed' 
        ORDER BY completed_at DESC LIMIT 1
    """)
    
    if tasks_df.empty:
        st.warning("Awaiting first completed simulation...")
        return

    latest = tasks_df.iloc[0]
    last_ts = latest['completed_at'].strftime("%d-%b-%Y %H:%M:%S")
    
    # Header with Timestamp
    st.markdown(f"### 🔥 CoilSim 1D Digital Twin | <span style='color:#d32f2f;'>Last Update: {last_ts}</span>", unsafe_allow_html=True)

    # B. Process Profiles & Yields
    profile_df = get_db_data(f"SELECT axial_position, tgas, mass_conversion FROM cs_py_int.profile_details WHERE task_id = {latest['id']} ORDER BY axial_position")
    yield_df = get_db_data(f'SELECT component_name as "Component", yield_value as "Yield" FROM cs_py_int.yield_history WHERE task_id = {latest["id"]} ORDER BY yield_value DESC')

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("Process Schematic")
        
        # Define display values
        cot_disp = f"{latest['cot_input']:.1f}" if pd.notnull(latest['cot_input']) else "---"
        flow_disp = f"{latest['flow_input']:.0f}" if pd.notnull(latest['flow_input']) else "---"
        
        # Restore SVG Logic
        svg_html = f"""
        <div style="background:#ffffff; padding:20px; border-radius:12px; border:1px solid #ddd; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
            <svg viewBox="0 0 400 320" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto;">
                <defs>
                    <marker id="ar" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#d32f2f" /></marker>
                    <marker id="ab" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#1976d2" /></marker>
                </defs>
                <rect x="80" y="60" width="240" height="200" fill="#f8f9fa" stroke="#6c757d" stroke-width="2" rx="5" />
                <path d="M 100 280 L 100 80 L 160 240 L 220 80 L 280 240 L 280 40" fill="none" stroke="#f39c12" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
                <line x1="100" y1="310" x2="100" y2="285" stroke="#1976d2" stroke-width="3" marker-end="url(#ab)" />
                <text x="100" y="315" fill="#1976d2" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">INLET: {flow_disp} kg/h</text>
                <line x1="280" y1="35" x2="280" y2="10" stroke="#d32f2f" stroke-width="3" marker-end="url(#ar)" />
                <text x="280" y="55" fill="#d32f2f" font-size="12" font-family="sans-serif" font-weight="bold" text-anchor="middle">OUTLET: {cot_disp} °C</text>
            </svg>
        </div>
        """
        components.html(svg_html, height=380)
        
        st.write("---")
        
        # --- CREATIVE YIELDS DISPLAY (Bar Chart) ---
        st.subheader(f"🧪 Product Slate (Run #{latest['id']})")
        if not yield_df.empty:
            top_yields = yield_df.head(10).copy().sort_values("Yield", ascending=True)
            
            fig_yield = go.Figure(go.Bar(
                x=top_yields["Yield"],
                y=top_yields["Component"],
                orientation='h',
                marker=dict(color=top_yields["Yield"], colorscale='Viridis'),
                text=top_yields["Yield"].apply(lambda x: f"{x:.2f}%"),
                textposition='outside',
            ))
            fig_yield.update_layout(
                template="plotly_white", height=400, margin=dict(l=10, r=50, t=10, b=10),
                xaxis=dict(title="Yield (wt%)", showgrid=True),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_yield, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Awaiting yield data...")

    with col2:
        st.subheader("Lengthwise Profiles")
        if not profile_df.empty and len(profile_df) > 1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['tgas'], name="Tgas (°C)", line=dict(color="#d32f2f", width=3)))
            fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['mass_conversion'], name="Conv (%)", yaxis="y2", line=dict(color="#1976d2", dash='dash', width=3)))
            fig.update_layout(
                template="plotly_white", height=550, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title=dict(text="Axial Position [m]")),
                yaxis=dict(title=dict(text="Tgas (°C)", font=dict(color="#d32f2f"))),
                yaxis2=dict(title=dict(text="Conversion (%)", font=dict(color="#1976d2")), overlaying="y", side="right"),
                legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
            )
            st.plotly_chart(fig, use_container_width=True)

# --- 4. MAIN PAGE EXECUTION ---
with st.sidebar:
    st.header("⚙️ Worker Status")
    hb_data = get_db_data("SELECT * FROM cs_py_int.worker_heartbeat WHERE worker_name = 'CoilSim_SQL_Worker_01'")
    if not hb_data.empty:
        st.success("CoilSim Worker: Online")
        st.caption(f"Last Pulse: {hb_data.iloc[0]['last_pulse'].strftime('%H:%M:%S')}")
    else:
        st.error("Worker: Offline")

# Start the dashboard update
update_dashboard()
