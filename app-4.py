import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, datetime, time
from dateutil import parser
import base64

# --- PAGE SETUP ---
st.set_page_config(page_title="Cloud Job Card", layout="wide")

# Inject CSS to prevent button text from wrapping, lock the sidebar scroll, and make the header container sticky
st.markdown(
    """
    <style>
    div.stButton > button {
        white-space: nowrap !important;
    }
    /* Target the vertical container parent of our fixed-header anchor and make it sticky */
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
    /* Force the sidebar container to be completely static and non-scrollable */
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

# 1. Create connection
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["spreadsheet"]

# Global helper function for key normalization (Defined globally at the top to avoid NameErrors)
def normalize_key(val_one, val_two=None):
    if val_one is None:
         return ""
    if val_two is not None:
        return f"{val_one}_{val_two}"
    return str(val_one)

# Helper function to convert uploaded images to base64 strings safely
def get_image_base64(file):
    return base64.b64encode(file.getvalue()).decode()

# --- OPTIMIZED CACHED DATA LOADER ENGINE ---
@st.cache_data(ttl=300)
def load_history_cached(spreadsheet_url):
    """Retrieve and cache the primary job card history worksheet."""
    try:
        return conn.read(spreadsheet=spreadsheet_url, ttl="5m")
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_tech_config_cached(spreadsheet_url):
    """Retrieve and cache the administrator's technician configuration worksheet."""
    try:
        return conn.read(spreadsheet=spreadsheet_url, worksheet="TechConfig", ttl="10m")
    except Exception:
        return pd.DataFrame()

# 2. Base Data Lists (Alphabetized A-Z)
ALL_TECHS = [
    "Audrine", "Austin", "Brad", "Daniello", "Denzel", "Denver", 
    "Elvin", "Ernest", "James", "Lionel", "Randell", "Sam", 
    "Sylvester", "Wayne", "Wynand"
]

# Admin Default Seed Passcode Registry
TECH_PASSWORDS = {
    "Audrine": "Aud901", "Austin": "Aus782", "Brad": "Bra302", "Daniello": "Dan661",
    "Denzel": "Den868", "Denver": "Dev923", "Elvin": "Elv518", "Ernest": "Ern189",
    "James": "Jam871", "Lionel": "Lio225", "Randell": "Ran661", "Sam": "Sam108",
    "Sylvester": "Syl109", "Wayne": "Way110", "Wynand": "Wyn111"
}

ADMIN_PASSCODE = "admin123"

VEHICLE_LIST = ["CJ108-920", "CJ108-921", "CJ18927", "CJ22510", "CJ30224", "CJ51885", "CJ59445", "CJ61135", "CJ66164", "CJ66657", "CJ77944", "CJ77945", "CJ78246", "CJ86828", "CJ87120", "CJ91137", "CJ92340"]

SITE_LIST = ["Other", "Site A", "Site B", "Site C"]

LOCATION_LIST = ["Home", "Stores"]

MATERIAL_LIST = ["Boxes", "Cable", "Conduit", "DB", "DB parts", "Fittings", "Lights", "Solar", "Wire", "Wireway"]

TYPE_LIST = {
    "Boxes": ["Fibre", "Galv", "PVC", "Steel"],
    "Cable": ["HO7", "SWA", "Surfix", "Twin & Earth"],
    "Conduit": ["Galv", "PVC", "Sleeve", "Spraque"],
    "DB": ["Flush", "Flush 1 door", "Flush 2 door", "Surface", "Surface 1 door", "Flush 1 door", "Surface 2 door", "Flush 2 door"],
    "DB parts": ["Breakers", "Busbar", "Contactors", "Timers"],
    "Fittings": ["Isolators", "Plugs", "Switches"],
    "Lights": ["External", "Internal"],
    "Solar": ["Battery", "Inverter grid-tied", "Inverter hybrid", "Panels"],
    "Wire": ["AC", "DC"],
    "Wireway": ["Galv", "PVC"]
}

QTY_ITEMS = ["Boxes", "Fittings", "DB", "DB parts", "Solar"]
METER_ITEMS = ["Conduit", "Wire", "Cable"]
WATTS_ITEMS = ["Lights"]

QTY_METER_LIST = {
    "Boxes": {
        "Fibre": ["1phase meter box", "2x4 wp", "3phase meter box", "4x4 wp", "pool"],
        "Galv": ["2x4 flush", "2x4 surface", "4x4 flush", "4x4 surface", "round", "round extension", "round lid", "round lid o/size"],
        "PVC": ["2x4 flush", "2x4 surface", "4x4 flush", "4x4 surface", "round", "round extension", "round lid", "round lid o/size"],
        "Steel": ["1phase meter box", "2x4 surface", "3phase meter box", "4x4 surface"]
    },
    "Cable": {
        "HO7": ["1.5x2c", "1.5x3c", "1.5x4c", "4x2c", "4x3c", "4x4c", "6x2c", "6x3c", "6x4c", "10x2c", "10x3c", "10x4c", "16x2c", "16x3c", "16x4c", "25x4c", "35x4c", "50x4c", "70x4c", "95x4c", "120x4c", "150x4c", "185x4c", "200x4c", "250x4c", "300x4c", "400x4c", "500x4c", "630x4c"],
        "SWA": ["1.5x2c", "1.5x3c", "1.5x4c", "4x2c", "4x3c", "4x4c", "6x2c", "6x3c", "6x4c", "10x2c", "10x3c", "10x4c", "16x2c", "16x3c", "16x4c", "25x4c", "35x4c", "50x4c", "70x4c", "95x4c", "120x4c", "150x4c", "185x4c", "200x4c", "250x4c", "300x4c", "400x4c", "500x4c", "630x4c"],
        "Surfix": ["1.5x2c", "1.5x3c", "1.5x4c", "4x2c", "4x3c", "4x4c", "6x2c", "6x3c", "6x4c", "10x2c", "10x3c"],
        "Twin & Earth": ["1.5x2c", "1.5x3c", "4x2c", "6x2c", "10x2c"]
    },
    "Conduit": {
        "Galv": [20, 25, 32, 40, 50],
        "PVC": [20, 25, 32, 40, 50], 
        "Sleeve": [110], 
        "Spraque": [20, 25, 32, 40, 50]
    },
    "DB": {
        "Flush": {"max_rows": 10, "max_ways": 20},
        "Flush 1 door": {"max_rows": 10, "max_ways": 20},
        "Flush 2 door": {"max_rows": 10, "max_ways": 20},
        "Surface": {"max_rows": 10, "max_ways": 20},
        "Surface 1 door": {"max_rows": 10, "max_ways": 20},
        "Surface 2 door": {"max_rows": 10, "max_ways": 20}
    },
    "DB parts": {
        "Breakers": ["amp", "ATS", "change over", "double pole", "four pole", "single pole", "three pole"],
        "Busbar": ["insulator", "length", "neutral clip-in", "phase clip-in", "size"],
        "Contactors": ["amp", "coil", "double pole", "four pole", "overboard", "three pole"],
        "Timers": ["standard", "wifi"]
    },
    "Fittings": {
        "Isolators": ["2x4", "4x4", "6way", "8way", "own box", "rounds"],
        "Plugs": ["2x4", "4x4", "6way", "8way", "own box", "rounds"],
        "Switches": ["2x4", "4x4", "6way", "8way", "own box", "rounds"]
    },
    "Lights": {
        "External": ["ceiling light", "donwlight", "flood", "panel", "post top", "wall light"],
        "Internal": ["downlight", "flood", "highbay", "wall light"]
    },
    "Solar": {
        "Battery": ["KW"],
        "Inverter grid-tied": ["KW"],
        "Inverter hybrid": ["KW"],
        "Panels": ["Watt"]
    },
    "Wire": {
        "AC": [1, 1.5, 2.5, 4, 6, 10, 16, 25], 
        "DC": [6, 10, 16, 25, 35, 50, 70]
    },
    "Wireway": {
        "Galv": ["duct", "light duty tray", "medium duty tray", "wiremesh"],
        "PVC": ["power skirt", "trunking"]
    }
}

MODULE_MAKE_LIST = {
    "rounds": {"Modules": ["5A"], "Make": ["CBI"]}, 
    "2x4": {
        "Modules": ["16A", "1lever", "2 Pin", "2x 16A", "Dim<500W", "Dim>500W", "RJ45", "Shuko", "USB"], 
        "Make": ["ARTEOR", "CRABTREE", "WACO"]
    }, 
    "4x4": {
        "Modules": ["16A", "1lever", "2 Pin", "2x 16A", "Dim<500W", "Dim>500W", "RJ45", "Shuko", "USB"], 
        "Make": ["ARTEOR", "CRABTREE", "WACO"]
    }, 
    "6way": {
        "Modules": ["16A", "1lever", "2 Pin", "2x 16A", "Dim<500W", "Dim>500W", "RJ45", "Shuko", "USB"], 
        "Make": ["ARTEOR", "CRABTREE", "WACO"]
    }, 
    "8way": {
        "Modules": ["16A", "1lever", "2 Pin", "2x 16A", "Dim<500W", "Dim>500W", "RJ45", "Shuko", "USB"], 
        "Make": ["ARTEOR", "CRABTREE", "WACO"]
    }, 
    "own box": {
        "Modules": ["16A", "1lever", "2 Pin", "2x 16A", "5A", "Dim<500W", "Dim>500W", "RJ45", "Shuko", "USB"], 
        "Make": ["ARTEOR", "CBI", "CRABTREE", "WACO"]
    }
}

COLOUR_LIST = {
    "AC": {
        "1": ["black", "blue", "brown", "green_yellow", "grey", "pink", "purple", "red", "white", "yellow"], 
        "1.5": ["black", "blue", "brown", "green_yellow", "grey", "pink", "purple", "red", "white", "yellow"], 
        "2.5": ["black", "blue", "brown", "green_yellow", "grey", "pink", "purple", "red", "white", "yellow"], 
        "4": ["black", "blue", "brown", "green_yellow", "grey", "pink", "purple", "red", "white", "yellow"], 
        "6": ["black", "blue", "brown", "green_yellow", "grey", "pink", "purple", "red", "white", "yellow"], 
        "10": ["black", "blue", "green_yellow", "red", "white", "yellow"], 
        "16": ["black", "blue", "green_yellow", "red", "white", "yellow"], 
        "25": ["black", "blue", "green_yellow", "red", "white", "yellow"]
    }, 
    "DC": {
        "6": ["black", "blue", "brown", "green_yellow", "grey", "pink", "purple", "red", "white", "yellow"], 
        "10": ["black", "blue", "green_yellow", "red", "white", "yellow"], 
        "16": ["black", "blue", "green_yellow", "red", "white", "yellow"], 
        "25": ["black", "blue", "green_yellow", "red", "white", "yellow"], 
        "35": ["black", "blue", "green_yellow", "red", "white", "yellow"], 
        "50": ["black", "blue", "green_yellow", "red", "white", "yellow"], 
        "70": ["black", "blue", "green_yellow", "red", "white", "yellow"]
    }, 
    "Twin & Earth": {
        "1.5x2c": ["Black", "White"], 
        "1.5x3c": ["Black", "White"], 
        "4x2c": ["Black", "White"], 
        "6x2c": ["Black", "White"], 
        "10x2c": ["Black", "White"]
    }, 
    "Surfix": {
        "1.5x2c": ["Black", "White"], "1.5x3c": ["Black", "White"], "1.5x4c": ["Black", "White"], 
        "4x2c": ["Black", "White"], "4x3c": ["Black", "White"], "4x4c": ["Black", "White"], 
        "6x2c": ["Black", "White"], "6x3c": ["Black", "White"], "6x4c": ["Black", "White"], 
        "10x2c": ["Black", "White"], "10x3c": ["Black", "White"]
    }, 
    "Panels": {
        "Watt": ["Black", "Blue"]
    }
}

ITEM_SIZE_LIST = {
    "power skirt": ["1compartment", "2compartment"], 
    "trunking": ["100x40", "16x16", "16x25", "40x40"], 
    "duct": ["p2000", "p2000 lid galv", "p2000 lid pvc", "p4000", "p4000 lid galv", "p4000 lid pvc", "p8000", "p8000 lid galv", "p8000 lid pvc", "p9000", "p9000 lid galv", "p9000 lid pvc"], 
    "wiremesh": [50, 75, 110, 200], 
    "light duty tray": [50, 75, 110, 200], 
    "medium duty tray": [50, 75, 110, 200]
}
LIGHT_SIZE_LIST = {"wall light": ["Watt"], "ceiling light": ["Watt"], "panel": ["Watt"], "downlight": ["Watt"], "flood": ["Watt"], "highbay": ["Watt"], "post top": ["Watt"]}

LOCATION_LIST = ["Home", "Stores"]

# 3. Initialize Session State
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

# Load/Initialize Technicians Configuration from GSheets dynamically using optimized caching
if "tech_config" not in st.session_state:
    df_techs = load_tech_config_cached(SHEET_URL)
    if not df_techs.empty:
        # Ensure 'LockedOut' and 'OverrideDate' columns exist cleanly inside the read dataframe
        if "LockedOut" not in df_techs.columns:
            df_techs["LockedOut"] = False
        if "OverrideDate" not in df_techs.columns:
            df_techs["OverrideDate"] = "default"
        # Convert df back to a nested config dictionary with state
        st.session_state.tech_config = df_techs.set_index("Technician").to_dict(orient="index")
    else:
        # Fallback dictionary with lockout states initialized as False and OverrideDate as "default"
        st.session_state.tech_config = {
            t: {"Password": TECH_PASSWORDS[t], "LockedOut": False, "OverrideDate": "default"} for t in ALL_TECHS
        }
        # Attempt to write this worksheet to GSheets silently to initialize database
        try:
            df_init = pd.DataFrame([
                {"Technician": k, "Password": v["Password"], "LockedOut": v["LockedOut"], "OverrideDate": v.get("OverrideDate", "default")}
                for k, v in st.session_state.tech_config.items()
            ])
            conn.update(spreadsheet=SHEET_URL, worksheet="TechConfig", data=df_init)
        except Exception:
            pass

# --- SECURE USER LOGIN GATEWAY ---
if st.session_state.logged_in_user is None and not st.session_state.is_admin:
    st.markdown("<br><br>", unsafe_allow_html=True)
    login_col1, login_col2, login_col3 = st.columns([1, 2, 1])
    with login_col2:
        # Gateway Login Title Header placed cleanly above inputs
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="margin-bottom: 0px;">Job card System Login</h1>
                <p style="color: gray; margin-top: 5px;">Select your profile and enter passcode to access the system</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Gateway Login Tabs separating technicians from the administrator
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
                # Fetch dynamically updated user state from database
                user_record = st.session_state.tech_config.get(login_user, {})
                
                if not login_user:
                    st.error("Please select your profile to log in.")
                elif user_record.get("LockedOut", False):
                    st.error("❌ Access Denied: Your profile has been locked by the administrator.")
                elif login_password != user_record.get("Password"):
                    st.error("Incorrect password. Please try again.")
                else:
                    st.session_state.logged_in_user = login_user
                    # Automatically add the logged-in user to Assigned Technicians list on login
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
    st.stop() # Freeze application flow until active authentication is met

# --- SIDEBAR: LOGGED IN USER PROFILE DASHBOARD ---
logged_user = st.session_state.logged_in_user

if st.session_state.is_admin:
    # 1. Admin Profile picture square rounded box positioned at the absolute top of the sidebar panel
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
        # Minimalist Admin Avatar fallback display
        st.sidebar.markdown(
            f"""
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
        # Compact warning notice banner instructing admin to upload an image
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
    # 1. Profile picture square rounded box positioned at the absolute top of the sidebar panel
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
        # Compact initials fallback styled inside a clean rounded square
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
    
        # Compact warning notice banner instructing user to upload an image
        st.sidebar.markdown(
            """
            <div style="text-align: center; padding: 6px; font-size: 11px; color: #856404; background-color: #fff3cd; border-radius: 8px; border: 1px solid #ffeeba; margin: 5px 10px 5px 10px;">
                📸 <b>Setup Required:</b> Upload profile picture below to permanently set a photo.
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Let users upload their profile picture only the first time they log in
        uploaded_img = st.sidebar.file_uploader("Upload Profile Picture", type=["png", "jpg", "jpeg"], key="profile_pic_upload", label_visibility="collapsed")
        if uploaded_img:
            st.session_state.profile_pics[logged_user] = get_image_base64(uploaded_img)
            st.rerun()

    # 2. Text headers and login status located directly under the avatar box
    st.sidebar.markdown("<h3 style='text-align: center; margin-top: 5px; margin-bottom: 0px;'>User Profile</h3>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<div style='text-align: center;'>Logged in as: <b>{logged_user}</b></div>", unsafe_allow_html=True)

    # 3. Compact line separator dividing profile identity and administrative metadata
    st.sidebar.markdown("<hr style='margin: 8px 0px;' />", unsafe_allow_html=True)

    # 4. Submitted Job Cards compact metric count (styled smaller under the separator)
    # Read history once globally via optimized cached engine
    df_history_global = load_history_cached(SHEET_URL)
    try:
        if not df_history_global.empty and "Technicians" in df_history_global.columns and "Date" in df_history_global.columns:
            # Drop rows where vital fields are null to filter out empty rows from count [2]
            df_valid = df_history_global.dropna(subset=["Technicians", "Date"]) [2]
            logged_jobs_count = df_valid["Technicians"].str.contains(logged_user, case=False, na=False).sum() [2]
        else:
            logged_jobs_count = 0
    except Exception:
        logged_jobs_count = 0
        
    st.sidebar.markdown(
        f"""
        <div style="text-align: center; margin-top: 5px; margin-bottom: 10px;">
            <div style="font-size: 11px; color: #808495; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Submitted Job Cards</div>
            <div style="font-size: 24px; font-weight: 700; color: var(--text-color); margin-top: 2px;">{logged_jobs_count}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# 5. Logout action box styled solid matching neutral/grey secondary configuration positioned exactly below the metrics card
if st.sidebar.button("🚪 Log Out", use_container_width=True, type="secondary"):
    st.session_state.logged_in_user = None
    st.session_state.is_admin = False
    st.session_state.temp_techs = []
    st.session_state.temp_materials = []
    st.rerun()

# --- BACKGROUND RECENT/FAVORITE METRIC EXTRACTION ENGINE ---
user_most_used = {
    "sites": [],
    "vehicles": [],
    "techs": [],
    "materials": [],
    "times_start": [],
    "times_end": []
}

time_options = [time(h, m) for h in range(24) for m in (0, 15, 30, 45)]

# Optimized: Reuse the globally loaded cached history dataframe to extract user favorites with zero extra network reads
if logged_user and not st.session_state.is_admin and not df_history_global.empty and "Technicians" in df_history_global.columns:
    try:
        df_user = df_history_global[df_history_global["Technicians"].dropna().str.contains(logged_user, case=False, na=False)]
        
        if not df_user.empty:
            # 1. Extract most visited Sites (exclude header structures)
            if "Site" in df_user.columns:
                top_sites = df_user["Site"].dropna().value_counts().index.tolist()
                user_most_used["sites"] = [s for s in top_sites if s in SITE_LIST][:3]
            
            # 2. Extract most driven Vehicles
            if "Vehicle" in df_user.columns:
                top_vehicles = df_user["Vehicle"].dropna().value_counts().index.tolist()
                user_most_used["vehicles"] = [v for v in top_vehicles if v in VEHICLE_LIST][:3]
            
            # 3. Extract most frequent co-workers (Technicians)
            all_coworkers = []
            for t_list in df_user["Technicians"].dropna().tolist():
                parts = [p.strip() for p in t_list.split(",")]
                for p in parts:
                    if p != logged_user and p in ALL_TECHS:
                        all_coworkers.append(p)
            if all_coworkers:
                user_most_used["techs"] = pd.Series(all_coworkers).value_counts().index.tolist()[:3]
            
            # 4. Extract most logged Material Categories
            all_mats = []
            if "Materials" in df_user.columns:
                for m_list in df_user["Materials"].dropna().tolist():
                    parts = [p.strip() for p in m_list.split(",")]
                    for p in parts:
                        category = p.split(":")[0].strip() if ":" in p else p.split(" ")[0].strip()
                        if category in MATERIAL_LIST:
                            all_mats.append(category)
                if all_mats:
                    user_most_used["materials"] = pd.Series(all_mats).value_counts().index.tolist()[:3]
                    
            # 5. Extract most common Start Times
            if "Start Time" in df_user.columns:
                top_starts = df_user["Start Time"].dropna().value_counts().index.tolist()
                for ts in top_starts:
                    try:
                        t_obj = parser.parse(ts).time()
                        if t_obj in time_options:
                            user_most_used["times_start"].append(t_obj)
                    except Exception:
                        pass
                user_most_used["times_start"] = user_most_used["times_start"][:3]
                
            # 6. Extract most common End Times
            if "End Time" in df_user.columns:
                top_ends = df_user["End Time"].dropna().value_counts().index.tolist()
                for te in top_ends:
                    try:
                        t_obj = parser.parse(te).time()
                        if t_obj in time_options:
                            user_most_used["times_end"].append(t_obj)
                    except Exception:
                        pass
                user_most_used["times_end"] = user_most_used["times_end"][:3]
    except Exception:
        pass

# --- APP MASTER STICKY PROGRESS CONTAINER AT THE ABSOLUTE TOP OF THE PAGE ---
header_container = st.container()

# ==========================================
# ============ ADMINISTRATOR VIEW ============
# ==========================================
if st.session_state.is_admin:
    st.title("🛠️ Job Card System Admin Console")
    st.markdown("Use this terminal panel to manage user profiles, locks, and configure job settings globally.")
    
    # We removed the Credentials Locker page from here completely as requested
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
                    # Update local state
                    st.session_state.tech_config[edit_user]["Password"] = new_pass
                    # Sync to GSheets worksheet 'TechConfig' and invalidate cache to load update live
                    try:
                        df_sync = pd.DataFrame([
                            {"Technician": k, "Password": v["Password"], "LockedOut": v["LockedOut"], "OverrideDate": v.get("OverrideDate", "default")}
                            for k, v in st.session_state.tech_config.items()
                        ])
                        conn.update(spreadsheet=SHEET_URL, worksheet="TechConfig", data=df_sync)
                        load_tech_config_cached.clear()
                        st.success(f"🔒 Password for **{edit_user}** successfully updated in the GSheets cloud database!")
                    except Exception:
                        st.success(f"🔒 Password for **{edit_user}** updated in local secure memory fallback.")
                    
                    st.rerun()
                    
    with admin_tabs[1]:
        st.write("### Technician Lockout Control Dashboard")
        st.markdown("Locking a technician blocks them from accessing the Job Card System entirely.")
        
        # Build locked list table
        table_rows = []
        for k, v in st.session_state.tech_config.items():
            status = "🔴 Locked Out" if v["LockedOut"] else "🟢 Active"
            table_rows.append({"Technician": k, "Access Status": status})
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
        
        st.markdown("---")
        lock_user = st.selectbox("Select Technician to Toggle Access", options=ALL_TECHS, index=None, placeholder="Pick user...", key="admin_lockout_user_select")
        if lock_user:
            current_lock_state = st.session_state.tech_config[lock_user]["LockedOut"]
            st.write(f"Current State: **{'Locked Out' if current_lock_state else 'Active'}**")
            
            # Action toggle button
            action_label = "🔓 Unlock Technician" if current_lock_state else "🔒 Lock Out Technician"
            if st.button(action_label, use_container_width=True, type="primary" if not current_lock_state else "secondary"):
                # Toggle Boolean
                st.session_state.tech_config[lock_user]["LockedOut"] = not current_lock_state
                # Sync back to GSheets TechConfig worksheet and invalidate cache
                try:
                    df_sync = pd.DataFrame([
                        {"Technician": k, "Password": v["Password"], "LockedOut": v["LockedOut"], "OverrideDate": v.get("OverrideDate", "default")}
                        for k, v in st.session_state.tech_config.items()
                    ])
                    conn.update(spreadsheet=SHEET_URL, worksheet="TechConfig", data=df_sync)
                    load_tech_config_cached.clear()
                    st.success(f"Status for **{lock_user}** synced in the cloud database!")
                except Exception:
                    st.success(f"Status for **{lock_user}** updated in local secure memory.")
                st.rerun()
                
    with admin_tabs[2]:
        st.write("### Configure Global Job Card Date")
        st.markdown("Set a custom date for selected technicians job card entry. If set to default, forms will automatically load today's present date.")
        
        # We can display the current custom overridden date (or default state) of each technician inside a clean dataframe
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
            
            override_option = st.radio(
                "Date Status Setup",
                options=["Default", "Custom Overridden Date"],
                index=0 if current_override == "default" else 1,
                key="admin_date_radio_option"
            )
            
            custom_date = date.today()
            if override_option == "Custom Overridden Date":
                try:
                    initial_override_date = parser.parse(current_override).date() if current_override != "default" else date.today()
                except Exception:
                    initial_override_date = date.today()
                custom_date = st.date_input("Select Custom Date Override", value=initial_override_date, key="admin_date_picker")
            
            if st.button("📅 Save Date Configuration", use_container_width=True):
                if override_option == "Custom Overridden Date":
                    st.session_state.tech_config[target_tech]["OverrideDate"] = str(custom_date)
                else:
                    st.session_state.tech_config[target_tech]["OverrideDate"] = "default"
                
                # Sync back to TechConfig worksheet on GSheets and invalidate cache
                try:
                    df_sync = pd.DataFrame([
                        {"Technician": k, "Password": v["Password"], "LockedOut": v["LockedOut"], "OverrideDate": v.get("OverrideDate", "default")}
                        for k, v in st.session_state.tech_config.items()
                    ])
                    conn.update(spreadsheet=SHEET_URL, worksheet="TechConfig", data=df_sync)
                    load_tech_config_cached.clear()
                    st.success(f"📅 Date configuration for **{target_tech}** successfully synchronized to GSheets!")
                except Exception:
                    st.success(f"📅 Date configuration for **{target_tech}** successfully updated in local memory.")
                
                st.rerun()

    st.sidebar.markdown("---")
    st.stop() # Freeze page execution for administrative actions to prevent rendering form

# ==========================================
# ============= TECHNICIAN VIEW ============
# ==========================================

# Form Title Header displayed at the top of the user form (below the master sticky progress container)
st.title("🏗️ Job card System")

# Resolve dynamically overridden form date setup
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
    
    # Site Quick Select Badges
    if user_most_used["sites"]:
        st.caption("⭐ **Most Used:**")
        cols_quick = st.columns(len(user_most_used["sites"]) + 1)
        for q_idx, q_site in enumerate(user_most_used["sites"]):
            with cols_quick[q_idx]:
                if st.button(q_site, key=f"quick_site_{q_site}_{q_idx}"):
                    st.session_state["site_select_core"] = q_site
                    st.rerun()
with col_3:
    start_location = st.selectbox("Start Location", options=LOCATION_LIST, index=None, placeholder="Select start location.", key="start_location_select_core")

with col_4:
    # Format functions are added to remove the display of seconds (HH:MM)
    start_time = st.selectbox(
        "Start Time", 
        options=time_options, 
        index=None, 
        placeholder="Choose start time.",
        format_func=lambda t: t.strftime("%H:%M") if t else "",
        key="start_time_select_core"
    )
    # Start Time Quick Select Badges
    if user_most_used["times_start"]:
        st.caption("⭐ **Most Used:**")
        cols_quick = st.columns(len(user_most_used["times_start"]) + 1)
        for q_idx, q_time in enumerate(user_most_used["times_start"]):
            with cols_quick[q_idx]:
                if st.button(q_time.strftime("%H:%M"), key=f"quick_st_{q_time.strftime('%H_%M')}_{q_idx}"):
                    st.session_state["start_time_select_core"] = q_time
                    st.rerun()
with col_5:
    end_time = st.selectbox(
        "End Time", 
        options=time_options, 
        index=None, 
        placeholder="Choose end time.",
        format_func=lambda t: t.strftime("%H:%M") if t else "",
        key="end_time_select_core"
    )
    # End Time Quick Select Badges
    if user_most_used["times_end"]:
        st.caption("⭐ **Most Used:**")
        cols_quick = st.columns(len(user_most_used["times_end"]) + 1)
        for q_idx, q_time in enumerate(user_most_used["times_end"]):
            with cols_quick[q_idx]:
                if st.button(q_time.strftime("%H:%M"), key=f"quick_et_{q_time.strftime('%H_%M')}_{q_idx}"):
                    st.session_state["end_time_select_core"] = q_time
                    st.rerun()

with col_6:
    vehicle = st.selectbox("Vehicle", options=VEHICLE_LIST, index=None, placeholder="Select Vehicle.", key="vehicle_select_core")
        
    # Vehicle Quick Select Badges
    if user_most_used["vehicles"]:
        st.caption("⭐ **Most Used:**")
        cols_quick = st.columns(len(user_most_used["vehicles"]) + 1)
        for q_idx, q_veh in enumerate(user_most_used["vehicles"]):
            with cols_quick[q_idx]:
                if st.button(q_veh, key=f"quick_veh_{q_veh}_{q_idx}"):
                    st.session_state["vehicle_select_core"] = q_veh
                    st.rerun()

done_options = ("placeholder1", "placeholder2", "placeholder3")
work_done = st.selectbox("Description of Work", options=done_options, index=None, placeholder="Select type of Work Done.", key="work_done_select_core")

st.markdown("---")

# --- UI LAYOUT: MULTIPLE TECHNICIANS ---
st.subheader("👨‍🔧 Technicians Assigned")

# Filter list to hide technicians already added
available_techs = [t for t in ALL_TECHS if t not in st.session_state.temp_techs]

# Configured 3 columns to align selection controls alongside a visual metric assigned count
t_col1, t_col2, t_col3 = st.columns([3, 1, 1])
with t_col1:
    selected_tech = st.selectbox("Pick Technician", options=available_techs, index=None, placeholder="Choose Technician.", key="tech_select_input")
    
    # Co-worker Favorite Quick Select Badges
    if user_most_used["techs"]:
        st.write("⭐ **Most Worked With:**")
        cols_quick = st.columns(len(user_most_used["techs"]) + 1)
        for q_idx, q_tech in enumerate(user_most_used["techs"]):
            if q_tech not in st.session_state.temp_techs:
                with cols_quick[q_idx]:
                    if st.button(q_tech, key=f"quick_tech_{q_tech}_{q_idx}"):
                        st.session_state.temp_techs.append(q_tech)
                        st.rerun()

with t_col2:
    st.write(" ") # Padding
    st.write(" ") # Padding for dynamic alignment with selectbox
    if st.button("✅ Done", key="btn_add_tech") and selected_tech:
        st.session_state.temp_techs.append(selected_tech)
        st.rerun()

with t_col3:
    # Metric card keeps track of total assigned technicians
    st.metric(label="Technicians Count", value=len(st.session_state.temp_techs))

# Display selected technicians divided horizontally into two compact rows
if st.session_state.temp_techs:
    st.write("**Added Technicians:**")
    techs = st.session_state.temp_techs
    total_techs = len(techs)
    
    # Ceiling division to calculate split index
    half_index = (total_techs + 1) // 2
    row1_techs = techs[:half_index]
    row2_techs = techs[half_index:]

    # Render Row 1 Compactly
    if row1_techs:
        num_r1 = len(row1_techs)
        col_widths_r1 = [3] * num_r1 + [max(1, 20 - 3 * num_r1)]
        cols_r1 = st.columns(col_widths_r1)
        for idx, t in enumerate(row1_techs):
            with cols_r1[idx]:
                # Formatted exactly as f"{t} ❌" to display the ❌ symbol on the right of each name
                if st.button(f"{t} ❌", key=f"t_{idx}"):
                    st.session_state.temp_techs.pop(idx)
                    st.rerun()

    # Render Row 2 Compactly
    if row2_techs:
        num_r2 = len(row2_techs)
        col_widths_r2 = [3] * num_r2 + [max(1, 20 - 3 * num_r2)]
        cols_r2 = st.columns(col_widths_r2)
        for idx, t in enumerate(row2_techs):
            true_idx = idx + half_index
            with cols_r2[idx]:
                if st.button(f"{t} ❌", key=f"t_{true_idx}"):
                    st.session_state.temp_techs.pop(true_idx)
                    st.rerun()

st.markdown("---")

# --- UI LAYOUT: MATERIALS ---
st.subheader("🛠️ Materials")

# Dynamic non-sticky placeholder container for the material item selection pill inside the Materials section
material_pill_container = st.container()

# Initialize global layout variables to prevent NameErrors during first execution run
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

x_col_1, x_col_2 = st.columns(2)

with x_col_1:
    # Dropdowns are strictly clean flat lists with zero category headers
    selected_item = st.selectbox("Pick Material", options=MATERIAL_LIST, index=None, placeholder="Choose Material.", key="material_select")
        
    # Material Favorites Quick Select Badges
    if user_most_used["materials"]:
        st.write("⭐ **Most Used Materials:**")
        cols_quick = st.columns(len(user_most_used["materials"]) + 1)
        for q_idx, q_mat in enumerate(user_most_used["materials"]):
            with cols_quick[q_idx]:
                if st.button(q_mat, key=f"quick_mat_{q_mat}_{q_idx}"):
                    st.session_state["material_select"] = q_mat
                    # Clear type select to avoid mismatch
                    st.session_state["type_select"] = None
                    st.rerun()

with x_col_2:
    if selected_item:
        selected_type = st.selectbox("Pick Type", options=TYPE_LIST.get(selected_item, []), index=None, placeholder="Choose Type.", key="type_select")
    else:
        selected_type = st.selectbox("Pick Type", options=[], index=None, placeholder="Choose Type.", key="type_select_empty")

    if selected_item and selected_type:
        type_options = QTY_METER_LIST.get(selected_item, {})
        options_list = type_options.get(selected_type, [])

        is_meter_item = selected_item in METER_ITEMS
        is_qty_item = selected_item in QTY_ITEMS
        is_size_item = selected_item in ["Conduit", "Boxes", "Wire", "Fittings", "Cable", "Solar"]
        show_colour = selected_type in COLOUR_LIST

        # Dynamically calculate precise column layout requirements
        active_widgets = 0
        if selected_item not in ["Wireway", "Lights", "DB", "DB parts"]:
            if is_size_item: active_widgets += 1
            if show_colour: active_widgets += 1
            if is_meter_item: active_widgets += 1
            if selected_item == "Fittings": active_widgets += 2
            if is_qty_item: active_widgets += 1  # Put Qty last in sizing count
        else:
            if selected_item == "DB":
                active_widgets = 4
            elif selected_item == "DB parts":
                part_spec_state = st.session_state.get("db_part_spec_select")
                # Length, size, amp, and overboard must bypass Qty render (2 columns)
                if part_spec_state in ["length", "size", "amp", "overboard"]:
                    active_widgets = 2  
                elif part_spec_state == "coil":
                    active_widgets = 3  # Spec dropdown + Volts dropdown + Qty block
                else:
                    active_widgets = 2  # Spec dropdown + Qty block
            else:
                active_widgets = 3  # Custom blocks (Wireway, Lights) are consistently structured with 3 columns

        cols = st.columns(active_widgets) if active_widgets > 0 else []
        current_col = 0

        # General Widget Group Rendering
        if selected_item not in ["Wireway", "Lights", "DB", "DB parts"]:
            if is_size_item:
                with cols[current_col]:
                    size_options = options_list if options_list else []
                    type_size = st.selectbox("Type Size", options=size_options, index=None, placeholder="Select size.", key=f"size_select_{selected_item}")
                current_col += 1

            if show_colour:
                with cols[current_col]:
                    spec_clrs = COLOUR_LIST.get(selected_type, {})
                    if is_size_item:
                        active_size = type_size if type_size is not None else (options_list[0] if options_list else "")
                        colours = spec_clrs.get(normalize_key(active_size), [])
                    else:
                        colours = COLOUR_LIST.get(selected_type, [])
                    
                    current_colour = st.selectbox("Colour", options=colours, index=None, placeholder="Select colour.", key=f"wire_colour_{selected_item}")
                current_col += 1

            if is_meter_item:
                with cols[current_col]:
                    raw_text = str(options_list[0]) if options_list else "0"
                    if raw_text not in ["0,00", "0.00"]:
                        # Meters step altered to 1 and value to 0 to remove decimal points
                        meters = st.number_input("Meters", min_value=0, step=1, value=0, key=f"meter_input_{selected_item}")
                current_col += 1

            if selected_item == "Fittings":
                with cols[current_col]:
                    module = st.selectbox("Module", options=MODULE_MAKE_LIST.get(type_size, {}).get("Modules", []), index=None, placeholder="Select module.", key=f"module_select_{selected_item}")
                current_col += 1

                with cols[current_col]:
                    make = st.selectbox("Make", options=MODULE_MAKE_LIST.get(type_size, {}).get("Make", []), index=None, placeholder="Select make.", key=f"make_select_{selected_item}")
                current_col += 1

            # Render Quantity at the very end of the group so it stays on the far right
            if is_qty_item:
                with cols[current_col]:
                    qty = st.number_input("Quantity", min_value=0, step=1, value=0, key=f"qty_select_{selected_item}")
                current_col += 1

        # Specialized Widget Blocks
        elif selected_item == "Wireway":
            with cols[current_col]:
                item_data = QTY_METER_LIST.get("Wireway", {})
                available_items = item_data.get(selected_type, [])
                item = st.selectbox("Item", options=available_items, index=None, placeholder="Select item.", key="wireway_item_select")
            current_col += 1

            with cols[current_col]:
                lookup_key = item.lower() if isinstance(item, str) else item
                available_size = ITEM_SIZE_LIST.get(lookup_key, [])
                item_size = st.selectbox("Item Size", options=available_size, index=None, placeholder="Select size.", key="wireway_size_select")
            current_col += 1

            with cols[current_col]:
                # Meters step altered to 1 and value to 0 to remove decimal points
                item_meter = st.number_input("Meters", min_value=0, step=1, value=0, key="wireway_meter_select")
            current_col += 1

        elif selected_item == "Lights":
            with cols[current_col]:
                place_data = QTY_METER_LIST.get("Lights", {})
                available_places = place_data.get(selected_type, [])
                where = st.selectbox("Light Placement", options=available_places, index=None, placeholder="Select Placement.", key="place_select")
            current_col += 1

            with cols[current_col]:
                watt = st.selectbox("Watt", options=list(range(1, 201)), index=None, placeholder="Select Wattage.", key="watt_select")
            current_col += 1

            # Render Light Size consistently in the 3rd column if wattage is selected
            if watt is not None:
                with cols[current_col]:
                    sizes = LIGHT_SIZE_LIST.get(where, []) if where is not None else []
                    size = st.selectbox("Light Size", options=sizes, index=None, placeholder='Select size.', key="light_size_select")
                current_col += 1

        elif selected_item == "DB":
            
            with cols[current_col]:
                sizes = QTY_METER_LIST.get("DB", {})
                size = st.selectbox("Size", options=list(sizes.keys()), index=None, placeholder="Select Size.", key="size_door_select")
            current_col += 1

            if size is not None:
                config = sizes.get(size, {})
                max_rows = config.get("max_rows", 10)

                with cols[current_col]:
                    rows_selection = st.selectbox("No. of rows", options=list(range(1, max_rows + 1)), index=None, placeholder="Select rows.", key="db_rows_select")
                current_col += 1

                max_ways = config.get("max_ways", 20)

                with cols[current_col]:
                    ways_selection = st.selectbox("No. ways per row", options=list(range(1, max_ways + 1)), index=None, placeholder="Select ways.", key="db_ways_select")
                current_col += 1

                with cols[current_col]:
                    qty = st.number_input("Quantity", min_value=0, step=1, value=0, key="db_qty_input")
                current_col += 1

        elif selected_item == "DB parts":
            with cols[current_col]:
                spec_options = options_list if options_list else []
                part_spec = st.selectbox("Part Specification", options=spec_options, index=None, placeholder="Select specification.", key="db_part_spec_select")
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

            # Render Quantity input only if selected part spec is NOT length, size, amp, or overboard
            if part_spec not in ["length", "size", "amp", "overboard"]:
                with cols[current_col]:
                    qty = st.number_input("Quantity", min_value=0, step=1, value=0, key="db_part_qty_input")
                current_col += 1

        # Comprehensive material dynamic label construction (decimals omitted)
        if selected_item == "Fittings":
            material_label = f"Fittings: {selected_type}"
            if type_size: material_label += f" (Size: {type_size})"
            if module: material_label += f" | Module: {module}"
            if make: material_label += f" | Make: {make}"
            if qty > 0: material_label += f" | Qty: {qty}"
        elif selected_item == "Wireway":
            material_label = f"Wireway: {selected_type}"
            if item: material_label += f" | Item: {item}"
            if item_size: material_label += f" | Size: {item_size}"
            if item_meter > 0: material_label += f" | {item_meter}m"
        elif selected_item == "Lights":
            material_label = f"Lights: {selected_type}"
            if where: material_label += f" | Placement: {where}"
            if size: material_label += f" | Size: {size}"
            if watt and watt > 0: material_label += f" | {watt}W"
        elif selected_item == "DB":
            material_label = f"DB: {selected_type}"
            if size: material_label += f" | Size: {size}"
            if rows_selection: material_label += f" | Rows: {rows_selection}"
            if ways_selection: material_label += f" | Ways/Row: {ways_selection}"
            if qty > 0: material_label += f" | Qty: {qty}"
        elif selected_item == "DB parts":
            material_label = f"DB parts: {selected_type}"
            if part_spec:
                material_label += f" | {part_spec}"
                if part_value:
                    # Append units cleanly depending on part spec
                    unit = ""
                    if part_spec in ["amp", "overboard"]:
                        unit = "A"
                    material_label += f" ({part_value}{unit})"
            if part_spec not in ["length", "size", "amp", "overboard"] and qty > 0:
                material_label += f" | Qty: {qty}"
        else:
            material_label = f"{selected_item}: {selected_type}"
            if type_size: 
                spec_label = "Specification" if selected_item == "DB parts" else "Size"
                material_label += f" ({spec_label}: {type_size})"
            if current_colour: material_label += f" | Color: {current_colour}"
            if is_meter_item and meters > 0: material_label += f" | {meters}m"
            if is_qty_item and qty > 0: material_label += f" | Qty: {qty}"

        if st.button("✅ Done", key="btn_add_material"):
            st.session_state.temp_materials.append(material_label)

    # Display added materials with "❌" delete action
    if st.session_state.temp_materials:
        st.write("**Added Materials:**")
        for idx, m in enumerate(st.session_state.temp_materials):
            mc1, mc2 = st.columns([0.9, 0.1])
            mc1.info(m)
            if mc2.button("❌", key=f"m_{idx}"):
                st.session_state.temp_materials.pop(idx)
                st.rerun()

st.markdown("---")

# --- POPULATE THE CONFERENCES AND HEADER RETROACTIVELY AT THE BOTTOM OF SCRIPT ---
with header_container:
    # Invisible CSS helper div inside the header block
    st.markdown("<div class='fixed-header'></div>", unsafe_allow_html=True)

    # Calculate global form completion items
    completed_items = []
    
    if site:
        completed_items.append(f"Site: {site}")
    if start_location:
        completed_items.append(f"Start Location: {start_location}")
    if start_time:
        completed_items.append(f"Start: {start_time.strftime('%H:%M')}")
    if end_time:
        completed_items.append(f"End: {end_time.strftime('%H:%M')}")
    if vehicle:
        completed_items.append(f"Vehicle: {vehicle}")
    if work_done:
        completed_items.append("Work Description")
    if st.session_state.temp_techs:
        completed_items.append(f"Technicians Assigned ({len(st.session_state.temp_techs)})")
    
    # Progress slot registers as selected as soon as any active material selection is made
    if st.session_state.temp_materials or selected_item:
        mats_desc = f"Materials ({len(st.session_state.temp_materials)})" if len(st.session_state.temp_materials) > 0 else f"Material Selected: {selected_item}"
        completed_items.append(mats_desc)

    # Master progress bar calculation
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

# Populate the dynamic scrollable material pill container retroactively at the bottom
with material_pill_container:
    # Build active material label using local, fully evaluated widget states
    live_material_label = ""
    
    if selected_item:
        live_material_label = f"{selected_item}"
        if selected_type:
            if selected_item == "Fittings":
                live_material_label = f"Fittings: {selected_type}"
                if type_size: live_material_label += f" (Size: {type_size})"
                if module: live_material_label += f" | Module: {module}"
                if make: live_material_label += f" | Make: {make}"
                if qty > 0: live_material_label += f" | Qty: {qty}"
            elif selected_item == "Wireway":
                live_material_label = f"Wireway: {selected_type}"
                if item: live_material_label += f" | Item: {item}"
                if item_size: live_material_label += f" | Size: {item_size}"
                if item_meter > 0: live_material_label += f" | {item_meter}m"
            elif selected_item == "Lights":
                live_material_label = f"Lights: {selected_type}"
                if where: live_material_label += f" | Placement: {where}"
                if size: live_material_label += f" | Size: {size}"
                if watt and watt > 0: live_material_label += f" | {watt}W"
            elif selected_item == "DB":
                live_material_label = f"DB: {selected_type}"
                if size: live_material_label += f" | Size: {size}"
                if rows_selection: live_material_label += f" | Rows: {rows_selection}"
                if ways_selection: live_material_label += f" | Ways/Row: {ways_selection}"
                if db_qty > 0: live_material_label += f" | Qty: {db_qty}"
            elif selected_item == "DB parts":
                live_material_label = f"DB parts: {selected_type}"
                if part_spec:
                    live_material_label += f" | {part_spec}"
                    if part_value:
                        unit = "A" if part_spec in ["amp", "overboard"] else ""
                        live_material_label += f" ({part_value}{unit})"
                if part_spec not in ["length", "size", "amp", "overboard"] and dbp_qty > 0:
                    live_material_label += f" | Qty: {dbp_qty}"
            else:
                live_material_label = f"{selected_item}: {selected_type}"
                if type_size: 
                    live_material_label += f" (Size: {type_size})"
                if current_colour: 
                    live_material_label += f" | Color: {current_colour}"
                # Standard meters for Conduit, Wire, Cable
                if selected_item in ["Conduit", "Wire", "Cable"]:
                    type_options_material = QTY_METER_LIST.get(selected_item, {})
                    options_list_material = type_options_material.get(selected_type, [])
                    raw_text_material = str(options_list_material[0]) if options_list_material else "0"
                    if raw_text_material not in ["0,00", "0.00"] and meters > 0:
                        live_material_label += f" | {meters}m"
                # Standard qty for Boxes, Fittings, Solar
                if selected_item in ["Boxes", "Fittings", "Solar"]:
                    if qty > 0:
                        live_material_label += f" | Qty: {qty}"

    # Only show the active selection info block if a material has actually been picked (completely hides empty block)
    if selected_item and live_material_label:
        st.info(f"🛠️ **Active Material Selection:** {live_material_label}")

# --- FINAL SAVE ACTION ---
# Custom confirmation dialog modal to prevent accidental submissions
@st.dialog("Confirm Save")
def confirm_save_modal():
    st.write("❓ Are you sure you would like to save this job card to the cloud?")
    
    # Display a concise, clean summary of what is being saved
    st.markdown(f"**Site:** {site if site else 'Not Selected'}")
    st.markdown(f"**Vehicle:** {vehicle if vehicle else 'Not Selected'}")
    st.markdown(f"**Work Description:** {work_done if work_done else 'Not Selected'}")
    st.markdown(f"**Technicians:** {', '.join(st.session_state.temp_techs)}")
    st.markdown(f"**Materials Added:** {len(st.session_state.temp_materials)} items")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Yes, Save", use_container_width=True, key="modal_confirm_yes"):
            with st.spinner("Saving to Cloud..."):
                try:
                    existing_data = conn.read(spreadsheet=SHEET_URL, ttl=0) [2]
                    
                    # Format the summaries
                    mat_summary = ", ".join(st.session_state.temp_materials)
                    tech_summary = ", ".join(st.session_state.temp_techs)
                    
                    new_entry = pd.DataFrame([{
                        "Type": job_type,
                        "Date": str(job_date),
                        "Start Time": start_time.strftime("%H:%M") if start_time else "",
                        "End Time": end_time.strftime("%H:%M") if end_time else "",
                        "Site": site,
                        "Work Done": work_done,
                        "Materials": mat_summary if mat_summary else "None",
                        "Technicians": tech_summary,
                        "Start Location": start_location if start_location else "None"
                    }])
                    
                    updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, data=updated_df)
                    
                    # Clear temporary lists
                    st.session_state.temp_materials = []
                    st.session_state.temp_techs = []
                    
                    st.success(f"✅ {job_type} successfully recorded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Cloud Connection Error: Failed to save to Google Sheets. ({str(e)})")
            
    with c2:
        if st.button("❌ No, Cancel", use_container_width=True, key="modal_confirm_no"):
            st.rerun()

# Save action triggers the confirmation modal
if st.button("🚀 SAVE FULL JOB CARD TO CLOUD"):
    if not work_done:
        st.error("Please enter a description.")
    elif not st.session_state.temp_techs:
        st.error("Please add at least one technician.")
    else:
        confirm_save_modal()

if st.checkbox("Show Recent History"):
    data = conn.read(spreadsheet=SHEET_URL, ttl=0)
    st.dataframe(data.tail(10))