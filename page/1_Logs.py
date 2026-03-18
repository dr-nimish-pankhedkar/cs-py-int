import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import urllib.parse

st.set_page_config(page_title="Simulation Logs", layout="wide")

def get_db_data(query):
    creds = st.secrets
    encoded_pass = urllib.parse.quote_plus(creds["db_password"])
    conn_str = f"postgresql://{creds['db_user']}:{encoded_pass}@{creds['db_host']}:{creds['db_port']}/{creds['db_name']}"
    engine = create_engine(conn_str)
    return pd.read_sql(query, engine)

st.title("📋 Simulation History & Analytics")

tab1, tab2 = st.tabs(["📈 Profile Comparison", "🧪 Yield History"])

with tab1:
    st.subheader("Last 10 Lengthwise Profiles")
    all_profiles = get_db_data("SELECT * FROM cs_py_int.profile_details ORDER BY task_id DESC, axial_position ASC")
    if not all_profiles.empty:
        all_profiles['task_id'] = all_profiles['task_id'].astype(str)
        var = st.selectbox("Select Parameter", ["tgas", "mass_conversion", "velocity"])
        fig = px.line(all_profiles, x="axial_position", y=var, color="task_id", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Yield Search")
    yields = get_db_data("SELECT t.id, t.created_at, y.component_name, y.yield_value FROM cs_py_int.yield_history y JOIN cs_py_int.simulation_tasks t ON y.task_id = t.id ORDER BY t.created_at DESC")
    comps = st.multiselect("Components", options=yields['component_name'].unique(), default=["C2H4", "C3H6"])
    st.dataframe(yields[yields['component_name'].isin(comps)], use_container_width=True)
