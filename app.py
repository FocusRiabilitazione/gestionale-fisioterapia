import streamlit as st
from pyairtable import Api
import pandas as pd
from requests.exceptions import HTTPError

# --- 1. CONFIGURAZIONE CONNESSIONE ---
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    API_KEY = "tua_chiave"
    BASE_ID = "tuo_base_id"

api = Api(API_KEY)

# --- 2. FUNZIONI ---

def get_data(table_name):
    """Scarica i dati da Airtable"""
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records:
            return pd.DataFrame()
        data = [r['fields'] for r in records]
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

def save_paziente(nome, cognome, area, disdetto):
    """Salva i dati. 'disdetto' viene inviato come True/False ad Airtable"""
    table = api.table(BASE_ID, "Pazienti")
    record = {
        "Nome": nome,
        "Cognome": cognome,
        "Area": area,
        "Disdetto": disdetto 
    }
    table.create(record, typecast=True)

# --- 3. INTERFACCIA GRAFICA ---

st.set_page_config(page_title="Gestionale Fisio", page_icon="🏥", layout="wide")

# Menu Laterale
st.sidebar.title("Navigazione")
menu = st.sidebar.radio(
    "Vai a:", 
    ["📊 Dashboard & Allarmi", "👥 Gestione Pazienti", "💰 Calcolo Preventivo", "📝 Scadenze Ufficio"]
)
st.sidebar.divider()
st.sidebar.info("App collegata ad Airtable.")

# =========================================================
# SEZIONE 1: DASHBOARD
# =========================================================
if menu == "📊 Dashboard & Allarmi":
    st.title("Buongiorno! ☕")
    st.write("Panoramica dello studio.")
    
    df = get_data("Pazienti")
    
    if not df.empty:
        if 'Disdetto' not in df.columns:
            df['Disdetto'] = False 

        totali = len(df)
        # Conta quanti hanno la spunta True
        disdetti_count = len(df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) ])
        attivi = totali - disdetti_count
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Totale Anagrafica", totali)
        col2.metric("Pazienti Attivi", attivi)
        col3.metric("Pazienti Disdetti", disdetti_count, delta_color="inverse")
        
        st.divider()
        
        if 'Area' in df.columns:
            st.subheader("📍 Distribuzione per Area Trattata")
            st.bar_chart(df['Area'].value_counts())
    else:
        st.info("Nessun dato pazienti trovato.")

# =========================================================
# SEZIONE 2: GESTIONE PAZIENTI (MODIFICATA)
# =========================================================
elif menu == "👥 Gestione Pazienti":
    st.title("📂 Anagrafica Pazienti")
    
    # --- FORM INSERIMENTO ---
    with st.container(border=True):
        st.subheader("Nuovo Inserimento")
        with st.form("form_paziente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome")
                area = st.text_input("Area (es. Spalla, Ginocchio)")
            with c2:
                cognome = st.text_input("Cognome")
                # Qui usiamo la spunta perché è più comoda per inserire
                disdetto = st.checkbox("Paziente Disdetto (Spunta se ha abbandonato)")
                
            submit = st.form_submit_button("Salva nel Database")
            
            if submit:
                if nome and cognome:
                    try:
                        save_paziente(nome, cognome, area, disdetto)
                        st.success(f"✅ {nome} {cognome} salvato!")
                    except HTTPError as e:
                        st.error("❌ Errore Airtable.")
                        st.code(e.response.text)
                    except Exception as e:
                        st.error(f"❌ Errore: {e}")
                else:
                    st.warning("⚠️ Nome e Cognome obbligatori.")

    # --- TABELLA PULITA ---
    st.divider()
    st.subheader("Elenco Completo")
    
    df = get_data("Pazienti")
    
    if not df.empty:
        # 1. Normalizziamo la colonna Disdetto (se manca la creiamo vuota)
        if 'Disdetto' not in df.columns:
            df['Disdetto'] = False
            
        # 2. Convertiamo VERO/FALSO in "SI"/"NO" per la tabella
        # Usiamo una funzione lambda: se è vero mette "SI", altrimenti "NO"
        df['Stato Disdetto'] = df['Disdetto'].apply(lambda x: "SI" if x is True or x == 1 else "NO")

        # 3. Selezioniamo SOLO le colonne che vogliamo vedere, nell'ordine giusto
        colonne_da_mostrare = ['Nome', 'Cognome', 'Area', 'Stato Disdetto']
        
        # Filtriamo per sicurezza solo quelle che esistono davvero (per evitare errori se manca 'Area')
        colonne_finali = [c for c in colonne_da_mostrare if c in df.columns]
        
        # Mostriamo la tabella pulita
        st.dataframe(df[colonne_finali], use_container_width=True)
        
    else:
        st.info("Database vuoto.")

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💰 Calcolo Preventivo":
    st.title("Generatore Preventivi")
    listino = {
        "Valutazione Iniziale": 50, "Seduta Tecar": 35, "Laser Terapia": 30,
        "Rieducazione Motoria": 45, "Massaggio Decontratturante": 50, "Onde d'Urto": 40
    }
    
    c1, c2 = st.columns([2, 1])
    with c1: scelte = st.multiselect("Scegli Trattamenti", list(listino.keys()))
        
    totale = 0
    if scelte:
        st.write("---")
        for t in scelte:
            qty = st.number_input(f"Sedute di {t}", 1, 20, 5, key=t)
            costo = listino[t] * qty
            st.write(f"▫️ {t}: {listino[t]}€ x {qty} = **{costo} €**")
            totale += costo
        st.write("---")
        st.subheader(f"TOTALE: {totale} €")
        if totale > 300: st.success(f"SCONTO PACCHETTO: **{int(totale*0.9)} €**")

# =========================================================
# SEZIONE 4: SCADENZE
# =========================================================
elif menu == "📝 Scadenze Ufficio":
    st.title("Checklist Pagamenti")
    df_scad = get_data("Scadenze")
    if not df_scad.empty:
        if 'Data_Scadenza' in df_scad.columns:
            df_scad = df_scad.sort_values("Data_Scadenza")
        st.dataframe(df_scad, use_container_width=True)
    else:
        st.info("Nessuna scadenza trovata.")
