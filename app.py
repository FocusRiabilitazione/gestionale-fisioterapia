import streamlit as st
from pyairtable import Api
from datetime import datetime, timedelta
import pandas as pd
from requests.exceptions import HTTPError # NECESSARIO per vedere l'errore reale

# --- 1. CONFIGURAZIONE CONNESSIONE ---
# Tenta di prendere le chiavi dai Secrets di Streamlit Cloud
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    # Se sei in locale e non hai il file secrets, metti qui le tue chiavi per testare
    # (Non condividere questo file se ci metti le chiavi vere!)
    API_KEY = "inserisci_qui_tua_chiave_se_serve"
    BASE_ID = "inserisci_qui_tuo_base_id"

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
    
    # ATTENZIONE: Questi nomi a sinistra ("Nome", "Cognome"...) DEVONO essere identici 
    # alle colonne su Airtable (Maiuscole e spazi compresi).
    record = {
        "Nome": nome,
        "Cognome": cognome,
        "Telefono": telefono,
        "Diagnosi_Attuale": diagnosi,
        "Piano_Cura_Attivo": "SI", 
        "Data_Ultima_Visita": datetime.now().strftime("%Y-%m-%d") 
    }
    
    # typecast=True aiuta Airtable a capire i formati (es. stringa in data)
    table.create(record, typecast=True)

# --- 3. INTERFACCIA GRAFICA ---

st.set_page_config(page_title="Gestionale Fisio", page_icon="🏥", layout="wide")

# Menu Laterale
st.sidebar.title("Navigazione")
menu = st.sidebar.radio("Vai a:", ["📊 Dashboard & Allarmi", "👥 Gestione Pazienti", "💰 Calcolo Preventivo", "📝 Scadenze Ufficio"])
st.sidebar.divider()
st.sidebar.info("App collegata al database Airtable.")

# =========================================================
# SEZIONE 1: DASHBOARD
# =========================================================
if menu == "📊 Dashboard & Allarmi":
    st.title("Buongiorno! ☕")
    st.write("Ecco la situazione aggiornata del centro.")
    
    df_pazienti = get_data("Pazienti")
    
    if not df_pazienti.empty:
        # Calcoli veloci
        totali = len(df_pazienti)
        
        if 'Piano_Cura_Attivo' in df_pazienti.columns:
            attivi = len(df_pazienti[df_pazienti['Piano_Cura_Attivo'] == "SI"])
        else:
            attivi = 0
            
        col1, col2 = st.columns(2)
        col1.metric("Pazienti in Archivio", totali)
        col2.metric("Pazienti Attivi Ora", attivi)
        
        st.divider()
        
        # --- LOGICA INTELLIGENZA: CHI RICHIAMARE? ---
        st.subheader("🚨 Pazienti da Richiamare (Retention)")
        
        col_data = 'Data_Ultima_Visita'
        col_attivo = 'Piano_Cura_Attivo'
        
        if col_data in df_pazienti.columns and col_attivo in df_pazienti.columns:
            df_pazienti[col_data] = pd.to_datetime(df_pazienti[col_data], errors='coerce')
            
            # Criterio: Chi è attivo MA non viene da più di 20 giorni
            limite = datetime.now() - timedelta(days=20)
            
            pazienti_rischio = df_pazienti[
                (df_pazienti[col_attivo] == "SI") & 
                (df_pazienti[col_data] < limite)
            ]
            
            if not pazienti_rischio.empty:
                st.error(f"Attenzione: {len(pazienti_rischio)} pazienti non si vedono da 20 giorni!")
                cols_to_show = ['Nome', 'Cognome', 'Telefono', 'Diagnosi_Attuale']
                # Filtriamo solo le colonne che esistono davvero per evitare errori
                valid_cols = [c for c in cols_to_show if c in pazienti_rischio.columns]
                st.dataframe(pazienti_rischio[valid_cols])
            else:
                st.success("✅ Ottimo! Tutti i pazienti attivi sono venuti di recente.")
        else:
            st.warning(f"⚠️ Mancano le colonne '{col_data}' o '{col_attivo}' su Airtable.")

    else:
        st.info("Il database pazienti è ancora vuoto o irraggiungibile.")

# =========================================================
# SEZIONE 2: PAZIENTI (QUI C'ERA L'ERRORE)
# =========================================================
elif menu == "👥 Gestione Pazienti":
    st.title("Anagrafica Pazienti")
    
    # Form per aggiungere nuovo
    with st.expander("➕ AGGIUNGI NUOVO PAZIENTE", expanded=True):
        with st.form("form_nuovo_paziente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome")
            cognome = c2.text_input("Cognome")
            telefono = c1.text_input("Telefono")
            diagnosi = c2.text_area("Diagnosi / Motivo")
            
            submit = st.form_submit_button("Salva nel Database")
            
            if submit:
                if nome and cognome:
                    # --- QUI C'È LA CORREZIONE FONDAMENTALE ---
                    try:
                        save_paziente(nome, cognome, telefono, diagnosi)
                        st.success(f"✅ Paziente {nome} {cognome} salvato correttamente!")
                    
                    except HTTPError as e:
                        st.error("❌ Airtable ha rifiutato i dati.")
                        st.warning("Ecco il motivo esatto (mostra questo errore per il debug):")
                        # Stampa l'errore esatto che arriva da Airtable
                        st.code(e.response.text) 
                    
                    except Exception as e:
                        st.error(f"❌ Errore generico: {e}")
                    # ------------------------------------------
                else:
                    st.warning("⚠️ Inserisci almeno Nome e Cognome.")

    # Tabella completa
    st.write("### Elenco Completo")
    df = get_data("Pazienti")
    if not df.empty:
        st.dataframe(df)

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💰 Calcolo Preventivo":
    st.title("Generatore Preventivi")
    
    listino = {
        "Valutazione Iniziale": 50,
        "Seduta Tecar": 35,
        "Laser Terapia": 30,
        "Rieducazione Motoria": 45,
        "Massaggio Decontratturante": 50,
        "Onde d'Urto": 40
    }
    
    col1, col2 = st.columns([2, 1])
    with col1:
        scelte = st.multiselect("Scegli Trattamenti", list(listino.keys()))
        
    totale = 0
    
    if scelte:
        st.write("---")
        for trattamento in scelte:
            qty = st.number_input(f"Sedute di {trattamento}", min_value=1, value=5, key=trattamento)
            costo = listino[trattamento] * qty
            st.write(f"▫️ {trattamento}: {listino[trattamento]}€ x {qty} = **{costo} €**")
            totale += costo
            
        st.write("---")
        st.subheader(f"TOTALE PREVENTIVO: {totale} €")
        
        if totale > 300:
            st.success(f"💡 SCONTO PACCHETTO: **{int(totale*0.9)} €** (10% sconto)")

# =========================================================
# SEZIONE 4: SCADENZE
# =========================================================
elif menu == "📝 Scadenze Ufficio":
    st.title("Checklist Pagamenti")
    
    df_scadenze = get_data("Scadenze")
    
    if not df_scadenze.empty:
        if 'Data_Scadenza' in df_scadenze.columns:
            df_scadenze = df_scadenze.sort_values(by="Data_Scadenza")
        st.dataframe(df_scadenze, use_container_width=True)
    else:
        st.info("Nessuna scadenza trovata.")
