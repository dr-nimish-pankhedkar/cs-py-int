import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import urllib.parse

st.set_page_config(page_title="Simulation Logs", layout="wide")

# --- DB CONNECTION ---
def get_db_engine():
    user, host, port, dbname = "dtwinuser", "192.168.10.189", "8503", "poc-digital-twin"
    password = st.secrets["db_password"]
    conn_str = f"postgresql://{user}:{urllib.parse.quote_plus(password)}@{host}:{port}/{dbname}"
    return create_engine(conn_str)

engine = get_db_engine()

st.title("📋 Simulation History & Analytics")

tab1, tab2 = st.tabs(["📈 Profile Comparison", "🧪 Yield History"])

with tab1:
    st.subheader("Last 10 Lengthwise Profiles")
    # Fetch all profiles in the 'rolling' table
    query_p = "SELECT * FROM cs_py_int.profile_details ORDER BY task_id DESC, axial_position ASC"
    all_profiles = pd.read_sql(query_p, engine)
    
    if not all_profiles.empty:
        # Convert task_id to string for discrete color mapping in the legend
        all_profiles['task_id'] = all_profiles['task_id'].astype(str)
        
        var_to_plot = st.selectbox("Select Parameter to Compare", ["tgas", "mass_conversion", "velocity"])
        
        fig = px.line(all_profiles, 
                      x="axial_position", 
                      y=var_to_plot, 
                      color="task_id",
                      title=f"Lengthwise {var_to_plot} Comparison (Last 10 Runs)",
                      template="plotly_dark")
        
        fig.update_layout(xaxis_title="Reactor Length (m)", yaxis_title=var_to_plot)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No profile data available.")

with tab2:
    st.subheader("All-Time Yield Records")
    # Join with simulation_tasks to show COT/Flow alongside yields
    query_y = """
        SELECT t.id, t.created_at, t.cot_input, t.flow_input, y.component_name, y.yield_value
        FROM cs_py_int.yield_history y
        JOIN cs_py_int.simulation_tasks t ON y.task_id = t.id
        ORDER BY t.created_at DESC
    """
    yields_df = pd.read_sql(query_y, engine)
    
    # Filter for specific components
    comps = st.multiselect("Filter Components", options=yields_df['component_name'].unique(), default=["C2H4", "C3H6"])
    filtered_yields = yields_df[yields_df['component_name'].isin(comps)]
    
    st.dataframe(filtered_yields, use_container_width=True)
    
    # Download Button
    csv = filtered_yields.to_csv(index=False).encode('utf-8')
    st.download_button("Download Yield Data (CSV)", data=csv, file_name="coilsim_yield_history.csv")
