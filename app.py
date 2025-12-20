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
# 0. CONFIGURAZIONE & GLASS UI (RESET DEFINITIVO)
# =========================================================
st.set_page_config(page_title="Gestionale Fisio Pro", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    :root {
        --glass-bg: rgba(255, 255, 255, 0.04);
        --glass-border: 1px solid rgba(255, 255, 255, 0.08);
        --neon-blue: #4299e1;
    }

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* SFONDO */
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

    /* --- KPI BUTTONS (CARD CLICCABILI) --- */
    /* Modificato: Grandezza Icone RIPRISTINATA */
    div[data-testid="column"] button {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border: var(--glass-border);
        border-radius: 16px;
        padding: 20px 10px;
        height: auto;
        width: 100%;
        text-align: center;
        transition: all 0.2s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 10px; /* Più spazio */
    }
    div[data-testid="column"] button:hover {
        background: rgba(255, 255, 255, 0.08);
        transform: translateY(-4px);
        border-color: rgba(255, 255, 255, 0.2);
        box-shadow: 0 10px 20px rgba(0,0,0,0.25);
    }
    
    /* ICONA GRANDE (Ripristinata) */
    .kpi-icon-wrapper {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 60px;  /* Aumentato */
        height: 60px; /* Aumentato */
        border-radius: 16px;
        font-size: 30px; /* Aumentato */
        margin-bottom: 5px;
    }
    /* TESTO BUTTON */
    div[data-testid="column"] button p {
        font-size: 1.2rem;
        font-weight: 700;
        line-height: 1.4;
    }

    /* --- TABELLE TRASPARENTI (Richiesta Specifica) --- */
    div[data-testid="stDataFrame"] {
        background-color: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
    }
    div[data-testid="stDataFrame"] div[data-testid="stTable"] {
        background-color: transparent !important;
    }
    
    /* --- PULSANTI AZIONE (Piccoli nei container) --- */
    div.stButton > button {
        background: linear-gradient(135deg, #3182ce, #2b6cb0);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        box-shadow: 0 0 15px rgba(66, 153, 225, 0.5);
        transform: scale(1.02);
    }
    /* Specifico per i pulsanti dentro le colonne (Rientrato, Fatto) */
    div[data-testid="column"] div.stButton > button {
        width: 100%;
        padding: 0.4rem;
        font-size: 0.85rem;
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

    /* INPUT & CONTAINER */
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
    
    /* Contenitori degli alert trasparenti */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.08);
    }
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
    st.caption("Focus App v3.6 - Final Release")

# =========================================================
# SEZIONE 1: DASHBOARD
# =========================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")
    st.write("")

    if 'dash_filter' not in st.session_state: st.session_state.dash_filter = None

    df = get_data("Pazienti")
    
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
        limite_recall = oggi - pd.Timedelta(days=10)
        da_richiamare = df_disdetti[ (df_disdetti['Data_Disdetta'].notna()) & (df_disdetti['Data_Disdetta'] <= limite_recall) ]
        
        df_visite = df[ (df['Visita_Esterna'] == True) | (df['Visita_Esterna'] == 1) ]
        domani = oggi + pd.Timedelta(days=1)
        visite_imminenti = df_visite[ (df_visite['Data_Visita'].notna()) & (df_visite['Data_Visita'] >= oggi) & (df_visite['Data_Visita'] <= domani) ]
        
        sette_giorni_fa = oggi - pd.Timedelta(days=7)
        visite_passate = df_visite[ (df_visite['Data_Visita'].notna()) & (df_visite['Data_Visita'] <= sette_giorni_fa) ]

        # 1. RIGA KPI (PULSANTI CLICCABILI)
        col1, col2, col3, col4 = st.columns(4)
        
        def btn_label(icon, val, lbl):
            return f"{icon}  {val}\n\n{lbl}"

        with col1:
            if st.button(btn_label("👥", cnt_attivi, "PAZIENTI ATTIVI"), key="kpi_attivi"):
                st.session_state.dash_filter = "Attivi"
        with col2:
            if st.button(btn_label("📉", len(df_disdetti), "DISDETTI STORICO"), key="kpi_disdetti"):
                st.session_state.dash_filter = "Disdetti"
        with col3:
            if st.button(btn_label("📞", len(da_richiamare), "DA RICHIAMARE"), key="kpi_recall"):
                st.session_state.dash_filter = "Recall"
        with col4:
            if st.button(btn_label("🩺", len(visite_imminenti), "VISITE MEDICHE"), key="kpi_visite"):
                st.session_state.dash_filter = "Visite"

        st.write("")

        # 2. LISTA COMPARSA (SE FILTRO ATTIVO)
        if st.session_state.dash_filter:
            with st.container(border=True):
                c_head, c_x = st.columns([9, 1])
                c_head.subheader(f"📋 Lista: {st.session_state.dash_filter}")
                if c_x.button("❌", key="close_list"):
                    st.session_state.dash_filter = None
                    st.rerun()
                
                df_show = pd.DataFrame()
                if st.session_state.dash_filter == "Attivi":
                    df_show = df[ (df['Disdetto'] == False) | (df['Disdetto'] == 0) ]
                elif st.session_state.dash_filter == "Disdetti":
                    df_show = df_disdetti
                elif st.session_state.dash_filter == "Recall":
                    df_show = da_richiamare
                elif st.session_state.dash_filter == "Visite":
                    df_show = df_visite
                
                if not df_show.empty:
                    # Tabella Trasparente
                    st.dataframe(
                        df_show[['Nome', 'Cognome', 'Area', 'Data_Disdetta', 'Data_Visita']],
                        use_container_width=True,
                        height=250
                    )
                else:
                    st.info("Nessun dato.")
            st.divider()

        # 3. SEZIONE ALLARMI E GRAFICI
        c_left, c_right = st.columns([1, 1.6], gap="large")

        with c_left:
            st.markdown("### 🔔 Avvisi Operativi")
            
            # --- VISITE IMMINENTI (Solo info) ---
            if not visite_imminenti.empty:
                st.markdown(f"""<div class="alert-box" style='border-color:#38b2ac'>
                    <strong style='color:#38b2ac'>👨‍⚕️ Visite Imminenti ({len(visite_imminenti)})</strong><br>
                    {'<br>'.join([f"• {row['Nome']} {row['Cognome']} ({row['Data_Visita'].strftime('%d/%m')})" for i, row in visite_imminenti.iterrows()])}
                    </div>""", unsafe_allow_html=True)

            # --- VISITE SCADUTE (Con Pulsante RIENTRATO) ---
            if not visite_passate.empty:
                st.markdown(f"""<div class="alert-box" style='border-color:#e53e3e'>
                    <strong style='color:#e53e3e'>⚠️ Visite Scadute (Richiedono azione)</strong>
                    </div>""", unsafe_allow_html=True)
                
                # Lista con pulsanti d'azione
                with st.container(border=True):
                    for i, row in visite_passate.iterrows():
                        rec_id = row['id']
                        c1, c2 = st.columns([3, 1.5])
                        c1.markdown(f"**{row['Nome']} {row['Cognome']}**")
                        if c2.button("Rientrato ✅", key=f"rientro_{rec_id}"):
                            update_generic("Pazienti", rec_id, {"Visita_Esterna": False, "Data_Visita": None})
                            st.rerun()

            # --- RECALL (Con Pulsante FATTO) ---
            if len(da_richiamare) > 0:
                st.markdown(f"""<div class="alert-box" style='border-color:#ed8936; margin-top:15px'>
                    <strong style='color:#ed8936'>📞 Recall Necessari (>10gg)</strong>
                    </div>""", unsafe_allow_html=True)
                
                with st.container(border=True):
                    for i, row in da_richiamare.iterrows():
                        rec_id = row['id']
                        c1, c2 = st.columns([3, 1.5])
                        c1.markdown(f"**{row['Nome']} {row['Cognome']}**")
                        if c2.button("Fatto ✅", key=f"recall_{rec_id}"):
                            # Logica: lo rimuove dalla lista recall (togliendo flag disdetto o aggiornando data)
                            update_generic("Pazienti", rec_id, {"Disdetto": False}) 
                            st.rerun()

            if visite_imminenti.empty and visite_passate.empty and len(da_richiamare) == 0:
                st.success("✅ Tutto regolare. Nessun avviso.")

        with c_right:
            st.markdown("### 📈 Performance Aree")
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
                
                # COLORI ORIGINALI
                domain = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
                range_ = ["#33A1C9", "#F1C40F", "#2ECC71", "#9B59B6", "#E74C3C", "#7F8C8D"]
                
                chart = alt.Chart(counts).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Pazienti', axis=None), 
                    y=alt.Y('Area', sort='-x', title=None, axis=alt.Axis(domain=False, ticks=False, labelColor="#cbd5e0", labelFontSize=13)),
                    color=alt.Color('Area', scale=alt.Scale(domain=domain, range=range_), legend=None),
                    tooltip=['Area', 'Pazienti']
                ).properties(height=350).configure_view(strokeWidth=0).configure_axis(grid=False)
                
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("I dati sulle aree saranno visualizzati qui.")

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
        with col_search: search = st.text_input("🔍 Cerca Paziente", placeholder="Digita il cognome...")
        df_filt = df_original[df_original['Cognome'].astype(str).str.contains(search, case=False, na=False)] if search else df_original

        cols_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'Data_Disdetta', 'Visita_Esterna', 'Data_Visita', 'Dimissione', 'id']
        valid_cols = [c for c in cols_show if c in df_filt.columns]

        edited = st.data_editor(
            df_filt[valid_cols],
            column_config={
                "Disdetto": st.column_config.CheckboxColumn("Disd.", width="small", help="Segna come disdetto"),
                "Data_Disdetta": st.column_config.DateColumn("Data Disd.", format="DD/MM/YYYY"),
                "Visita_Esterna": st.column_config.CheckboxColumn("Visita Ext.", width="small", help="Inviato a visita medica"),
                "Data_Visita": st.column_config.DateColumn("Data Visita", format="DD/MM/YYYY"),
                "Dimissione": st.column_config.CheckboxColumn("🗑️", width="small", help="Elimina definitivamente"),
                "Area": st.column_config.SelectboxColumn("Area Principale", options=lista_aree),
                "id": None
            },
            disabled=["Nome", "Cognome"], hide_index=True, use_container_width=True, key="editor_main", num_rows="fixed", height=500
        )

        if st.button("💾 Salva Modifiche Tabella", type="primary", use_container_width=True):
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
                get_data.clear(); st.toast("Database aggiornato con successo!", icon="✅"); st.rerun()

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💳 Preventivi":
    st.title("Preventivi & Proposte")
    tab1, tab2 = st.tabs(["📝 Generatore", "📂 Archivio Salvati"])
    df_srv = get_data("Servizi")
    df_paz = get_data("Pazienti")
    df_std = get_data("Preventivi_Standard")

    with tab1:
        with st.expander("📋 Listino Prezzi Attuale", expanded=False):
            if not df_srv.empty and 'Area' in df_srv.columns:
                aree_uniche = df_srv['Area'].dropna().unique(); cols = st.columns(3)
                for i, area in enumerate(aree_uniche):
                    with cols[i % 3]:
                        st.markdown(f"<strong style='color:var(--neon-blue)'>📍 {area}</strong>", unsafe_allow_html=True)
                        items = df_srv[df_srv['Area'] == area]
                        for _, r in items.iterrows(): prz = f"{r['Prezzo']}€" if 'Prezzo' in r else "-"; st.caption(f"{r['Servizio']}: **{prz}**")
            else: st.warning("Configura la colonna 'Area' in Servizi.")

        with st.container(border=True):
            st.subheader("Creazione Nuovo Preventivo")
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
                    scelta_std = st.selectbox("Carica Pacchetto Standard (Opzionale):", opt_std)
                
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

            nomi_pazienti = ["Seleziona Paziente..."]
            if not df_paz.empty:
                nomi_pazienti += sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows() if r.get('Cognome')])
            
            col_paz, col_serv = st.columns([1, 2])
            with col_paz: paziente_scelto = st.selectbox("Intestato a:", nomi_pazienti)
            
            listino_dict = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i, r in df_srv.iterrows() if r.get('Servizio')}
            valid_defaults = [s for s in selected_services_default if s in listino_dict]
            
            with col_serv:
                servizi_scelti = st.multiselect("Aggiungi Trattamenti:", sorted(list(listino_dict.keys())), default=valid_defaults)

            st.markdown("**Descrizione del Percorso / Obiettivi** (Appare nel PDF)")
            note_preventivo = st.text_area("Dettagli...", value=default_descrizione, height=100, label_visibility="collapsed")
            
            righe_preventivo = []
            totale = 0

            if servizi_scelti:
                st.divider()
                st.subheader("Dettaglio Costi")
                for s in servizi_scelti:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1: st.write(f"**{s}**")
                    def_qty = st.session_state.get(f"qty_preload_{s}", 1)
                    with c2: qty = st.number_input(f"Q.tà", 1, 50, def_qty, key=f"q_{s}", label_visibility="collapsed")
                    with c3: 
                        costo = listino_dict[s] * qty
                        st.markdown(f"<div style='text-align:right; font-weight:bold'>{costo} €</div>", unsafe_allow_html=True)
                    totale += costo
                    righe_preventivo.append({"nome": s, "qty": qty, "tot": costo})
                
                st.divider()
                col_tot, col_btn = st.columns([2, 1])
                with col_tot: 
                    st.markdown(f"<div style='font-size: 24px; font-weight: 800; color: var(--neon-blue);'>TOTALE: {totale} €</div>", unsafe_allow_html=True)
                with col_btn:
                    st.write("") 
                    if st.button("💾 Salva e Genera PDF", type="primary", use_container_width=True):
                        if paziente_scelto == "Seleziona Paziente...":
                            st.error("Seleziona un paziente!")
                        else:
                            dettagli_str = " | ".join([f"{r['nome']} x{r['qty']} ({r['tot']}€)" for r in righe_preventivo])
                            save_preventivo_temp(paziente_scelto, dettagli_str, totale, note_preventivo)
                            st.balloons()
                            for k in list(st.session_state.keys()):
                                if k.startswith("qty_preload_"): del st.session_state[k]
                            st.success("Preventivo salvato! Vai nella tab 'Archivio'.")

    with tab2:
        st.subheader("Archivio Preventivi")
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
                        st.download_button("📄 Scarica PDF", data=pdf_bytes, file_name=f"Prev_{paz}.pdf", mime="application/pdf", key=f"pdf_{rec_id}", use_container_width=True, type="primary")
                    with c3:
                        if st.button("✅ Archivia/Elimina", key=f"conf_{rec_id}", use_container_width=True):
                            delete_generic("Preventivi_Salvati", rec_id); st.rerun()
        else: st.info("Nessun preventivo salvato.")

