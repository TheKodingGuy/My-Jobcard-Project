import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime, time, timedelta
from dateutil import parser
import base64
from concurrent.futures import ThreadPoolExecutor

# --- PAGE SETUP ---
st.set_page_config(page_title="Cloud Job Card", layout="wide")

# Global Pre-computed Static Lookups & Constants
TIME_OPTIONS = [time(h, m) for h in range(24) for m in (0, 15, 30, 45)]
TIME_SET = set(TIME_OPTIONS)
DONE_OPTIONS = ("Electrical Maintenance", "Installation", "Fault Finding", "Solar Maintenance", "DB Wiring")
ADMIN_PASSCODE = "admin123"

# Inject CSS to prevent button text from wrapping, lock the sidebar scroll, and make the header container sticky
st.markdown(
    """
    <style>
    div.stButton > button {
        white-space: nowrap !important;
    }
    div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
        position: sticky;
        top: 2.875rem;
        background-color: var(--background-color, #ffffff);
        z-index: 999;
        padding-top: 10px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--divider-color, rgba(49, 51, 63, 0.2));
    }
    .fixed-header {
        display: none;
    }
    [data-testid="stSidebar"] {
        overflow: hidden !important;
    }
    [data-testid="stSidebar"] > div {
        overflow: hidden !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 1. Create Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["spreadsheet"]

# Global helper functions
def normalize_key(val_one, val_two=None):
    if val_one is None:
        return ""
    if val_two is not None:
        return f"{val_one}_{val_two}"
    return str(val_one)

def clean_size_str(val):
    if val is None:
        return ""
    s = str(val).strip()
    return s[:-2] if s.endswith(".0") else s

def get_image_base64(file):
    return base64.b64encode(file.getvalue()).decode()

# --- Callback Helpers for Quick-Select Buttons ---
def set_quick_val(key, val):
    st.session_state[key] = val

def set_quick_material(mat):
    st.session_state["material_select"] = mat
    if "type_select" in st.session_state:
        st.session_state["type_select"] = None

def add_quick_tech(tech):
    if tech not in st.session_state.temp_techs:
        st.session_state.temp_techs.append(tech)

# ==============================================================================
# HIGH-SPEED CONCURRENT DATA LOADER & IN-MEMORY COMPILER
# ==============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_history_cached(spreadsheet_url):
    """Retrieve and cache the primary job card history worksheet from 'JobCards'."""
    try:
        df = conn.read(spreadsheet=spreadsheet_url, worksheet="JobCards", ttl="5m")
        if df is not None and not df.empty:
            return df.dropna(how="all")
    except Exception:
        pass
    try:
        df = conn.read(spreadsheet=spreadsheet_url, ttl="5m")
        return df.dropna(how="all") if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600, show_spinner=False)
def load_and_compile_cloud_config(spreadsheet_url):
    """
    Loads all configuration tabs simultaneously using parallel worker threads
    for microsecond response times.
    """
    tabs = [
        "TechnicianData", "LocationData", "MaterialLayer1", "MaterialLayer2",
        "DBData", "FittingsData", "WireData", "WirewayData", "LightData"
    ]
    raw = {}

    def fetch_tab(tab_name):
        try:
            df = conn.read(spreadsheet=spreadsheet_url, worksheet=tab_name, ttl="10m")
            return tab_name, (df if df is not None else pd.DataFrame())
        except Exception:
            return tab_name, pd.DataFrame()

    with ThreadPoolExecutor(max_workers=min(9, len(tabs))) as executor:
        results = executor.map(fetch_tab, tabs)
        for tab_name, df_result in results:
            raw[tab_name] = df_result

    # 1. Technicians
    df_tech = raw.get("TechnicianData", pd.DataFrame())
    if not df_tech.empty and "Technician" in df_tech.columns:
        all_techs = sorted(df_tech["Technician"].dropna().astype(str).unique().tolist())
        tech_passwords = df_tech.set_index("Technician")["Password"].astype(str).to_dict()
    else:
        all_techs, tech_passwords = [], {}

    # 2. Locations / Dropdowns
    df_drops = raw.get("LocationData", pd.DataFrame())
    vehicles = [v for v in df_drops["Vehicles"].dropna().astype(str).tolist() if v.strip()] if "Vehicles" in df_drops.columns else []
    sites = [s for s in df_drops["Sites"].dropna().astype(str).tolist() if s.strip()] if "Sites" in df_drops.columns else []
    locations = [l for l in df_drops["Locations"].dropna().astype(str).tolist() if l.strip()] if "Locations" in df_drops.columns else []

    # 3. MaterialMaster
    df_mm = raw.get("MaterialLayer1", pd.DataFrame())
    if not df_mm.empty and "Category" in df_mm.columns and "Type" in df_mm.columns:
        materials = sorted(df_mm["Category"].dropna().astype(str).unique().tolist())
        type_list = {cat: df_mm[df_mm["Category"] == cat]["Type"].dropna().astype(str).unique().tolist() for cat in materials}
        qty_items = df_mm[df_mm["Unit"].astype(str).str.lower() == "qty"]["Category"].dropna().astype(str).unique().tolist() if "Unit" in df_mm.columns else []
        meter_items = df_mm[df_mm["Unit"].astype(str).str.lower() == "meter"]["Category"].dropna().astype(str).unique().tolist() if "Unit" in df_mm.columns else []
        watts_items = df_mm[df_mm["Unit"].astype(str).str.lower() == "watt"]["Category"].dropna().astype(str).unique().tolist() if "Unit" in df_mm.columns else []
    else:
        materials, type_list, qty_items, meter_items, watts_items = [], {}, [], [], []

    # 4. DB Configuration
    df_db = raw.get("DBData", pd.DataFrame())
    db_config = {}
    if not df_db.empty and "Size" in df_db.columns:
        for _, row in df_db.iterrows():
            db_config[str(row["Size"])] = {
                "max_rows": int(row.get("MaxRows", 10)),
                "max_ways": int(row.get("MaxWays", 20))
            }

    # 5. Material Specs
    df_specs = raw.get("MaterialLayer2", pd.DataFrame())
    qty_meter_list = {}
    if not df_specs.empty and "Category" in df_specs.columns and "Type" in df_specs.columns and "Spec" in df_specs.columns:
        for cat, cat_grp in df_specs.groupby("Category"):
            qty_meter_list[str(cat)] = {}
            for t_name, t_grp in cat_grp.groupby("Type"):
                qty_meter_list[str(cat)][str(t_name)] = t_grp["Spec"].dropna().astype(str).tolist()
    if db_config:
        qty_meter_list["DB"] = db_config

    # 6. Fittings Matrix
    df_fittings = raw.get("FittingsData", pd.DataFrame())
    module_make_list = {}
    if not df_fittings.empty and "FittingType" in df_fittings.columns:
        for f_type, f_grp in df_fittings.groupby("FittingType"):
            module_make_list[str(f_type)] = {
                "Modules": f_grp["Module"].dropna().astype(str).unique().tolist(),
                "Make": f_grp["Make"].dropna().astype(str).unique().tolist()
            }

    # 7. Wire Specs / Colours
    df_wire = raw.get("WireData", pd.DataFrame())
    colour_list = {}
    if not df_wire.empty and "WireType" in df_wire.columns and "Size" in df_wire.columns and "Colour" in df_wire.columns:
        for w_type, w_grp in df_wire.groupby("WireType"):
            colour_list[str(w_type)] = {}
            for sz, sz_grp in w_grp.groupby("Size"):
                clean_sz = clean_size_str(sz)
                colour_list[str(w_type)][clean_sz] = sz_grp["Colour"].dropna().astype(str).unique().tolist()

    # 8. Wireway Specs
    df_ww = raw.get("WirewayData", pd.DataFrame())
    item_size_list = {}
    if not df_ww.empty and "Item" in df_ww.columns and "Size" in df_ww.columns:
        for itm, itm_grp in df_ww.groupby("Item"):
            item_size_list[str(itm).lower()] = itm_grp["Size"].dropna().astype(str).unique().tolist()

    # 9. Light Specs
    df_ls = raw.get("LightData", pd.DataFrame())
    light_size_list = {}
    if not df_ls.empty and "Placement" in df_ls.columns and "Size" in df_ls.columns:
        for plc, plc_grp in df_ls.groupby("Placement"):
            light_size_list[str(plc).lower()] = plc_grp["Size"].dropna().astype(str).unique().tolist()

    return {
        "raw_techs": df_tech,
        "ALL_TECHS": all_techs,
        "TECH_PASSWORDS": tech_passwords,
        "VEHICLE_LIST": vehicles,
        "SITE_LIST": sites,
        "LOCATION_LIST": locations,
        "MATERIAL_LIST": materials,
        "TYPE_LIST": type_list,
        "QTY_ITEMS": qty_items,
        "METER_ITEMS": meter_items,
        "WATTS_ITEMS": watts_items,
        "DB_CONFIG_DICT": db_config,
        "QTY_METER_LIST": qty_meter_list,
        "MODULE_MAKE_LIST": module_make_list,
        "COLOUR_LIST": colour_list,
        "ITEM_SIZE_LIST": item_size_list,
        "LIGHT_SIZE_LIST": light_size_list
    }

# Instant compiled data lookup
CONFIG = load_and_compile_cloud_config(SHEET_URL)
ALL_TECHS = CONFIG["ALL_TECHS"]
TECH_PASSWORDS = CONFIG["TECH_PASSWORDS"]
VEHICLE_LIST = CONFIG["VEHICLE_LIST"]
SITE_LIST = CONFIG["SITE_LIST"]
LOCATION_LIST = CONFIG["LOCATION_LIST"]
MATERIAL_LIST = CONFIG["MATERIAL_LIST"]
TYPE_LIST = CONFIG["TYPE_LIST"]
QTY_ITEMS = CONFIG["QTY_ITEMS"]
METER_ITEMS = CONFIG["METER_ITEMS"]
WATTS_ITEMS = CONFIG["WATTS_ITEMS"]
DB_CONFIG_DICT = CONFIG["DB_CONFIG_DICT"]
QTY_METER_LIST = CONFIG["QTY_METER_LIST"]
MODULE_MAKE_LIST = CONFIG["MODULE_MAKE_LIST"]
COLOUR_LIST = CONFIG["COLOUR_LIST"]
ITEM_SIZE_LIST = CONFIG["ITEM_SIZE_LIST"]
LIGHT_SIZE_LIST = CONFIG["LIGHT_SIZE_LIST"]

# Fast lookup sets
SET_METER_ITEMS = set(METER_ITEMS)
SET_QTY_ITEMS = set(QTY_ITEMS)
SET_ALL_TECHS = set(ALL_TECHS)
SET_MATERIAL_LIST = set(MATERIAL_LIST)

# ==============================================================================
# SESSION STATE INITIALIZATION & COMPLIANCE HELPERS
# ==============================================================================
if "temp_materials" not in st.session_state:
    st.session_state.temp_materials = []
if "temp_techs" not in st.session_state:
    st.session_state.temp_techs = []
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "profile_pics" not in st.session_state:
    st.session_state.profile_pics = {}
if "user_analytics" not in st.session_state:
    st.session_state.user_analytics = None

if "tech_config" not in st.session_state:
    df_t = CONFIG["raw_techs"]
    if not df_t.empty and "Technician" in df_t.columns:
        if "LockedOut" not in df_t.columns:
            df_t["LockedOut"] = False
        if "OverrideDate" not in df_t.columns:
            df_t["OverrideDate"] = "default"
        df_t["LockedOut"] = df_t["LockedOut"].astype(str).str.upper() == "TRUE"
        st.session_state.tech_config = df_t.set_index("Technician").to_dict(orient="index")
    else:
        st.session_state.tech_config = {}

def sync_tech_config_to_gsheets():
    """Syncs user states (passwords, lockouts, dates) live to GSheets with auto-create support."""
    try:
        df_sync = pd.DataFrame([
            {
                "Technician": k,
                "Password": v["Password"],
                "LockedOut": "TRUE" if (str(v["LockedOut"]).upper() == "TRUE" or v["LockedOut"] is True) else "FALSE",
                "OverrideDate": v.get("OverrideDate", "default")
            }
            for k, v in st.session_state.tech_config.items()
        ])
        try:
            conn.update(spreadsheet=SHEET_URL, worksheet="TechnicianData", data=df_sync)
        except Exception:
            try:
                conn.create(spreadsheet=SHEET_URL, worksheet="TechnicianData", data=df_sync)
            except Exception:
                pass
        load_and_compile_cloud_config.clear()
    except Exception:
        pass

def evaluate_technician_lockout(username, user_record):
    """Evaluates whether technician missed filling their job card on the day."""
    if str(user_record.get("LockedOut", False)).upper() == "TRUE" or user_record.get("LockedOut", False) is True:
        return True, "Your profile has been locked by the administrator. Please ask the admin to unlock your profile."

    df_hist = load_history_cached(SHEET_URL)
    today = date.today()
    override_val = str(user_record.get("OverrideDate", "default"))

    tech_col = "Technicians Assigned" if "Technicians Assigned" in df_hist.columns else ("Technicians" if "Technicians" in df_hist.columns else None)

    # 1. Custom OverrideDate check
    if override_val != "default":
        try:
            target_date = parser.parse(override_val).date()
            if target_date < today:
                if not df_hist.empty and "Date" in df_hist.columns and tech_col:
                    matched = df_hist[
                        (df_hist["Date"].astype(str) == str(target_date)) &
                        (df_hist[tech_col].astype(str).str.contains(username, case=False, na=False))
                    ]
                    if matched.empty:
                        return True, f"You did not fill in your job card on {target_date}. Your profile has been automatically locked. Please ask the admin to unlock your profile."
                else:
                    return True, f"You did not fill in your job card on {target_date}. Your profile has been automatically locked. Please ask the admin to unlock your profile."
        except Exception:
            pass

    # 2. Daily standard check
    else:
        if today.weekday() == 0:
            prev_workday = today - timedelta(days=3)
        elif today.weekday() == 6:
            prev_workday = today - timedelta(days=2)
        else:
            prev_workday = today - timedelta(days=1)

        if not df_hist.empty and "Date" in df_hist.columns and tech_col:
            user_history = df_hist[df_hist[tech_col].astype(str).str.contains(username, case=False, na=False)]
            if not user_history.empty:
                submitted_prev = df_hist[
                    (df_hist["Date"].astype(str).isin([str(prev_workday), str(today - timedelta(days=1))])) &
                    (df_hist[tech_col].astype(str).str.contains(username, case=False, na=False))
                ]
                if submitted_prev.empty:
                    submitted_today = df_hist[
                        (df_hist["Date"].astype(str) == str(today)) &
                        (df_hist[tech_col].astype(str).str.contains(username, case=False, na=False))
                    ]
                    if submitted_today.empty:
                        return True, f"You did not fill in your job card on {prev_workday}. Your profile has been automatically locked. Please ask the admin to unlock your profile."

    return False, ""

def compute_user_analytics(username):
    """Computes top favorites once and caches in session state."""
    analytics = {
        "job_count": 0, "sites": [], "vehicles": [], "techs": [], 
        "materials": [], "times_start": [], "times_end": []
    }
    df_hist = load_history_cached(SHEET_URL)
    if df_hist.empty or "Date" not in df_hist.columns:
        return analytics
    
    tech_col = "Technicians Assigned" if "Technicians Assigned" in df_hist.columns else ("Technicians" if "Technicians" in df_hist.columns else None)
    if not tech_col:
        return analytics

    df_valid = df_hist.dropna(subset=[tech_col, "Date"])
    user_mask = df_valid[tech_col].astype(str).str.contains(username, case=False, na=False)
    analytics["job_count"] = int(user_mask.sum())
    
    df_u = df_valid[user_mask]
    if not df_u.empty:
        site_col = "Site Location" if "Site Location" in df_u.columns else ("Site" if "Site" in df_u.columns else None)
        if site_col:
            analytics["sites"] = [s for s in df_u[site_col].dropna().astype(str).value_counts().index if s in SITE_LIST][:3]
        if "Vehicle" in df_u.columns:
            analytics["vehicles"] = [v for v in df_u["Vehicle"].dropna().astype(str).value_counts().index if v in VEHICLE_LIST][:3]
        
        all_coworkers = []
        for t_list in df_u[tech_col].dropna().astype(str):
            for p in [x.strip() for x in t_list.split(",")]:
                if p != username and p in SET_ALL_TECHS:
                    all_coworkers.append(p)
        if all_coworkers:
            analytics["techs"] = pd.Series(all_coworkers).value_counts().index.tolist()[:3]
        
        mat_col = "Materials Used" if "Materials Used" in df_u.columns else ("Materials" if "Materials" in df_u.columns else None)
        if mat_col and mat_col in df_u.columns:
            all_mats = []
            for m_list in df_u[mat_col].dropna().astype(str):
                for p in [x.strip() for x in m_list.replace(" | ", ",").replace(" , ", ",").split(",")]:
                    cat = p.split(":")[0].strip() if ":" in p else p.split(" ")[0].strip()
                    if cat in SET_MATERIAL_LIST:
                        all_mats.append(cat)
            if all_mats:
                analytics["materials"] = pd.Series(all_mats).value_counts().index.tolist()[:3]
        
        if "Start Time" in df_u.columns:
            for ts in df_u["Start Time"].dropna().value_counts().index:
                try:
                    t_obj = parser.parse(str(ts)).time()
                    matched = next((opt for opt in TIME_OPTIONS if opt.hour == t_obj.hour and opt.minute == t_obj.minute), None)
                    if matched and matched not in analytics["times_start"]:
                        analytics["times_start"].append(matched)
                except Exception:
                    pass
            analytics["times_start"] = analytics["times_start"][:3]
            
        if "End Time" in df_u.columns:
            for te in df_u["End Time"].dropna().value_counts().index:
                try:
                    t_obj = parser.parse(str(te)).time()
                    matched = next((opt for opt in TIME_OPTIONS if opt.hour == t_obj.hour and opt.minute == t_obj.minute), None)
                    if matched and matched not in analytics["times_end"]:
                        analytics["times_end"].append(matched)
                except Exception:
                    pass
            analytics["times_end"] = analytics["times_end"][:3]

    return analytics

# ==============================================================================
# SECURE LOGIN GATEWAY WITH AUTOMATED COMPLIANCE LOCKOUT
# ==============================================================================
if st.session_state.logged_in_user is None and not st.session_state.is_admin:
    st.markdown("<br><br>", unsafe_allow_html=True)
    login_col1, login_col2, login_col3 = st.columns([1, 2, 1])
    with login_col2:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="margin-bottom: 0px;">Job card System Login</h1>
                <p style="color: gray; margin-top: 5px;">Select your profile and enter passcode to access the system</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        login_tabs = st.tabs(["👷 Technician Login", "🔑 Administrator Login"])
        
        with login_tabs[0]:
            st.markdown("<br>", unsafe_allow_html=True)
            login_user = st.selectbox(
                "Select Your Name", 
                options=ALL_TECHS, 
                index=None, 
                placeholder="Choose your name...",
                key="tech_login_selectbox"
            )
            
            login_password = st.text_input(
                "Password", 
                type="password", 
                placeholder="••••••••", 
                key="tech_login_password"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔓 Access Job Card System", use_container_width=True, key="tech_login_btn"):
                user_record = st.session_state.tech_config.get(login_user, {})
                
                if not login_user:
                    st.error("Please select your profile to log in.")
                elif login_password != str(user_record.get("Password")):
                    st.error("Incorrect password. Please try again.")
                else:
                    is_locked, lock_reason = evaluate_technician_lockout(login_user, user_record)
                    
                    if is_locked:
                        st.session_state.tech_config[login_user]["LockedOut"] = True
                        sync_tech_config_to_gsheets()
                        st.error(f"❌ Access Denied: {lock_reason}")
                    else:
                        st.session_state.logged_in_user = login_user
                        st.session_state.user_analytics = compute_user_analytics(login_user)
                        if login_user not in st.session_state.temp_techs:
                            st.session_state.temp_techs.append(login_user)
                        st.rerun()
                    
        with login_tabs[1]:
            st.markdown("<br>", unsafe_allow_html=True)
            admin_password = st.text_input(
                "Enter Administrator Password", 
                type="password", 
                placeholder="••••••••", 
                key="admin_login_password"
            )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🛠️ Enter Admin Console", use_container_width=True, key="admin_login_btn"):
                if admin_password != ADMIN_PASSCODE:
                    st.error("Access Denied: Incorrect administrator password.")
                else:
                    st.session_state.is_admin = True
                    st.session_state.logged_in_user = "Admin"
                    st.rerun()
    st.stop()

# ==============================================================================
# SIDEBAR: USER PROFILE & METRICS
# ==============================================================================
logged_user = st.session_state.logged_in_user

if st.session_state.is_admin:
    has_uploaded_pic = "Admin" in st.session_state.profile_pics

    if has_uploaded_pic:
        img_b64 = st.session_state.profile_pics["Admin"]
        st.sidebar.markdown(
            f"""
            <div style="text-align: center;">
                <img src="data:image/png;base64,{img_b64}" style="
                    width: 80px;
                    height: 80px;
                    object-fit: cover;
                    border-radius: 16px;
                    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.15);
                    margin: 5px auto 5px auto;
                " />
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown(
            """
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                background-color: #31333F;
                color: white;
                width: 80px;
                height: 80px;
                border-radius: 16px;
                font-size: 28px;
                font-weight: bold;
                margin: 5px auto 5px auto;
                box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
            ">
                AD
            </div>
            """,
            unsafe_allow_html=True
        )
        st.sidebar.markdown(
            """
            <div style="text-align: center; padding: 6px; font-size: 11px; color: #856404; background-color: #fff3cd; border-radius: 8px; border: 1px solid #ffeeba; margin: 5px 10px 5px 10px;">
                📸 <b>Setup Required:</b> Upload admin profile picture below. This only needs to be done once!
            </div>
            """,
            unsafe_allow_html=True
        )
        uploaded_img = st.sidebar.file_uploader("Upload Profile Picture", type=["png", "jpg", "jpeg"], key="admin_profile_pic_upload", label_visibility="collapsed")
        if uploaded_img:
            st.session_state.profile_pics["Admin"] = get_image_base64(uploaded_img)
            st.rerun()

    st.sidebar.markdown("<h3 style='text-align: center; margin-top: 5px; margin-bottom: 0px;'>Admin Panel</h3>", unsafe_allow_html=True)
    st.sidebar.markdown("<div style='text-align: center;'>Logged in as: <b>Administrator</b></div>", unsafe_allow_html=True)
    st.sidebar.markdown("<hr style='margin: 8px 0px;' />", unsafe_allow_html=True)
