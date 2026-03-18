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

# --- 1. FULL TASK HISTORY TABLE ---
st.subheader("Run History (Tasks)")
tasks_query = "SELECT id, status, created_at, completed_at, cot_input, flow_input FROM cs_py_int.simulation_tasks ORDER BY created_at DESC"
df_tasks = get_db_data(tasks_query)

if not df_tasks.empty:
    st.dataframe(df_tasks, use_container_width=True, hide_index=True)
else:
    st.info("No tasks found in simulation_tasks table.")

st.divider()

# --- 2. YIELD HISTORY TABLE (FILTERABLE) ---
st.subheader("Product Yields")

# Fetch Yields joined with Task ID for context
yield_query = """
    SELECT y.task_id, t.created_at, y.component_name, y.yield_value 
    FROM cs_py_int.yield_history y 
    JOIN cs_py_int.simulation_tasks t ON y.task_id = t.id 
    ORDER BY t.created_at DESC
"""
df_yields = get_db_data(yield_query)

if not df_yields.empty:
    # Get available components from the actual data
    available_comps = df_yields['component_name'].unique().tolist()
    
    # SAFETY FIX: Only use defaults if they exist in the data
    default_selection = [c for c in ["C2H4", "C3H6"] if c in available_comps]

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_comps = st.multiselect(
            "Filter by Components", 
            options=available_comps, 
            default=default_selection
        )
    
    # Filter the dataframe
    if selected_comps:
        filtered_df = df_yields[df_yields['component_name'].isin(selected_comps)]
    else:
        filtered_df = df_yields

    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # Download Section
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Filtered Yields (CSV)", data=csv, file_name="coilsim_logs.csv")
else:
    st.info("No data found in yield_history table.")
