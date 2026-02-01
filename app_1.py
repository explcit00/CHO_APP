import streamlit as st
import pandas as pd
import io
import re
import base64

# --- 1. REFERENCE DATA ---
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

# --- 2. CLEANING LOGIC ---
def process_strict_address(row):
    addr_val = str(row.get('ADDRESS', '')).upper().strip()
    spec_val = str(row.get('SPECIFIC ADDRESS', '')).upper().strip()
    full_text = f"{addr_val} {spec_val}".strip()
    if full_text in ["NAN", "NONE", ""]: return "MISSING"
    
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
    return found_brgy if found_brgy else ("TRANSIENT" if "TRANSIENT" not in full_text else "TRANSIENT")

# --- 3. SUMMARY ENGINE (Calculates values from Raw Data) ---
def generate_health_summary(df, group_by_col='ADDRESS'):
    summary_list = []
    if group_by_col not in df.columns: return pd.DataFrame()

    # Filter out empty/missing groups
    groups = [g for g in df[group_by_col].unique() if str(g) not in ["MISSING", "nan", "None", ""]]
    
    # Chronological sort for months
    if group_by_col == 'MONTH':
        months_order = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 
                        'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
        groups = sorted(groups, key=lambda x: months_order.index(str(x).upper()) if str(x).upper() in months_order else 99)
    else:
        groups = sorted(groups)

    for group in groups:
        subset = df[df[group_by_col] == group]
        total = len(subset)
        if total == 0: continue

        # Calculations based on strings in your Raw Data
        m = len(subset[subset['GENDER'].astype(str).str.startswith('M', na=False)])
        f = len(subset[subset['GENDER'].astype(str).str.startswith('F', na=False)])
        
        gt = len(subset[subset['WGT. IN GRAMS'].astype(str).str.contains('GREATER|2500', case=False, na=False)])
        lt = len(subset[subset['WGT. IN GRAMS'].astype(str).str.contains('LESSER|2500', case=False, na=False)])
        
        # Place of Delivery Logic
        hosp = len(subset[subset['PLACE_OF_DELIVERY'].astype(str).str.contains('HOSP', case=False, na=False)])
        hc = len(subset[subset['PLACE_OF_DELIVERY'].astype(str).str.contains('HC|HEALTH CENTER', case=False, na=False)])
        lying = len(subset[subset['PLACE_OF_DELIVERY'].astype(str).str.contains('LYING', case=False, na=False)])
        fac_total = hosp + hc + lying
        
        # Attendant Logic
        md = len(subset[subset['ATTENDANT'].astype(str).str.contains('MD|PHYSICIAN', case=False, na=False)])
        mw = len(subset[subset['ATTENDANT'].astype(str).str.contains('MIDWIFE|RHM|PHN', case=False, na=False)])
        skilled = md + mw
        
        # Age Logic
        ages = pd.to_numeric(subset['AGE'], errors='coerce')
        a1 = len(subset[(ages >= 10) & (ages <= 14)])
        a2 = len(subset[(ages >= 15) & (ages <= 19)])
        a3 = len(subset[(ages >= 20) & (ages <= 24)])
        a4 = len(subset[ages >= 25])
        
        # Provider Logic
        gov = len(subset[subset['GOV/PRI'].astype(str).str.contains('GOV', case=False, na=False)])
        pri = total - gov

        summary_list.append([
            group, m, f, total, gt, lt, total,
            hosp, hc, lying, fac_total, (total - fac_total), total, (fac_total/total if total > 0 else 0),
            md, mw, skilled, (total - skilled), total, (skilled/total if total > 0 else 0),
            a1, a2, a3, a4, total, ((a1+a2)/total if total > 0 else 0),
            gov, pri, total
        ])

    label = "Month" if group_by_col == 'MONTH' else "Barangay"
    cols = [
        label, 'Male', 'Female', 'Total Count', '>2500g', '<2500g', 'Total W',
        'Hospital', 'Health Center', 'Lying-In', 'Total Facility', 'Home/Other', 'Total P', '% FBD',
        'MD/Physician', 'Midwife/Nurse', 'Total Skilled', 'Non-Skilled', 'Total A', '% SBA',
        '10-14Y', '15-19Y', '20-24Y', '25+Y', 'Total Age', '% Teenage', 'Govt', 'Private', 'Total G'
    ]
    return pd.DataFrame(summary_list, columns=cols)

# --- 4. UI AND AUTO-MERGE ---
st.set_page_config(page_title="CHO Records Standardizer", layout="wide")

def get_base64(path):
    try:
        with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return ""

# PNG Background Logic
bg_img = get_base64("CITY-HEALTH-OFFICE-DOCTORS.png")
logo_img = get_base64("images.png")

