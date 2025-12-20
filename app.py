import streamlit as st
from pyairtable import Api
import pandas as pd
from requests.exceptions import HTTPError
import altair as alt
from datetime import date, timedelta
from fpdf import FPDF
import io
import os

# =========================================================
# 0. CONFIGURAZIONE & GLASS DESIGN (V22 CUSTOM)
# =========================================================
st.set_page_config(page_title="Gestionale Fisio Pro", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    :root {
        --glass-bg: rgba(255, 255, 255, 0.05);
        --glass-border: 1px solid rgba(255, 255, 255, 0.1);
        --neon-blue: #4299e1;
    }

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* SFONDO GLOBALE (V22) */
    .stApp {
        background: radial-gradient(circle at top left, #1a202c, #0d1117);
        color: #e2e8f0;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95);
        backdrop-filter: blur(12px);
        border-right: var(--glass-border);
    }
    
    /* TITOLI */
    h1 {
        background: linear-gradient(90deg, #FFF, #cbd5e0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    h2, h3, h4 { color: #FFF !important; font-weight: 600; }

    /* --- CARD KPI CLICCABILI (PULSANTI GRANDI) --- */
    div[data-testid="column"] button {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border: var(--glass-border);
        border-radius: 16px;
        padding: 25px 10px; /* Spazio interno aumentato */
        height: auto;
        width: 100%;
        text-align: center;
        transition: all 0.2s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    div[data-testid="column"] button:hover {
        background: rgba(255, 255, 255, 0.1);
        transform: translateY(-4px);
        border-color: rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 25px rgba(66, 153, 225, 0.15);
    }
    
    /* Stile del testo dentro il bottone (Icona + Numero) */
    div[data-testid="column"] button p {
        font-size: 28px !important; /* ICONA E NUMERO GRANDI */
        font-weight: 700;
        line-height: 1.5;
        margin: 0;
        color: #FFFFFF;
    }

    /* --- PULSANTI AZIONE (PICCOLI NEGLI ALERT) --- */
    div.stButton > button {
        background: linear-gradient(135deg, #3182ce, #2b6cb0);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    div.stButton > button:hover {
        box-shadow: 0 0 15px rgba(66, 153, 225, 0.5);
        transform: scale(1.02);
    }
    /* Pulsanti specifici dentro le colonne (Rientrato, Fatto) */
    div[data-testid="column"] div.stButton > button {
        width: 100%;
        padding: 0.4rem;
        font-size: 0.9rem !important;
    }

    /* --- TABELLE TRASPARENTI --- */
    div[data-testid="stDataFrame"] {
        background-color: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
    }
    div[data-testid="stDataFrame"] div[data-testid="stTable"] {
        background-color: transparent !important;
    }

    /* --- NAVIGAZIONE --- */
    div.row-widget.stRadio > div { background-color: transparent; }
    div.row-widget.stRadio > div[role="radiogroup"] > label {
        background-color: transparent;
        padding: 10px 15px;
        margin-bottom: 5px;
        border-radius: 10px;
        color: #94a3b8;
        border: 1px solid transparent;
        transition: all 0.2s;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
        color: #fff;
        background: rgba(255,255,255,0.03);
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background: rgba(66, 153, 225, 0.15);
        border: 1px solid var(--neon-blue);
        color: #fff;
        font-weight: 600;
    }
    div.row-widget.stRadio div[role="radiogroup"] > label > div:first-child { display: none; }

    /* INPUT & ALERT CONTAINER */
    input, select, textarea {
        background-color: rgba(13, 17, 23, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: white !important;
        border-radius: 8px;
    }
    .streamlit-expanderHeader {
        background-color: rgba(255,255,255,0.02);
        border-radius: 8px;
        color: white;
    }
    hr { border-color: rgba(255,255,255,0.1); opacity: 0.5; }
    
    /* Contenitori per le liste azioni (Alert) */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.08);
    }
    
    /* Titoli alert */
    .alert-title { font-weight: bold; margin-bottom: 5px; display: block; }
    .alert-info { color: #38b2ac; }
    .alert-warn { color: #ed8936; }
    .alert-err { color: #e53e3e; }

</style>
""", unsafe_allow_html=True)

# --- 1. CONFIGURAZIONE CONNESSIONE ---
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    API_KEY = "tua_chiave"
    BASE_ID = "tuo_base_id"

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
    except Exception: return pd.DataFrame()

def save_paziente(nome, cognome, area, disdetto):
    table = api.table(BASE_ID, "Pazienti")
    record = {"Nome": nome, "Cognome": cognome, "Area": area, "Disdetto": disdetto}
    get_data.clear()
    table.create(record, typecast=True)

def update_generic(table_name, record_id, dati_aggiornati):
    table = api.table(BASE_ID, table_name)
    fields_to_send = {}
    for k, v in dati_aggiornati.items():
        if "Data" in k: 
            if pd.isna(v) or str(v) == "NaT" or v == "": fields_to_send[k] = None
            else: fields_to_send[k] = v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else str(v)
        else: fields_to_send[k] = v
    table.update(record_id, fields_to_send, typecast=True)

def delete_generic(table_name, record_id):
    table = api.table(BASE_ID, table_name)
    table.delete(record_id)
    get_data.clear()

def save_prestito(paziente, oggetto, data_prestito):
    table = api.table(BASE_ID, "Prestiti")
    data_str = data_prestito.strftime('%Y-%m-%d') if hasattr(data_prestito, 'strftime') else str(data_prestito)
    record = {"Paziente": paziente, "Oggetto": oggetto, "Data_Prestito": data_str, "Restituito": False}
    get_data.clear()
    table.create(record, typecast=True)

def save_prodotto(prodotto, quantita):
    table = api.table(BASE_ID, "Inventario")
    record = {"Prodotto": prodotto, "Quantita": quantita}
    get_data.clear()
    table.create(record, typecast=True)

def save_preventivo_temp(paziente, dettagli_str, totale, note):
    table = api.table(BASE_ID, "Preventivi_Salvati")
    record = {
        "Paziente": paziente, 
        "Dettagli": dettagli_str, 
        "Totale": totale, 
        "Note": note, 
        "Data_Creazione": str(date.today())
    }
    get_data.clear()
    table.create(record, typecast=True)

def create_pdf(paziente, righe_preventivo, totale, note=""):
    euro = chr(128)
    class PDF(FPDF):
        def header(self):
            if os.path.exists("logo.png"):
                try: self.image('logo.png', 75, 10, 60)
                except: pass
            self.set_y(32)
            self.set_font('Arial', 'B', 12)
            self.set_text_color(80, 80, 80)
            self.cell(0, 10, 'PREVENTIVO PERCORSO RIABILITATIVO', 0, 1, 'C')
            self.set_draw_color(200, 200, 200)
            self.line(20, self.get_y(), 190, self.get_y())
            self.ln(8)
        def footer(self):
            self.set_y(-15); self.set_font('Arial', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_text_color(0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(95, 8, f'Paziente: {paziente}', 0, 0, 'L')
    pdf.set_font('Arial', '', 12)
    pdf.cell(95, 8, f'Data: {date.today().strftime("%d/%m/%Y")}', 0, 1, 'R')
    pdf.ln(8)
    
    if note and len(note) > 5:
        pdf.set_font('Arial', 'BI', 11)
        pdf.cell(0, 8, 'Obiettivi e Descrizione del Percorso:', 0, 1)
        pdf.set_font('Arial', 'I', 11)
        pdf.set_text_color(60, 60, 60)
        clean_note = note.replace("€", euro).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, clean_note)
        pdf.ln(10)
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(110, 10, ' Trattamento', 0, 0, 'L', 1) 
    pdf.cell(30, 10, 'Q.ta', 0, 0, 'C', 1)
    pdf.cell(50, 10, 'Importo ', 0, 1, 'R', 1)
    
    pdf.set_text_color(0); pdf.set_font('Arial', '', 11)
    for riga in righe_preventivo:
        nome = str(riga.get('nome', '-'))[:55]
        qty = str(riga.get('qty', '0'))
        tot_riga = str(riga.get('tot', '0'))
        pdf.cell(110, 10, f" {nome}", 'B') 
        pdf.cell(30, 10, qty, 'B', 0, 'C')
        pdf.cell(50, 10, f"{tot_riga} {euro} ", 'B', 1, 'R')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(140, 12, 'TOTALE COMPLESSIVO:', 0, 0, 'R')
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(50, 12, f'{totale} {euro}', 1, 1, 'R', 1)
    pdf.ln(10)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, 'PIANO DI PAGAMENTO CONCORDATO:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.set_draw_color(180, 180, 180)
    pdf.cell(15, 8, f'1) {euro}', 0, 0); pdf.cell(40, 8, '______________', 0, 0)
    pdf.cell(20, 8, ' entro il', 0, 0); pdf.cell(40, 8, '______________', 0, 1)
    pdf.cell(15, 8, f'2) {euro}', 0, 0); pdf.cell(40, 8, '______________', 0, 0)
    pdf.cell(20, 8, ' entro il', 0, 0); pdf.cell(40, 8, '______________', 0, 1)
    pdf.cell(15, 8, f'3) {euro}', 0, 0); pdf.cell(40, 8, '______________', 0, 0)
    pdf.cell(20, 8, ' entro il', 0, 0); pdf.cell(40, 8, '______________', 0, 1)
    pdf.ln(15)

    y_pos = pdf.get_y()
    pdf.set_font('Arial', '', 11)
    pdf.set_xy(110, y_pos)
    pdf.cell(80, 6, 'Firma per accettazione:', 0, 1, 'L')
    pdf.set_xy(110, y_pos + 15)
    pdf.cell(80, 0, '', 'T')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. INTERFACCIA GRAFICA ---

with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.title("Focus Rehab")
    st.write("")
    menu = st.radio(
        "Menu", 
        ["⚡ Dashboard", "👥 Pazienti", "💳 Preventivi", "📦 Magazzino", "🔄 Prestiti", "📅 Scadenze"],
        label_visibility="collapsed"
    )
    st.divider()
    st.caption("Focus App v3.7")

# =========================================================
# SEZIONE 1: DASHBOARD (Clickable Version)
# =========================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")

    # 1. CSS SPECIALE PER TRASFORMARE I BOTTONI IN CARD
    # Questo CSS rende i bottoni della dashboard alti, scuri e con bordo, simili alle tue card precedenti.
    st.markdown("""
    <style>
    div[data-testid="column"] button {
        height: 100px;
        width: 100%;
        border-radius: 12px;
        border: 1px solid #252525;
        background-color: #121212;
        color: #FAFAFA;
        transition: all 0.3s ease;
    }
    div[data-testid="column"] button:hover {
        border-color: #FF4B2B;
        background-color: #1A1A1A;
        transform: translateY(-2px);
    }
    div[data-testid="column"] button p {
        font-size: 18px !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 2. GESTIONE STATO (Memoria di cosa stai guardando)
    if 'dash_view' not in st.session_state:
        st.session_state['dash_view'] = 'main' # stati possibili: main, attivi, disdetti, recall, visite

    # Pulsante per tornare indietro (appare solo se stai guardando una lista)
    if st.session_state['dash_view'] != 'main':
        if st.button("🔙 Torna alla Panoramica", type="secondary"):
            st.session_state['dash_view'] = 'main'
            st.rerun()
        st.divider()

    # 3. PREPARAZIONE DATI
    df = get_data("Pazienti")
    
    if not df.empty:
        # Pulizia dati (identica a prima)
        for col in ['Disdetto', 'Visita_Esterna']:
            if col not in df.columns: df[col] = False
            df[col] = df[col].fillna(False)
        for col in ['Data_Disdetta', 'Data_Visita']:
            if col not in df.columns: df[col] = None
            df[col] = pd.to_datetime(df[col], errors='coerce')
        if 'Area' not in df.columns: df['Area'] = None

        # Calcoli contatori
        df_disdetti = df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) ]
        df_attivi = df[ (df['Disdetto'] == False) | (df['Disdetto'] == 0) ]
        
        oggi = pd.Timestamp.now().normalize()
        limite_recall = oggi - pd.Timedelta(days=10)
        da_richiamare = df_disdetti[ (df_disdetti['Data_Disdetta'].notna()) & (df_disdetti['Data_Disdetta'] <= limite_recall) ]
        
        df_visite = df[ (df['Visita_Esterna'] == True) | (df['Visita_Esterna'] == 1) ]
        domani = oggi + pd.Timedelta(days=1)
        visite_imminenti = df_visite[ (df_visite['Data_Visita'].notna()) & (df_visite['Data_Visita'] >= oggi) & (df_visite['Data_Visita'] <= domani) ]
        visite_passate = df_visite[ (df_visite['Data_Visita'].notna()) & (df_visite['Data_Visita'] <= (oggi - pd.Timedelta(days=7))) ]

        # 4. LE 4 CARD CLICCABILI (Usiamo st.button mascherati da card)
        # Nota: Se siamo in una vista specifica, evidenziamo quella selezione (opzionale), qui li lascio sempre cliccabili
        
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            # Uso le emoji per mantenere il colore visivo (Streamlit button supporta solo testo)
            label_attivi = f"👥  {len(df_attivi)}\nPazienti Attivi"
            if st.button(label_attivi, key="btn_attivi"):
                st.session_state['dash_view'] = 'attivi'
                st.rerun()

        with c2:
            label_disdetti = f"📉  {len(df_disdetti)}\nDisdetti Tot."
            if st.button(label_disdetti, key="btn_disdetti"):
                st.session_state['dash_view'] = 'disdetti'
                st.rerun()

        with c3:
            label_recall = f"📞  {len(da_richiamare)}\nRecall (>10gg)"
            if st.button(label_recall, key="btn_recall"):
                st.session_state['dash_view'] = 'recall'
                st.rerun()
                
        with c4:
            label_visite = f"🩺  {len(visite_imminenti)}\nVisite Imminenti"
            if st.button(label_visite, key="btn_visite"):
                st.session_state['dash_view'] = 'visite'
                st.rerun()

        st.write("")

        # 5. LOGICA DI VISUALIZZAZIONE: COSA MOSTRO SOTTO?
        
        # CASO A: VISTA DASHBOARD NORMALE (Grafici e Avvisi)
        if st.session_state['dash_view'] == 'main':
            
            c_left, c_right = st.columns([1, 1.5], gap="large")

            with c_left:
                st.markdown("### 🔔 Avvisi Rapidi")
                # Visite Imminenti
                if not visite_imminenti.empty:
                    with st.container(border=True):
                        st.markdown(f"<div style='color:#A3CB38; font-weight:bold'>👨‍⚕️ Visite Oggi/Domani</div>", unsafe_allow_html=True)
                        for i, row in visite_imminenti.iterrows():
                            st.caption(f"**{row['Nome']} {row['Cognome']}** ({row['Data_Visita'].strftime('%d/%m')})")
                
                # Visite Passate (da far rientrare)
                if not visite_passate.empty:
                    with st.container(border=True):
                        st.markdown(f"<div style='color:#FF6B6B; font-weight:bold'>⚠️ Visite Passate (Da chiudere)</div>", unsafe_allow_html=True)
                        for i, row in visite_passate.iterrows():
                            rec_id = row['id']
                            cc1, cc2 = st.columns([3, 1])
                            cc1.caption(f"{row['Nome']} {row['Cognome']}")
                            if cc2.button("Rientrato", key=f"rientro_{rec_id}"):
                                update_generic("Pazienti", rec_id, {"Visita_Esterna": False, "Data_Visita": None})
                                st.rerun()
                
                if visite_imminenti.empty and visite_passate.empty:
                    st.success("Nessun avviso urgente.")

            with c_right:
                st.markdown("### 📈 Statistiche Aree")
                # Grafico Altair
                all_areas = []
                if 'Area' in df_attivi.columns:
                    for item in df_attivi['Area'].dropna():
                        if isinstance(item, list): all_areas.extend(item)
                        elif isinstance(item, str): all_areas.extend([p.strip() for p in item.split(',')])
                        else: all_areas.append(str(item))
                
                if all_areas:
                    counts = pd.Series(all_areas).value_counts().reset_index()
                    counts.columns = ['Area', 'Pazienti']
                    domain = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
                    range_ = ["#33A1C9", "#F1C40F", "#2ECC71", "#9B59B6", "#E74C3C", "#7F8C8D"]
                    
                    chart = alt.Chart(counts).mark_bar(cornerRadius=4, height=20).encode(
                        x=alt.X('Pazienti', axis=None), 
                        y=alt.Y('Area', sort='-x', title=None, axis=alt.Axis(domain=False, ticks=False, labelColor="#CCC")),
                        color=alt.Color('Area', scale=alt.Scale(domain=domain, range=range_), legend=None),
                        tooltip=['Area', 'Pazienti']
                    ).properties(height=300).configure_view(strokeWidth=0)
                    st.altair_chart(chart, use_container_width=True)

        # CASO B: HAI CLICCATO UNA CARD (Mostro la tabella dettagliata)
        else:
            df_show = pd.DataFrame()
            cols_to_show = ['Nome', 'Cognome', 'Area']
            
            if st.session_state['dash_view'] == 'attivi':
                st.subheader("👥 Lista Pazienti Attivi")
                df_show = df_attivi
            
            elif st.session_state['dash_view'] == 'disdetti':
                st.subheader("📉 Lista Pazienti Disdetti")
                df_show = df_disdetti
                cols_to_show.append('Data_Disdetta')
            
            elif st.session_state['dash_view'] == 'recall':
                st.subheader("📞 Lista Recall (Disdetti > 10gg)")
                df_show = da_richiamare
                cols_to_show.append('Data_Disdetta')
            
            elif st.session_state['dash_view'] == 'visite':
                st.subheader("🩺 Lista Visite Imminenti")
                df_show = visite_imminenti
                cols_to_show.append('Data_Visita')

            if not df_show.empty:
                # Mostra tabella pulita
                valid_cols = [c for c in cols_to_show if c in df_show.columns]
                st.dataframe(
                    df_show[valid_cols], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "Data_Disdetta": st.column_config.DateColumn("Disdetta il", format="DD/MM/YYYY"),
                        "Data_Visita": st.column_config.DateColumn("Visita il", format="DD/MM/YYYY")
                    }
                )
            else:
                st.info("Nessun paziente in questa categoria.")
# =========================================================
# SEZIONE 2: PAZIENTI
# =========================================================
elif menu == "👥 Pazienti":
    st.title("📂 Anagrafica Pazienti")
    lista_aree = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
    
    with st.container(border=True):
        st.subheader("➕ Nuovo Paziente")
        with st.form("form_paziente", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.text_input("Nome", key="new_name")
            c2.text_input("Cognome", key="new_surname")
            c3.multiselect("Area", lista_aree, key="new_area")
            if st.form_submit_button("Salva Paziente", use_container_width=True):
                if st.session_state.new_name and st.session_state.new_surname:
                    area_s = ", ".join(st.session_state.new_area)
                    save_paziente(st.session_state.new_name, st.session_state.new_surname, area_s, False)
                    st.success("Salvato!"); st.rerun()
    
    st.write("")
    df_original = get_data("Pazienti")
    
    if not df_original.empty:
        for c in ['Disdetto', 'Visita_Esterna', 'Dimissione']:
            if c not in df_original.columns: df_original[c] = False
            df_original[c] = df_original[c].fillna(False).infer_objects(copy=False)
        for c in ['Data_Disdetta', 'Data_Visita']:
            if c not in df_original.columns: df_original[c] = None
            df_original[c] = pd.to_datetime(df_original[c], errors='coerce')
        if 'Area' in df_original.columns:
             df_original['Area'] = df_original['Area'].apply(lambda x: x[0] if isinstance(x, list) and len(x)>0 else (str(x) if x else "")).str.strip() 
        df_original['Area'] = df_original['Area'].astype("category")

        col_search, _ = st.columns([1, 2])
        with col_search: search = st.text_input("🔍 Cerca...", placeholder="Cognome...")
        df_filt = df_original[df_original['Cognome'].astype(str).str.contains(search, case=False, na=False)] if search else df_original

        cols_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'Data_Disdetta', 'Visita_Esterna', 'Data_Visita', 'Dimissione', 'id']
        valid_cols = [c for c in cols_show if c in df_filt.columns]

        edited = st.data_editor(
            df_filt[valid_cols],
            column_config={
                "Disdetto": st.column_config.CheckboxColumn("Disdetto", width="small"),
                "Data_Disdetta": st.column_config.DateColumn("Data Disd.", format="DD/MM/YYYY"),
                "Visita_Esterna": st.column_config.CheckboxColumn("Visita Ext.", width="small"),
                "Data_Visita": st.column_config.DateColumn("Data Visita", format="DD/MM/YYYY"),
                "Dimissione": st.column_config.CheckboxColumn("🗑️", help="Elimina"),
                "Area": st.column_config.SelectboxColumn("Area", options=lista_aree),
                "id": None
            },
            disabled=["Nome", "Cognome"], hide_index=True, use_container_width=True, key="editor_main", num_rows="fixed"
        )

        if st.button("💾 Salva Modifiche", type="primary"):
            count_upd = 0; count_del = 0
            for i, row in edited.iterrows():
                rec_id = row['id']
                if row.get('Dimissione') == True:
                    delete_generic("Pazienti", rec_id); count_del += 1; continue

                orig = df_original[df_original['id'] == rec_id].iloc[0]
                changes = {}
                
                if row['Disdetto'] != (orig['Disdetto'] in [True, 1]): changes['Disdetto'] = row['Disdetto']
                d_dis = row['Data_Disdetta']
                if row['Disdetto'] and (pd.isna(d_dis) or str(d_dis) == "NaT"): 
                    d_dis = pd.Timestamp.now().normalize(); changes['Data_Disdetta'] = d_dis
                elif str(d_dis) != str(orig['Data_Disdetta']): changes['Data_Disdetta'] = d_dis

                if row['Visita_Esterna'] != (orig['Visita_Esterna'] in [True, 1]): changes['Visita_Esterna'] = row['Visita_Esterna']
                if str(row['Data_Visita']) != str(orig['Data_Visita']): changes['Data_Visita'] = row['Data_Visita']
                if row['Area'] != orig['Area']: changes['Area'] = row['Area']

                if changes: update_generic("Pazienti", rec_id, changes); count_upd += 1

            if count_upd > 0 or count_del > 0:
                get_data.clear(); st.toast("Aggiornato!", icon="✅"); st.rerun()

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💳 Preventivi":
    st.title("💳 Preventivi & Proposte")
    tab1, tab2 = st.tabs(["📝 Generatore", "📂 Archivio"])
    df_srv = get_data("Servizi")
    df_paz = get_data("Pazienti")
    df_std = get_data("Preventivi_Standard")

    with tab1:
        with st.expander("📋 Vedi Listino Prezzi", expanded=False):
            if not df_srv.empty and 'Area' in df_srv.columns:
                aree_uniche = df_srv['Area'].dropna().unique(); cols = st.columns(3)
                for i, area in enumerate(aree_uniche):
                    with cols[i % 3]:
                        st.markdown(f"**📍 {area}**")
                        items = df_srv[df_srv['Area'] == area]
                        for _, r in items.iterrows(): prz = f"{r['Prezzo']}€" if 'Prezzo' in r else "-"; st.caption(f"{r['Servizio']}: **{prz}**")
            else: st.warning("Configura la colonna 'Area' in Servizi.")

        with st.container(border=True):
            st.subheader("Nuovo Preventivo")
            selected_services_default = []
            default_descrizione = "" 
            
            if not df_std.empty and 'Nome' in df_std.columns:
                c_filtro, c_pack = st.columns(2)
                with c_filtro:
                    if 'Area' in df_std.columns:
                        aree_std = ["Tutte"] + sorted(list(df_std['Area'].astype(str).unique()))
                        filtro_area = st.selectbox("Filtra Area Pacchetti:", aree_std)
                        df_std_filt = df_std[df_std['Area'].astype(str) == filtro_area] if filtro_area != "Tutte" else df_std
                    else: df_std_filt = df_std
                with c_pack:
                    opt_std = ["-- Seleziona --"] + sorted(list(df_std_filt['Nome'].unique()))
                    scelta_std = st.selectbox("Carica Pacchetto Standard:", opt_std)
                
                if scelta_std != "-- Seleziona --":
                    row_std = df_std_filt[df_std_filt['Nome'] == scelta_std].iloc[0]
                    content = row_std.get('Contenuto', '')
                    default_descrizione = row_std.get('Descrizione', '')
                    if pd.isna(default_descrizione): default_descrizione = ""
                    
                    if content:
                        parts = [x.strip() for x in content.split(',')]
                        for p in parts:
                            if ' x' in p:
                                srv_name, srv_qty = p.split(' x')
                                selected_services_default.append(srv_name)
                                st.session_state[f"qty_preload_{srv_name}"] = int(srv_qty)
            st.divider()

            nomi_pazienti = ["Nuovo Paziente"]
            if not df_paz.empty:
                nomi_pazienti += sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows() if r.get('Cognome')])
            
            col_paz, col_serv = st.columns([1, 2])
            with col_paz: paziente_scelto = st.selectbox("Intestato a:", nomi_pazienti)
            
            listino_dict = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i, r in df_srv.iterrows() if r.get('Servizio')}
            valid_defaults = [s for s in selected_services_default if s in listino_dict]
            
            with col_serv:
                servizi_scelti = st.multiselect("Trattamenti:", sorted(list(listino_dict.keys())), default=valid_defaults)

            st.markdown("**Descrizione del Percorso / Obiettivi** (Appare nel PDF)")
            note_preventivo = st.text_area("Scrivi qui i dettagli del percorso...", value=default_descrizione, height=100)
            
            righe_preventivo = []
            totale = 0

            if servizi_scelti:
                st.divider()
                st.markdown("### Dettaglio Costi")
                for s in servizi_scelti:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1: st.write(f"**{s}**")
                    def_qty = st.session_state.get(f"qty_preload_{s}", 1)
                    with c2: qty = st.number_input(f"Q.tà", 1, 50, def_qty, key=f"q_{s}", label_visibility="collapsed")
                    with c3: 
                        costo = listino_dict[s] * qty
                        st.markdown(f"**{costo} €**")
                    totale += costo
                    righe_preventivo.append({"nome": s, "qty": qty, "tot": costo})
                
                st.divider()
                col_tot, col_btn = st.columns([2, 1])
                with col_tot: st.metric("TOTALE PREVENTIVO", f"{totale} €")
                with col_btn:
                    st.write("") 
                    if st.button("💾 Salva e Genera", type="primary", use_container_width=True):
                        dettagli_str = " | ".join([f"{r['nome']} x{r['qty']} ({r['tot']}€)" for r in righe_preventivo])
                        save_preventivo_temp(paziente_scelto, dettagli_str, totale, note_preventivo)
                        st.balloons()
                        for k in list(st.session_state.keys()):
                            if k.startswith("qty_preload_"): del st.session_state[k]
                        st.success("Salvato!")

    with tab2:
        st.markdown("### 🗂 Preventivi in attesa")
        df_prev = get_data("Preventivi_Salvati")
        if not df_prev.empty:
            for i, row in df_prev.iterrows():
                rec_id = row['id']
                paz = row.get('Paziente', 'Sconosciuto')
                dett = str(row.get('Dettagli', '')) if not pd.isna(row.get('Dettagli')) else ""
                note_saved = str(row.get('Note', '')) if not pd.isna(row.get('Note')) else ""
                tot = row.get('Totale', 0)
                data_c = row.get('Data_Creazione', '')

                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**{paz}**"); st.caption(f"Emesso: {data_c} • Tot: **{tot} €**")
                    with c2:
                        righe_pdf = []
                        if dett:
                            items = dett.split(" | ")
                            for it in items:
                                try:
                                    parts = it.split(" x")
                                    nome = parts[0]; rest = parts[1].split(" ("); qty = rest[0]; prz = rest[1].replace("€)", "")
                                    righe_pdf.append({"nome": nome, "qty": qty, "tot": prz})
                                except: righe_pdf.append({"nome": it, "qty": "-", "tot": "-"})
                        pdf_bytes = create_pdf(paz, righe_pdf, tot, note_saved)
                        st.download_button("📄 PDF", data=pdf_bytes, file_name=f"Prev_{paz}.pdf", mime="application/pdf", key=f"pdf_{rec_id}", use_container_width=True)
                    with c3:
                        if st.button("✅ Ok", key=f"conf_{rec_id}", use_container_width=True):
                            delete_generic("Preventivi_Salvati", rec_id); st.rerun()
        else: st.info("Nessun preventivo salvato.")

# =========================================================
# SEZIONE 4: INVENTARIO
# =========================================================
elif menu == "📦 Magazzino":
    st.title("📦 Magazzino")
    col_add, col_tab = st.columns([1, 2])
    with col_add:
        with st.container(border=True):
            st.subheader("Nuovo Prodotto")
            with st.form("add_prod"):
                new_prod = st.text_input("Nome"); new_qty = st.number_input("Quantità", 0, 1000, 1)
                if st.form_submit_button("Aggiungi", use_container_width=True): save_prodotto(new_prod, new_qty); st.rerun()
    with col_tab:
        df_inv = get_data("Inventario")
        if not df_inv.empty:
            if 'Prodotto' in df_inv.columns: df_inv = df_inv.sort_values('Prodotto')
            edited_inv = st.data_editor(df_inv[['Prodotto', 'Quantita', 'id']], column_config={"Prodotto": st.column_config.TextColumn("Prodotto", disabled=True), "Quantita": st.column_config.NumberColumn("Quantità", min_value=0, step=1), "id": None}, hide_index=True, use_container_width=True)
            st.caption("Modifica quantità e clicca Aggiorna.")
            if st.button("🔄 Aggiorna Stock", type="primary"):
                cnt = 0
                for i, row in edited_inv.iterrows():
                    rec_id = row['id']; orig_qty = df_inv[df_inv['id']==rec_id].iloc[0]['Quantita']
                    if row['Quantita'] != orig_qty: update_generic("Inventario", rec_id, {"Quantita": row['Quantita']}); cnt += 1
                if cnt > 0: get_data.clear(); st.success("Stock aggiornato!"); st.rerun()
        else: st.info("Magazzino vuoto.")

# =========================================================
# SEZIONE 5: PRESTITI
# =========================================================
elif menu == "🔄 Prestiti":
    st.title("🔄 Registro Prestiti")
    df_paz = get_data("Pazienti"); df_inv = get_data("Inventario")
    with st.expander("➕ Registra Nuovo Prestito", expanded=True):
        nomi_pazienti = sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows() if r.get('Cognome')]) if not df_paz.empty else []
        nomi_prodotti = sorted([r['Prodotto'] for i, r in df_inv.iterrows() if r.get('Prodotto')]) if not df_inv.empty else []
        with st.form("form_prestito"):
            c1, c2, c3 = st.columns(3); paz_scelto = c1.selectbox("Chi?", nomi_pazienti); prod_scelto = c2.selectbox("Cosa?", nomi_prodotti); data_prestito = c3.date_input("Quando?", date.today())
            if st.form_submit_button("Registra Prestito", use_container_width=True): save_prestito(paz_scelto, prod_scelto, data_prestito); st.success("Registrato!"); st.rerun()
    st.subheader("Attualmente fuori"); df_pres = get_data("Prestiti")
    if not df_pres.empty:
        if 'Restituito' not in df_pres.columns: df_pres['Restituito'] = False
        df_pres['Restituito'] = df_pres['Restituito'].fillna(False)
        if 'Data_Prestito' not in df_pres.columns: df_pres['Data_Prestito'] = None
        df_pres['Data_Prestito'] = pd.to_datetime(df_pres['Data_Prestito'], errors='coerce')
        active_loans = df_pres[df_pres['Restituito'] != True].copy()
        if not active_loans.empty:
            edited_loans = st.data_editor(active_loans[['Paziente', 'Oggetto', 'Data_Prestito', 'Restituito', 'id']], column_config={"Paziente": st.column_config.TextColumn("Paziente", disabled=True), "Oggetto": st.column_config.TextColumn("Oggetto", disabled=True), "Data_Prestito": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True), "Restituito": st.column_config.CheckboxColumn("Rientrato?", help="Spunta se restituito"), "id": None}, hide_index=True, use_container_width=True)
            if st.button("💾 Conferma Restituzioni", type="primary"):
                cnt = 0
                for i, row in edited_loans.iterrows():
                    if row['Restituito'] == True: update_generic("Prestiti", row['id'], {"Restituito": True}); cnt += 1
                if cnt > 0: get_data.clear(); st.success("Aggiornato!"); st.rerun()
        else: st.success("Tutti i materiali sono in sede!")

# =========================================================
# SEZIONE 6: SCADENZE
# =========================================================
elif menu == "📅 Scadenze":
    st.title("📅 Checklist Scadenze")
    df_scad = get_data("Scadenze")
    if not df_scad.empty and 'Data_Scadenza' in df_scad.columns:
        df_scad['Data_Scadenza'] = pd.to_datetime(df_scad['Data_Scadenza'], errors='coerce'); df_scad = df_scad.sort_values("Data_Scadenza")
        st.dataframe(df_scad, column_config={"Data_Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"), "Importo": st.column_config.NumberColumn("Importo", format="%d €"), "Descrizione": st.column_config.TextColumn("Dettagli")}, use_container_width=True, height=500)
    else: st.info("Nessuna scadenza.")
        
