import streamlit as st
import pandas as pd
import io
import re
import base64

# --- Barangay Reference Lists and Mapping
CDO_BARANGAYS = [
    "AGUSAN", "BAIKINGON", "BALUBAL", "BALULANG", "BAYABAS", "BAYANGA", "BESIGAN", 
    "BONBON", "BUGO", "BUHUAWEN", "BULUA", "CAMAMAN-AN", "CANITOAN", "CARMEN", 
    "CONSOLACION", "CUGMAN", "DANSOLIHON", "F.S. CATANICO", "GUSA", "INDAHAG", 
    "IPONAN", "KAUSWAGAN", "LAPASAN", "LUMBAMBIA", "LUMBIA", "MACABALAN", 
    "MACASANDIG", "MAGSAYSAY", "MAMBUAYA", "NAZARETH", "PAGALUNGAN", "PAGATPAT", 
    "PATAG", "PIGSAG-AN", "PUERTO", "PUNTOD", "SAN SIMON", "TABLON", "TAGLIMAO", 
    "TAGPANGI", "TIGNAPOLOAN", "TUBURAN", "TUMPAGON"
]
for i in range(1, 41):
    CDO_BARANGAYS.append(f"BARANGAY {i}")

SUB_BRGY_MAP = {
    "CALAANAN": "CANITOAN", "PASIL": "KAUSWAGAN", "AGORA": "LAPASAN",
    "MACANHAN": "CARMEN", "ORO HABITAT": "CANITOAN"
}

# --- Address Standardization Function
def process_strict_address(row):
    addr_val = str(row.get('ADDRESS', '')).upper().strip()
    spec_val = str(row.get('SPECIFIC ADDRESS', '')).upper().strip()
    if addr_val in ["NAN", "NONE"]: addr_val = ""
    if spec_val in ["NAN", "NONE"]: spec_val = ""
    full_text = f"{addr_val} {spec_val}".strip()
    found_brgy = None
    for sitio, parent_brgy in SUB_BRGY_MAP.items():
        if re.search(r'\b' + re.escape(sitio) + r'\b', full_text):
            found_brgy = parent_brgy
            break
    if not found_brgy:
        for brgy in CDO_BARANGAYS:
            if re.search(r'\b' + re.escape(brgy) + r'\b', full_text):
                found_brgy = brgy
                break
    return found_brgy if found_brgy else ("TRANSIENT" if full_text != "" else "MISSING")

# --- Streamlit Page Configuration
st.set_page_config(page_title="CHO Records Standardizer", layout="wide")

def get_image_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError: return ""

bg_img_b64 = get_image_base64("CITY-HEALTH-OFFICE-DOCTORS.png")
img_b64 = get_image_base64("images.png")

# --- Custom CSS Styling
st.markdown(f"""
    <style>
    [data-testid="stApp"] {{
        background-image: url("data:image/jpeg;base64,{bg_img_b64}");
        background-size: cover; background-position: center; background-attachment: fixed;
    }}
    [data-testid="stHeader"] {{ visibility: hidden; }}
    [data-testid="stAppViewBlockContainer"] {{
        max-width: 900px; margin: auto; padding-top: 10rem;
        background-color: rgba(255, 255, 255, 0.9); 
        border-radius: 20px; padding: 40px; color: black !important;
    }}
    .top-header {{
        position: fixed; top: 0; left: 0; width: 100%; height: 70px;
        background-color: white; display: flex; align-items: center;
        padding: 0 40px; border-bottom: 3px solid #87b97b; z-index: 9999;
    }}
    .logo-img {{ height: 45px; margin-right: 20px; }}
    .header-label {{ font-weight: bold; color: black; font-size: 1.2rem; }}
    
    /* Side-by-Side White Buttons Styling */
    .stButton>button, .stDownloadButton>button {{ 
        background-color: white !important; 
        color: #000000 !important; 
        border: 0px solid #87b97b !important; 
        border-radius: 10px; font-weight: bold; height: 3.5rem; transition: 0.3s;
    }}
    .stButton>button:hover, .stDownloadButton>button:hover {{
        background-color: #FFFFFF !important; color: white !important; font-weight: bold;
    }}
    th {{ background-color: #FFFFFF !important; color: white !important; font-weight: bold; }}
    </style>
    <div class="top-header">
        <img src="data:image/png;base64,{img_b64}" class="logo-img">
        <div class="header-label">City Health Office | Records Standardizer</div>
    </div>
""", unsafe_allow_html=True)

