import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Cloud Job Card", layout="wide")

# 1. Create connection
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["spreadsheet"]

# 2. Base Data Lists
ALL_TECHS = [
    "Denver", "Randell", "Wynand", "Lionel", "Austin", "Audrine", 
    "Sam", "Wayne", "Ernest", "Denzel", "James", "Brad", 
    "Sylvester", "Elvin", "Daniello"
]

SITE_LIST = ["Site A", "Site B", "Site C", "Other"]

MATERIAL_LIST = ["PVC Conduit", "Copper Tubing", "PVC Pipe", "Electrical Wire", "Sealant", "Screws", "Brackets"]

# Define items that use meter measurements
METER_ITEMS = ["PVC Conduit", "Copper Tubing", "PVC Pipe", "Electrical Wire"]

# 3. Initialize Session State
if "temp_materials" not in st.session_state:
    st.session_state.temp_materials = []
if "temp_techs" not in st.session_state:
    st.session_state.temp_techs = []

# --- APP HEADER ---
st.title("🏗️ Job Card System")

# Card Type Dropdown
job_type = st.selectbox("Select Card Type:", ["Jobcard (Completed Job)", "Pre-Jobcard (Planned Job)"])

st.markdown("---")

# --- UI LAYOUT: CORE DETAILS ---
col_1, col_2, col_3 = st.columns(3)
with col_1:
    job_date = st.date_input("Date", date.today())
    site = st.selectbox("Site Location", options=SITE_LIST)
with col_2:
    start_time = st.time_input("Start Time", value=datetime.now().time())
with col_3:
    end_time = st.time_input("End Time", value=datetime.now().time())

work_done = st.text_area("Description of Work (Done or Planned)")

st.markdown("---")

# --- UI LAYOUT: MULTIPLE TECHNICIANS ---
st.subheader("👨‍🔧 Technicians Assigned")

# Filter list to hide technicians already added
available_techs = [t for t in ALL_TECHS if t not in st.session_state.temp_techs]

t_col1, t_col2 = st.columns([3, 1])
with t_col1:
    if not available_techs:
        st.info("All technicians have been added.")
        selected_tech = None
    else:
        selected_tech = st.selectbox("Pick Technician", options=available_techs)

with t_col2:
    st.write(" ") # Padding
    if st.button("✅ Done", key="btn_add_tech") and selected_tech:
        st.session_state.temp_techs.append(selected_tech)
        st.rerun()

# Display selected technicians
if st.session_state.temp_techs:
    st.write("**Added Technicians:**")
    cols = st.columns(4) 
    for idx, t in enumerate(st.session_state.temp_techs):
        with cols[idx % 4]:
            if st.button(f"🗑️ {t}", key=f"t_{idx}"):
                st.session_state.temp_techs.pop(idx)
                st.rerun()

st.markdown("---")

# --- UI LAYOUT: MATERIALS ---
st.subheader("🛠️ Materials Used")

# Material Selection
selected_item = st.selectbox("Pick Material", options=MATERIAL_LIST)

# Format Logic
is_meter_item = selected_item in METER_ITEMS

if is_meter_item:
    c1, c2 = st.columns(2)
    with c1:
        meters = st.number_input("Meters", min_value=1, step=1, value=20)
    with c2:
        qty = st.number_input("Quantity", min_value=1, step=1, value=1)
    material_label = f"{selected_item} m{meters} x{qty}"
else:
    qty = st.number_input("Quantity", min_value=1, step=1, value=1)
    material_label = f"{selected_item} x{qty}"

if st.button("✅ Done", key="btn_add_material"):
    st.session_state.temp_materials.append(material_label)

# Display added materials
if st.session_state.temp_materials:
    st.write("**Added Materials:**")
    for idx, m in enumerate(st.session_state.temp_materials):
        mc1, mc2 = st.columns([0.9, 0.1])
        mc1.info(m)
        if mc2.button("🗑️", key=f"m_{idx}"):
            st.session_state.temp_materials.pop(idx)
            st.rerun()

st.markdown("---")

# --- FINAL SAVE ACTION ---
if st.button("🚀 SAVE FULL JOB CARD TO CLOUD"):
    if not work_done:
        st.error("Please enter a description.")
    elif not st.session_state.temp_techs:
        st.error("Please add at least one technician.")
    else:
        existing_data = conn.read(spreadsheet=SHEET_URL, ttl=0)
        
        # Format the summaries
        mat_summary = ", ".join(st.session_state.temp_materials)
        tech_summary = ", ".join(st.session_state.temp_techs)
        
        new_entry = pd.DataFrame([{
            "Type": job_type,
            "Date": str(job_date),
            "Start Time": start_time.strftime("%H:%M"),
            "End Time": end_time.strftime("%H:%M"),
            "Site": site,
            "Work Done": work_done,
            "Materials": mat_summary if mat_summary else "None",
            "Technicians": tech_summary
        }])
        
        updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
        conn.update(spreadsheet=SHEET_URL, data=updated_df)
        
        # Clear temporary lists
        st.session_state.temp_materials = []
        st.session_state.temp_techs = []
        st.success(f"✅ {job_type} successfully recorded!")

if st.checkbox("Show Recent History"):
    data = conn.read(spreadsheet=SHEET_URL, ttl=0)
    st.dataframe(data.tail(10))