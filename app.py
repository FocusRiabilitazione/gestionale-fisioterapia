import streamlit as st
from pyairtable import Api
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
from fpdf import FPDF
import io
import os
import time

# ==============================================================================
# 1. CONFIGURAZIONE PAGINA E STATO
# ==============================================================================
st.set_page_config(
    page_title="Gestionale Fisio Pro",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inizializzazione Session State se manca
if 'dash_filter' not in st.session_state:
    st.session_state.dash_filter = None

# ==============================================================================
# 2. STILE CSS AVANZATO (GHOST UI + FIX PULSANTI)
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    :root {
        --bg-dark: #0e1117;
        --sidebar-bg: #161b22;
        --accent-blue: #4299e1;
        --text-primary: #e2e8f0;
    }

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* SFONDO GALAXY */
    .stApp {
        background: radial-gradient(circle at top left, #1a202c, #0d1117);
        color: var(--text-primary);
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    
    /* TITOLI */
    h1 {
        background: linear-gradient(90deg, #FFF, #cbd5e0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
        margin-bottom: 20px;
    }
    h2, h3, h4 { color: #FFF !important; font-weight: 600; }

    /* ============================================================
       KPI CARDS (VISUALI HTML)
       ============================================================ */
    .glass-kpi {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 140px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin-bottom: 0px; 
        transition: transform 0.3s ease;
    }
    .glass-kpi:hover {
        transform: translateY(-3px);
        background: rgba(255,255,255,0.05);
        border-color: rgba(255,255,255,0.2);
    }
    .kpi-icon { font-size: 32px; margin-bottom: 8px; opacity: 0.9; }
    .kpi-value { font-size: 36px; font-weight: 800; color: white; line-height: 1.1; }
    .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #a0aec0; margin-top: 5px; }

    /* ============================================================
       PULSANTI GHOST (QUELLI SOTTO LE CARD)
       Usiamo !important per forzare la trasparenza e rimuovere il blu
       ============================================================ */
    
    /* Selettore specifico per i bottoni dentro le colonne della dashboard */
    div[data-testid="column"] button {
        background-color: transparent !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        color: #718096 !important; /* Grigio scuro elegante */
        box-shadow: none !important;
        font-size: 11px !important;
        font-weight: 400 !important;
        padding: 5px 0px !important;
        height: auto !important;
        min-height: 0px !important;
        margin-top: -10px !important; /* Li avvicina alla card */
        width: 100% !important;
        transition: all 0.2s ease !important;
        text-decoration: none !important;
    }

    /* Effetto Hover: diventano leggermente colorati */
    div[data-testid="column"] button:hover {
        color: #4299e1 !important;
        border: none !important;
        background-color: rgba(255, 255, 255, 0.02) !important;
        text-decoration: underline !important;
        transform: translateY(-2px);
    }
    
    div[data-testid="column"] button:focus,
    div[data-testid="column"] button:active {
        border: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
        color: #4299e1 !important;
        outline: none !important;
    }

    /* ============================================================
       PULSANTI AZIONE (Salva, Fatto, Rientrato)
       Devono rimanere visibili e colorati
       ============================================================ */
    
    /* Selettore specifico per i pulsanti nelle liste verticali o form */
    div[data-testid="stVerticalBlock"] button {
        background: linear-gradient(135deg, #3182ce, #2b6cb0) !important;
        border: none !important;
        color: white !important;
        padding: 0.5rem 1rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        margin-top: 0px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
    }
    
    div[data-testid="stVerticalBlock"] button:hover {
        opacity: 0.9 !important;
        transform: scale(1.02) !important;
    }

    /* Override specifico per i pulsanti 'Primary' (es. Salva Modifiche) */
    button[kind="primary"] {
        background: linear-gradient(135deg, #3182ce, #2b6cb0) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
    }

    /* ============================================================
       ALTRI ELEMENTI
       ============================================================ */

    /* TABELLE TRASPARENTI */
    div[data-testid="stDataFrame"] {
        background-color: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
    }
    
    /* INTESTAZIONI TABELLE */
    div[data-testid="stDataFrame"] div[data-testid="stTable"] {
        background-color: transparent !important;
    }

    /* ALERT BOX */
    .alert-box {
        padding: 15px; 
        border-radius: 12px; 
        margin-bottom: 15px;
        border-left: 4px solid; 
        background: rgba(255,255,255,0.03);
        border-top: 1px solid rgba(255,255,255,0.05);
        border-right: 1px solid rgba(255,255,255,0.05);
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    
    /* INPUT FIELDS */
    input, select, textarea {
        background-color: rgba(13, 17, 23, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: white !important;
        border-radius: 8px;
    }
    
    /* EXPANDER */
    .streamlit-expanderHeader {
        background-color: rgba(255,255,255,0.02) !important;
        border-radius: 8px !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. GESTIONE CONNESSIONE E API
# ==============================================================================
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    # Gestione robusta per evitare crash se mancano i secrets
    API_KEY = "key_mancante"
    BASE_ID = "id_mancante"

api = Api(API_KEY)

# ==============================================================================
# 4. FUNZIONI DI GESTIONE DATI (CRUD ESTESO)
# ==============================================================================

@st.cache_data(ttl=30)
def get_data(table_name):
    """
    Recupera tutti i record da una tabella Airtable.
    Include gestione errori e caching per performance.
    """
    if API_KEY == "key_mancante":
        return pd.DataFrame()
        
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records:
            return pd.DataFrame()
        # Converte la lista di dizionari in DataFrame
        data = [{'id': r['id'], **r['fields']} for r in records]
        return pd.DataFrame(data)
    except Exception as e:
        # Silenzio l'errore per non rompere la UI, ritorno DF vuoto
        return pd.DataFrame()

# --- FUNZIONI SPECIFICHE PER PAZIENTI ---
def save_paziente(nome, cognome, area, disdetto):
    """Salva un nuovo paziente nel database."""
    try:
        table = api.table(BASE_ID, "Pazienti")
        record = {
            "Nome": nome, 
            "Cognome": cognome, 
            "Area": area, 
            "Disdetto": disdetto,
            "Data_Inserimento": str(date.today())
        }
        table.create(record, typecast=True)
        get_data.clear() # Pulisce la cache per vedere subito i cambiamenti
        return True
    except Exception as e:
        st.error(f"Errore durante il salvataggio: {e}")
        return False

def update_paziente_status(record_id, changes):
    """Aggiorna lo stato di un paziente (es. disdetta, visita)."""
    try:
        table = api.table(BASE_ID, "Pazienti")
        # Pulizia date
        clean_changes = {}
        for k, v in changes.items():
            if "Data" in k:
                if pd.isna(v) or str(v) == "NaT" or v == "":
                    clean_changes[k] = None
                else:
                    clean_changes[k] = v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else str(v)
            else:
                clean_changes[k] = v
                
        table.update(record_id, clean_changes, typecast=True)
        get_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore aggiornamento: {e}")
        return False

def delete_paziente(record_id):
    """Elimina un paziente (o lo archivia)."""
    try:
        table = api.table(BASE_ID, "Pazienti")
        table.delete(record_id)
        get_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore eliminazione: {e}")
        return False

# --- FUNZIONI SPECIFICHE PER PREVENTIVI ---
def save_preventivo_db(paziente, dettagli_str, totale, note):
    """Salva un preventivo nella tabella Preventivi_Salvati."""
    try:
        table = api.table(BASE_ID, "Preventivi_Salvati")
        record = {
            "Paziente": paziente, 
            "Dettagli": dettagli_str, 
            "Totale": totale, 
            "Note": note, 
            "Data_Creazione": str(date.today())
        }
        table.create(record, typecast=True)
        get_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio preventivo: {e}")
        return False

def delete_preventivo(record_id):
    """Elimina un preventivo salvato."""
    try:
        api.table(BASE_ID, "Preventivi_Salvati").delete(record_id)
        get_data.clear()
        return True
    except Exception:
        return False

# --- FUNZIONI SPECIFICHE PER MAGAZZINO ---
def save_prodotto_magazzino(prodotto, quantita):
    """Aggiunge un nuovo prodotto al magazzino."""
    try:
        api.table(BASE_ID, "Inventario").create({
            "Prodotto": prodotto, 
            "Quantita": quantita
        }, typecast=True)
        get_data.clear()
        return True
    except Exception:
        return False

def update_prodotto_qty(record_id, nuova_quantita):
    """Aggiorna la quantità di un prodotto."""
    try:
        api.table(BASE_ID, "Inventario").update(record_id, {"Quantita": nuova_quantita}, typecast=True)
        get_data.clear()
        return True
    except Exception:
        return False

# --- FUNZIONI SPECIFICHE PER PRESTITI ---
def save_nuovo_prestito(paziente, oggetto, data_prestito):
    """Registra un prestito."""
    try:
        data_str = str(data_prestito)
        api.table(BASE_ID, "Prestiti").create({
            "Paziente": paziente, 
            "Oggetto": oggetto, 
            "Data_Prestito": data_str, 
            "Restituito": False
        }, typecast=True)
        get_data.clear()
        return True
    except Exception:
        return False

def mark_prestito_restituito(record_id):
    """Segna un prestito come restituito."""
    try:
        api.table(BASE_ID, "Prestiti").update(record_id, {"Restituito": True}, typecast=True)
        get_data.clear()
        return True
    except Exception:
        return False

# --- FUNZIONI PDF GENERATION ---
def create_pdf_preventivo(paziente, righe_preventivo, totale, note=""):
    """
    Crea un PDF professionale per il preventivo usando FPDF.
    Restituisce i byte del PDF pronti per il download.
    """
    euro_symbol = chr(128)
    
    class PDF(FPDF):
        def header(self):
            # Prova a caricare il logo se esiste
            if os.path.exists("logo.png"):
                try: 
                    self.image('logo.png', 75, 10, 60) # Posizionato al centro
                except: 
                    pass
            
            self.set_y(35)
            self.set_font('Arial', 'B', 14)
            self.set_text_color(50, 50, 50)
            self.cell(0, 10, 'PREVENTIVO PERCORSO RIABILITATIVO', 0, 1, 'C')
            self.set_draw_color(200, 200, 200)
            self.line(20, self.get_y(), 190, self.get_y())
            self.ln(10)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Pagina {self.page_no()} - Documento generato da Studio Focus', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Dati Paziente e Data
    pdf.set_text_color(0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, f'Spett.le Paziente: {paziente}', 0, 1)
    
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, f'Data emissione: {date.today().strftime("%d/%m/%Y")}', 0, 1)
    pdf.ln(5)
    
    # Note opzionali
    if note and len(note) > 2:
        pdf.set_font('Arial', 'I', 11)
        pdf.set_text_color(80)
        # Pulizia caratteri speciali
        clean_note = note.replace("€", euro_symbol).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, clean_note)
        pdf.ln(8)
        
    # Intestazione Tabella
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0)
    pdf.cell(110, 10, ' Descrizione Trattamento', 1, 0, 'L', 1)
    pdf.cell(30, 10, 'Q.ta', 1, 0, 'C', 1)
    pdf.cell(50, 10, 'Importo ', 1, 1, 'R', 1)
    
    # Righe Tabella
    pdf.set_font('Arial', '', 11)
    for riga in righe_preventivo:
        nome = str(riga.get('nome', '-'))[:55]
        qty = str(riga.get('qty', '0'))
        tot_riga = str(riga.get('tot', '0'))
        
        pdf.cell(110, 10, f" {nome}", 1)
        pdf.cell(30, 10, qty, 1, 0, 'C')
        pdf.cell(50, 10, f"{tot_riga} {euro_symbol} ", 1, 1, 'R')
        
    pdf.ln(5)
    
    # Totale
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(140, 12, 'TOTALE:', 0, 0, 'R')
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(50, 12, f'{totale} {euro_symbol}', 1, 1, 'R', 1)
    
    return pdf.output(dest='S').encode('latin-1')

# ==============================================================================
# 5. STRUTTURA SIDEBAR E NAVIGAZIONE
# ==============================================================================
with st.sidebar:
    try: 
        st.image("logo.png", use_container_width=True)
    except: 
        st.title("Focus Rehab")
    
    st.write("")
    
    # Menu di Navigazione
    menu = st.radio(
        "NAVIGAZIONE", 
        ["⚡ Dashboard", "👥 Pazienti", "💳 Preventivi", "📦 Magazzino", "🔄 Prestiti", "📅 Scadenze"],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.caption("Versione 42 - Max Extended")

# ==============================================================================
# SEZIONE 1: DASHBOARD
# ==============================================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")
    st.write("")
    
    # Controllo Sicurezza Chiavi
    if not API_KEY or not BASE_ID:
        st.error("⚠️ ERRORE CRITICO: Chiavi Airtable mancanti. Inseriscile nei 'Secrets' di Streamlit.")
        st.stop()

    df = get_data("Pazienti")
    
    if not df.empty:
        # Preprocessing Dati
        for c in ['Disdetto','Visita_Esterna']: 
            if c not in df.columns: df[c] = False
            df[c] = df[c].fillna(False)
        
        for c in ['Data_Disdetta','Data_Visita']: 
            if c not in df.columns: df[c] = None
            df[c] = pd.to_datetime(df[c], errors='coerce')
            
        if 'Area' not in df.columns: df['Area'] = "Non specificato"

        # Calcolo Metriche
        tot_pazienti = len(df)
        df_disdetti = df[(df['Disdetto']==True)]
        num_attivi = tot_pazienti - len(df_disdetti)
        
        # Logica Date (Senza Walrus Operator := per compatibilità)
        today_date = pd.Timestamp.now().normalize()
        limit_recall_date = today_date - pd.Timedelta(days=10)
        
        # Filtri
        recall_list = df_disdetti[(df_disdetti['Data_Disdetta'].notna()) & (df_disdetti['Data_Disdetta'] <= limit_recall_date)]
        
        df_visite = df[(df['Visita_Esterna']==True)]
        visite_imminenti = df_visite[(df_visite['Data_Visita'] >= today_date)]
        visite_scadute = df_visite[(df_visite['Data_Visita'] < today_date)]

        # --- KPI CARDS + LINK GHOST ---
        col1, col2, col3, col4 = st.columns(4)
        
        # Funzione helper per disegnare le card
        def draw_dashboard_card(column, icon, number, label, color_hex, filter_key):
            with column:
                # HTML Card
                st.markdown(f"""
                <div class="glass-kpi" style="border-bottom: 4px solid {color_hex};">
                    <div class="kpi-icon" style="color:{color_hex}">{icon}</div>
                    <div class="kpi-value">{number}</div>
                    <div class="kpi-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Bottone Ghost (Trasparente grazie al CSS)
                if st.button("› vedi dettagli", key=f"btn_dash_{filter_key}"):
                    st.session_state.dash_filter = filter_key

        draw_dashboard_card(col1, "👥", num_attivi, "ATTIVI", "#4299e1", "Attivi")
        draw_dashboard_card(col2, "📉", len(df_disdetti), "DISDETTI", "#e53e3e", "Disdetti")
        draw_dashboard_card(col3, "💡", len(recall_list), "RECALL", "#ed8936", "Recall")
        draw_dashboard_card(col4, "🩺", len(visite_imminenti), "VISITE", "#38b2ac", "Visite")

        st.write("")

        # --- SEZIONE LISTA A COMPARSA ---
        if st.session_state.dash_filter:
            with st.container(border=True):
                cl_head, cl_close = st.columns([9,1])
                cl_head.subheader(f"📋 Dettaglio: {st.session_state.dash_filter}")
                
                # Bottone Chiudi
                if cl_close.button("❌", key="btn_close_list", type="primary"): 
                    st.session_state.dash_filter = None
                    st.rerun()
                
                # Logica visualizzazione tabella filtrata
                df_display = pd.DataFrame()
                if st.session_state.dash_filter == "Attivi":
                    df_display = df[(df['Disdetto']==False)]
                elif st.session_state.dash_filter == "Disdetti":
                    df_display = df_disdetti
                elif st.session_state.dash_filter == "Recall":
                    df_display = recall_list
                elif st.session_state.dash_filter == "Visite":
                    df_display = df_visite
                
                if not df_display.empty: 
                    st.dataframe(
                        df_display[['Nome','Cognome','Area','Data_Disdetta','Data_Visita']], 
                        use_container_width=True, 
                        height=250
                    )
                else: 
                    st.info("Nessun dato presente in questa categoria.")
            st.divider()

        # --- SEZIONE AVVISI E GRAFICI ---
        col_avvisi, col_grafico = st.columns([1, 1.5], gap="large")
        
        with col_avvisi:
            st.subheader("🔔 Avvisi")
            
            # Avviso Visite Scadute
            if not visite_scadute.empty:
                st.markdown(f"<div class='alert-box' style='border-color:#e53e3e; color:#e53e3e'><strong>⚠️ Visite Scadute ({len(visite_scadute)})</strong></div>", unsafe_allow_html=True)
                for i, r in visite_scadute.iterrows():
                    with st.container(border=True):
                        cn, cb = st.columns([2, 1])
                        cn.write(f"**{r['Nome']} {r['Cognome']}**")
                        # Bottone Azione (Sarà colorato)
                        if cb.button("Rientrato", key=f"btn_rientro_{r['id']}"):
                            update_paziente_status(r['id'], {"Visita_Esterna": False, "Data_Visita": None})
                            st.rerun()

            # Avviso Recall
            if len(recall_list) > 0:
                st.markdown(f"<div class='alert-box' style='border-color:#ed8936; color:#ed8936'><strong>📞 Recall Necessari ({len(recall_list)})</strong></div>", unsafe_allow_html=True)
                for i, r in recall_list.iterrows():
                    with st.container(border=True):
                        cn, cb = st.columns([2, 1])
                        cn.write(f"**{r['Nome']} {r['Cognome']}**")
                        # Bottone Azione (Sarà colorato)
                        if cb.button("Fatto", key=f"btn_recall_done_{r['id']}"):
                            update_paziente_status(r['id'], {"Disdetto": False})
                            st.rerun()

            # Avviso Visite Imminenti (Solo Info)
            if not visite_imminenti.empty:
                st.markdown(f"<div class='alert-box' style='border-color:#38b2ac; color:#38b2ac'><strong>👨‍⚕️ Visite Imminenti ({len(visite_imminenti)})</strong></div>", unsafe_allow_html=True)
                for i, r in visite_imminenti.iterrows(): 
                    st.caption(f"• {r['Nome']} {r['Cognome']} ({r['Data_Visita'].strftime('%d/%m')})")

            if visite_scadute.empty and len(recall_list) == 0 and visite_imminenti.empty: 
                st.success("✅ Nessun avviso urgente. Tutto regolare.")

        with col_grafico:
            st.subheader("📈 Performance Aree")
            
            # Calcolo dati grafico
            df_attivi_grafico = df[(df['Disdetto']==False)]
            lista_aree = []
            
            if 'Area' in df_attivi_grafico.columns:
                for a in df_attivi_grafico['Area'].dropna():
                    if isinstance(a, list): 
                        lista_aree.extend(a)
                    else: 
                        lista_aree.extend([x.strip() for x in str(a).split(',')])
            
            if lista_aree:
                count_series = pd.Series(lista_aree).value_counts().reset_index()
                count_series.columns = ['Area', 'Pazienti']
                
                domain_aree = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
                range_colors = ["#33A1C9", "#F1C40F", "#2ECC71", "#9B59B6", "#E74C3C", "#7F8C8D"]
                
                chart_aree = alt.Chart(count_series).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Pazienti', axis=None), 
                    y=alt.Y('Area', sort='-x', title=None),
                    color=alt.Color('Area', scale=alt.Scale(domain=domain_aree, range=range_colors), legend=None),
                    tooltip=['Area', 'Pazienti']
                ).properties(height=350).configure_view(strokeWidth=0).configure_axis(grid=False)
                
                st.altair_chart(chart_aree, use_container_width=True)
            else:
                st.info("Dati insufficienti per generare il grafico aree.")

# ==============================================================================
# SEZIONE 2: PAZIENTI
# ==============================================================================
elif menu == "👥 Pazienti":
    st.title("Anagrafica Pazienti")
    
    # Form Aggiunta
    with st.expander("➕ Nuovo Paziente"):
        with st.form("form_nuovo_paziente"):
            c_nome, c_cogn, c_area = st.columns(3)
            input_nome = c_nome.text_input("Nome")
            input_cognome = c_cogn.text_input("Cognome")
            input_area = c_area.multiselect("Area", ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"])
            
            if st.form_submit_button("Salva Paziente", type="primary"): 
                if input_nome and input_cognome:
                    save_paziente(input_nome, input_cognome, ",".join(input_area), False)
                    st.success("Paziente salvato con successo!")
                    st.rerun()
                else:
                    st.warning("Inserisci almeno Nome e Cognome.")
    
    # Tabella Modificabile
    df_paz = get_data("Pazienti")
    if not df_paz.empty:
        df_paz['Disdetto'] = df_paz['Disdetto'].fillna(False)
        
        # Filtro Ricerca
        search_term = st.text_input("🔍 Cerca Paziente", placeholder="Digita il cognome...")
        if search_term:
            df_paz = df_paz[df_paz['Cognome'].astype(str).str.contains(search_term, case=False, na=False)]
        
        editor_pazienti = st.data_editor(
            df_paz[['Nome','Cognome','Area','Disdetto','Data_Disdetta','Visita_Esterna','Data_Visita','id']],
            key="editor_anagrafica", 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Disdetto": st.column_config.CheckboxColumn("Disd.", width="small"),
                "Visita_Esterna": st.column_config.CheckboxColumn("Visita", width="small"),
                "Data_Disdetta": st.column_config.DateColumn("Data Disd."),
                "Data_Visita": st.column_config.DateColumn("Data Visita"),
                "Area": st.column_config.SelectboxColumn("Area", options=["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]),
                "id": None
            }
        )
        
        if st.button("💾 Salva Modifiche Tabella", type="primary"):
            modifiche_counter = 0
            for index, row in editor_pazienti.iterrows():
                original_row = df_paz[df_paz['id']==row['id']].iloc[0]
                changes = {}
                
                # Logica Disdetta
                if row['Disdetto'] != original_row['Disdetto']: 
                    changes['Disdetto'] = row['Disdetto']
                    if row['Disdetto'] and pd.isna(row['Data_Disdetta']):
                        changes['Data_Disdetta'] = pd.Timestamp.now()
                
                # Logica Date
                if str(row['Data_Disdetta']) != str(original_row['Data_Disdetta']): 
                    changes['Data_Disdetta'] = row['Data_Disdetta']
                
                if str(row['Data_Visita']) != str(original_row['Data_Visita']): 
                    changes['Data_Visita'] = row['Data_Visita']
                
                # Altri Campi
                if row['Visita_Esterna'] != original_row['Visita_Esterna']: 
                    changes['Visita_Esterna'] = row['Visita_Esterna']
                
                if row['Area'] != original_row['Area']: 
                    changes['Area'] = row['Area']
                
                if changes: 
                    update_paziente_status(row['id'], changes)
                    modifiche_counter += 1
            
            if modifiche_counter > 0:
                st.success(f"Aggiornati {modifiche_counter} pazienti!")
                time.sleep(1)
                st.rerun()

# ==============================================================================
# SEZIONE 3: PREVENTIVI
# ==============================================================================
elif menu == "💳 Preventivi":
    st.title("Preventivi")
    tab_crea, tab_archivio = st.tabs(["📝 Genera Preventivo", "📂 Archivio Salvati"])
    
    df_pazienti = get_data("Pazienti")
    df_servizi = get_data("Servizi")
    
    with tab_crea:
        col_paz, col_serv = st.columns([1, 2])
        
        # Selezione Paziente
        lista_nomi = sorted([f"{r['Cognome']} {r['Nome']}" for i,r in df_pazienti.iterrows()]) if not df_pazienti.empty else []
        paziente_selezionato = col_paz.selectbox("Seleziona Paziente", lista_nomi)
        
        # Selezione Servizi
        dict_listino = {}
        if not df_servizi.empty:
            dict_listino = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i,r in df_servizi.iterrows()}
            
        servizi_selezionati = col_serv.multiselect("Aggiungi Trattamenti", sorted(list(dict_listino.keys())))
        note_prev = st.text_area("Note / Obiettivi (Opzionale)")
        
        if servizi_selezionati:
            st.divider()
            totale_prev = 0
            righe_dettaglio = []
            
            st.subheader("Dettaglio Costi")
            for serv in servizi_selezionati:
                c_nome, c_qty, c_prezzo = st.columns([3,1,1])
                c_nome.write(f"**{serv}**")
                qty = c_qty.number_input("Q.tà", 1, 50, 1, key=f"qty_{serv}")
                costo_riga = dict_listino[serv] * qty
                c_prezzo.write(f"**{costo_riga} €**")
                
                totale_prev += costo_riga
                righe_dettaglio.append({"nome":serv, "qty":qty, "tot":costo_riga})
            
            st.divider()
            st.metric("TOTALE PREVENTIVO", f"{totale_prev} €")
            
            if st.button("💾 Salva e Genera PDF", type="primary"):
                stringa_dettagli = " | ".join([f"{r['nome']} x{r['qty']}" for r in righe_dettaglio])
                save_preventivo_db(paziente_selezionato, stringa_dettagli, totale_prev, note_prev)
                st.success("Preventivo salvato correttamente! Vai nell'Archivio per scaricarlo.")

    with tab_archivio:
        df_archivio = get_data("Preventivi_Salvati")
        if not df_archivio.empty:
            for idx, row in df_archivio.iterrows():
                with st.container(border=True):
                    c_info, c_pdf, c_del = st.columns([3, 1, 1])
                    
                    c_info.markdown(f"**{row['Paziente']}**")
                    c_info.caption(f"Data: {row['Data_Creazione']} - Importo: {row['Totale']} €")
                    
                    # Ricostruzione dati per PDF
                    righe_per_pdf = []
                    if not pd.isna(row['Dettagli']):
                        for item in row['Dettagli'].split(" | "):
                            parts = item.split(" x")
                            if len(parts) >= 2:
                                righe_per_pdf.append({"nome":parts[0], "qty":parts[1], "tot":"-"})
                    
                    # Generazione PDF al volo
                    pdf_bytes = create_pdf_preventivo(row['Paziente'], righe_per_pdf, row['Totale'], str(row.get('Note','')))
                    
                    c_pdf.download_button(
                        "📄 Scarica PDF", 
                        data=pdf_bytes, 
                        file_name=f"Preventivo_{row['Paziente']}.pdf", 
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    if c_del.button("🗑️ Elimina", key=f"del_prev_{row['id']}", type="primary"):
                        delete_preventivo(row['id'])
                        st.rerun()
        else:
            st.info("Nessun preventivo in archivio.")

# ==============================================================================
# SEZIONE 4: MAGAZZINO
# ==============================================================================
elif menu == "📦 Magazzino":
    st.title("Magazzino")
    
    col_nuovo, col_tabella = st.columns([1, 2], gap="large")
    
    with col_nuovo:
        with st.container(border=True):
            st.subheader("Nuovo Prodotto")
            with st.form("form_prodotto"):
                nuovo_prod = st.text_input("Nome Prodotto")
                nuova_qty = st.number_input("Quantità Iniziale", 1)
                if st.form_submit_button("Aggiungi", type="primary"):
                    save_prodotto_magazzino(nuovo_prod, nuova_qty)
                    st.success("Aggiunto!")
                    st.rerun()
    
    with col_tabella:
        st.subheader("Inventario")
        df_inv = get_data("Inventario")
        if not df_inv.empty:
            editor_inv = st.data_editor(
                df_inv[['Prodotto','Quantita','id']], 
                hide_index=True, 
                use_container_width=True
            )
            
            if st.button("Aggiorna Giacenze", type="primary"):
                for idx, r in editor_inv.iterrows():
                    update_prodotto_qty(r['id'], r['Quantita'])
                st.success("Magazzino aggiornato!")
                st.rerun()
        else:
            st.info("Magazzino vuoto.")

# ==============================================================================
# SEZIONE 5: PRESTITI
# ==============================================================================
elif menu == "🔄 Prestiti":
    st.title("Registro Prestiti")
    
    with st.expander("➕ Nuovo Prestito"):
        col_chi, col_cosa, col_btn = st.columns([2, 2, 1])
        
        lista_pazienti = get_data("Pazienti")['Cognome'].tolist() if not get_data("Pazienti").empty else []
        
        paz_prestito = col_chi.selectbox("Paziente", lista_pazienti)
        ogg_prestito = col_cosa.text_input("Oggetto Prestato")
        
        if col_btn.button("Registra Prestito", type="primary"):
            save_nuovo_prestito(paz_prestito, ogg_prestito, date.today())
            st.success("Registrato!")
            st.rerun()
            
    st.divider()
    st.subheader("Materiale Fuori")
    
    df_prestiti = get_data("Prestiti")
    if not df_prestiti.empty:
        df_prestiti['Restituito'] = df_prestiti['Restituito'].fillna(False)
        
        editor_prestiti = st.data_editor(
            df_prestiti[['Paziente','Oggetto','Restituito','id']], 
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("Salva Restituzioni", type="primary"):
            for idx, r in editor_prestiti.iterrows(): 
                if r['Restituito']:
                    mark_prestito_restituito(r['id'])
            st.success("Aggiornato!")
            st.rerun()
    else:
        st.info("Nessun prestito attivo.")

# ==============================================================================
# SEZIONE 6: SCADENZE
# ==============================================================================
elif menu == "📅 Scadenze":
    st.title("Scadenzario")
    
    df_scadenze = get_data("Scadenze")
    if not df_scadenze.empty: 
        if 'Data_Scadenza' in df_scadenze.columns:
            df_scadenze['Data_Scadenza'] = pd.to_datetime(df_scadenze['Data_Scadenza'])
            df_scadenze = df_scadenze.sort_values('Data_Scadenza')
            
        st.dataframe(df_scadenze, use_container_width=True)
    else:
        st.info("Nessuna scadenza in arrivo.")
        
