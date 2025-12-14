import streamlit as st
from pyairtable import Api
from datetime import datetime, timedelta
import pandas as pd
from requests.exceptions import HTTPError # <--- Importante per gestire l'errore

# --- 1. CONFIGURAZIONE CONNESSIONE ---
# Qui il programma cerca le chiavi che inserirai dopo su Streamlit Cloud
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    # Fallback per test locale se non hai il file secrets
    # (Non lasciare queste chiavi vere qui se pubblichi il codice su GitHub!)
    API_KEY = "tua_chiave_se_sei_in_locale" 
    BASE_ID = "tuo_base_id_se_sei_in_locale"

# Connessione ad Airtable
api = Api(API_KEY)

# --- 2. FUNZIONI UTILI (Il motore) ---

def get_data(table_name):
    """Scarica i dati da una tabella Airtable e li trasforma in tabella leggibile"""
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records:
            return pd.DataFrame()
        # Estrae solo i campi utili (il contenuto delle colonne)
        data = [r['fields'] for r in records]
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Errore nel leggere la tabella '{table_name}'. Controlla che il nome su Airtable sia identico.")
        return pd.DataFrame()

def save_paziente(nome, cognome, telefono, diagnosi):
    """Salva un nuovo paziente su Airtable"""
    table = api.table(BASE_ID, "Pazienti")
    # ATTENZIONE: I nomi a sinistra ("Nome", "Cognome", etc.) devono essere identici alle colonne Airtable
    table.create({
        "Nome": nome,
        "Cognome": cognome,
        "Telefono": telefono,
        "Diagnosi_Attuale": diagnosi,
        "Piano_Cura_Attivo": "SI",
        "Data_Ultima_Visita": datetime.now().strftime("%Y-%m-%d")
    }, typecast=True) 

# --- 3. INTERFACCIA GRAFICA (Quello che vede la segretaria) ---

st.set_page_config(page_title="Gestionale Fisio", page_icon="🏥", layout="wide")

# Menu Laterale
st.sidebar.title("Navigazione")
menu = st.sidebar.radio("Vai a:", ["📊 Dashboard & Allarmi", "👥 Gestione Pazienti", "💰 Calcolo Preventivo", "📝 Scadenze Ufficio"])
st.sidebar.divider()
st.sidebar.info("App collegata al database Airtable.")

# =========================================================
# SEZIONE 1: DASHBOARD (Il cuore del sistema)
# =========================================================
if menu == "📊 Dashboard & Allarmi":
    st.title("Buongiorno! ☕")
    st.write("Ecco la situazione aggiornata del centro.")
    
    df_pazienti = get_data("Pazienti")
    
    if not df_pazienti.empty:
        # Calcoli veloci
        totali = len(df_pazienti)
        # Controlliamo se esiste la colonna 'Piano_Cura_Attivo', altrimenti errore
        if 'Piano_Cura_Attivo' in df_pazienti.columns:
            attivi = len(df_pazienti[df_pazienti['Piano_Cura_Attivo'] == "SI"])
        else:
            attivi = 0
            
        # Mostra i numeri in alto
        col1, col2, col3 = st.columns(3)
        col1.metric("Pazienti in Archivio", totali)
        col2.metric("Pazienti Attivi Ora", attivi)
        
        st.divider()
        
        # --- LOGICA INTELLIG