# --- Summary Report Logic
def generate_summary(df):
    facility_keywords = ['HOSP', 'HSOP', 'LYING-IN', 'CHO', 'HEALTH CENTER', 'HC']
    skilled_keywords = ['MD', 'MIDWIFE', 'NURSE', 'RHM', 'PHN', 'PHYSICIAN']
    govt_keywords = ['GOVERNMENT', 'GOVERNEMNT', 'GOV']
    
    summary_list = []
    # Use official column headers
    brgys = sorted([b for b in df['ADDRESS'].unique() if b not in ["UNKNOWN", "MISSING"]])

    for brgy in brgys:
        subset = df[df['ADDRESS'] == brgy]
        total = len(subset)
        if total == 0: continue

        m = len(subset[subset['GENDER'] == 'M'])
        f = len(subset[subset['GENDER'] == 'F'])
        gt = len(subset[subset['WGT. IN GRAMS'].astype(str).str.contains('GREATER|2500|>', na=False)])
        lt = len(subset[subset['WGT. IN GRAMS'].astype(str).str.contains('LESSER|<', na=False)])
        is_fac = subset['PLACE OF DELIVERY'].apply(lambda x: any(k in str(x).upper() for k in facility_keywords))
        fac_count = len(subset[is_fac])
        is_skilled = subset['ATTENDANT'].apply(lambda x: any(k in str(x).upper() for k in skilled_keywords))
        skilled_count = len(subset[is_skilled])
        
        age_col = pd.to_numeric(subset['AGE'], errors='coerce')
        a1 = len(subset[(age_col >= 10) & (age_col <= 14)])
        a2 = len(subset[(age_col >= 15) & (age_col <= 19)])
        a3 = len(subset[(age_col >= 20) & (age_col <= 24)])
        a4 = len(subset[age_col >= 25])
        
        is_gov = subset['GOV/PRI'].apply(lambda x: any(k in str(x).upper() for k in govt_keywords))
        gov_count = len(subset[is_gov])

        summary_list.append([
            brgy, m, f, total, gt, lt, total,
            fac_count, total-fac_count, total, (fac_count/total if total > 0 else 0),
            skilled_count, total-skilled_count, total, (skilled_count/total if total > 0 else 0),
            a1, a2, a3, a4, total, ((a1+a2)/total if total > 0 else 0),
            gov_count, total-gov_count, total
        ])

    cols = [
        'Name of Brgy', 'Male', 'Female', 'Grand Total', '>2500g', '<2500g', 'Total (W)',
        'FACILITY', 'NON-FACILITY', 'Total (P)', '% FBD', 'Skilled', 'Non-Skilled', 'Total (A)', '% SBA',
        '10-14Y', '15-19Y', '20-24Y', '25+Y', 'Total (Age)', '% Teenage', 'Govt', 'Pri', 'Total (G)'
    ]
    return pd.DataFrame(summary_list, columns=cols)

# --- Main App Execution
uploaded_file = st.file_uploader("Please Upload raw file!", type=["csv", "xlsx"])

if uploaded_file:
    try:
        # Load Data
        df = pd.read_csv(uploaded_file, encoding='latin1') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        
        # Clean Headers
        df.columns = [re.sub(' +', ' ', str(c).strip().upper()) for c in df.columns]

        # 1. DROP UNNAMED, NAME, AND MOTHER'S NAME
        pii_cols = ["NAME", "MOTHER'S NAME", "SPECIFIC ADDRESS"]
        unnamed_cols = [col for col in df.columns if "UNNAMED" in col]
        df = df.drop(columns=[c for c in (pii_cols + unnamed_cols) if c in df.columns])

        # 2. STANDARD CLEANING
        if 'ADDRESS' in df.columns:
            df['ADDRESS'] = df.apply(process_strict_address, axis=1)

        if 'ATTENDANT' in df.columns:
            df['ATTENDANT'] = df['ATTENDANT'].astype(str).str.upper().replace({'MIDWIFE': 'RHM', 'PHYSICIAN': 'MD'})

        # UI Success and Preview
        st.success("Standards Applied: Names removed, Unnamed columns cleared, and Addresses mapped.")
        st.dataframe(df.head(10), use_container_width=True)

        # --- EXPORT PREPARATION ---
        # Masterlist
        buffer_master = io.BytesIO()
        with pd.ExcelWriter(buffer_master, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        
        # Summary Report
        df_summary = generate_summary(df)
        buffer_summary = io.BytesIO()
        with pd.ExcelWriter(buffer_summary, engine='xlsxwriter') as writer:
            df_summary.to_excel(writer, index=False)

        # --- SIDE-BY-SIDE WHITE BUTTONS ---
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="DOWNLOAD CLEANED DATA",
                data=buffer_master.getvalue(),
                file_name="OFFICIAL_CHO_BIRTH_RECORDS.xlsx",
                use_container_width=True
            )
        with col2:
            st.download_button(
                label="DOWNLOAD ANNUAL SUMMARY REPORT",
                data=buffer_summary.getvalue(),
                file_name="Annual_Summary_Report.xlsx",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Error processing file: {e}")