import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG & ENGINE ---
st.set_page_config(page_title="CoilSim Digital Twin", layout="wide")

@st.cache_resource
def get_engine():
    creds = st.secrets
    encoded_pass = urllib.parse.quote_plus(creds["db_password"])
    conn_str = f"postgresql://{creds['db_user']}:{encoded_pass}@{creds['db_host']}:{creds['db_port']}/{creds['db_name']}"
    return create_engine(conn_str, connect_args={'connect_timeout': 10})

def get_db_data(query):
    try:
        return pd.read_sql(query, get_engine())
    except Exception:
        return pd.DataFrame()

# --- 2. REFRESH FRAGMENT ---
@st.fragment(run_every="30s")
def update_dashboard():
    # Get LATEST COMPLETED task
    tasks_df = get_db_data("SELECT * FROM cs_py_int.simulation_tasks WHERE status = 'Completed' ORDER BY id DESC LIMIT 1")
    
    if tasks_df.empty:
        st.warning("Awaiting first completed simulation...")
        return

    latest = tasks_df.iloc[0]
    tid = latest['id']
    last_ts = latest['completed_at'].strftime("%d-%b-%Y %H:%M:%S")
    
    st.markdown(f"### 🔥 CoilSim 1D Digital Twin | <span style='color:#d32f2f;'>Last Update: {last_ts}</span>", unsafe_allow_html=True)

    # Fetch Data for this ID
    profile_df = get_db_data(f"SELECT * FROM cs_py_int.profile_details WHERE task_id = {tid} ORDER BY axial_position")
    yield_df = get_db_data(f'SELECT component_name as "Component", yield_value as "Yield" FROM cs_py_int.yield_history WHERE task_id = {tid} ORDER BY yield_value DESC')

    # Normalize column names to lowercase to prevent Plotly KeyErrors
    profile_df.columns = [c.lower() for c in profile_df.columns]

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("Process Schematic")
        cot_disp = f"{latest['cot_input']:.1f}" if pd.notnull(latest['cot_input']) else "---"
        flow_disp = f"{latest['flow_input']:.0f}" if pd.notnull(latest['flow_input']) else "---"
        
        svg_html = f"""
<div style="background:#ffffff; padding:20px; border-radius:12px; border:1px solid #ddd;">
    <svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: auto;">
        <defs>
            <marker id="ar" markerWidth="8" markerHeight="8" refX="0" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#d32f2f" /></marker>
            <marker id="ab" markerWidth="8" markerHeight="8" refX="0" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#1976d2" /></marker>
        </defs>
        <rect x="60" y="110" width="280" height="240" fill="#fcfcfc" stroke="#999" stroke-width="2" />
        <line x1="60" y1="110" x2="340" y2="110" stroke="#444" stroke-width="4" />
        <rect x="100" y="70" width="14" height="260" fill="#f39c12" stroke="#e67e22" />
        <path d="M 100 330 Q 135 380 170 330" fill="none" stroke="#e67e22" stroke-width="12" stroke-linecap="round" />
        <rect x="163" y="150" width="14" height="180" fill="#f39c12" stroke="#e67e22" />
        <path d="M 170 150 Q 200 100 230 150" fill="none" stroke="#e67e22" stroke-width="12" stroke-linecap="round" />
        <rect x="223" y="150" width="14" height="180" fill="#f39c12" stroke="#e67e22" />
        <path d="M 230 330 Q 265 380 300 330" fill="none" stroke="#e67e22" stroke-width="12" stroke-linecap="round" />
        <rect x="293" y="70" width="14" height="260" fill="#f39c12" stroke="#e67e22" />
        <line x1="107" y1="20" x2="107" y2="60" stroke="#1976d2" stroke-width="3" marker-end="url(#ab)" />
        <text x="107" y="15" fill="#1976d2" font-size="14" font-family="sans-serif" font-weight="bold" text-anchor="middle">FEED: {flow_disp} kg/h</text>
        <text x="107" y="30" fill="#1976d2" font-size="10" font-family="sans-serif" font-weight="bold" text-anchor="middle">(DCS)</text>
        <line x1="300" y1="60" x2="300" y2="20" stroke="#d32f2f" stroke-width="3" marker-end="url(#ar)" />
        <text x="300" y="85" fill="#d32f2f" font-size="14" font-family="sans-serif" font-weight="bold" text-anchor="middle">COT: {cot_disp} °C</text>
        <text x="300" y="100" fill="#d32f2f" font-size="10" font-family="sans-serif" font-weight="bold" text-anchor="middle">(DCS)</text>
    </svg>
</div>
"""
        components.html(svg_html, height=440)
        
        st.write("---")
        st.subheader(f"🧪 Product Slate (Run #{tid})")
        st.caption("**(SIMULATED)**")
        if not yield_df.empty:
            top_y = yield_df.head(10).copy().sort_values("Yield", ascending=True)
            fig_y = go.Figure(go.Bar(x=top_y["Yield"], y=top_y["Component"], orientation='h', marker=dict(color=top_y["Yield"], colorscale='Viridis')))
            fig_y.update_layout(template="plotly_white", height=350, margin=dict(l=10, r=40, t=10, b=10), xaxis=dict(visible=False))
            st.plotly_chart(fig_y, use_container_width=True)

    with col2:
        st.subheader("Lengthwise Profiles")
        st.caption("**(SIMULATED)**")
        
        # Check for column names exactly as they are in SQL result
        if not profile_df.empty and 'axial_position' in profile_df.columns:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['tgas'], name="Tgas (°C)", line=dict(color="#d32f2f", width=3)))
            fig.add_trace(go.Scatter(x=profile_df['axial_position'], y=profile_df['mass_conversion'], name="Conv (%)", yaxis="y2", line=dict(color="#1976d2", dash='dash', width=3)))
            
            fig.update_layout(
                template="plotly_white", height=550, margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Axial Position [m]"),
                yaxis=dict(title="Tgas (°C)", titlefont=dict(color="#d32f2f")),
                yaxis2=dict(title="Conversion (%)", overlaying="y", side="right", titlefont=dict(color="#1976d2")),
                legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center")
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"📊 Run #{tid} completed, but no profile points were found.")

# --- 3. MAIN ---
with st.sidebar:
    st.header("⚙️ Worker Status")
    hb = get_db_data("SELECT * FROM cs_py_int.worker_heartbeat LIMIT 1")
    if not hb.empty:
        st.success(f"Online | {hb.iloc[0]['last_pulse'].strftime('%H:%M:%S')}")

update_dashboard()