# =========================================================
# SEZIONE 4: INVENTARIO
# =========================================================
elif menu == "📦 Magazzino":
    st.title("Magazzino & Materiali")
    col_add, col_tab = st.columns([1, 2], gap="large")
    with col_add:
        with st.container(border=True):
            st.subheader("Nuovo Prodotto")
            with st.form("add_prod"):
                new_prod = st.text_input("Nome Prodotto"); new_qty = st.number_input("Quantità Iniziale", 0, 1000, 1)
                if st.form_submit_button("Aggiungi al Magazzino", use_container_width=True, type="primary"): save_prodotto(new_prod, new_qty); st.rerun()
    with col_tab:
        df_inv = get_data("Inventario")
        if not df_inv.empty:
            st.subheader("Giacenze Attuali")
            if 'Prodotto' in df_inv.columns: df_inv = df_inv.sort_values('Prodotto')
            edited_inv = st.data_editor(df_inv[['Prodotto', 'Quantita', 'id']], column_config={"Prodotto": st.column_config.TextColumn("Prodotto", disabled=True), "Quantita": st.column_config.NumberColumn("Q.tà Disponibile", min_value=0, step=1), "id": None}, hide_index=True, use_container_width=True, height=400)
            if st.button("🔄 Aggiorna Giacenze", type="primary", use_container_width=True):
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
    st.title("Registro Prestiti")
    df_paz = get_data("Pazienti"); df_inv = get_data("Inventario")
    with st.expander("➕ Registra Nuovo Prestito", expanded=True):
        nomi_pazienti = sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows() if r.get('Cognome')]) if not df_paz.empty else []
        nomi_prodotti = sorted([r['Prodotto'] for i, r in df_inv.iterrows() if r.get('Prodotto')]) if not df_inv.empty else []
        with st.form("form_prestito"):
            c1, c2, c3 = st.columns(3); paz_scelto = c1.selectbox("Chi?", nomi_pazienti); prod_scelto = c2.selectbox("Cosa?", nomi_prodotti); data_prestito = c3.date_input("Quando?", date.today())
            if st.form_submit_button("Registra Prestito", use_container_width=True, type="primary"): save_prestito(paz_scelto, prod_scelto, data_prestito); st.success("Registrato!"); st.rerun()
    
    st.write(""); st.subheader("Materiali Attualmente Fuori")
    df_pres = get_data("Prestiti")
    if not df_pres.empty:
        if 'Restituito' not in df_pres.columns: df_pres['Restituito'] = False
        df_pres['Restituito'] = df_pres['Restituito'].fillna(False)
        if 'Data_Prestito' not in df_pres.columns: df_pres['Data_Prestito'] = None
        df_pres['Data_Prestito'] = pd.to_datetime(df_pres['Data_Prestito'], errors='coerce')
        active_loans = df_pres[df_pres['Restituito'] != True].copy()
        if not active_loans.empty:
            edited_loans = st.data_editor(active_loans[['Paziente', 'Oggetto', 'Data_Prestito', 'Restituito', 'id']], column_config={"Paziente": st.column_config.TextColumn("Paziente", disabled=True), "Oggetto": st.column_config.TextColumn("Oggetto", disabled=True), "Data_Prestito": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True), "Restituito": st.column_config.CheckboxColumn("Rientrato?", help="Spunta per confermare il rientro"), "id": None}, hide_index=True, use_container_width=True)
            if st.button("💾 Conferma Restituzioni Selezionate", type="primary", use_container_width=True):
                cnt = 0
                for i, row in edited_loans.iterrows():
                    if row['Restituito'] == True: update_generic("Prestiti", row['id'], {"Restituito": True}); cnt += 1
                if cnt > 0: get_data.clear(); st.success("Aggiornato!"); st.rerun()
        else: st.success("Tutti i materiali sono in sede!")

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
        