st.markdown(f"""
    <style>
    /* 1. Background image for the app - Updated for movement/zoom */
    [data-testid="stApp"] {{
        background-image: url("data:image/jpeg;base64,{bg_img}");
        
        /* 'cover' ensures the image stretches to fill the space without gaps */
        background-size: cover;
        
        /* 'center' ensures the zoom originates from the middle of the image */
        background-position: center center;
        
        /* 'fixed' keeps the image in place while content scrolls over it */
        background-attachment: fixed;
        
        background-repeat: no-repeat;
    }}

    /* Hide default Streamlit header */
    [data-testid="stHeader"] {{
        visibility: hidden;
    }}

    /* 2. Main container (Centered) */
    [data-testid="stAppViewBlockContainer"] {{
        width: 95%; /* Ensures it doesn't hit screen edges when zoomed */
        max-width: 850px;
        margin-left: auto;
        margin-right: auto;
        padding-top: 12rem;
        padding-bottom: 5rem;
        
        /* Box background */
        background-color: rgba(255, 255, 255, 0.9); 
        padding-left: 40px;
        padding-right: 40px;
        border-radius: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        margin-top: 50px;
        margin-bottom: 50px;
        
        color: black !important;
    }}

    /* Target all headers, labels, and standard text to be BLACK */
    h1, h2, h3, p, label, .stMarkdown, [data-testid="stMarkdownContainer"] p {{
        color: black !important;
    }}

    /* 3. Top corner header styling */
    .top-header {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 70px;
        background-color: white;
        display: flex;
        align-items: center;
        padding: 0 40px;
        border-bottom: 3px solid #87b97b;
        z-index: 9999;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }}

    .logo-img {{
        height: 45px;
        margin-right: 20px;
    }}

    .header-label {{
        font-weight: bold;
        color: black !important;
        font-family: 'Segoe UI', sans-serif;
        font-size: 1.2rem;
    }}

    .main-title {{ 
        font-size: 28px; 
        font-weight: bold; 
        color: black !important; 
        text-align: center; 
        margin-bottom: 30px; 
    }}
    
    .stFileUploader {{
        text-align: center;
        color: black !important;
    }}

    [data-testid="stFileUploadDropzone"] div {{
        color: black !important;
    }}

    /* Table styling */
    th {{
        background-color: #1E3A8A !important;
        color: white !important; 
        font-weight: bold !important;
        text-align: center !important;
    }}
    
    td {{
        color: black !important;
    }}
    
    /* Button styling */
    .stButton>button {{ 
        background-color: #1E3A8A; 
        color: white !important; 
        border-radius: 10px; 
        font-weight: bold; 
    }}
    
    /* Optional: Add a hover effect so it reacts when touched */
    .stButton>button:hover {{
        background-color: #1E3A8A;
        color: white !important;
        border-radius: 10px; 
        font-weight: bold;
    }}
    
    </style>

    <div class="top-header">
        <img src="data:image/png;base64,{logo_img}" class="logo-img">
        <div class="header-label">City Health Office | Records Standardizer</div>
    </div>
""", unsafe_allow_html=True)

st.write("Upload your **Raw Data** files. The app will automatically merge and calculate summaries!")
files = st.file_uploader("Upload Excel/CSV Files:", accept_multiple_files=True)

if files:
    try:
        combined_list = []
        for file in files:
            if file.name.endswith('.csv'):
                data = pd.read_csv(file)
            else:
                data = pd.read_excel(file)
            
            # Auto-Clean Column Names
            data.columns = [str(c).upper().strip() for c in data.columns]
            
            # Flexible Mapping to match your Raw Data file
            mapping = {
                'PLACE OF DELIVERY': 'PLACE_OF_DELIVERY',
                'DATE OF BIRTH': 'DATE',
                'MOTHER\'S NAME': 'MOTHER_NAME',
                'WGT. IN GRAMS': 'WGT. IN GRAMS'
            }
            data = data.rename(columns=mapping)
            combined_list.append(data)

        # AUTO-MERGE
        full_raw = pd.concat(combined_list, ignore_index=True, sort=False)
        
        # Clean Address and PII
        if 'ADDRESS' in full_raw.columns:
            full_raw['ADDRESS'] = full_raw.apply(process_strict_address, axis=1)
        
        pii = ["NAME", "MOTHER_NAME", "SPECIFIC ADDRESS"]
        full_raw_clean = full_raw.drop(columns=[c for c in pii if c in full_raw.columns])

        # GENERATE SUMMARIES
        df_monthly = generate_health_summary(full_raw_clean, group_by_col='MONTH')
        df_annual = generate_health_summary(full_raw_clean, group_by_col='ADDRESS')

        st.success(f"Merged {len(combined_list)} files. Summaries Generated.")
        st.dataframe(df_monthly, use_container_width=True)

        # EXCEL EXPORT
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_monthly.to_excel(writer, sheet_name='Summary per Month', index=False)
            df_annual.to_excel(writer, sheet_name='Annual Summary', index=False)
            full_raw_clean.to_excel(writer, sheet_name='Merged Raw Data', index=False)
            
            # Formatting
            workbook = writer.book
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            for sheetname in writer.sheets:
                sheet = writer.sheets[sheetname]
                sheet.set_column('A:Z', 18)
                # Apply header format manually for row 0
                cols = df_monthly.columns if sheetname == 'Summary per Month' else (df_annual.columns if sheetname == 'Annual Summary' else full_raw_clean.columns)
                for col_num, value in enumerate(cols):
                    sheet.write(0, col_num, value, header_fmt)

        st.download_button(
            label="Download Consolidated Reports",
            data=output.getvalue(),
            file_name="CHO_Consolidated_Health_Records.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Processing Error: {str(e)}")