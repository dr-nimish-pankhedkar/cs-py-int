import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="CoilSim Config", layout="wide")

st.title("⚙️ CoilSim Configuration Manager")

# Logic to select Inputs vs Outputs
mode = st.radio("Configuration Type", ["Input Mapping (exp.txt)", "Output Mapping (yields.csv)"])

if mode == "Input Mapping (exp.txt)":
    st.subheader("Assign DB Columns to exp.txt Rows")
    col1, col2, col3 = st.columns(3)
    with col1:
        var_name = st.text_input("Variable Name (e.g., COT)")
    with col2:
        row_idx = st.number_input("exp.txt Row Index", min_value=1, max_value=16, value=3)
    with col3:
        db_col = st.text_input("DB Column Name (in simulation_tasks)")
    
    if st.button("Register Input"):
        # Logic to insert into cs_py_int.coilsim_map
        st.success(f"Mapped {var_name} to Row {row_idx}")

else:
    st.subheader("Select High-Priority Yields for Dashboard")
    # This allows you to pick components like C2H4, C3H6 from the 700+ list
    comp_to_track = st.text_input("Component ID/Name from CoilSim (e.g., C2H4)")
    display_name = st.text_input("Display Label (e.g., Ethylene)")
    
    if st.button("Save Output Mapping"):
        st.success(f"Dashboard will now track {comp_to_track} as {display_name}")

st.divider()
st.info("Note: Changes here will affect the next background worker run.")
