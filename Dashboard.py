import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
import urllib.parse
import streamlit.components.v1 as components
from datetime import datetime

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="CoilSim Digital Twin", layout="wide")

# CSS to hide the "Running..." man and make transitions smoother
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
    except Exception as e:
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
        # ... [Keep your SVG logic here] ...
        components.html(svg_html, height=380)
        
        st.write("---")
        
        # --- CREATIVE YIELDS DISPLAY ---
        st.subheader(f"🧪 Product Slate (Run #{latest['id']})")
        
        if not yield_df.empty:
            # We filter for top 8-10 components to keep the UI clean
            top_yields = yield_df.head(10).copy()
            
            # Create a horizontal bar chart
            fig_yield = go.Figure(go.Bar(
                x=top_yields["Yield"],
                y=top_yields["Component"],
                orientation='h',
                marker=dict(
                    color=top_yields["Yield"],
                    colorscale='Viridis',
                    line=dict(color='rgba(255, 255, 255, 0.5)', width=1)
                ),
                text=top_yields["Yield"].apply(lambda x: f"{x:.2f}%"),
                textposition='outside',
            ))

            fig_yield.update_layout(
                template="plotly_white",
                height=400,
                margin=dict(l=10, r=40, t=10, b=10),
                xaxis=dict(title="Yield (wt%)", showgrid=True, gridcolor="#eee"),
                yaxis=dict(autorange="reversed"), # High yields at the top
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            
            st.plotly_chart(fig_yield, use_container_width=True, config={'displayModeBar': False})
            
            # Optional: Add a small expander if the user still wants to see the raw table
            with st.expander("View Raw Data Table"):
                st.dataframe(yield_df, use_container_width=True, hide_index=True)
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
# Execute the sidebar once (it won't flicker)
with st.sidebar:
    st.header("⚙️ Worker Status")
    hb_df = get_db_data("SELECT * FROM cs_py_int.worker_heartbeat WHERE worker_name = 'CoilSim_SQL_Worker_01'")
    if not hb_df.empty:
        st.success("CoilSim Worker: Online")
        st.caption(f"Last Pulse: {hb_row['last_pulse'].strftime('%H:%M:%S') if 'hb_row' in locals() else 'Active'}")
    else:
        st.error("Worker: Offline")

# Start the smooth update fragment
update_dashboard()
