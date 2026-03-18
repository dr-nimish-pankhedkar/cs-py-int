import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse

st.set_page_config(page_title="Configuration", layout="wide")

def get_engine():
    creds = st.secrets
    encoded_pass = urllib.parse.quote_plus(creds["db_password"])
    conn_str = f"postgresql://{creds['db_user']}:{encoded_pass}@{creds['db_host']}:{creds['db_port']}/{creds['db_name']}"
    return create_engine(conn_str)

st.title("⚙️ CoilSim Configuration")

st.subheader("Input Assignment (exp.txt)")
st.write("Current configuration maps DB columns to CoilSim 16-line input file.")

c1, c2 = st.columns(2)
with c1:
    st.info("**Row 3 (COT):** Mapped to `cot_input` column")
with c2:
    st.info("**Row 9 (HC Flow):** Mapped to `flow_input` column")

st.divider()
if st.button("Reset Incomplete Tasks"):
    if st.text_input("Admin Password", type="password") == st.secrets["admin_password"]:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text("UPDATE cs_py_int.simulation_tasks SET status = 'Pending' WHERE status = 'Processing'"))
        st.success("Tasks Reset.")