else:
    has_uploaded_pic = logged_user in st.session_state.profile_pics

    if has_uploaded_pic:
        img_b64 = st.session_state.profile_pics[logged_user]
        st.sidebar.markdown(
            f"""
            <div style="text-align: center;">
                <img src="data:image/png;base64,{img_b64}" style="
                    width: 80px;
                    height: 80px;
                    object-fit: cover;
                    border-radius: 16px;
                    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.15);
                    margin: 5px auto 5px auto;
                " />
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        initials = "".join([part[0].upper() for part in logged_user.split()[:2]]) if logged_user else "U"
        st.sidebar.markdown(
            f"""
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                background-color: var(--primary-color, #ff4b4b);
                color: white;
                width: 80px;
                height: 80px;
                border-radius: 16px;
                font-size: 28px;
                font-weight: bold;
                margin: 5px auto 5px auto;
                box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
        ">
                {initials}
        </div>
        """,
            unsafe_allow_html=True
        )
    
        st.sidebar.markdown(
            """
            <div style="text-align: center; padding: 6px; font-size: 11px; color: #856404; background-color: #fff3cd; border-radius: 8px; border: 1px solid #ffeeba; margin: 5px 10px 5px 10px;">
                📸 <b>Setup Required:</b> Upload profile picture below to permanently set a photo.
            </div>
            """,
            unsafe_allow_html=True
        )
        
        uploaded_img = st.sidebar.file_uploader("Upload Profile Picture", type=["png", "jpg", "jpeg"], key="profile_pic_upload", label_visibility="collapsed")
        if uploaded_img:
            st.session_state.profile_pics[logged_user] = get_image_base64(uploaded_img)
            st.rerun()

    st.sidebar.markdown("<h3 style='text-align: center; margin-top: 5px; margin-bottom: 0px;'>User Profile</h3>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<div style='text-align: center;'>Logged in as: <b>{logged_user}</b></div>", unsafe_allow_html=True)
    st.sidebar.markdown("<hr style='margin: 8px 0px;' />", unsafe_allow_html=True)

    if st.session_state.user_analytics is None:
        st.session_state.user_analytics = compute_user_analytics(logged_user)
    
    logged_jobs_count = st.session_state.user_analytics["job_count"]
    st.sidebar.markdown(
        f"""
        <div style="text-align: center; margin-top: 5px; margin-bottom: 10px;">
            <div style="font-size: 11px; color: #808495; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Submitted Job Cards</div>
            <div style="font-size: 24px; font-weight: 700; color: var(--text-color); margin-top: 2px;">{logged_jobs_count}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

if st.sidebar.button("🚪 Log Out", use_container_width=True, type="secondary"):
    st.session_state.logged_in_user = None
    st.session_state.is_admin = False
    st.session_state.temp_techs = []
    st.session_state.temp_materials = []
    st.session_state.user_analytics = None
    st.rerun()

# Rapid analytics extraction
user_most_used = st.session_state.user_analytics if st.session_state.user_analytics else {
    "sites": [], "vehicles": [], "techs": [], "materials": [], "times_start": [], "times_end": []
}

# --- APP MASTER STICKY PROGRESS CONTAINER ---
header_container = st.container()

# ==============================================================================
# ADMINISTRATOR VIEW (LOCKOUT UNLOCK & PROFILE CONTROLS)
# ==============================================================================
if st.session_state.is_admin:
    st.title("🛠️ Job Card System Admin Console")
    st.markdown("Use this terminal panel to manage user profiles, unlock locked technicians, and configure job dates globally.")
    
    admin_tabs = st.tabs(["🔐 Manage Passwords", "🚫 Lockout Manager", "📅 Configure Global Date"])
    
    with admin_tabs[0]:
        st.write("### Update Technician Passwords")
        edit_user = st.selectbox("Select Technician to Modify", options=ALL_TECHS, index=None, placeholder="Pick user...")
        if edit_user:
            current_pass = st.session_state.tech_config[edit_user]["Password"]
            st.write(f"**Current Password:** `{current_pass}`")
            new_pass = st.text_input("Enter New Password", placeholder="Enter unique password...", key="admin_edit_new_pwd")
            if st.button("🔒 Save Password Update", use_container_width=True):
                if not new_pass:
                    st.error("Please enter a valid password.")
                else:
                    st.session_state.tech_config[edit_user]["Password"] = new_pass
                    sync_tech_config_to_gsheets()
                    st.success(f"🔒 Password for **{edit_user}** successfully updated in GSheets!")
                    st.rerun()
                    
    with admin_tabs[1]:
        st.write("### Technician Lockout Control Dashboard")
        st.markdown("Technicians who miss submitting their daily job card are automatically locked out. You can unlock them below.")
        
        table_rows = []
        for k, v in st.session_state.tech_config.items():
            is_locked = str(v.get("LockedOut", False)).upper() == "TRUE" or v.get("LockedOut", False) is True
            status = "🔴 Locked Out" if is_locked else "🟢 Active"
            table_rows.append({"Technician": k, "Access Status": status, "Due Date": v.get("OverrideDate", "default")})
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
        
        st.markdown("---")
        lock_user = st.selectbox("Select Technician to Toggle Access", options=ALL_TECHS, index=None, placeholder="Pick user...", key="admin_lockout_user_select")
        if lock_user:
            current_lock_state = str(st.session_state.tech_config[lock_user].get("LockedOut", False)).upper() == "TRUE" or st.session_state.tech_config[lock_user].get("LockedOut", False) is True
            st.write(f"Current State: **{'🔴 Locked Out' if current_lock_state else '🟢 Active'}**")
            
            action_label = "🔓 Unlock Profile & Reset Date" if current_lock_state else "🔒 Lock Out Technician"
            if st.button(action_label, use_container_width=True, type="primary" if current_lock_state else "secondary"):
                st.session_state.tech_config[lock_user]["LockedOut"] = not current_lock_state
                if current_lock_state:
                    st.session_state.tech_config[lock_user]["OverrideDate"] = "default"
                sync_tech_config_to_gsheets()
                st.success(f"Status for **{lock_user}** successfully updated in GSheets!")
                st.rerun()
                
    with admin_tabs[2]:
        st.write("### Configure Global Job Card Date")
        st.markdown("Set a custom date for selected technicians job card entry. If set to default, forms will automatically load today's present date.")
        
        table_rows = []
        for k, v in st.session_state.tech_config.items():
            override_val = v.get("OverrideDate", "default")
            date_status = f"📅 Custom: {override_val}" if override_val != "default" else "🟢 Default"
            table_rows.append({"Technician": k, "Date Setup": date_status})
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
        
        st.markdown("---")
        target_tech = st.selectbox("Select Technician to Configure", options=ALL_TECHS, index=None, placeholder="Pick user...", key="admin_date_tech_select")
        if target_tech:
            current_override = st.session_state.tech_config[target_tech].get("OverrideDate", "default")
            st.write(f"Current Date Setup: **{'Default' if current_override == 'default' else current_override}**")
            
            override_option = st.radio("Date Status Setup", options=["Default", "Custom Overridden Date"], index=0 if current_override == "default" else 1, key="admin_date_radio_option")
            custom_date = date.today()
            if override_option == "Custom Overridden Date":
                try:
                    initial_override_date = parser.parse(current_override).date() if current_override != "default" else date.today()
                except Exception:
                    initial_override_date = date.today()
                custom_date = st.date_input("Select Custom Date Override", value=initial_override_date, key="admin_date_picker")
            
            if st.button("📅 Save Date Configuration", use_container_width=True):
                st.session_state.tech_config[target_tech]["OverrideDate"] = str(custom_date) if override_option == "Custom Overridden Date" else "default"
                sync_tech_config_to_gsheets()
                st.success(f"📅 Date configuration for **{target_tech}** successfully synchronized to GSheets!")
                st.rerun()

    st.sidebar.markdown("---")
    st.stop()

# ==============================================================================
# TECHNICIAN VIEW (DYNAMIC JOB CARD FORM)
# ==============================================================================
st.title("🏗️ Job card System")

override_date_val = st.session_state.tech_config.get(logged_user, {}).get("OverrideDate", "default")
try:
    current_job_date = parser.parse(override_date_val).date() if override_date_val != "default" else date.today()
except Exception:
    current_job_date = date.today()

# --- UI LAYOUT: CORE DETAILS ---
col_1, col_2, col_3, col_4, col_5, col_6 = st.columns(6)
with col_1:
    job_date = st.date_input("Date", current_job_date, disabled=True)

with col_2:
    site = st.selectbox("Site Location", options=SITE_LIST, index=None, placeholder="Type to Search.", key="site_select_core")
    if user_most_used["sites"]:
        st.caption("⭐ **Most Used:**")
        cols_quick = st.columns(len(user_most_used["sites"]))
        for q_idx, q_site in enumerate(user_most_used["sites"]):
            with cols_quick[q_idx]:
                st.button(
                    q_site,
                    key=f"quick_site_{q_site}_{q_idx}",
                    on_click=set_quick_val,
                    args=("site_select_core", q_site),
                    use_container_width=True
                )

with col_3:
    start_location = st.selectbox("Start Location", options=LOCATION_LIST, index=None, placeholder="Select start location.", key="start_location_select_core")

with col_4:
    start_time = st.selectbox(
        "Start Time", 
        options=TIME_OPTIONS, 
        index=None, 
        placeholder="Choose start time.",
        format_func=lambda t: t.strftime("%H:%M") if t else "",
        key="start_time_select_core"
    )
    if user_most_used["times_start"]:
        st.caption("⭐ **Most Used:**")
        cols_quick = st.columns(len(user_most_used["times_start"]))
        for q_idx, q_time in enumerate(user_most_used["times_start"]):
            with cols_quick[q_idx]:
                st.button(
                    q_time.strftime("%H:%M"),
                    key=f"quick_st_{q_time.strftime('%H_%M')}_{q_idx}",
                    on_click=set_quick_val,
                    args=("start_time_select_core", q_time),
                    use_container_width=True
                )

with col_5:
    end_time = st.selectbox(
        "End Time", 
        options=TIME_OPTIONS, 
        index=None, 
        placeholder="Choose end time.",
        format_func=lambda t: t.strftime("%H:%M") if t else "",
        key="end_time_select_core"
    )
    if user_most_used["times_end"]:
        st.caption("⭐ **Most Used:**")
        cols_quick = st.columns(len(user_most_used["times_end"]))
        for q_idx, q_time in enumerate(user_most_used["times_end"]):
            with cols_quick[q_idx]:
                st.button(
                    q_time.strftime("%H:%M"),
                    key=f"quick_et_{q_time.strftime('%H_%M')}_{q_idx}",
                    on_click=set_quick_val,
                    args=("end_time_select_core", q_time),
                    use_container_width=True
                )

with col_6:
    vehicle = st.selectbox("Vehicle", options=VEHICLE_LIST, index=None, placeholder="Select Vehicle.", key="vehicle_select_core")
    if user_most_used["vehicles"]:
        st.caption("⭐ **Most Used:**")
        cols_quick = st.columns(len(user_most_used["vehicles"]))
        for q_idx, q_veh in enumerate(user_most_used["vehicles"]):
            with cols_quick[q_idx]:
                st.button(
                    q_veh,
                    key=f"quick_veh_{q_veh}_{q_idx}",
                    on_click=set_quick_val,
                    args=("vehicle_select_core", q_veh),
                    use_container_width=True
                )

work_done = st.selectbox("Description of Work", options=DONE_OPTIONS, index=None, placeholder="Select type of Work Done.", key="work_done_select_core")

st.markdown("---")

# --- UI LAYOUT: MULTIPLE TECHNICIANS ---
st.subheader("👨‍🔧 Technicians Assigned")
available_techs = [t for t in ALL_TECHS if t not in st.session_state.temp_techs]

t_col1, t_col2, t_col3 = st.columns([3, 1, 1])
with t_col1:
    selected_tech = st.selectbox("Pick Technician", options=available_techs, index=None, placeholder="Choose Technician.", key="tech_select_input")
    available_fav_techs = [t for t in user_most_used["techs"] if t not in st.session_state.temp_techs]
    if available_fav_techs:
        st.write("⭐ **Most Worked With:**")
        cols_quick = st.columns(len(available_fav_techs))
        for q_idx, q_tech in enumerate(available_fav_techs):
            with cols_quick[q_idx]:
                st.button(
                    q_tech,
                    key=f"quick_tech_{q_tech}_{q_idx}",
                    on_click=add_quick_tech,
                    args=(q_tech,),
                    use_container_width=True
                )

with t_col2:
    st.write(" ")
    st.write(" ")
    if st.button("✅ Done", key="btn_add_tech") and selected_tech:
        st.session_state.temp_techs.append(selected_tech)
        st.rerun()

with t_col3:
    st.metric(label="Technicians Count", value=len(st.session_state.temp_techs))

if st.session_state.temp_techs:
    st.write("**Added Technicians:**")
    techs = st.session_state.temp_techs
    total_techs = len(techs)
    half_index = (total_techs + 1) // 2
    row1_techs = techs[:half_index]
    row2_techs = techs[half_index:]

    if row1_techs:
        num_r1 = len(row1_techs)
        cols_r1 = st.columns([3] * num_r1 + [max(1, 20 - 3 * num_r1)])
        for idx, t in enumerate(row1_techs):
            with cols_r1[idx]:
                if st.button(f"{t} ❌", key=f"t_{idx}"):
                    st.session_state.temp_techs.pop(idx)
                    st.rerun()

    if row2_techs:
        num_r2 = len(row2_techs)
        cols_r2 = st.columns([3] * num_r2 + [max(1, 20 - 3 * num_r2)])
        for idx, t in enumerate(row2_techs):
            true_idx = idx + half_index
            with cols_r2[idx]:
                if st.button(f"{t} ❌", key=f"t_{true_idx}"):
                    st.session_state.temp_techs.pop(true_idx)
                    st.rerun()

st.markdown("---")

# --- UI LAYOUT: MATERIALS ---
st.subheader("🛠️ Materials Used")
material_pill_container = st.container()

type_size = None
qty = 0
current_colour = ""
meters = 0
module = None
make = None
item = None
item_size = None
item_meter = 0
where = None
size = None
watt = 0
door_type = None
rows_selection = None
ways_selection = None
part_spec = None
part_value = None
is_meter_item = False
is_qty_item = False
db_qty = 0

x_col_1, x_col_2 = st.columns(2)
with x_col_1:
    selected_item = st.selectbox("Pick Material", options=MATERIAL_LIST, index=None, placeholder="Choose Material.", key="material_select")
    if user_most_used["materials"]:
        st.write("⭐ **Most Used Materials:**")
        cols_quick = st.columns(len(user_most_used["materials"]))
        for q_idx, q_mat in enumerate(user_most_used["materials"]):
            with cols_quick[q_idx]:
                st.button(
                    q_mat,
                    key=f"quick_mat_{q_mat}_{q_idx}",
                    on_click=set_quick_material,
                    args=(q_mat,),
                    use_container_width=True
                )

with x_col_2:
    if selected_item:
        selected_type = st.selectbox("Pick Type", options=TYPE_LIST.get(selected_item, []), index=None, placeholder="Choose Type.", key="type_select")
    else:
        selected_type = st.selectbox("Pick Type", options=[], index=None, placeholder="Choose Type.", key="type_select_empty")

    if selected_item and selected_type:
        type_options = QTY_METER_LIST.get(selected_item, {})
        options_list = type_options.get(selected_type, [])

        is_meter_item = selected_item in SET_METER_ITEMS
        is_qty_item = selected_item in SET_QTY_ITEMS
        is_size_item = selected_item in ["Conduit", "Boxes", "Wire", "Fittings", "Cable", "Solar"]
        show_colour = selected_type in COLOUR_LIST

        # Calculate exact number of columns required
        active_widgets = 0
        if selected_item not in ["Wireway", "Lights", "DB", "DB parts"]:
            if is_size_item: active_widgets += 1
            if show_colour: active_widgets += 1
            if is_meter_item: active_widgets += 1
            if selected_item == "Fittings": active_widgets += 2
            if is_qty_item: active_widgets += 1
        else:
            if selected_item == "DB":
                active_widgets = 4
            elif selected_item == "DB parts":
                part_spec_state = st.session_state.get(f"db_part_spec_select_{selected_type}")
                if part_spec_state in ["length", "size", "amp", "overboard"]:
                    active_widgets = 2  
                elif part_spec_state == "coil":
                    active_widgets = 3
                else:
                    active_widgets = 2
            else:
                active_widgets = 3

        cols = st.columns(active_widgets) if active_widgets > 0 else []
        current_col = 0

        # General Group Rendering
        if selected_item not in ["Wireway", "Lights", "DB", "DB parts"]:
            if is_size_item:
                with cols[current_col]:
                    size_options = options_list if isinstance(options_list, list) else []
                    type_size = st.selectbox("Type Size", options=size_options, index=None, placeholder="Select size.", key=f"size_select_{selected_item}_{selected_type}")
                current_col += 1

            if show_colour:
                with cols[current_col]:
                    spec_clrs = COLOUR_LIST.get(selected_type, {})
                    if isinstance(spec_clrs, dict):
                        active_size = clean_size_str(type_size) if type_size is not None else (clean_size_str(options_list[0]) if options_list else "")
                        colours = spec_clrs.get(active_size, spec_clrs.get(str(type_size), []))
                    elif isinstance(spec_clrs, list):
                        colours = spec_clrs
                    else:
                        colours = []
                    current_colour = st.selectbox("Colour", options=colours, index=None, placeholder="Select colour.", key=f"wire_colour_{selected_item}_{selected_type}")
                current_col += 1

            if is_meter_item:
                with cols[current_col]:
                    meters = st.number_input("Meters", min_value=0, step=1, value=0, key=f"meter_input_{selected_item}_{selected_type}")
                current_col += 1

            if selected_item == "Fittings":
                with cols[current_col]:
                    module = st.selectbox("Module", options=MODULE_MAKE_LIST.get(type_size, {}).get("Modules", []), index=None, placeholder="Select module.", key=f"module_select_{selected_item}_{type_size}")
                current_col += 1
                with cols[current_col]:
                    make = st.selectbox("Make", options=MODULE_MAKE_LIST.get(type_size, {}).get("Make", []), index=None, placeholder="Select make.", key=f"make_select_{selected_item}_{type_size}")
                current_col += 1

            if is_qty_item:
                with cols[current_col]:
                    qty = st.number_input("Quantity", min_value=0, step=1, value=0, key=f"qty_select_{selected_item}_{selected_type}")
                current_col += 1

        # Specialized Widget Blocks
        elif selected_item == "Wireway":
            with cols[current_col]:
                item_data = QTY_METER_LIST.get("Wireway", {})
                available_items = item_data.get(selected_type, [])
                item = st.selectbox("Item", options=available_items, index=None, placeholder="Select item.", key=f"wireway_item_select_{selected_type}")
            current_col += 1
            with cols[current_col]:
                lookup_key = item.lower() if isinstance(item, str) else str(item)
                available_size = ITEM_SIZE_LIST.get(lookup_key, [])
                item_size = st.selectbox("Item Size", options=available_size, index=None, placeholder="Select size.", key=f"wireway_size_select_{selected_type}_{item}")
            current_col += 1
            with cols[current_col]:
                item_meter = st.number_input("Meters", min_value=0, step=1, value=0, key=f"wireway_meter_select_{selected_type}")
            current_col += 1

        elif selected_item == "Lights":
            with cols[current_col]:
                place_data = QTY_METER_LIST.get("Lights", {})
                available_places = place_data.get(selected_type, [])
                where = st.selectbox("Light Placement", options=available_places, index=None, placeholder="Select Placement.", key=f"place_select_{selected_type}")
            current_col += 1
            with cols[current_col]:
                watt = st.selectbox("Watt", options=list(range(1, 201)), index=None, placeholder="Select Wattage.", key=f"watt_select_{selected_type}")
            current_col += 1
            if watt is not None:
                with cols[current_col]:
                    lookup_where = where.lower() if isinstance(where, str) else str(where)
                    sizes = LIGHT_SIZE_LIST.get(lookup_where, ["Watt"]) if where is not None else ["Watt"]
                    size = st.selectbox("Light Size", options=sizes, index=None, placeholder='Select size.', key=f"light_size_select_{selected_type}_{where}")
                current_col += 1

        elif selected_item == "DB":
            with cols[current_col]:
                sizes = DB_CONFIG_DICT if DB_CONFIG_DICT else QTY_METER_LIST.get("DB", {})
                size = st.selectbox("Size", options=list(sizes.keys()), index=None, placeholder="Select Size.", key="size_door_select")
            current_col += 1
            if size is not None:
                config = sizes.get(size, {}) if isinstance(sizes.get(size), dict) else {"max_rows": 10, "max_ways": 20}
                max_rows = config.get("max_rows", 10)
                with cols[current_col]:
                    rows_selection = st.selectbox("No. of rows", options=list(range(1, max_rows + 1)), index=None, placeholder="Select rows.", key="db_rows_select")
                current_col += 1
                max_ways = config.get("max_ways", 20)
                with cols[current_col]:
                    ways_selection = st.selectbox("No. ways per row", options=list(range(1, max_ways + 1)), index=None, placeholder="Select ways.", key="db_ways_select")
                current_col += 1
                with cols[current_col]:
                    db_qty = st.number_input("Quantity", min_value=0, step=1, value=0, key="db_qty_input")
                current_col += 1

        elif selected_item == "DB parts":
            with cols[current_col]:
                spec_options = options_list if isinstance(options_list, list) else []
                part_spec = st.selectbox("Part Specification", options=spec_options, index=None, placeholder="Select specification.", key=f"db_part_spec_select_{selected_type}")
            current_col += 1
            if part_spec in ["length", "size", "amp", "overboard", "coil"]:
                with cols[current_col]:
                    if part_spec == "length":
                        part_value = st.selectbox("meters", options=list(range(1, 11)), index=None, placeholder="Select length.", key="db_part_length_select")
                    elif part_spec == "size":
                        part_value = st.selectbox("Size", options=list(range(1, 21)), index=None, placeholder="Select size.", key="db_part_size_select")
                    elif part_spec == "amp":
                        part_value = st.selectbox("Amps", options=list(range(1, 1001)), index=None, placeholder="Select amps.", key="db_part_amp_select")
                    elif part_spec == "overboard":
                        part_value = st.selectbox("Overboard Amps", options=list(range(1, 51)), index=None, placeholder="Select amps.", key="db_part_overboard_select")
                    elif part_spec == "coil":
                        part_value = st.selectbox("Volts", options=["24V", "220V", "400V"], index=None, placeholder="Select voltage.", key="db_part_coil_select")
                current_col += 1
            if part_spec not in ["length", "size", "amp", "overboard"]:
                with cols[current_col]:
                    db_qty = st.number_input("Quantity", min_value=0, step=1, value=0, key=f"db_part_qty_input_{selected_type}")
                current_col += 1

        # Format Material Summary
        if selected_item == "Fittings":
            material_label = f"Fittings: {selected_type}"
            if type_size: material_label += f" (Size: {type_size})"
            if module: material_label += f" , Module: {module}"
            if make: material_label += f"  Make: {make}"
            if qty > 0: material_label += f" , Qty: {qty}"
        elif selected_item == "Wireway":
            material_label = f"Wireway: {selected_type}"
            if item: material_label += f" , Item: {item}"
            if item_size: material_label += f" , Size: {item_size}"
            if item_meter > 0: material_label += f" , {item_meter}m"
        elif selected_item == "Lights":
            material_label = f"Lights: {selected_type}"
            if where: material_label += f" , Placement: {where}"
            if size: material_label += f" , Size: {size}"
            if watt and watt > 0: material_label += f" , {watt}W"
        elif selected_item == "DB":
            material_label = f"DB: {selected_type}"
            if size: material_label += f" , Size: {size}"
            if rows_selection: material_label += f" , Rows: {rows_selection}"
            if ways_selection: material_label += f" , Ways/Row: {ways_selection}"
            if db_qty > 0: material_label += f" , Qty: {db_qty}"
        elif selected_item == "DB parts":
            material_label = f"DB parts: {selected_type}"
            if part_spec:
                material_label += f" , {part_spec}"
                if part_value:
                    unit = "A" if part_spec in ["amp", "overboard"] else ""
                    material_label += f" ({part_value}{unit})"
            if part_spec not in ["length", "size", "amp", "overboard"] and db_qty > 0:
                material_label += f" , Qty: {db_qty}"
        else:
            material_label = f"{selected_item}: {selected_type}"
            if type_size: 
                spec_label = "Specification" if selected_item == "DB parts" else "Size"
                material_label += f" ({spec_label}: {type_size})"
            if current_colour: material_label += f" , Color: {current_colour}"
            if is_meter_item and meters > 0: material_label += f" , {meters}m"
            if is_qty_item and qty > 0: material_label += f" , Qty: {qty}"

        if st.button("✅ Done", key="btn_add_material"):
            st.session_state.temp_materials.append(material_label)

    if st.session_state.temp_materials:
        st.write("**Added Materials:**")
        for idx, m in enumerate(st.session_state.temp_materials):
            mc1, mc2 = st.columns([0.9, 0.1])
            mc1.info(m)
            if mc2.button("❌", key=f"m_{idx}"):
                st.session_state.temp_materials.pop(idx)
                st.rerun()

st.markdown("---")

# --- POPULATE STICKY PROGRESS HEADER ---
with header_container:
    st.markdown("<div class='fixed-header'></div>", unsafe_allow_html=True)
    completed_items = []
    if site: completed_items.append(f"Site: {site}")
    if start_location: completed_items.append(f"Start Location: {start_location}")
    if start_time: completed_items.append(f"Start: {start_time.strftime('%H:%M')}")
    if end_time: completed_items.append(f"End: {end_time.strftime('%H:%M')}")
    if vehicle: completed_items.append(f"Vehicle: {vehicle}")
    if work_done: completed_items.append("Work Description")
    if st.session_state.temp_techs: completed_items.append(f"Technicians Assigned ({len(st.session_state.temp_techs)})")
    if st.session_state.temp_materials or selected_item:
        mats_desc = f"Materials ({len(st.session_state.temp_materials)})" if len(st.session_state.temp_materials) > 0 else f"Material Selected: {selected_item}"
        completed_items.append(mats_desc)

    total_slots = 8
    filled_slots = sum([
        1 if site else 0,
        1 if start_location else 0,
        1 if start_time else 0,
        1 if end_time else 0,
        1 if vehicle else 0,
        1 if work_done else 0,
        1 if st.session_state.temp_techs else 0,
        1 if (st.session_state.temp_materials or selected_item) else 0
    ])
    progress_pct = int((filled_slots / total_slots) * 100)
    st.progress(filled_slots / total_slots)
    if completed_items:
        st.caption(f"📊 **Job Card Completion Progress ({progress_pct}%):** Selected: {', '.join(completed_items)}")
    else:
        st.caption("📊 **Job Card Completion Progress (0%):** Start by selecting options below.")

with material_pill_container:
    live_material_label = ""
    if selected_item:
        live_material_label = f"{selected_item}"
        if selected_type:
            if selected_item == "Fittings":
                live_material_label = f"Fittings: {selected_type}"
                if type_size: live_material_label += f" (Size: {type_size})"
                if module: live_material_label += f" , Module: {module}"
                if make: live_material_label += f"  Make: {make}"
                if qty > 0: live_material_label += f" , Qty: {qty}"
            elif selected_item == "Wireway":
                live_material_label = f"Wireway: {selected_type}"
                if item: live_material_label += f" , Item: {item}"
                if item_size: live_material_label += f" , Size: {item_size}"
                if item_meter > 0: live_material_label += f" , {item_meter}m"
            elif selected_item == "Lights":
                live_material_label = f"Lights: {selected_type}"
                if where: live_material_label += f" , Placement: {where}"
                if size: live_material_label += f" , Size: {size}"
                if watt and watt > 0: live_material_label += f" , {watt}W"
            elif selected_item == "DB":
                live_material_label = f"DB: {selected_type}"
                if size: live_material_label += f" , Size: {size}"
                if rows_selection: live_material_label += f" , Rows: {rows_selection}"
                if ways_selection: live_material_label += f" , Ways/Row: {ways_selection}"
                if db_qty > 0: live_material_label += f" , Qty: {db_qty}"
            elif selected_item == "DB parts":
                live_material_label = f"DB parts: {selected_type}"
                if part_spec:
                    live_material_label += f" , {part_spec}"
                    if part_value:
                        unit = "A" if part_spec in ["amp", "overboard"] else ""
                        live_material_label += f" ({part_value}{unit})"
                if part_spec not in ["length", "size", "amp", "overboard"] and db_qty > 0:
                    live_material_label += f" , Qty: {db_qty}"
            else:
                live_material_label = f"{selected_item}: {selected_type}"
                if type_size: live_material_label += f" (Size: {type_size})"
                if current_colour: live_material_label += f" , Color: {current_colour}"
                if selected_item in ["Conduit", "Wire", "Cable"] and meters > 0:
                    live_material_label += f" , {meters}m"
                if selected_item in ["Boxes", "Fittings", "Solar"] and qty > 0:
                    live_material_label += f" , Qty: {qty}"

    if selected_item and live_material_label:
        st.info(f"🛠️ **Active Material Selection:** {live_material_label}")

# ==============================================================================
# CONFIRMATION MODAL & SAVE DIRECTLY TO 'JobCards' WORKSHEET
# ==============================================================================
@st.dialog("Confirm Save")
def confirm_save_modal():
    st.write("❓ Are you sure you would like to save this job card to the **JobCards** sheet?")
    st.markdown(f"**Date:** {job_date}")
    st.markdown(f"**Site:** {site if site else 'Not Selected'}")
    st.markdown(f"**Start Location:** {start_location if start_location else 'Not Selected'}")
    st.markdown(f"**Start Time:** {start_time.strftime('%H:%M') if start_time else 'Not Selected'}")
    st.markdown(f"**End Time:** {end_time.strftime('%H:%M') if end_time else 'Not Selected'}")
    st.markdown(f"**Vehicle:** {vehicle if vehicle else 'Not Selected'}")
    st.markdown(f"**Work Description:** {work_done if work_done else 'Not Selected'}")
    st.markdown(f"**Technicians Assigned:** {', '.join(st.session_state.temp_techs)}")
    st.markdown(f"**Materials Added ({len(st.session_state.temp_materials)} items):**")
    for m_item in st.session_state.temp_materials:
        st.markdown(f"- {m_item}")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Yes, Save", use_container_width=True, key="modal_confirm_yes"):
            with st.spinner("Writing Job Card to 'JobCards' tab in Google Sheets..."):
                try:
                    existing_data = pd.DataFrame()
                    try:
                        df_read = conn.read(spreadsheet=SHEET_URL, worksheet="JobCards", ttl=0)
                        if df_read is not None and not df_read.empty:
                            existing_data = df_read.dropna(how="all")
                    except Exception:
                        existing_data = pd.DataFrame()
                    
                    mat_summary = " , ".join(st.session_state.temp_materials) if st.session_state.temp_materials else "None"
                    tech_summary = ", ".join(st.session_state.temp_techs) if st.session_state.temp_techs else logged_user
                    
                    new_entry = pd.DataFrame([{
                        "Date": str(job_date),
                        "Site Location": site if site else "Other",
                        "Start Location": start_location if start_location else "Stores",
                        "Start Time": start_time.strftime("%H:%M") if start_time else "",
                        "End Time": end_time.strftime("%H:%M") if end_time else "",
                        "Vehicle": vehicle if vehicle else "",
                        "Work Description": work_done if work_done else "",
                        "Technicians Assigned": tech_summary,
                        "Materials Used": mat_summary,
                        "Submitted By": logged_user,
                        "Submission Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }])
                    
                    if not existing_data.empty:
                        updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                    else:
                        updated_df = new_entry
                    
                    updated_df = updated_df.fillna("")

                    try:
                        conn.update(spreadsheet=SHEET_URL, worksheet="JobCards", data=updated_df)
                    except Exception:
                        conn.create(spreadsheet=SHEET_URL, worksheet="JobCards", data=updated_df)
                    
                    if logged_user in st.session_state.tech_config:
                        st.session_state.tech_config[logged_user]["OverrideDate"] = "default"
                        sync_tech_config_to_gsheets()
                    
                    st.session_state.temp_materials = []
                    st.session_state.temp_techs = [logged_user]
                    load_history_cached.clear()
                    st.session_state.user_analytics = compute_user_analytics(logged_user)
                    
                    st.toast("✅ Job Card written to 'JobCards' worksheet successfully!", icon="🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Cloud Connection Error: Failed to save to 'JobCards' worksheet. ({str(e)})")
            
    with c2:
        if st.button("❌ No, Cancel", use_container_width=True, key="modal_confirm_no"):
            st.rerun()

if st.button("🚀 SAVE FULL JOB CARD TO CLOUD"):
    if not work_done:
        st.error("Please enter a work description.")
    elif not st.session_state.temp_techs:
        st.error("Please add at least one technician.")
    else:
        confirm_save_modal()

if st.checkbox("Show Recent History"):
    data = load_history_cached(SHEET_URL)
    st.dataframe(data.tail(10), use_container_width=True)