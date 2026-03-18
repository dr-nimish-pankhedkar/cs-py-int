import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import urllib.parse

st.set_page_config(page_title="Simulation Logs", layout="wide")

# --- DATABASE UTILITY ---
def get_db_data(query):
    try:
        creds = st.secrets
        encoded_pass = urllib.parse.quote_plus(creds["db_password"])
        conn_str = f"postgresql://{creds['db_user']}:{encoded_pass}@{creds['db_host']}:{creds['db_port']}/{creds['db_name']}"
        engine = create_engine(conn_str)
        return pd.read_sql(query, engine)
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame()

st.title("📋 Historical Simulation Logs")

# Create 3 sub-pages using Tabs
tab1, tab2, tab3 = st.tabs(["📝 Task Summary", "🧪 Component Yields", "📉 Axial Profiles"])

# --- TAB 1: TASK SUMMARY ---
with tab1:
    st.subheader("Run History")
    tasks_query = "SELECT id, status, created_at, completed_at, cot_input, flow_input FROM cs_py_int.simulation_tasks ORDER BY id DESC"
    df_tasks = get_db_data(tasks_query)
    if not df_tasks.empty:
        st.dataframe(df_tasks, use_container_width=True, hide_index=True)
    else:
        st.info("No tasks found.")

# --- TAB 2: COMPONENT YIELDS ---
with tab2:
    st.subheader("Global Yield Records")
    yield_query = """
        SELECT y.task_id, y.component_name, y.yield_value 
        FROM cs_py_int.yield_history y 
        ORDER BY y.task_id DESC
    """
    df_yields = get_db_data(yield_query)

    if not df_yields.empty:
        # Check available components
        available_comps = df_yields['component_name'].unique().tolist()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_comps = st.multiselect("Select Components", options=available_comps)
        
        if selected_comps:
            filtered_df = df_yields[df_yields['component_name'].isin(selected_comps)]
        else:
            filtered_df = df_yields

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ No yields found. Check if the Worker is harvesting yields.csv correctly.")

# --- TAB 3: AXIAL PROFILES ---
with tab3:
    st.subheader("Raw Axial Data (Last 10 Runs)")
    profile_query = "SELECT * FROM cs_py_int.profile_details ORDER BY task_id DESC, axial_position ASC"
    df_profiles = get_db_data(profile_query)
    
    if not df_profiles.empty:
        st.dataframe(df_profiles, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ No profile data found. This is why the Dashboard RHS graphs are empty.")
