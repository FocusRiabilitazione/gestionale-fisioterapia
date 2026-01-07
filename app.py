import streamlit as st
import streamlit.components.v1 as components
from pyairtable import Api
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
import io
import os
import base64

# =========================================================
# 0. CONFIGURAZIONE & STILE
# =========================================================
[cite_start]st.set_page_config(page_title="Gestionale Fisio Pro", page_icon="🏥", layout="wide") [cite: 1]

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at top left, #1a202c, #0d1117);
        color: #e2e8f0;
    [cite_start]} [cite: 2]

    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(20px);
    [cite_start]} [cite: 3]

    h1 {
        font-family: 'Outfit', sans-serif;
        font-weight: 800 !important;
        background: linear-gradient(120deg, #ffffff, #a0aec0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
        margin-bottom: 10px;
    [cite_start]} [cite: 4, 5]
    h2, h3, h4 {
        font-family: 'Outfit', sans-serif;
        font-weight: 600 !important;
        color: #f7fafc !important;
        letter-spacing: 0.5px;
    [cite_start]} [cite: 6]

    /* KPI CARDS */
    .glass-kpi {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        height: 140px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        margin-bottom: 10px;
        transition: transform 0.3s ease, border-color 0.3s ease;
    [cite_start]} [cite: 7, 8, 9]
    .glass-kpi:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.06);
    [cite_start]} [cite: 10]
    
    .kpi-icon { 
        font-size: 32px;
        margin-bottom: 8px; 
        transition: transform 0.3s ease;
        filter: drop-shadow(0 0 5px rgba(255,255,255,0.3));
    [cite_start]} [cite: 11]
    .glass-kpi:hover .kpi-icon { transform: scale(1.1); [cite_start]} [cite: 12]

    .kpi-value { font-size: 36px; font-weight: 800; color: white; line-height: 1; letter-spacing: -1px; [cite_start]} [cite: 13]
    .kpi-label { font-size: 11px; text-transform: uppercase; color: #a0aec0; margin-top: 8px; letter-spacing: 1.5px; font-weight: 600; [cite_start]} [cite: 14]

    /* PULSANTI */
    div[data-testid="column"] .stButton > button {
        background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 12px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 6px 0 !important;
        box-shadow: 0 4px 10px rgba(66, 153, 225, 0.3) !important;
        transition: all 0.3s ease;
        margin-top: 0px !important;
    [cite_start]} [cite: 15, 16, 17]
    div[data-testid="column"] .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(66, 153, 225, 0.5) !important;
    [cite_start]} [cite: 18]

    /* RIGHE AVVISI */
    .alert-row-name {
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 10px;
        padding: 0 15px;
        height: 42px;    
        display: flex; align-items: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
        font-weight: 600;
        color: #fff; font-size: 14px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    [cite_start]} [cite: 19, 20, 21]

    .border-orange { border-left: 4px solid #ed8936 !important; [cite_start]} [cite: 22]
    .border-red { border-left: 4px solid #e53e3e !important; [cite_start]} [cite: 23]
    .border-blue { border-left: 4px solid #0bc5ea !important; [cite_start]} [cite: 24]
    .border-purple { border-left: 4px solid #9f7aea !important; [cite_start]} [cite: 25]
    .border-yellow { border-left: 4px solid #ecc94b !important; [cite_start]} [cite: 26]
    .border-green { border-left: 4px solid #2ecc71 !important; [cite_start]} [cite: 27]
    .border-gray { border-left: 4px solid #a0aec0 !important; [cite_start]} [cite: 28]

    /* PULSANTI AZIONE */
    div[data-testid="stHorizontalBlock"] button {
        padding: 2px 12px !important;
        font-size: 11px !important; min-height: 0px !important;
        height: 32px !important; line-height: 1 !important; border-radius: 8px !important;
        margin-top: 6px !important;
        font-weight: 500 !important;
    [cite_start]} [cite: 29, 30]
    button[kind="primary"] { background: linear-gradient(135deg, #3182ce, #2b6cb0) !important; border: none !important; color: white !important; [cite_start]} [cite: 31]
    button[kind="secondary"] { background: rgba(255, 255, 255, 0.08) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; color: #cbd5e0 !important; [cite_start]} [cite: 32]
    button[kind="secondary"]:hover { border-color: #a0aec0 !important; color: white !important; [cite_start]} [cite: 33]

    div[data-testid="stDataFrame"] { background: transparent; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; [cite_start]} [cite: 34]
    input, select, textarea { background-color: rgba(13, 17, 23, 0.8) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; color: white !important; border-radius: 8px; [cite_start]} [cite: 35, 36]

    div[data-testid="stVerticalBlockBorderWrapper"] { padding: 10px !important; margin-bottom: 5px !important; background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); [cite_start]} [cite: 37, 38]
    div[data-testid="stProgress"] > div > div { height: 6px !important; [cite_start]} [cite: 39]
    .compact-text { font-size: 13px; color: #cbd5e0; margin: 0; [cite_start]} [cite: 40]
</style>
""", unsafe_allow_html=True)

# --- 1. CONNESSIONE ---
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except:
    API_KEY = "key"
    BASE_ID = "id"

api = Api(API_KEY)

# --- 2. FUNZIONI ---
@st.cache_data(ttl=60)
def get_data(table_name):
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records: return pd.DataFrame()
        data = [{'id': r['id'], **r['fields']} for r in records]
        return pd.DataFrame(data)
    [cite_start]except: return pd.DataFrame() [cite: 41]

def save_paziente(n, c, a, d):
    try: api.table(BASE_ID, "Pazienti").create({"Nome": n, "Cognome": c, "Area": a, "Disdetto": d}, typecast=True); get_data.clear(); return True
    except: return False

def update_generic(tbl, rid, data):
    try:
        clean_data = {}
        for k, v in data.items():
            if v is None: clean_data[k] = None
            elif hasattr(v, 'strftime'): clean_data[k] = v.strftime('%Y-%m-%d')
            [cite_start]else: clean_data[k] = v [cite: 42]
        api.table(BASE_ID, tbl).update(rid, clean_data, typecast=True)
        get_data.clear()
        return True
    except: return False

def delete_generic(tbl, rid):
    [cite_start]try: api.table(BASE_ID, tbl).delete(rid); get_data.clear(); return True [cite: 43]
    except: return False

def save_preventivo_temp(paziente, dettagli_str, totale, note):
    [cite_start]try: api.table(BASE_ID, "Preventivi_Salvati").create({"Paziente": paziente, "Dettagli": dettagli_str, "Totale": totale, "Note": note, "Data_Creazione": str(date.today())}, typecast=True); get_data.clear(); return True [cite: 44]
    except: return False

def save_materiale_avanzato(materiale, area, quantita, obiettivo, soglia):
    try: 
        api.table(BASE_ID, "Inventario").create({
            "Materiali": materiale, 
            "Area": area,
            "Quantità": int(quantita),
            "Obiettivo": int(obiettivo),
            "Soglia_Minima": int(soglia)
        [cite_start]}, typecast=True) [cite: 45]
        get_data.clear()
        return True
    [cite_start]except Exception as e: st.error(f"Errore Salvataggio: {e}"); return False [cite: 46]

def save_consegna(paziente, area, indicazione, scadenza):
    try:
        api.table(BASE_ID, "Consegne").create({
            "Paziente": paziente, "Area": area, "Indicazione": indicazione, 
            "Data_Scadenza": str(scadenza), "Completato": False
        }, typecast=True)
        [cite_start]get_data.clear(); return True [cite: 47]
    except: return False

# NUOVA FUNZIONE PER I PRESTITI AVANZATI
def save_prestito_new(paziente, oggetto, categoria, data_prestito, data_scadenza):
    try: 
        api.table(BASE_ID, "Prestiti").create({
            "Paziente": paziente, 
            "Oggetto": oggetto,
            "Categoria": categoria, 
            "Data_Prestito": str(data_prestito), 
            "Data_Scadenza": str(data_scadenza),
            "Restituito": False
        }, typecast=True); 
        get_data.clear(); 
        return True
    except: return False

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
    except: return ""

# --- PDF GENERATOR ---
def generate_html_preventivo(paziente, data_oggi, note, righe_preventivo, totale_complessivo, logo_b64=None, auto_print=False):
    rows_html = ""
    for r in righe_preventivo:
        rows_html += f"<tr><td>{r['nome']}</td><td class='col-qty'>{r['qty']}</td><td class='col-price'>{r['tot']} €</td></tr>"
    
    header_content = f"<div style='text-align:center;'><img src='data:image/png;base64,{logo_b64}' class='logo-img'></div>" if logo_b64 else "<div class='brand-text-container'><div class='doc-brand-main'>FOCUS</div></div>"
    print_script = "<script>window.print();</script>" if auto_print else ""
    [cite_start]action_bar_style = "display:none;" if auto_print else "display:flex;" [cite: 49]
    return f"""
    <!DOCTYPE html> <html lang="it"> <head> <meta charset="UTF-8"> <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    body {{ font-family: 'Segoe UI', sans-serif; background: #fff; margin: 0; padding: 20px; color: #000; }}
    .action-bar {{ margin-bottom: 20px; justify-content: flex-end; {action_bar_style} }}
    .btn-download {{ background-color: #333; color: white; border: none; padding: 10px 20px; font-weight: bold; border-radius: 4px; cursor: pointer; }}
    .sheet-a4 {{ width: 210mm; min-height: 296mm; padding: 10mm 15mm; margin: 0 auto; background: white; box-sizing: border-box; position: relative; box-shadow: 0 0 10px rgba(0,0,0,0.1); overflow: hidden; }}
    [cite_start].logo-img {{ max-width: 150px; height: auto; display: block; margin: 0 auto 5px auto; }} [cite: 51]
    .doc-brand-main {{ font-size: 26px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; color: #000; text-align: center; }}
    .doc-title {{ font-size: 18px; font-weight: 700; text-transform: uppercase; color: #000; border-bottom: 2px solid #000; padding-bottom: 5px; margin-bottom: 15px; margin-top: 10px; [cite_start]}} [cite: 52, 53]
    .info-box {{ margin-bottom: 15px; font-size: 13px; display: flex; justify-content: space-between; [cite_start]}} [cite: 54]
    .info-label {{ font-weight: bold; color: #000; margin-right: 5px; [cite_start]}} [cite: 55]
    .obj-box {{ background-color: #f2f2f2; border-left: 4px solid #333; padding: 10px; margin-bottom: 20px; font-size: 12px; line-height: 1.5; white-space: pre-wrap; [cite_start]}} [cite: 56, 57]
    .obj-title {{ font-weight: bold; text-transform: uppercase; display: block; margin-bottom: 3px; font-size: 11px; [cite_start]}} [cite: 58]
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
    th {{ background-color: #e0e0e0; text-align: left; padding: 6px 8px; text-transform: uppercase; font-size: 10px; font-weight: bold; border-bottom: 1px solid #000; color: #000; [cite_start]}} [cite: 59, 60]
    td {{ padding: 6px 8px; border-bottom: 1px solid #ccc; font-size: 12px; vertical-align: middle; [cite_start]}} [cite: 61]
    .col-qty {{ text-align: center; width: 10%; }} .col-price {{ text-align: right; width: 20%; [cite_start]}} [cite: 62]
    .total-row td {{ font-weight: bold; font-size: 14px; border-top: 2px solid #000; padding-top: 8px; color: #000; [cite_start]}} [cite: 63]
    .payment-section {{ border: 1px solid #999; padding: 10px; border-radius: 0; margin-bottom: 20px; [cite_start]}} [cite: 64]
    .pay-title {{ font-weight: bold; text-transform: uppercase; font-size: 11px; margin-bottom: 8px; color: #000; [cite_start]}} [cite: 65]
    .pay-line {{ display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 12px; [cite_start]}} [cite: 66]
    .dotted {{ border-bottom: 1px dotted #000; width: 80px; display: inline-block; }} .dotted-date {{ border-bottom: 1px dotted #000; width: 120px; display: inline-block; [cite_start]}} [cite: 67]
    .footer {{ margin-top: 40px; display: flex; justify-content: flex-end; [cite_start]}} [cite: 68]
    .sign-box {{ text-align: center; width: 200px; }} .sign-line {{ border-bottom: 1px solid #000; margin-top: 30px; [cite_start]}} [cite: 69]
    .page-num {{ position: absolute; bottom: 10mm; left: 15mm; font-size: 9px; color: #666; [cite_start]}} [cite: 70]
    @media print {{ @page {{ size: A4; margin: 0; }} body {{ margin: 0; padding: 0; background: none; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }} .action-bar {{ display: none !important; }} .sheet-a4 {{ margin: 0; box-shadow: none; border: none; width: 100%; height: 100%; page-break-after: avoid; page-break-inside: avoid; [cite_start]}} }} [cite: 71, 72, 73]
    </style> </head> <body>
    <div class="action-bar"><button class="btn-download" onclick="window.print()">📥 SALVA PDF</button></div>
    <div class="sheet-a4"> {header_content}
    <div class="doc-title">PREVENTIVO PERCORSO RIABILITATIVO</div>
    <div class="info-box"><div><span class="info-label">Paziente:</span> {paziente}</div><div><span class="info-label">Data:</span> {data_oggi}</div></div>
    <div class="obj-box"><span class="obj-title">Obiettivi e Descrizione del Percorso:</span>{note}</div>
    <table><thead><tr><th>Trattamento</th><th class="col-qty">Q.ta</th><th class="col-price">Importo</th></tr></thead><tbody>{rows_html}<tr class="total-row"><td colspan="2" style="text-align:right">TOTALE COMPLESSIVO:</td><td class="col-price">{totale_complessivo} €</td></tr></tbody></table>
    <div class="payment-section"><div class="pay-title">Piano di Pagamento Concordato:</div><div class="pay-line"><span>1) € <span class="dotted"></span></span> <span>entro il <span class="dotted-date"></span></span></div><div class="pay-line"><span>2) € <span class="dotted"></span></span> <span>entro il <span class="dotted-date"></span></span></div><div class="pay-line"><span>3) € <span class="dotted"></span></span> <span>entro il <span class="dotted-date"></span></span></div></div>
    <div class="footer"><div class="sign-box"><div>Firma per accettazione:</div><div class="sign-line"></div></div></div>
    <div class="page-num">Pagina 1</div> </div> {print_script} </body> </html>
    [cite_start]""" [cite: 74]

# --- 3. INTERFACCIA ---
with st.sidebar:
    LOGO_B64 = ""
    try: 
        st.image("logo.png", use_container_width=True)
        LOGO_B64 = get_base64_image("logo.png")
    except: 
        st.title("Focus Rehab")
        
    menu = st.radio("Menu", ["⚡ Dashboard", "👥 Pazienti", "💳 Preventivi", "📨 Consegne", "📦 Magazzino", "🔄 Prestiti", "📅 Scadenze"], label_visibility="collapsed")
    [cite_start]st.divider(); st.caption("App v101 - Segreteria & Noleggi") [cite: 75]

# =========================================================
# DASHBOARD
# =========================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")
    st.write("")
    
    # --- ALERT PRESTITI SCADUTI (CORRETTO PER EVITARE TypeError) ---
    df_pres_alert = get_data("Prestiti")
    if not df_pres_alert.empty:
        # Pulisci e normalizza dati
        if 'Restituito' not in df_pres_alert.columns: df_pres_alert['Restituito'] = False
        if 'Data_Scadenza' not in df_pres_alert.columns: df_pres_alert['Data_Scadenza'] = None
        if 'Oggetto' not in df_pres_alert.columns: df_pres_alert['Oggetto'] = "Strumento"
        if 'Paziente' not in df_pres_alert.columns: df_pres_alert['Paziente'] = "Sconosciuto"
        
        # FIX: Conversione sicura in datetime Pandas
        df_pres_alert['Data_Scadenza'] = pd.to_datetime(df_pres_alert['Data_Scadenza'], errors='coerce')
        
        # Filtro: Non restituiti E Scaduti (data < oggi normalizzata)
        oggi_ts = pd.Timestamp.now().normalize()
        scaduti = df_pres_alert[
            (df_pres_alert['Restituito'] != True) & 
            (df_pres_alert['Data_Scadenza'] < oggi_ts) &
            (df_pres_alert['Data_Scadenza'].notna())
        ]
        
        if not scaduti.empty:
            st.error(f"⚠️ ATTENZIONE: Ci sono {len(scaduti)} strumenti NON restituiti in tempo!")
            for i, row in scaduti.iterrows():
                # Formattiamo la data solo per visualizzazione
                data_str = row['Data_Scadenza'].strftime('%d/%m') if pd.notnull(row['Data_Scadenza']) else "N.D."
                st.markdown(f"🔴 **{row['Oggetto']}** - {row['Paziente']} (Scaduto il {data_str})")
            st.divider()
    # ------------------------------

    if 'kpi_filter' not in st.session_state: st.session_state.kpi_filter = "None"

    df = get_data("Pazienti")
    df_prev = get_data("Preventivi_Salvati")
    df_inv = get_data("Inventario")
    df_cons = get_data("Consegne")
    
    if not df.empty:
        # Preprocessing
        for col in ['Disdetto', 'Visita_Esterna']:
            [cite_start]if col not in df.columns: df[col] = False [cite: 76]
            df[col] = df[col].fillna(False)
        for col in ['Data_Disdetta', 'Data_Visita']:
            if col not in df.columns: df[col] = None
            df[col] = pd.to_datetime(df[col], errors='coerce')
        if 'Area' not in df.columns: df['Area'] = None

        totali = len(df)
        df_disdetti = df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) [cite_start]] [cite: 77, 78]
        cnt_attivi = totali - len(df_disdetti)
        oggi = pd.Timestamp.now().normalize()
        
        limite_recall = oggi - pd.Timedelta(days=7)
        da_richiamare = df_disdetti[ (df_disdetti['Data_Disdetta'].notna()) & (df_disdetti['Data_Disdetta'] <= limite_recall) ]
        
        df_visite = df[ (df['Visita_Esterna'] == True) | (df['Visita_Esterna'] == 1) [cite_start]] [cite: 79]
        domani = oggi + pd.Timedelta(days=1)
        visite_imminenti = df_visite[ (df_visite['Data_Visita'].notna()) & (df_visite['Data_Visita'] >= oggi) & (df_visite['Data_Visita'] <= domani) ]
        
        curr_week = oggi.isocalendar()[1]
        visite_settimana = df_visite[ df_visite['Data_Visita'].apply(lambda x: x.isocalendar()[1] if pd.notnull(x) else -1) == curr_week ]
        visite_da_reinserire = df_visite[ (df_visite['Data_Visita'].notna()) & (oggi >= (df_visite['Data_Visita'] + pd.Timedelta(days=2))) ]

        [cite_start]cnt_prev = len(df_prev) [cite: 80]
        prev_scaduti = pd.DataFrame()
        if not df_prev.empty:
            df_prev['Data_Creazione'] = pd.to_datetime(df_prev['Data_Creazione'], errors='coerce')
            limite_prev = oggi - timedelta(days=7)
            prev_scaduti = df_prev[df_prev['Data_Creazione'] <= limite_prev]

        low_stock = pd.DataFrame()
        if not df_inv.empty:
            [cite_start]if 'Quantità' in df_inv.columns: df_inv = df_inv.rename(columns={'Quantità': 'Quantita'}) [cite: 81]
            for c in ['Quantita', 'Soglia_Minima', 'Materiali']:
                if c not in df_inv.columns: df_inv[c] = 0
            low_stock = df_inv[df_inv['Quantita'] <= df_inv['Soglia_Minima']]

        # Consegne: Filtro dati sporchi
        consegne_pendenti = pd.DataFrame()
        if not df_cons.empty:
            [cite_start]if 'Completato' not in df_cons.columns: df_cons['Completato'] = False [cite: 82]
            if 'Data_Scadenza' not in df_cons.columns: df_cons['Data_Scadenza'] = None
            if 'Paziente' not in df_cons.columns: df_cons['Paziente'] = None
            
            [cite_start]df_cons = df_cons.dropna(subset=['Paziente']) [cite: 83]
            df_cons['Data_Scadenza'] = pd.to_datetime(df_cons['Data_Scadenza'], errors='coerce')
            consegne_pendenti = df_cons[df_cons['Completato'] != True]

        col1, col2, col3, col4, col5 = st.columns(5)
        def draw_kpi(col, icon, num, label, color, filter_key):
            with col:
                [cite_start]st.markdown(f"""<div class="glass-kpi" style="border-bottom: 4px solid {color};"><div class="kpi-icon" style="color:{color};">{icon}</div><div class="kpi-value">{num}</div><div class="kpi-label">{label}</div></div>""", unsafe_allow_html=True) [cite: 84]
                if st.button("Vedi Lista", key=f"btn_{filter_key}"): st.session_state.kpi_filter = filter_key

        draw_kpi(col1, "👥", cnt_attivi, "Attivi", "#2ecc71", "Attivi")
        draw_kpi(col2, "📉", len(df_disdetti), "Disdetti", "#e53e3e", "Disdetti")
        draw_kpi(col3, "💡", len(da_richiamare), "Recall", "#ed8936", "Recall")
        draw_kpi(col4, "🩺", len(df_visite), "Visite", "#0bc5ea", "Visite")
        draw_kpi(col5, "💳", cnt_prev, "Preventivi", "#9f7aea", "Preventivi")

        [cite_start]st.write("") [cite: 85]
        if st.session_state.kpi_filter != "None":
            [cite_start]st.divider(); c_head, c_close = st.columns([9, 1]) [cite: 86]
            c_head.subheader(f"📋 Lista: {st.session_state.kpi_filter}")
            [cite_start]if c_close.button("❌"): st.session_state.kpi_filter = "None"; st.rerun() [cite: 87]
            df_show = pd.DataFrame()
            if st.session_state.kpi_filter == "Attivi": df_show = df[ (df['Disdetto'] == False) | (df['Disdetto'] == 0) [cite_start]] [cite: 88]
            elif st.session_state.kpi_filter == "Disdetti": df_show = df_disdetti
            elif st.session_state.kpi_filter == "Recall": df_show = da_richiamare
            elif st.session_state.kpi_filter == "Visite": df_show = df_visite
            elif st.session_state.kpi_filter == "Preventivi": df_show = df_prev
            if not df_show.empty: 
                [cite_start]cols_to_show = ['Nome', 'Cognome', 'Area', 'Data_Disdetta', 'Data_Visita'] [cite: 89]
                if st.session_state.kpi_filter == "Preventivi": cols_to_show = ['Paziente', 'Data_Creazione', 'Totale']
                valid_show = [c for c in cols_to_show if c in df_show.columns]
                st.dataframe(df_show[valid_show], use_container_width=True, height=250)
            else: st.info("Nessun dato.")
            [cite_start]st.divider() [cite: 90]

        st.write("")
        st.subheader("🔔 Avvisi e Scadenze")
        
        # 1. Consegne (Grigio)
        if not consegne_pendenti.empty:
            st.caption(f"📨 Consegne in sospeso: {len(consegne_pendenti)}")
            for i, row in consegne_pendenti.iterrows():
                [cite_start]c_info, c_btn1, c_void = st.columns([3, 1, 1], gap="small") [cite: 91]
                scad_str = row['Data_Scadenza'].strftime('%d/%m') if pd.notnull(row['Data_Scadenza']) else "N.D."
                with c_info: 
                    [cite_start]st.markdown(f"""<div class="alert-row-name border-gray">{row['Paziente']}: {row['Indicazione']} (Entro: {scad_str})</div>""", unsafe_allow_html=True) [cite: 92]
                with c_btn1:
                    if st.button("✅ Fatto", key=f"ok_dash_{row['id']}", type="secondary", use_container_width=True):
                        update_generic("Consegne", row['id'], {"Completato": True})
                        [cite_start]st.rerun() [cite: 93]

        # 2. Magazzino (Giallo)
        if not low_stock.empty:
            st.caption(f"⚠️ Prodotti in esaurimento: {len(low_stock)}")
            for i, row in low_stock.iterrows():
                c_info, c_btn, c_void = st.columns([3, 1, 1], gap="small")
                [cite_start]with c_info: [cite: 94]
                    mat_name = row.get('Materiali', 'Sconosciuto')
                    st.markdown(f"""<div class="alert-row-name border-yellow">{mat_name} (Qta: {row.get('Quantita',0)})</div>""", unsafe_allow_html=True)
                with c_btn:
                    [cite_start]if st.button("🔄 Riordinato", key=f"restock_{row['id']}", type="primary", use_container_width=True): [cite: 95]
                        target = int(row.get('Obiettivo', 5))
                        update_generic("Inventario", row['id'], {"Quantità": target})
                        st.rerun()

        # 3. Preventivi (Viola)
        [cite_start]if not prev_scaduti.empty: [cite: 96]
            st.caption(f"⏳ Preventivi > 7gg: {len(prev_scaduti)}")
            for i, row in prev_scaduti.iterrows():
                c_info, c_btn1, c_btn2 = st.columns([3, 1, 1], gap="small")
                with c_info: st.markdown(f"""<div class="alert-row-name border-purple">{row['Paziente']} ({row['Data_Creazione'].strftime('%d/%m')})</div>""", unsafe_allow_html=True)
                with c_btn1:
                    [cite_start]if st.button("📞 Rinnova", key=f"ren_{row['id']}", type="primary", use_container_width=True): update_generic("Preventivi_Salvati", row['id'], {"Data_Creazione": str(date.today())}); st.rerun() [cite: 97, 98]
                with c_btn2:
                    [cite_start]if st.button("🗑️ Elimina", key=f"del_prev_{row['id']}", type="secondary", use_container_width=True): delete_generic("Preventivi_Salvati", row['id']); st.rerun() [cite: 98, 99]

        # 4. Recall (Arancio)
        if not da_richiamare.empty:
            st.caption(f"📞 Recall Necessari: {len(da_richiamare)}")
            for i, row in da_richiamare.iterrows():
                c_info, c_btn1, c_btn2 = st.columns([3, 1, 1], gap="small")
                with c_info: st.markdown(f"""<div class="alert-row-name border-orange">{row['Nome']} {row['Cognome']}</div>""", unsafe_allow_html=True)
                [cite_start]with c_btn1: [cite: 100]
                    [cite_start]if st.button("✅ Rientrato", key=f"rk_{row['id']}", type="primary", use_container_width=True): update_generic("Pazienti", row['id'], {"Disdetto": False, "Data_Disdetta": None}); st.rerun() [cite: 100, 101]
                with c_btn2: 
                    [cite_start]if st.button("📅 Rimandare", key=f"pk_{row['id']}", type="secondary", use_container_width=True): update_generic("Pazienti", row['id'], {"Data_Disdetta": str(date.today())}); st.rerun() [cite: 101, 102]
        
        # 5. Visite Post (Blu)
        if not visite_da_reinserire.empty:
            st.caption(f"🛑 Reinserimento Post-Visita: {len(visite_da_reinserire)}")
            for i, row in visite_da_reinserire.iterrows():
                c_info, c_btn1, c_void = st.columns([3, 1, 1], gap="small")
                [cite_start]with c_info: st.markdown(f"""<div class="alert-row-name border-blue">{row['Nome']} {row['Cognome']} (Visitato il {row['Data_Visita'].strftime('%d/%m')})</div>""", unsafe_allow_html=True) [cite: 103]
                with c_btn1:
                    [cite_start]if st.button("✅ Rientrato", key=f"vk_{row['id']}", type="primary", use_container_width=True): update_generic("Pazienti", row['id'], {"Visita_Esterna": False, "Data_Visita": None}); st.rerun() [cite: 103, 104]
        
        if not visite_settimana.empty:
            st.caption(f"📅 Visite questa settimana: {len(visite_settimana)}")
            for i, row in visite_settimana.iterrows():
                st.markdown(f"""<div class="alert-row-name border-blue" style="justify-content: space-between;"><span>{row['Nome']} {row['Cognome']}</span><span style="color:#0bc5ea; font-size:13px;">{row['Data_Visita'].strftime('%A %d/%m')}</span></div>""", unsafe_allow_html=True)
        
        [cite_start]if da_richiamare.empty and visite_da_reinserire.empty and visite_settimana.empty and prev_scaduti.empty and low_stock.empty and consegne_pendenti.empty: st.success("Tutto tranquillo! Nessun avviso.") [cite: 105]
        
        st.divider()

        # GRAFICO
        st.subheader("📈 Performance Aree")
        df_attivi = df[ (df['Disdetto'] == False) | (df['Disdetto'] == 0) [cite_start]] [cite: 106]
        all_areas = []
        if 'Area' in df_attivi.columns:
            for item in df_attivi['Area'].dropna():
                if isinstance(item, list): all_areas.extend(item)
                elif isinstance(item, str): all_areas.extend([p.strip() for p in item.split(',')])
                else: all_areas.append(str(item))
        
        [cite_start]if all_areas: [cite: 107]
            counts = pd.Series(all_areas).value_counts().reset_index()
            counts.columns = ['Area', 'Pazienti']
            domain = ["Mano-Polso", "Muscolo-Scheletrico", "Colonna", "ATM", "Gruppi", "Ortopedico"]
            range_ = ["#0bc5ea", "#9f7aea", "#ecc94b", "#2ecc71", "#e53e3e", "#4a5568"]
            chart = alt.Chart(counts).mark_bar(cornerRadius=6, height=35).encode(
                [cite_start]x=alt.X('Pazienti', axis=None), [cite: 108]
                y=alt.Y('Area', sort='-x', title=None, axis=alt.Axis(domain=False, ticks=False, labelColor="#cbd5e0", labelFontSize=14)),
                color=alt.Color('Area', scale=alt.Scale(domain=domain, range=range_), legend=None),
                tooltip=['Area', 'Pazienti']
            ).properties(height=400).configure(background='transparent').configure_view(strokeWidth=0).configure_axis(grid=False)
            st.altair_chart(chart, use_container_width=True, theme=None)
        [cite_start]else: st.info("Dati insufficienti.") [cite: 109]

# =========================================================
# SEZIONE 2: PAZIENTI
# =========================================================
elif menu == "👥 Pazienti":
    st.title("Anagrafica Pazienti")
    lista_aree = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
    
    with st.container(border=True):
        st.subheader("➕ Aggiungi Paziente")
        with st.form("form_paziente", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            [cite_start]c1.text_input("Nome", key="new_name", placeholder="Es. Mario") [cite: 109, 110]
            c2.text_input("Cognome", key="new_surname", placeholder="Es. Rossi")
            c3.multiselect("Area", lista_aree, key="new_area")
            if st.form_submit_button("Salva Paziente", use_container_width=True, type="primary"):
                if st.session_state.new_name and st.session_state.new_surname:
                    save_paziente(st.session_state.new_name, st.session_state.new_surname, ", ".join(st.session_state.new_area), False)
                    [cite_start]st.success("Paziente salvato!"); st.rerun() [cite: 111]
    
    st.write(""); df_original = get_data("Pazienti")
    
    if not df_original.empty:
        for c in ['Disdetto', 'Visita_Esterna', 'Dimissione']:
            if c not in df_original.columns: df_original[c] = False
            df_original[c] = df_original[c].fillna(False).infer_objects(copy=False)
        for c in ['Data_Disdetta', 'Data_Visita']:
            [cite_start]if c not in df_original.columns: df_original[c] = None [cite: 112]
            df_original[c] = pd.to_datetime(df_original[c], errors='coerce')
        if 'Area' in df_original.columns: df_original['Area'] = df_original['Area'].apply(lambda x: x[0] if isinstance(x, list) and len(x)>0 else (str(x) if x else "")).str.strip() 
        df_original['Area'] = df_original['Area'].astype("category")
        
        col_search, _ = st.columns([1, 2])
        with col_search: search = st.text_input("🔍 Cerca Paziente", placeholder="Digita il cognome...")
        [cite_start]df_filt = df_original[df_original['Cognome'].astype(str).str.contains(search, case=False, na=False)] if search else df_original [cite: 113]
        cols_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'Data_Disdetta', 'Visita_Esterna', 'Data_Visita', 'Dimissione', 'id']
        valid_cols = [c for c in cols_show if c in df_filt.columns]
        
        edited = st.data_editor(df_filt[valid_cols], column_config={"Disdetto": st.column_config.CheckboxColumn("Disd.", width="small"), "Data_Disdetta": st.column_config.DateColumn("Data Disd.", format="DD/MM/YYYY"), "Visita_Esterna": st.column_config.CheckboxColumn("Visita Ext.", width="small"), "Data_Visita": st.column_config.DateColumn("Data Visita", format="DD/MM/YYYY"), "Dimissione": st.column_config.CheckboxColumn("🗑️", width="small"), "Area": st.column_config.SelectboxColumn("Area Principale", options=lista_aree), "id": None}, disabled=["Nome", "Cognome"], hide_index=True, use_container_width=True, key="editor_main", num_rows="fixed", height=500)
        
        [cite_start]if st.button("💾 Salva Modifiche Tabella", type="primary", use_container_width=True): [cite: 114]
            [cite_start]count_upd = 0; count_del = 0 [cite: 114, 115]
            for i, row in edited.iterrows():
                rec_id = row['id']
                [cite_start]if row.get('Dimissione') == True: delete_generic("Pazienti", rec_id); count_del += 1; continue [cite: 115, 116]
                [cite_start]orig = df_original[df_original['id'] == rec_id].iloc[0]; changes = {} [cite: 116, 117]
                if row['Disdetto'] != (orig['Disdetto'] in [True, 1]): changes['Disdetto'] = row['Disdetto']
                if str(row['Data_Disdetta']) != str(orig['Data_Disdetta']): changes['Data_Disdetta'] = row['Data_Disdetta']
                if row['Disdetto'] and (pd.isna(row['Data_Disdetta']) or str(row['Data_Disdetta']) == "NaT"): changes['Data_Disdetta'] = pd.Timestamp.now().normalize()
                [cite_start]if row['Visita_Esterna'] != (orig['Visita_Esterna'] in [True, 1]): changes['Visita_Esterna'] = row['Visita_Esterna'] [cite: 117, 118]
                if str(row['Data_Visita']) != str(orig['Data_Visita']): changes['Data_Visita'] = row['Data_Visita']
                if row['Area'] != orig['Area']: changes['Area'] = row['Area']
                [cite_start]if changes: update_generic("Pazienti", rec_id, changes); count_upd += 1 [cite: 118, 119]
            [cite_start]if count_upd > 0 or count_del > 0: get_data.clear(); st.toast("Database aggiornato!", icon="✅"); st.rerun() [cite: 119, 120]

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💳 Preventivi":
    st.title("Preventivi & Proposte")
    tab1, tab2 = st.tabs(["📝 Generatore", "📂 Archivio Salvati"])
    [cite_start]df_srv = get_data("Servizi"); df_paz = get_data("Pazienti"); df_std = get_data("Preventivi_Standard") [cite: 121]
    
    if 'prev_note' not in st.session_state: st.session_state.prev_note = ""
    if 'prev_selected_services' not in st.session_state: st.session_state.prev_selected_services = []
    
    listino_dict = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i, r in df_srv.iterrows() if r.get('Servizio')}
    all_services_list = sorted(list(listino_dict.keys()))

    with tab1:
        with st.container(border=True):
            st.subheader("Creazione Nuovo Preventivo")
            
            [cite_start]if not df_std.empty and 'Area' in df_std.columns and 'Nome' in df_std.columns: [cite: 122]
                c_filter, c_pack = st.columns(2)
                with c_filter:
                    [cite_start]aree_std = sorted(list(df_std['Area'].unique())) [cite: 123]
                    area_sel = st.selectbox("Filtra per Area:", ["-- Tutte --"] + aree_std)
                
                with c_pack:
                    [cite_start]if area_sel != "-- Tutte --": df_std_filtered = df_std[df_std['Area'] == area_sel] [cite: 124]
                    else: df_std_filtered = df_std
                    nomi_pacchetti = sorted(list(df_std_filtered['Nome'].unique()))
                    scelta_std = st.selectbox("Carica Pacchetto:", ["-- Seleziona --"] + nomi_pacchetti)

                [cite_start]if scelta_std != "-- Seleziona --": [cite: 125]
                    if 'last_std_pkg' not in st.session_state or st.session_state.last_std_pkg != scelta_std:
                        [cite_start]row_std = df_std[df_std['Nome'] == scelta_std].iloc[0] [cite: 126]
                        st.session_state.prev_note = row_std.get('Descrizione', '')
                        
                        [cite_start]new_services = [] [cite: 127]
                        if row_std.get('Contenuto'):
                            [cite_start]for p in row_std['Contenuto'].split(','): [cite: 128]
                                if ' x' in p: 
                                    srv_raw, qty_raw = p.split(' x')
                                    [cite_start]srv_clean = srv_raw.strip() [cite: 129]
                                    if srv_clean in all_services_list:
                                        [cite_start]new_services.append(srv_clean) [cite: 130]
                                        st.session_state[f"qty_{srv_clean}"] = int(qty_raw)
                        
                        [cite_start]st.session_state.prev_selected_services = new_services [cite: 131]
                        st.session_state.last_std_pkg = scelta_std
                        st.rerun()

            nomi_pazienti = ["Seleziona..."] + sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows()]) if not df_paz.empty else []
            c_paz, c_serv = st.columns([1, 2])
            
            [cite_start]with c_paz: [cite: 132]
                paziente_scelto = st.selectbox("Intestato a:", nomi_pazienti)
            
            with c_serv:
                [cite_start]servizi_scelti = st.multiselect("Trattamenti:", all_services_list, key="prev_selected_services") [cite: 133]

            st.write("---")
            st.caption("Strumenti Rapidi Note:")
            
            c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
            
            [cite_start]def append_note(text): [cite: 134]
                st.session_state.prev_note += text
            
            if c_btn1.button("🔥 Fase Infiammatoria"): 
                [cite_start]append_note("\n\nFase Infiammatoria: Il primo obiettivo è ridurre l'infiammazione e controllare il dolore, associando la prima fase di riabilitazione alla gestione del movimento e del carico.") [cite: 134, 135]
            if c_btn2.button("🤸 Fase Sub-Acuta"): 
                append_note("\n\nFase Sub-Acuta: L'obiettivo è recuperare la completa mobilità e la qualità del movimento, reintroducendo gradualmente i carichi per riabituare i tessuti allo sforzo.")
            if c_btn3.button("💪 Fase Rinforzo"): 
                [cite_start]append_note("\n\nFase Rinforzo: L'obiettivo è recuperare e incrementare la forza e la resistenza dei tessuti interessati, per una ripresa completa delle attività quotidiane e sportive, prevenendo future recidive.") [cite: 135, 136]
            if c_btn4.button("🏃 Fase Riatletizzazione"): 
                append_note("\n\nFase Riatletizzazione: L'obiettivo è recuperare il gesto specifico e la performance, lavorando su forza, resistenza ed esplosività per un ritorno allo sport in sicurezza.")
            
            c_prog1, c_prog2 = st.columns([1, 3])
            [cite_start]settimane = c_prog1.number_input("Settimane", 1, 52, 4) [cite: 137]
            if c_prog2.button("Genera Prognosi"): 
                append_note(f"\n\nPrognosi Funzionale: In base alla valutazione clinica, stimiamo un percorso di circa {settimane} settimane per il raggiungimento degli obiettivi.")

            [cite_start]note_preventivo = st.text_area("Dettagli del Percorso:", key="prev_note", height=150) [cite: 137, 138]
            
            [cite_start]righe = []; tot = 0 [cite: 138, 139]
            if servizi_scelti:
                st.divider()
                for s in servizi_scelti:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    [cite_start]if f"qty_{s}" not in st.session_state: st.session_state[f"qty_{s}"] = 1 [cite: 140]
                    qty = c2.number_input(f"Qta {s}", 1, 50, key=f"qty_{s}")
                    
                    cost = listino_dict[s] * qty
                    [cite_start]tot += cost [cite: 141]
                    c1.write(f"**{s}**")
                    c3.write(f"**{cost} €**")
                    righe.append({"nome": s, "qty": qty, "tot": cost})
                
                [cite_start]st.divider() [cite: 142]
                c_tot, c_btn = st.columns([2, 1])
                c_tot.markdown(f"### TOTALE: {tot} €")
                
                with c_btn:
                    [cite_start]if st.button("💾 Salva Preventivo", type="primary", use_container_width=True): [cite: 143]
                        if paziente_scelto != "Seleziona...":
                            [cite_start]dett = " | ".join([f"{r['nome']} x{r['qty']} ({r['tot']}€)" for r in righe]) [cite: 143, 144]
                            save_preventivo_temp(paziente_scelto, dett, tot, note_preventivo)
                            st.success("Salvato!")
                        [cite_start]else: st.error("Seleziona un paziente.") [cite: 145]
                    
                    if st.button("🖨️ Anteprima Stampa", use_container_width=True):
                        st.session_state.show_html = True

            [cite_start]if st.session_state.get('show_html'): [cite: 146]
                html = generate_html_preventivo(paziente_scelto, date.today().strftime("%d/%m/%Y"), note_preventivo, righe, tot, LOGO_B64)
                components.html(html, height=800, scrolling=True)
                if st.button("Chiudi Anteprima"):
                    st.session_state.show_html = False
                    [cite_start]st.rerun() [cite: 147]

    with tab2:
        st.subheader("Archivio"); df_prev = get_data("Preventivi_Salvati")
        if not df_prev.empty:
            for i, r in df_prev.iterrows():
                with st.expander(f"{r['Paziente']} - {r['Totale']}€ ({r['Data_Creazione']})"):
                    st.write(r['Dettagli'])
                    [cite_start]if st.button("Elimina", key=f"del_{r['id']}"): delete_generic("Preventivi_Salvati", r['id']); st.rerun() [cite: 148, 149]

# =========================================================
# SEZIONE NUOVA: CONSEGNE (AGGIORNATA CON SEGRETERIA)
# =========================================================
elif menu == "📨 Consegne":
    st.title("📨 Consegne Pazienti")
    df_cons = get_data("Consegne")
    [cite_start]df_paz = get_data("Pazienti") [cite: 149, 150]
    nomi_paz = ["-- Seleziona --"] + sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows()]) if not df_paz.empty else []
    
    with st.expander("➕ Nuova Consegna", expanded=True):
        with st.form("new_cons"):
            c1, c2 = st.columns(2)
            paz = c1.selectbox("Paziente", nomi_paz)
            # AGGIUNTA "Segreteria" QUI SOTTO
            [cite_start]area = c2.selectbox("Area Competenza", ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Segreteria"]) [cite: 151]
            ind = st.text_input("Cosa consegnare? (es. Referto, Scheda Esercizi)")
            scad = st.date_input("Entro quando?", date.today() + timedelta(days=3))
            if st.form_submit_button("Salva Promemoria"):
                if paz != "-- Seleziona --" and ind:
                    [cite_start]save_consegna(paz, area, ind, scad); st.success("Salvato!"); st.rerun() [cite: 152]
                else: st.error("Compila i campi.")

    st.write("")
    
    # AGGIUNTA "Segreteria" NELLE TABS E NEL MAPPING
    [cite_start]tabs = st.tabs(["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Segreteria"]) [cite: 153]
    mapping = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Segreteria"]
    
    if not df_cons.empty:
        if 'Data_Scadenza' in df_cons.columns: df_cons['Data_Scadenza'] = pd.to_datetime(df_cons['Data_Scadenza']).dt.date
        if 'Completato' not in df_cons.columns: df_cons['Completato'] = False
        
        [cite_start]for i, tab_name in enumerate(mapping): [cite: 154]
            with tabs[i]:
                # Filtra per l'area specifica della tab corrente
                items = df_cons[ (df_cons['Area'] == tab_name) & (df_cons['Completato'] != True) ]
                
                if items.empty: 
                    st.info(f"Nessuna consegna in attesa per {tab_name}.")
                else:
                    [cite_start]for _, row in items.iterrows(): [cite: 155]
                        # Calcolo giorni mancanti o ritardo
                        delta = (row['Data_Scadenza'] - date.today()).days
                        
                        # Logica colori avvisi
                        color = "border-green" if delta > 3 else "border-yellow" if delta >= 0 else "border-red"
                        [cite_start]status_text = f"Scade tra {delta} gg" if delta >= 0 else f"SCADUTO da {abs(delta)} gg" [cite: 155, 156]
                        
                        # Layout riga
                        c_chk, c_info, c_date = st.columns([1, 6, 2])
                        with c_chk:
                            if st.button("✅", key=f"ok_{row['id']}"):
                                [cite_start]update_generic("Consegne", row['id'], {"Completato": True}) [cite: 157]
                                [cite_start]st.rerun() [cite: 158]
                        with c_info:
                            st.markdown(f"""<div class="alert-row-name {color}"><b>{row['Paziente']}</b>: {row['Indicazione']}</div>""", unsafe_allow_html=True)
                        with c_date:
                            [cite_start]st.caption(f"{row['Data_Scadenza'].strftime('%d/%m')}\n({status_text})") [cite: 159]

# =========================================================
# SEZIONE 4: MAGAZZINO
# =========================================================
elif menu == "📦 Magazzino":
    st.title("Magazzino & Materiali")
    STANZE = ["Segreteria", "Mano", "Stanze", "Medicinali", "Pulizie"]
    col_add, col_view = st.columns([1, 2])
    
    with col_add:
        with st.container(border=True):
            st.subheader("Nuovo Articolo")
            with st.form("add_inv"):
                [cite_start]new_mat = st.text_input("Nome Materiale") [cite: 160]
                new_area = st.selectbox("Area/Stanza", STANZE)
                c_q1, c_q2, c_q3 = st.columns(3)
                qty_now = c_q1.number_input("Q.tà Attuale", 0, 1000, 1)
                qty_target = c_q2.number_input("Obiettivo", 1, 1000, 5)
                [cite_start]qty_min = c_q3.number_input("Soglia Minima", 0, 100, 2) [cite: 161]
                if st.form_submit_button("Aggiungi", use_container_width=True, type="primary"):
                    if new_mat:
                        save_materiale_avanzato(new_mat, new_area, qty_now, qty_target, qty_min)
                        [cite_start]st.success("Aggiunto!"); st.rerun() [cite: 162]

    with col_view:
        df_inv = get_data("Inventario")
        if not df_inv.empty:
            if 'Quantità' in df_inv.columns: df_inv = df_inv.rename(columns={'Quantità': 'Quantita'})
            for c in ['Quantita', 'Soglia_Minima', 'Materiali', 'Obiettivo']:
                if c not in df_inv.columns: df_inv[c] = 0
            [cite_start]df_inv['Quantita'] = df_inv['Quantita'].fillna(0).astype(int) [cite: 163]
            
            tabs = st.tabs(STANZE)
            for i, stanza in enumerate(STANZE):
                with tabs[i]:
                    items = df_inv[df_inv['Area'] == stanza]
                    [cite_start]if items.empty: st.caption("Nessun articolo.") [cite: 164]
                    else:
                        for _, row in items.iterrows():
                            is_low = row['Quantita'] <= row['Soglia_Minima']
                            [cite_start]with st.container(border=True): [cite: 165]
                                [cite_start]st.markdown('<style>div[data-testid="stVerticalBlockBorderWrapper"] {padding: 8px 15px !important; margin-bottom: 5px !important;}</style>', unsafe_allow_html=True) [cite: 166]
                                c_info, c_stat, c_act = st.columns([3, 2, 1], gap="small")
                                with c_info:
                                    [cite_start]mat_name = row.get('Materiali', 'Senza Nome') [cite: 167]
                                    st.markdown(f"**{mat_name}**")
                                    if is_low: st.caption(":red[⚠️ BASSO]")
                                    [cite_start]else: st.caption(":green[OK]") [cite: 168]
                                with c_stat:
                                    [cite_start]val = min(row['Quantita'] / max(row['Obiettivo'], 1), 1.0) [cite: 169]
                                    st.progress(val)
                                    st.caption(f"**{row['Quantita']}** / {row['Obiettivo']}")
                                [cite_start]with c_act: [cite: 170]
                                    st.write("") 
                                    if st.button("🔻1", key=f"dec_{row['id']}", type="primary" if is_low else "secondary"):
                                        [cite_start]if row['Quantita'] > 0: [cite: 171]
                                            new_qty = int(row['Quantita'] - 1)
                                            [cite_start]update_generic("Inventario", row['id'], {"Quantità": new_qty}) [cite: 172]
                                            st.rerun()
        else: st.info("Magazzino vuoto.")

# =========================================================
# SEZIONE 5: PRESTITI (NUOVA LOGICA INVENTARIO)
# =========================================================
elif menu == "🔄 Prestiti":
    st.title("Gestione Noleggi e Prestiti")
    
    # 1. DEFINISCI QUI IL TUO INVENTARIO STRUMENTI
    # Modifica le stringhe tra virgolette con i nomi reali dei tuoi strumenti
    INVENTARIO = {
        "Strumenti Mano": [
            "Tutore Polso A", "Tutore Polso B", "Kit Riabilitazione Mano", 
            "Dinamometro", "Molla Esercizi"
        ],
        "Elettrostimolatore": [
            "Compex Pro 1", "Compex Pro 2", "Compex Wireless", 
            "Neurostimolatore TENS"
        ],
        "Magnetoterapia": [
            "Mag 2000 (A)", "Mag 2000 (B)", "I-Tech Magneto", 
            "Solenoidi Fascia"
        ]
    }
    
    # Carichiamo i dati
    df_pres = get_data("Prestiti")
    [cite_start]df_paz = get_data("Pazienti") [cite: 173]
    nomi_paz = ["-- Seleziona --"] + sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows()]) if not df_paz.empty else []

    # Creiamo le 3 Aree richieste
    tabs = st.tabs(["✋ Strumenti Mano", "⚡ Elettrostimolatore", "🧲 Magnetoterapia"])
    
    # Ciclo per generare le tab
    mappa_tabs = {0: "Strumenti Mano", 1: "Elettrostimolatore", 2: "Magnetoterapia"}
    
    for i, tab_name in mappa_tabs.items():
        with tabs[i]:
            st.subheader(f"Disponibilità {tab_name}")
            
            # Recuperiamo la lista degli strumenti per questa categoria
            strumenti_categoria = INVENTARIO[tab_name]
            
            # Intestazione griglia
            c1, c2, c3, c4 = st.columns([2, 3, 2, 2])
            c1.markdown("**Strumento**")
            c2.markdown("**Stato / Paziente**")
            c3.markdown("**Scadenza**")
            c4.markdown("**Azione**")
            st.divider()

            for strumento in strumenti_categoria:
                # Controlliamo se lo strumento è attualmente prestato (non restituito)
                prestito_attivo = pd.DataFrame()
                if not df_pres.empty:
                    # Cerca prestito per questo oggetto che NON ha Restituito=True
                    # Assicuriamoci che le colonne esistano
                    if 'Oggetto' in df_pres.columns and 'Restituito' in df_pres.columns:
                        prestito_attivo = df_pres[
                            (df_pres['Oggetto'] == strumento) & 
                            (df_pres['Restituito'] != True)
                        ]
                
                # Creiamo le colonne per la riga
                row_c1, row_c2, row_c3, row_c4 = st.columns([2, 3, 2, 2])
                
                with row_c1:
                    st.write(f"🔹 {strumento}")
                
                # CASO 1: STRUMENTO OCCUPATO
                if not prestito_attivo.empty:
                    record = prestito_attivo.iloc[0] # Prendi il primo record trovato
                    scadenza = pd.to_datetime(record['Data_Scadenza']).date() if 'Data_Scadenza' in record and pd.notnull(record['Data_Scadenza']) else date.today()
                    days_left = (scadenza - date.today()).days
                    
                    color_class = "border-red" if days_left < 0 else "border-green"
                    msg_scad = f"Scade tra {days_left} gg" if days_left >= 0 else f"SCADUTO da {abs(days_left)} gg"
                    
                    with row_c2:
                        paz_nome = record['Paziente'] if 'Paziente' in record else "Sconosciuto"
                        st.markdown(f"<div class='{color_class}'>🔴 <b>{paz_nome}</b></div>", unsafe_allow_html=True)
                    with row_c3:
                        st.caption(f"{scadenza.strftime('%d/%m')}\n({msg_scad})")
                    with row_c4:
                        if st.button("🔄 Restituito", key=f"ret_{strumento}"):
                            update_generic("Prestiti", record['id'], {"Restituito": True})
                            st.success(f"{strumento} rientrato!")
                            st.rerun()
                            
                # CASO 2: STRUMENTO DISPONIBILE (Libero)
                else:
                    with row_c2:
                        # Form selezione paziente
                        paz_sel = st.selectbox(f"Paziente ({strumento})", nomi_paz, key=f"paz_{strumento}", label_visibility="collapsed")
                    
                    with row_c3:
                        # Selezione durata
                        cols_d = st.columns(2)
                        num = cols_d[0].number_input("Qta", min_value=1, value=1, key=f"n_{strumento}", label_visibility="collapsed")
                        unit = cols_d[1].selectbox("U", ["Sett", "Giorni"], key=f"u_{strumento}", label_visibility="collapsed")
                        
                    with row_c4:
                        if st.button("➕ Presta", key=f"btn_{strumento}"):
                            if paz_sel != "-- Seleziona --":
                                # Calcolo data scadenza
                                delta = timedelta(weeks=num) if unit == "Sett" else timedelta(days=num)
                                scadenza_calc = date.today() + delta
                                
                                # Salvataggio su Airtable
                                save_prestito_new(paz_sel, strumento, tab_name, date.today(), scadenza_calc)
                                st.rerun()
                            else:
                                st.toast("Seleziona un paziente!", icon="⚠️")
                st.divider()

# =========================================================
# SEZIONE 6: SCADENZE
# =========================================================
elif menu == "📅 Scadenze":
    st.title("Checklist Scadenze")
    df_scad = get_data("Scadenze")
    if not df_scad.empty and 'Data_Scadenza' in df_scad.columns:
        [cite_start]df_scad['Data_Scadenza'] = pd.to_datetime(df_scad['Data_Scadenza'], errors='coerce'); df_scad = df_scad.sort_values("Data_Scadenza") [cite: 178]
        st.dataframe(df_scad, column_config={"Data_Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"), "Importo": st.column_config.NumberColumn("Importo", format="%d €"), "Descrizione": st.column_config.TextColumn("Dettagli")}, use_container_width=True, height=500)
    else: st.info("Nessuna scadenza prossima.")
