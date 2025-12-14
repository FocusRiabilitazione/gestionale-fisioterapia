import streamlit as st
from pyairtable import Api
import pandas as pd
from requests.exceptions import HTTPError
import altair as alt

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
        
        data = [{'id': r['id'], **r['fields']} for r in records]
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        return pd.DataFrame()

def save_paziente(nome, cognome, area, disdetto):
    """Salva un nuovo paziente"""
    table = api.table(BASE_ID, "Pazienti")
    record = {
        "Nome": nome,
        "Cognome": cognome,
        "Area": area,
        "Disdetto": disdetto 
    }
    table.create(record, typecast=True)

def update_paziente(record_id, nuovo_stato):
    """Aggiorna lo stato"""
    table = api.table(BASE_ID, "Pazienti")
    # typecast=True è fondamentale qui per convertire il booleano nel formato che Airtable preferisce
    table.update(record_id, {"Disdetto": nuovo_stato}, typecast=True)

# --- 3. INTERFACCIA GRAFICA ---

st.set_page_config(page_title="Gestionale Fisio", page_icon="🏥", layout="wide")

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
    
    try:
        st.image("logo.png", width=300) 
    except FileNotFoundError:
        st.title("Buongiorno! ☕")

    st.write("Panoramica dello studio.")
    
    df = get_data("Pazienti")
    
    if not df.empty:
        if 'Disdetto' not in df.columns:
            df['Disdetto'] = False
        else:
            df['Disdetto'] = df['Disdetto'].fillna(False)

        totali = len(df)
        # Contiamo i disdetti (gestisce sia booleani che stringhe se presenti)
        disdetti_count = len(df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) | (df['Disdetto'] == "Checked") ])
        attivi = totali - disdetti_count
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Totale Anagrafica", totali)
        col2.metric("Pazienti Attivi", attivi)
        col3.metric("Pazienti Disdetti", disdetti_count, delta_color="inverse")
        
        st.divider()
        
        if 'Area' in df.columns:
            st.subheader("📍 Distribuzione per Area Trattata")
            all_areas = []
            for item in df['Area'].dropna():
                if isinstance(item, list):
                    all_areas.extend(item)
                elif isinstance(item, str):
                    all_areas.extend([p.strip() for p in item.split(',')])
                else:
                    all_areas.append(str(item))
            
            if all_areas:
                counts = pd.Series(all_areas).value_counts().reset_index()
                counts.columns = ['Area', 'Pazienti']
                domain = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
                range_ = ["#33A1C9", "#F1C40F", "#2ECC71", "#9B59B6", "#E74C3C", "#7F8C8D"]

                chart = alt.Chart(counts).mark_bar().encode(
                    x=alt.X('Area', sort='-y', title="Area Trattata"),
                    y=alt.Y('Pazienti', title="Numero Pazienti"),
                    color=alt.Color('Area', scale=alt.Scale(domain=domain, range=range_), legend=None),
                    tooltip=['Area', 'Pazienti']
                ).properties(height=400)
                st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Nessun dato pazienti trovato o errore di connessione.")

# =========================================================
# SEZIONE 2: GESTIONE PAZIENTI
# =========================================================
elif menu == "👥 Gestione Pazienti":
    st.title("📂 Anagrafica Pazienti")
    
    lista_aree = [
        "Mano-Polso", "Colonna", "ATM", 
        "Muscolo-Scheletrico", "Gruppi", "Ortopedico"
    ]
    
    # --- FORM INSERIMENTO ---
    with st.expander("➕ Nuovo Inserimento (Clicca per aprire)", expanded=False):
        with st.form("form_paziente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome")
                aree_scelte = st.multiselect("Area Trattata", options=lista_aree)
            with c2:
                cognome = st.text_input("Cognome")
                
            submit = st.form_submit_button("Salva nel Database")
            
            if submit:
                if nome and cognome:
                    try:
                        area_stringa = aree_scelte
                        save_paziente(nome, cognome, area_stringa, False)
                        st.success(f"✅ {nome} {cognome} salvato!")
                        st.rerun()
                    except HTTPError as e:
                        st.error(f"❌ Errore Airtable: {e}")
                    except Exception as e:
                        st.error(f"❌ Errore generico: {e}")
                else:
                    st.warning("⚠️ Nome e Cognome obbligatori.")

    st.divider()
    
    # --- TABELLA INTERATTIVA ---
    st.subheader("Elenco e Modifica Rapida")
    
    df_original = get_data("Pazienti")
    
    if not df_original.empty:
        # Gestione colonna mancante
        if 'Disdetto' not in df_original.columns:
            df_original['Disdetto'] = False
        
        # 1. CONVERSIONE PER VISUALIZZAZIONE (Backend -> Visuale)
        # Convertiamo True/False in "SI"/"NO" per il menu a tendina
        # fillna(False) assicura che i vuoti diventino "NO"
        df_original['Disdetto'] = df_original['Disdetto'].fillna(False).apply(
            lambda x: "SI" if x is True or x == 1 or x == "Checked" else "NO"
        )

        # Ricerca
        search_query = st.text_input("🔍 Cerca Paziente per Cognome", placeholder="Es. Rossi...")
        if search_query:
            df_filtered = df_original[df_original['Cognome'].astype(str).str.contains(search_query, case=False, na=False)]
        else:
            df_filtered = df_original

        cols_to_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'id']
        available_cols = [c for c in cols_to_show if c in df_filtered.columns]
        
        st.info("💡 Usa il menu a tendina nella colonna 'Disdetto' per cambiare stato (SI/NO).")
        
        # 2. CONFIGURAZIONE DATA EDITOR
        edited_df = st.data_editor(
            df_filtered[available_cols],
            column_config={
                "Disdetto": st.column_config.SelectboxColumn(
                    "Disdetto",
                    help="Il paziente ha disdetto?",
                    width="medium",
                    options=[
                        "NO",
                        "SI"
                    ],
                    required=True,
                ),
                "id": None, 
            },
            disabled=["Nome", "Cognome", "Area"], 
            hide_index=True,
            use_container_width=True,
            key="editor_pazienti"
        )

        # Bottone di salvataggio
        if st.button("💾 Salva Modifiche su Airtable"):
            changes_count = 0
            
            for index, row in edited_df.iterrows():
                record_id = row['id']
                nuovo_stato_str = row['Disdetto'] # Qui ora leggiamo "SI" o "NO"
                
                original_row = df_original[df_original['id'] == record_id]
                
                if not original_row.empty:
                    vecchio_stato_str = original_row.iloc[0]['Disdetto']
                    
                    if vecchio_stato_str != nuovo_stato_str:
                        # 3. RICONVERSIONE PER SALVATAGGIO (Visuale -> Backend)
                        # Airtable vuole True/False (o 1/0)
                        is_nuovo_true = True if nuovo_stato_str == "SI" else False
                        
                        try:
                            update_paziente(record_id, is_nuovo_true)
                            changes_count += 1
                        except Exception as e:
                            st.error(f"Errore aggiornamento ID {record_id}: {e}")
            
            if changes_count > 0:
                st.success(f"✅ Aggiornati {changes_count} pazienti!")
                st.rerun() 
            else:
                st.warning("⚠️ Nessuna modifica rilevata.")

    else:
        st.info("Database vuoto o errore nel recupero dati.")

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
        
        if totale > 300: 
            st.success(f"SCONTO PACCHETTO: **{int(totale*0.9)} €**")

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
