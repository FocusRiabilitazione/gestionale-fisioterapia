import streamlit as st
from pyairtable import Api
from datetime import datetime, timedelta
import pandas as pd

# --- 1. CONFIGURAZIONE CONNESSIONE ---
# Qui il programma cerca le chiavi che inserirai dopo su Streamlit Cloud
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    st.error("⚠️ Chiavi non trovate! Ricordati di inserirle nelle 'Advanced Settings' di Streamlit Cloud.")
    st.stop()

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
        
        # --- LOGICA INTELLIGENZA: CHI RICHIAMARE? ---
        st.subheader("🚨 Pazienti da Richiamare (Retention)")
        
        if 'Data_Ultima_Visita' in df_pazienti.columns and 'Piano_Cura_Attivo' in df_pazienti.columns:
            # Convertiamo la colonna data in formato data vero
            df_pazienti['Data_Ultima_Visita'] = pd.to_datetime(df_pazienti['Data_Ultima_Visita'], errors='coerce')
            
            # Criterio: Chi è attivo MA non viene da più di 20 giorni
            oggi = datetime.now()
            limite = today = datetime.now() - timedelta(days=20)
            
            pazienti_rischio = df_pazienti[
                (df_pazienti['Piano_Cura_Attivo'] == "SI") & 
                (df_pazienti['Data_Ultima_Visita'] < limite)
            ]
            
            if not pazienti_rischio.empty:
                st.error(f"Attenzione: {len(pazienti_rischio)} pazienti non si vedono da 20 giorni!")
                st.dataframe(pazienti_rischio[['Nome', 'Cognome', 'Telefono', 'Diagnosi_Attuale']])
                st.caption("Consiglio: Chiama questi pazienti per capire se hanno interrotto la cura.")
            else:
                st.success("✅ Ottimo! Tutti i pazienti attivi sono venuti di recente.")
        else:
            st.warning("⚠️ Mancano le colonne 'Data_Ultima_Visita' o 'Piano_Cura_Attivo' su Airtable.")

    else:
        st.info("Il database pazienti è ancora vuoto.")

# =========================================================
# SEZIONE 2: PAZIENTI
# =========================================================
elif menu == "👥 Gestione Pazienti":
    st.title("Anagrafica Pazienti")
    
    # Form per aggiungere nuovo
    with st.expander("➕ AGGIUNGI NUOVO PAZIENTE (Clicca per aprire)", expanded=False):
        with st.form("form_nuovo_paziente"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome")
            cognome = c2.text_input("Cognome")
            telefono = c1.text_input("Telefono")
            diagnosi = c2.text_area("Diagnosi / Motivo")
            
            submit = st.form_submit_button("Salva nel Database")
            
            if submit:
                if nome and cognome:
                    save_paziente(nome, cognome, telefono, diagnosi)
                    st.success(f"Paziente {nome} {cognome} salvato con successo!")
                    st.rerun() # Ricarica la pagina per vedere il nuovo dato
                else:
                    st.error("Inserisci almeno Nome e Cognome.")

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
    st.write("Seleziona i trattamenti per calcolare il totale al volo.")
    
    # LISTINO PREZZI (Puoi modificarlo direttamente qui nel codice per ora)
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
    dettaglio_text = ""
    
    if scelte:
        st.write("---")
        for trattamento in scelte:
            # Chiediamo quante sedute per ogni trattamento scelto
            qty = st.number_input(f"Quante sedute di {trattamento}?", min_value=1, value=5, key=trattamento)
            costo = listino[trattamento] * qty
            st.write(f"▫️ {trattamento}: {listino[trattamento]}€ x {qty} = **{costo} €**")
            totale += costo
            dettaglio_text += f"{trattamento} x{qty}\n"
            
        st.write("---")
        st.subheader(f"TOTALE PREVENTIVO: {totale} €")
        
        # Logica Sconto
        if totale > 300:
            st.success(f"💡 SCONTO PACCHETTO: Se paga subito puoi fare **{int(totale*0.9)} €** (10% sconto)")

# =========================================================
# SEZIONE 4: SCADENZE
# =========================================================
elif menu == "📝 Scadenze Ufficio":
    st.title("Checklist Pagamenti")
    
    df_scadenze = get_data("Scadenze")
    
    if not df_scadenze.empty:
        # Ordiniamo per data se possibile
        if 'Data_Scadenza' in df_scadenze.columns:
            df_scadenze = df_scadenze.sort_values(by="Data_Scadenza")  # <--- QUESTA RIGA DEVE AVERE SPAZIO DAVANTI
            
        st.dataframe(df_scadenze, use_container_width=True)
    else:
        st.info("Nessuna scadenza inserita nella tabella 'Scadenze' di Airtable.")
        # Ordiniamo per data se possibile
