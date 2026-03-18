# CoilSim 1D | Cracking Furnace Digital Twin POC

This repository contains the real-time Digital Twin dashboard for monitoring a Cracking Furnace. It bridges the **CoilSim 1D** simulation engine with a PostgreSQL database to provide predictive insights into reactor profiles and product yields.

## 🏗️ System Architecture

1.  **Data Ingestion (DCS Simulator):** Synthetic plant data (COT, HC Flow) is pushed to a PostgreSQL database on a 5-minute cycle.
2.  **Simulation Engine (Coilsim-Worker):** A background Python script on the server polls the DB, performs surgical updates to `exp.txt`, executes the CoilSim engine, and harvests results.
3.  **Dashboard (Streamlit):** A multi-page web app for visualizing furnace health, lengthwise profiles, and historical yields.

## 🚀 Repository Structure

* `Dashboard.py`: Main landing page with furnace schematic and real-time lengthwise profiles (Tgas/Conversion).
* `pages/1_Logs.py`: Comparison tools for the last 10 simulation profiles and searchable yield history.
* `pages/2_Configuration.py`: Admin tool for assigning `exp.txt` row indices to database inputs.
* `cs_worker.py`: The background worker script (runs on the CoilSim server).
* `dcs_simulator.py`: Ingestor script to simulate real-time DCS data.

## ⚙️ Data Management Rules

* **Inputs:** If a task contains `NULL` for COT or Flow, the system preserves the existing values in the project directory.
* **Yields:** Permanent row-wise storage for all non-zero components across every successful run.
* **Profiles:** A self-cleaning table that only retains lengthwise data for the **last 10 runs** to ensure high-speed dashboard rendering.

## 🛠️ Setup

1.  **Database:** Execute the SQL scripts in `/schema` to create the `cs_py_int` schema.
2.  **Worker:** Configure `config_coilsim.yaml` with your DB credentials and `root_dir`.
3.  **Secrets:** In Streamlit Cloud or `.streamlit/secrets.toml`, define:
    ```toml
    db_password = "your_password"
    admin_password = "your_admin_password"
    ```

---
**Author:** Dr. Nimish Pankhedkar 
**Project:** Digital Twin POC for Petrochemical Optimization
