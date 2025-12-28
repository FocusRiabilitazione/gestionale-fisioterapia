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
# 0. CONFIGURAZIONE & STILE (ULTIMATE UI)
# =========================================================
st.set_page_config(page_title="Gestionale Fisio Pro", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* SFONDO PROFONDO */
    .stApp {
        background: radial-gradient(circle at top left, #1a202c, #0d1117);
        color: #e2e8f0;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(20px);
    }

    /* --- TITOLI MODERNI --- */
    h1 {
        font-family: 'Outfit', sans-serif;
        font-weight: 800 !important;
        background: linear-gradient(120deg, #ffffff, #a0aec0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
        margin-bottom: 10px;
    }
    h2, h3, h4 {
        font-family: 'Outfit', sans-serif;
        font-weight: 600 !important;
        color: #f7fafc !important;
        letter-spacing: 0.5px;
    }

    /* --- KPI CARDS (CON GLOW EFFECT) --- */
    .glass-kpi {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px; /* Più arrotondato */
        padding: 20px;
        text-align: center;
        height: 140px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        margin-bottom: 10px;
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    .glass-kpi:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.06);
    }
    
    /* Icone animate */
    .kpi-icon { 
        font-size: 32px; 
        margin-bottom: 8px; 
        transition: transform 0.3s ease;
        filter: drop-shadow(0 0 5px rgba(255,255,255,0.3));
    }
    .glass-kpi:hover .kpi-icon { transform: scale(1.1); }

    .kpi-value { font-size: 36px; font-weight: 800; color: white; line-height: 1; letter-spacing: -1px; }
    .kpi-label { font-size: 11px; text-transform: uppercase; color: #a0aec0; margin-top: 8px; letter-spacing: 1.5px; font-weight: 600; }

    /* --- PULSANTI --- */
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
    }
    div[data-testid="column"] .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(66, 153, 225, 0.5) !important;
    }

    /* --- RIGHE AVVISI COMPATTE --- */
    .alert-row-name {
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 10px;
        padding: 0 15px;
        height: 42px;    
        display: flex; align-items: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
        font-weight: 600; color: #fff; font-size: 14px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }

    /* Bordi colorati */
    .border-orange { border-left: 4px solid #ed8936 !important; }
    .border-red { border-left: 4px solid #e53e3e !important; }
    .border-blue { border-left: 4px solid #0bc5ea !important; }
    .border-purple { border-left: 4px solid #9f7aea !important; }
    .border-yellow { border-left: 4px solid #ecc94b !important; }
    .border-green { border-left: 4px solid #2ecc71 !important; }

    /* --- PULSANTI AZIONE --- */
    div[data-testid="stHorizontalBlock"] button {
        padding: 2px 12px !important; font-size: 11px !important; min-height: 0px !important;
        height: 32px !important; line-height: 1 !important; border-radius: 8px !important;
        margin-top: 6px !important; font-weight: 500 !important;
    }
    button[kind="primary"] { background: linear-gradient(135deg, #3182ce, #2b6cb0) !important; border: none !important; color: white !important; }
    button[kind="secondary"] { background: rgba(255, 255, 255, 0.08) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; color: #cbd5e0 !important; }
    button[kind="secondary"]:hover { border-color: #a0aec0 !important; color: white !important; }

    /* --- ALTRI --- */
    div[data-testid="stDataFrame"] { background: transparent; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }
    input, select, textarea { background-color: rgba(13, 17, 23, 0.8) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; color: white !important; border-radius: 8px; }

    /* CSS MAGAZZINO COMPATTO */
    div[data-testid="stVerticalBlockBorderWrapper"] { padding: 10px !important; margin-bottom: 5px !important; background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); }
    div[data-testid="stProgress"] > div > div { height: 6px !important; }
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
    except: return pd.DataFrame()

def save_paziente(n, c, a, d):
    try: api.table(BASE_ID, "Pazienti").create({"Nome": n, "Cognome": c, "Area": a, "Disdetto": d}, typecast=True); get_data.clear(); return True
    except: return False

def update_generic(tbl, rid, data):
    try:
        clean_data = {}
        for k, v in data.items():
            if v is None: clean_data[k] = None
            elif hasattr(v, 'strftime'): clean_data[k] = v.strftime('%Y-%m-%d')
            else: clean_data[k] = v
        api.table(BASE_ID, tbl).update(rid, clean_data, typecast=True)
        get_data.clear()
        return True
    except: return False

def delete_generic(tbl, rid):
    try: api.table(BASE_ID, tbl).delete(rid); get_data.clear(); return True
    except: return False

def save_preventivo_temp(paziente, dettagli_str, totale, note):
    try: api.table(BASE_ID, "Preventivi_Salvati").create({"Paziente": paziente, "Dettagli": dettagli_str, "Totale": totale, "Note": note, "Data_Creazione": str(date.today())}, typecast=True); get_data.clear(); return True
    except: return False

def save_materiale_avanzato(materiale, area, quantita, obiettivo, soglia):
    try: 
        api.table(BASE_ID, "Inventario").create({
            "Materiali": materiale, 
            "Area": area,
            "Quantità": int(quantita),
            "Obiettivo": int(obiettivo),
            "Soglia_Minima": int(soglia)
        }, typecast=True)
        get_data.clear()
        return True
    except Exception as e: st.error(f"Errore Salvataggio: {e}"); return False

def save_consegna(paziente, area, indicazione, scadenza):
    try:
        api.table(BASE_ID, "Consegne").create({
            "Paziente": paziente, "Area": area, "Indicazione": indicazione, 
            "Data_Scadenza": str(scadenza), "Completato": False
        }, typecast=True)
        get_data.clear(); return True
    except: return False

def save_prestito(paziente, oggetto, data_prestito):
    try: api.table(BASE_ID, "Prestiti").create({"Paziente": paziente, "Oggetto": oggetto, "Data_Prestito": str(data_prestito), "Restituito": False}, typecast=True); get_data.clear(); return True
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
    action_bar_style = "display:none;" if auto_print else "display:flex;"

    return f"""
    <!DOCTYPE html> <html lang="it"> <head> <meta charset="UTF-8"> <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
    body {{ font-family: 'Segoe UI', sans-serif; background: #fff; margin: 0; padding: 20px; color: #000; }}
    .action-bar {{ margin-bottom: 20px; justify-content: flex-end; {action_bar_style} }}
    .btn-download {{ background-color: #333; color: white; border: none; padding: 10px 20px; font-weight: bold; border-radius: 4px; cursor: pointer; }}
    .sheet-a4 {{ width: 210mm; min-height: 296mm; padding: 10mm 15mm; margin: 0 auto; background: white; box-sizing: border-box; position: relative; box-shadow: 0 0 10px rgba(0,0,0,0.1); overflow: hidden; }}
    .logo-img {{ max-width: 150px; height: auto; display: block; margin: 0 auto 5px auto; }}
    .doc-brand-main {{ font-size: 26px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; color: #000; text-align: center; }}
    .doc-title {{ font-size: 18px; font-weight: 700; text-transform: uppercase; color: #000; border-bottom: 2px solid #000; padding-bottom: 5px; margin-bottom: 15px; margin-top: 10px; }}
    .info-box {{ margin-bottom: 15px; font-size: 13px; display: flex; justify-content: space-between; }}
    .info-label {{ font-weight: bold; color: #000; margin-right: 5px; }}
    .obj-box {{ background-color: #f2f2f2; border-left: 4px solid #333; padding: 10px; margin-bottom: 20px; font-size: 12px; line-height: 1.3; }}
    .obj-title {{ font-weight: bold; text-transform: uppercase; display: block; margin-bottom: 3px; font-size: 11px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
    th {{ background-color: #e0e0e0; text-align: left; padding: 6px 8px; text-transform: uppercase; font-size: 10px; font-weight: bold; border-bottom: 1px solid #000; color: #000; }}
    td {{ padding: 6px 8px; border-bottom: 1px solid #ccc; font-size: 12px; vertical-align: middle; }}
    .col-qty {{ text-align: center; width: 10%; }} .col-price {{ text-align: right; width: 20%; }}
    .total-row td {{ font-weight: bold; font-size: 14px; border-top: 2px solid #000; padding-top: 8px; color: #000; }}
    .payment-section {{ border: 1px solid #999; padding: 10px; border-radius: 0; margin-bottom: 20px; }}
    .pay-title {{ font-weight: bold; text-transform: uppercase; font-size: 11px; margin-bottom: 8px; color: #000; }}
    .pay-line {{ display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 12px; }}
    .dotted {{ border-bottom: 1px dotted #000; width: 80px; display: inline-block; }} .dotted-date {{ border-bottom: 1px dotted #000; width: 120px; display: inline-block; }}
    .footer {{ margin-top: 40px; display: flex; justify-content: flex-end; }}
    .sign-box {{ text-align: center; width: 200px; }} .sign-line {{ border-bottom: 1px solid #000; margin-top: 30px; }}
    .page-num {{ position: absolute; bottom: 10mm; left: 15mm; font-size: 9px; color: #666; }}
    @media print {{ @page {{ size: A4; margin: 0; }} body {{ margin: 0; padding: 0; background: none; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }} .action-bar {{ display: none !important; }} .sheet-a4 {{ margin: 0; box-shadow: none; border: none; width: 100%; height: 100%; page-break-after: avoid; page-break-inside: avoid; }} }}
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
    """

# --- 3. INTERFACCIA ---
with st.sidebar:
    LOGO_B64 = ""
    try: 
        st.image("logo.png", use_container_width=True)
        LOGO_B64 = get_base64_image("logo.png")
    except: 
        st.title("Focus Rehab")
        
    menu = st.radio("Menu", ["⚡ Dashboard", "👥 Pazienti", "💳 Preventivi", "📨 Consegne", "📦 Magazzino", "🔄 Prestiti", "📅 Scadenze"], label_visibility="collapsed")
    st.divider(); st.caption("App v81 - Final Fix")

# =========================================================
# DASHBOARD
# =========================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")
    st.write("")

    if 'kpi_filter' not in st.session_state: st.session_state.kpi_filter = "None"

    df = get_data("Pazienti")
    df_prev = get_data("Preventivi_Salvati")
    df_inv = get_data("Inventario")
    
    if not df.empty:
        # Preprocessing
        for col in ['Disdetto', 'Visita_Esterna']:
            if col not in df.columns: df[col] = False
            df[col] = df[col].fillna(False)
        for col in ['Data_Disdetta', 'Data_Visita']:
            if col not in df.columns: df[col] = None
            df[col] = pd.to_datetime(df[col], errors='coerce')
        if 'Area' not in df.columns: df['Area'] = None

        totali = len(df)
        df_disdetti = df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) ]
        cnt_attivi = totali - len(df_disdetti)
        oggi = pd.Timestamp.now().normalize()
        
        limite_recall = oggi - pd.Timedelta(days=7)
        da_richiamare = df_disdetti[ (df_disdetti['Data_Disdetta'].notna()) & (df_disdetti['Data_Disdetta'] <= limite_recall) ]
        
        df_visite = df[ (df['Visita_Esterna'] == True) | (df['Visita_Esterna'] == 1) ]
        domani = oggi + pd.Timedelta(days=1)
        visite_imminenti = df_visite[ (df_visite['Data_Visita'].notna()) & (df_visite['Data_Visita'] >= oggi) & (df_visite['Data_Visita'] <= domani) ]
        
        curr_week = oggi.isocalendar()[1]
        visite_settimana = df_visite[ df_visite['Data_Visita'].apply(lambda x: x.isocalendar()[1] if pd.notnull(x) else -1) == curr_week ]
        visite_da_reinserire = df_visite[ (df_visite['Data_Visita'].notna()) & (oggi >= (df_visite['Data_Visita'] + pd.Timedelta(days=2))) ]

        cnt_prev = len(df_prev)
        prev_scaduti = pd.DataFrame()
        if not df_prev.empty:
            df_prev['Data_Creazione'] = pd.to_datetime(df_prev['Data_Creazione'], errors='coerce')
            limite_prev = oggi - timedelta(days=7)
            prev_scaduti = df_prev[df_prev['Data_Creazione'] <= limite_prev]

        low_stock = pd.DataFrame()
        if not df_inv.empty:
            if 'Quantità' in df_inv.columns: df_inv = df_inv.rename(columns={'Quantità': 'Quantita'})
            for c in ['Quantita', 'Soglia_Minima', 'Materiali']:
                if c not in df_inv.columns: df_inv[c] = 0
            low_stock = df_inv[df_inv['Quantita'] <= df_inv['Soglia_Minima']]

        col1, col2, col3, col4, col5 = st.columns(5)
        def draw_kpi(col, icon, num, label, color, filter_key):
            with col:
                st.markdown(f"""<div class="glass-kpi" style="border-bottom: 4px solid {color};"><div class="kpi-icon" style="color:{color};">{icon}</div><div class="kpi-value">{num}</div><div class="kpi-label">{label}</div></div>""", unsafe_allow_html=True)
                if st.button("Vedi Lista", key=f"btn_{filter_key}"): st.session_state.kpi_filter = filter_key

        draw_kpi(col1, "👥", cnt_attivi, "Attivi", "#2ecc71", "Attivi")
        draw_kpi(col2, "📉", len(df_disdetti), "Disdetti", "#e53e3e", "Disdetti")
        draw_kpi(col3, "💡", len(da_richiamare), "Recall", "#ed8936", "Recall")
        draw_kpi(col4, "🩺", len(df_visite), "Visite", "#0bc5ea", "Visite")
        draw_kpi(col5, "💳", cnt_prev, "Preventivi", "#9f7aea", "Preventivi")

        st.write("")
        if st.session_state.kpi_filter != "None":
            st.divider(); c_head, c_close = st.columns([9, 1])
            c_head.subheader(f"📋 Lista: {st.session_state.kpi_filter}")
            if c_close.button("❌"): st.session_state.kpi_filter = "None"; st.rerun()
            df_show = pd.DataFrame()
            if st.session_state.kpi_filter == "Attivi": df_show = df[ (df['Disdetto'] == False) | (df['Disdetto'] == 0) ]
            elif st.session_state.kpi_filter == "Disdetti": df_show = df_disdetti
            elif st.session_state.kpi_filter == "Recall": df_show = da_richiamare
            elif st.session_state.kpi_filter == "Visite": df_show = df_visite
            elif st.session_state.kpi_filter == "Preventivi": df_show = df_prev
            if not df_show.empty: 
                cols_to_show = ['Nome', 'Cognome', 'Area', 'Data_Disdetta', 'Data_Visita']
                if st.session_state.kpi_filter == "Preventivi": cols_to_show = ['Paziente', 'Data_Creazione', 'Totale']
                valid_show = [c for c in cols_to_show if c in df_show.columns]
                st.dataframe(df_show[valid_show], use_container_width=True, height=250)
            else: st.info("Nessun dato.")
            st.divider()

        st.write("")
        st.subheader("🔔 Avvisi e Scadenze")
        
        # 1. Magazzino
        if not low_stock.empty:
            st.caption(f"⚠️ Prodotti in esaurimento: {len(low_stock)}")
            for i, row in low_stock.iterrows():
                c_info, c_btn, c_void = st.columns([3, 1, 1], gap="small")
                with c_info:
                    mat_name = row.get('Materiali', 'Sconosciuto')
                    st.markdown(f"""<div class="alert-row-name border-yellow">{mat_name} (Qta: {row.get('Quantita',0)})</div>""", unsafe_allow_html=True)
                with c_btn:
                    if st.button("🔄 Riordinato", key=f"restock_{row['id']}", type="primary", use_container_width=True):
                        target = int(row.get('Obiettivo', 5))
                        update_generic("Inventario", row['id'], {"Quantità": target})
                        st.rerun()

        # 2. Preventivi
        if not prev_scaduti.empty:
            st.caption(f"⏳ Preventivi > 7gg: {len(prev_scaduti)}")
            for i, row in prev_scaduti.iterrows():
                c_info, c_btn1, c_btn2 = st.columns([3, 1, 1], gap="small")
                with c_info: st.markdown(f"""<div class="alert-row-name border-purple">{row['Paziente']} ({row['Data_Creazione'].strftime('%d/%m')})</div>""", unsafe_allow_html=True)
                with c_btn1:
                    if st.button("📞 Rinnova", key=f"ren_{row['id']}", type="primary", use_container_width=True): update_generic("Preventivi_Salvati", row['id'], {"Data_Creazione": str(date.today())}); st.rerun()
                with c_btn2:
                    if st.button("🗑️ Elimina", key=f"del_prev_{row['id']}", type="secondary", use_container_width=True): delete_generic("Preventivi_Salvati", row['id']); st.rerun()

        # 3. Recall
        if not da_richiamare.empty:
            st.caption(f"📞 Recall Necessari: {len(da_richiamare)}")
            for i, row in da_richiamare.iterrows():
                c_info, c_btn1, c_btn2 = st.columns([3, 1, 1], gap="small")
                with c_info: st.markdown(f"""<div class="alert-row-name border-orange">{row['Nome']} {row['Cognome']}</div>""", unsafe_allow_html=True)
                with c_btn1: 
                    if st.button("✅ Rientrato", key=f"rk_{row['id']}", type="primary", use_container_width=True): update_generic("Pazienti", row['id'], {"Disdetto": False, "Data_Disdetta": None}); st.rerun()
                with c_btn2: 
                    if st.button("📅 Rimandare", key=f"pk_{row['id']}", type="secondary", use_container_width=True): update_generic("Pazienti", row['id'], {"Data_Disdetta": str(date.today())}); st.rerun()
        
        # 4. Visite Post (Blu)
        if not visite_da_reinserire.empty:
            st.caption(f"🛑 Reinserimento Post-Visita: {len(visite_da_reinserire)}")
            for i, row in visite_da_reinserire.iterrows():
                c_info, c_btn1, c_void = st.columns([3, 1, 1], gap="small")
                with c_info: st.markdown(f"""<div class="alert-row-name border-blue">{row['Nome']} {row['Cognome']} (Visitato il {row['Data_Visita'].strftime('%d/%m')})</div>""", unsafe_allow_html=True)
                with c_btn1:
                    if st.button("✅ Rientrato", key=f"vk_{row['id']}", type="primary", use_container_width=True): update_generic("Pazienti", row['id'], {"Visita_Esterna": False, "Data_Visita": None}); st.rerun()
        
        if not visite_settimana.empty:
            st.caption(f"📅 Visite questa settimana: {len(visite_settimana)}")
            for i, row in visite_settimana.iterrows():
                st.markdown(f"""<div class="alert-row-name border-blue" style="justify-content: space-between;"><span>{row['Nome']} {row['Cognome']}</span><span style="color:#0bc5ea; font-size:13px;">{row['Data_Visita'].strftime('%A %d/%m')}</span></div>""", unsafe_allow_html=True)
        
        if da_richiamare.empty and visite_da_reinserire.empty and visite_settimana.empty and prev_scaduti.empty and low_stock.empty: st.success("Tutto tranquillo! Nessun avviso.")
        
        st.divider()

        # GRAFICO
        st.subheader("📈 Performance Aree")
        df_attivi = df[ (df['Disdetto'] == False) | (df['Disdetto'] == 0) ]
        all_areas = []
        if 'Area' in df_attivi.columns:
            for item in df_attivi['Area'].dropna():
                if isinstance(item, list): all_areas.extend(item)
                elif isinstance(item, str): all_areas.extend([p.strip() for p in item.split(',')])
                else: all_areas.append(str(item))
        
        if all_areas:
            counts = pd.Series(all_areas).value_counts().reset_index()
            counts.columns = ['Area', 'Pazienti']
            domain = ["Mano-Polso", "Muscolo-Scheletrico", "Colonna", "ATM", "Gruppi", "Ortopedico"]
            range_ = ["#0bc5ea", "#9f7aea", "#ecc94b", "#2ecc71", "#e53e3e", "#4a5568"]
            chart = alt.Chart(counts).mark_bar(cornerRadius=6, height=35).encode(
                x=alt.X('Pazienti', axis=None), 
                y=alt.Y('Area', sort='-x', title=None, axis=alt.Axis(domain=False, ticks=False, labelColor="#cbd5e0", labelFontSize=14)),
                color=alt.Color('Area', scale=alt.Scale(domain=domain, range=range_), legend=None),
                tooltip=['Area', 'Pazienti']
            ).properties(height=400).configure(background='transparent').configure_view(strokeWidth=0).configure_axis(grid=False)
            st.altair_chart(chart, use_container_width=True, theme=None)
        else: st.info("Dati insufficienti.")

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
            c1.text_input("Nome", key="new_name", placeholder="Es. Mario")
            c2.text_input("Cognome", key="new_surname", placeholder="Es. Rossi")
            c3.multiselect("Area", lista_aree, key="new_area")
            if st.form_submit_button("Salva Paziente", use_container_width=True, type="primary"):
                if st.session_state.new_name and st.session_state.new_surname:
                    save_paziente(st.session_state.new_name, st.session_state.new_surname, ", ".join(st.session_state.new_area), False)
                    st.success("Paziente salvato!"); st.rerun()
    
    st.write(""); df_original = get_data("Pazienti")
    
    if not df_original.empty:
        for c in ['Disdetto', 'Visita_Esterna', 'Dimissione']:
            if c not in df_original.columns: df_original[c] = False
            df_original[c] = df_original[c].fillna(False).infer_objects(copy=False)
        for c in ['Data_Disdetta', 'Data_Visita']:
            if c not in df_original.columns: df_original[c] = None
            df_original[c] = pd.to_datetime(df_original[c], errors='coerce')
        if 'Area' in df_original.columns: df_original['Area'] = df_original['Area'].apply(lambda x: x[0] if isinstance(x, list) and len(x)>0 else (str(x) if x else "")).str.strip() 
        df_original['Area'] = df_original['Area'].astype("category")
        
        col_search, _ = st.columns([1, 2])
        with col_search: search = st.text_input("🔍 Cerca Paziente", placeholder="Digita il cognome...")
        df_filt = df_original[df_original['Cognome'].astype(str).str.contains(search, case=False, na=False)] if search else df_original
        cols_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'Data_Disdetta', 'Visita_Esterna', 'Data_Visita', 'Dimissione', 'id']
        valid_cols = [c for c in cols_show if c in df_filt.columns]
        
        edited = st.data_editor(df_filt[valid_cols], column_config={"Disdetto": st.column_config.CheckboxColumn("Disd.", width="small"), "Data_Disdetta": st.column_config.DateColumn("Data Disd.", format="DD/MM/YYYY"), "Visita_Esterna": st.column_config.CheckboxColumn("Visita Ext.", width="small"), "Data_Visita": st.column_config.DateColumn("Data Visita", format="DD/MM/YYYY"), "Dimissione": st.column_config.CheckboxColumn("🗑️", width="small"), "Area": st.column_config.SelectboxColumn("Area Principale", options=lista_aree), "id": None}, disabled=["Nome", "Cognome"], hide_index=True, use_container_width=True, key="editor_main", num_rows="fixed", height=500)
        
        if st.button("💾 Salva Modifiche Tabella", type="primary", use_container_width=True):
            count_upd = 0; count_del = 0
            for i, row in edited.iterrows():
                rec_id = row['id']
                if row.get('Dimissione') == True: delete_generic("Pazienti", rec_id); count_del += 1; continue
                orig = df_original[df_original['id'] == rec_id].iloc[0]; changes = {}
                if row['Disdetto'] != (orig['Disdetto'] in [True, 1]): changes['Disdetto'] = row['Disdetto']
                if str(row['Data_Disdetta']) != str(orig['Data_Disdetta']): changes['Data_Disdetta'] = row['Data_Disdetta']
                if row['Disdetto'] and (pd.isna(row['Data_Disdetta']) or str(row['Data_Disdetta']) == "NaT"): changes['Data_Disdetta'] = pd.Timestamp.now().normalize()
                if row['Visita_Esterna'] != (orig['Visita_Esterna'] in [True, 1]): changes['Visita_Esterna'] = row['Visita_Esterna']
                if str(row['Data_Visita']) != str(orig['Data_Visita']): changes['Data_Visita'] = row['Data_Visita']
                if row['Area'] != orig['Area']: changes['Area'] = row['Area']
                if changes: update_generic("Pazienti", rec_id, changes); count_upd += 1
            if count_upd > 0 or count_del > 0: get_data.clear(); st.toast("Database aggiornato!", icon="✅"); st.rerun()

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💳 Preventivi":
    st.title("Preventivi & Proposte")
    tab1, tab2 = st.tabs(["📝 Generatore", "📂 Archivio Salvati"])
    df_srv = get_data("Servizi"); df_paz = get_data("Pazienti"); df_std = get_data("Preventivi_Standard")
    with tab1:
        with st.expander("📋 Listino Prezzi", expanded=False):
            if not df_srv.empty and 'Area' in df_srv.columns:
                for i, area in enumerate(df_srv['Area'].unique()):
                    st.markdown(f"**{area}**"); st.caption(", ".join([f"{r['Servizio']} ({r['Prezzo']}€)" for _, r in df_srv[df_srv['Area']==area].iterrows()]))
        with st.container(border=True):
            st.subheader("Creazione Nuovo Preventivo"); selected_services_default = []; default_descrizione = ""
            if not df_std.empty and 'Nome' in df_std.columns:
                scelta_std = st.selectbox("Carica Pacchetto Standard (Opzionale):", ["-- Seleziona --"] + sorted(list(df_std['Nome'].unique())))
                if scelta_std != "-- Seleziona --":
                    row_std = df_std[df_std['Nome'] == scelta_std].iloc[0]; default_descrizione = row_std.get('Descrizione', '')
                    if row_std.get('Contenuto'):
                        for p in row_std['Contenuto'].split(','):
                            if ' x' in p: srv_name, srv_qty = p.split(' x'); selected_services_default.append(srv_name); st.session_state[f"qty_preload_{srv_name}"] = int(srv_qty)
            nomi_pazienti = ["Seleziona..."] + sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows()]) if not df_paz.empty else []
            c_paz, c_serv = st.columns([1, 2])
            paziente_scelto = c_paz.selectbox("Intestato a:", nomi_pazienti)
            listino_dict = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i, r in df_srv.iterrows() if r.get('Servizio')}
            valid_defaults = [s for s in selected_services_default if s in listino_dict]
            servizi_scelti = c_serv.multiselect("Trattamenti:", sorted(list(listino_dict.keys())), default=valid_defaults)
            note_preventivo = st.text_area("Descrizione del Percorso:", value=default_descrizione, height=100)
            
            righe_preventivo = []; totale = 0
            if servizi_scelti:
                st.divider(); st.subheader("Dettaglio Costi")
                for s in servizi_scelti:
                    c1, c2, c3 = st.columns([3, 1, 1]); c1.write(f"**{s}**"); def_qty = st.session_state.get(f"qty_preload_{s}", 1)
                    qty = c2.number_input(f"Q.tà", 1, 50, def_qty, key=f"q_{s}", label_visibility="collapsed")
                    with c3: 
                        costo = listino_dict[s] * qty
                        st.markdown(f"<div style='text-align:right; font-weight:bold'>{costo} €</div>", unsafe_allow_html=True)
                    totale += costo
                    righe_preventivo.append({"nome": s, "qty": qty, "tot": costo})
                st.divider(); c_tot, c_btn = st.columns([2, 1]); c_tot.markdown(f"### TOTALE: {totale} €")
                with c_btn:
                    if st.button("💾 Salva in Archivio", use_container_width=True):
                        if paziente_scelto == "Seleziona...": st.error("Manca il paziente!")
                        else: save_preventivo_temp(paziente_scelto, " | ".join([f"{r['nome']} x{r['qty']} ({r['tot']}€)" for r in righe_preventivo]), totale, note_preventivo); st.success("Salvato!")
                    if st.button("🖨️ Genera Anteprima", type="primary", use_container_width=True):
                        if paziente_scelto == "Seleziona...": st.error("Manca il paziente!")
                        else: st.session_state['show_html_preview'] = True
            if st.session_state.get('show_html_preview'):
                st.divider(); st.subheader("Anteprima")
                html_code = generate_html_preventivo(paziente_scelto, date.today().strftime("%d/%m/%Y"), note_preventivo, righe_preventivo, totale, LOGO_B64)
                components.html(html_code, height=800, scrolling=True)
                if st.button("❌ Chiudi"): st.session_state['show_html_preview'] = False; st.rerun()

    with tab2:
        st.subheader("Archivio Preventivi"); df_prev = get_data("Preventivi_Salvati")
        if not df_prev.empty:
            for i, row in df_prev.iterrows():
                rec_id = row['id']; paz = row.get('Paziente', 'Sconosciuto'); tot = row.get('Totale', 0); dett = str(row.get('Dettagli', '')); note_saved = str(row.get('Note', '')); data_c = row.get('Data_Creazione', '')
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1]); c1.markdown(f"**{paz}** ({data_c})"); c1.caption(f"Tot: {tot} €")
                    righe_pdf = []
                    if dett:
                        for it in dett.split(" | "):
                            try: parts = it.split(" x"); righe_pdf.append({"nome": parts[0], "qty": parts[1].split(" (")[0], "tot": parts[1].split(" (")[1].replace("€)", "")})
                            except: pass
                    if c2.button("🖨️ Stampa", key=f"p_{rec_id}", use_container_width=True):
                        html_archive = generate_html_preventivo(paz, data_c, note_saved, righe_pdf, tot, LOGO_B64, auto_print=True)
                        components.html(html_archive, height=0, width=0, scrolling=False)
                    if c3.button("🗑️ Elimina", key=f"d_{rec_id}", use_container_width=True): delete_generic("Preventivi_Salvati", rec_id); st.rerun()
        else: st.info("Archivio vuoto.")

# =========================================================
# SEZIONE NUOVA: CONSEGNE
# =========================================================
elif menu == "📨 Consegne":
    st.title("📨 Consegne Pazienti")
    df_cons = get_data("Consegne"); df_paz = get_data("Pazienti")
    nomi_paz = ["-- Seleziona --"] + sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows()]) if not df_paz.empty else []
    
    with st.expander("➕ Nuova Consegna", expanded=True):
        with st.form("new_cons"):
            c1, c2 = st.columns(2)
            paz = c1.selectbox("Paziente", nomi_paz)
            area = c2.selectbox("Area Competenza", ["Mano-Polso", "Colonna", "Sport", "Altro"])
            ind = st.text_input("Cosa consegnare? (es. Referto, Scheda Esercizi)")
            scad = st.date_input("Entro quando?", date.today() + timedelta(days=3))
            if st.form_submit_button("Salva Promemoria"):
                if paz != "-- Seleziona --" and ind:
                    save_consegna(paz, area, ind, scad); st.success("Salvato!"); st.rerun()
                else: st.error("Compila i campi.")

    st.write(""); tabs = st.tabs(["Mano-Polso", "Colonna", "Sport", "Altro"])
    if not df_cons.empty:
        if 'Data_Scadenza' in df_cons.columns: df_cons['Data_Scadenza'] = pd.to_datetime(df_cons['Data_Scadenza']).dt.date
        if 'Completato' not in df_cons.columns: df_cons['Completato'] = False
        mapping = ["Mano-Polso", "Colonna", "Sport", "Altro"]
        for i, tab_name in enumerate(mapping):
            with tabs[i]:
                items = df_cons[ (df_cons['Area'] == tab_name) & (df_cons['Completato'] != True) ]
                if items.empty: st.info("Nessuna consegna in attesa.")
                else:
                    for _, row in items.iterrows():
                        delta = (row['Data_Scadenza'] - date.today()).days
                        color = "border-green" if delta > 3 else "border-yellow" if delta >= 0 else "border-red"
                        status_text = f"Scade tra {delta} gg" if delta >= 0 else f"SCADUTO da {abs(delta)} gg"
                        c_chk, c_info, c_date = st.columns([1, 6, 2])
                        with c_chk:
                            if st.button("✅", key=f"ok_{row['id']}"):
                                update_generic("Consegne", row['id'], {"Completato": True}); st.rerun()
                        with c_info:
                            st.markdown(f"""<div class="alert-row-name {color}"><b>{row['Paziente']}</b>: {row['Indicazione']}</div>""", unsafe_allow_html=True)
                        with c_date:
                            st.caption(f"{row['Data_Scadenza'].strftime('%d/%m')}\n({status_text})")

# =========================================================
# SEZIONE 4: MAGAZZINO (RIFATTA: COMPATTA E FUNZIONANTE)
# =========================================================
elif menu == "📦 Magazzino":
    st.title("Magazzino & Materiali")
    STANZE = ["Segreteria", "Mano", "Stanze", "Medicinali", "Pulizie"]
    col_add, col_view = st.columns([1, 2])
    
    with col_add:
        with st.container(border=True):
            st.subheader("Nuovo Articolo")
            with st.form("add_inv"):
                new_mat = st.text_input("Nome Materiale")
                new_area = st.selectbox("Area/Stanza", STANZE)
                c_q1, c_q2, c_q3 = st.columns(3)
                qty_now = c_q1.number_input("Q.tà Attuale", 0, 1000, 1)
                qty_target = c_q2.number_input("Obiettivo", 1, 1000, 5)
                qty_min = c_q3.number_input("Soglia Minima", 0, 100, 2)
                if st.form_submit_button("Aggiungi", use_container_width=True, type="primary"):
                    if new_mat:
                        save_materiale_avanzato(new_mat, new_area, qty_now, qty_target, qty_min)
                        st.success("Aggiunto!"); st.rerun()

    with col_view:
        df_inv = get_data("Inventario")
        if not df_inv.empty:
            if 'Quantità' in df_inv.columns: df_inv = df_inv.rename(columns={'Quantità': 'Quantita'})
            for c in ['Quantita', 'Soglia_Minima', 'Materiali', 'Obiettivo']:
                if c not in df_inv.columns: df_inv[c] = 0
            df_inv['Quantita'] = df_inv['Quantita'].fillna(0).astype(int)
            
            tabs = st.tabs(STANZE)
            for i, stanza in enumerate(STANZE):
                with tabs[i]:
                    items = df_inv[df_inv['Area'] == stanza]
                    if items.empty: st.caption("Nessun articolo.")
                    else:
                        for _, row in items.iterrows():
                            is_low = row['Quantita'] <= row['Soglia_Minima']
                            with st.container(border=True):
                                st.markdown('<style>div[data-testid="stVerticalBlockBorderWrapper"] {padding: 8px 15px !important; margin-bottom: 5px !important;}</style>', unsafe_allow_html=True)
                                c_info, c_stat, c_act = st.columns([3, 2, 1], gap="small")
                                with c_info:
                                    mat_name = row.get('Materiali', 'Senza Nome')
                                    st.markdown(f"**{mat_name}**")
                                    if is_low: st.caption(":red[⚠️ BASSO]")
                                    else: st.caption(":green[OK]")
                                with c_stat:
                                    val = min(row['Quantita'] / max(row['Obiettivo'], 1), 1.0)
                                    st.progress(val)
                                    st.caption(f"**{row['Quantita']}** / {row['Obiettivo']}")
                                with c_act:
                                    st.write("") 
                                    if st.button("🔻1", key=f"dec_{row['id']}", type="primary" if is_low else "secondary"):
                                        if row['Quantita'] > 0:
                                            new_qty = int(row['Quantita'] - 1)
                                            update_generic("Inventario", row['id'], {"Quantità": new_qty})
                                            st.rerun()
        else: st.info("Magazzino vuoto.")

# =========================================================
# SEZIONE 5: PRESTITI
# =========================================================
elif menu == "🔄 Prestiti":
    st.title("Registro Prestiti")
    df_paz = get_data("Pazienti"); df_inv = get_data("Inventario")
    with st.expander("➕ Registra Prestito"):
        with st.form("fp"):
            c1, c2 = st.columns(2); pz = c1.selectbox("Chi?", sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows()]) if not df_paz.empty else []); pr = c2.selectbox("Cosa?", sorted([r['Materiali'] for i, r in df_inv.iterrows() if r.get('Materiali')]) if not df_inv.empty else [])
            if st.form_submit_button("Salva"): save_prestito(pz, pr, date.today()); st.rerun()
    df_pres = get_data("Prestiti")
    if not df_pres.empty:
        df_pres['Restituito'] = df_pres.get('Restituito', False).fillna(False)
        act = df_pres[df_pres['Restituito'] != True]
        if not act.empty:
            ed = st.data_editor(act[['Paziente', 'Oggetto', 'Data_Prestito', 'Restituito', 'id']], column_config={"id": None}, hide_index=True)
            if st.button("Conferma Resi"):
                for i, r in ed.iterrows():
                    if r['Restituito']: update_generic("Prestiti", r['id'], {"Restituito": True})
                st.rerun()

# =========================================================
# SEZIONE 6: SCADENZE
# =========================================================
elif menu == "📅 Scadenze":
    st.title("Checklist Scadenze")
    df_scad = get_data("Scadenze")
    if not df_scad.empty and 'Data_Scadenza' in df_scad.columns:
        df_scad['Data_Scadenza'] = pd.to_datetime(df_scad['Data_Scadenza'], errors='coerce'); df_scad = df_scad.sort_values("Data_Scadenza")
        st.dataframe(df_scad, column_config={"Data_Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"), "Importo": st.column_config.NumberColumn("Importo", format="%d €"), "Descrizione": st.column_config.TextColumn("Dettagli")}, use_container_width=True, height=500)
    else: st.info("Nessuna scadenza prossima.")
        
