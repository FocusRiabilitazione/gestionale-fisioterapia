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
    # Se non trova il file secrets, usa valori placeholder (o gestisci l'errore)
    API_KEY = "tua_chiave_se_non_usi_secrets"
    BASE_ID = "tuo_base_id_se_non_usi_secrets"

api = Api(API_KEY)

# --- 2. FUNZIONI ---

# AGGIUNTO IL TTL=60: I dati si aggiornano ogni 60 secondi
@st.cache_data(ttl=60)
def get_data(table_name):
    """Scarica i dati da Airtable e li converte in DataFrame"""
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records:
            return pd.DataFrame()
        
        # Recuperiamo ID e Campi appiattiti
        data = [{'id': r['id'], **r['fields']} for r in records]
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        print(f"Errore caricamento {table_name}: {e}")
        return pd.DataFrame()

def save_paziente(nome, cognome, area, disdetto):
    """Salva un nuovo paziente su Airtable"""
    table = api.table(BASE_ID, "Pazienti")
    record = {
        "Nome": nome,
        "Cognome": cognome,
        "Area": area,
        "Disdetto": disdetto 
    }
    table.create(record, typecast=True)

def update_paziente(record_id, nuovo_stato):
    """Aggiorna lo stato Disdetto su Airtable"""
    table = api.table(BASE_ID, "Pazienti")
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
        # Gestione colonna Disdetto
        if 'Disdetto' not in df.columns:
            df['Disdetto'] = False
        else:
            df['Disdetto'] = df['Disdetto'].fillna(False)

        totali = len(df)
        # Contiamo i disdetti (compatibile con checkbox airtable o booleani)
        disdetti_count = len(df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) ])
        attivi = totali - disdetti_count
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Totale Anagrafica", totali)
        col2.metric("Pazienti Attivi", attivi)
        col3.metric("Pazienti Disdetti", disdetti_count, delta_color="inverse")
        
        st.divider()
        
        # Grafico distribuzione Aree
        if 'Area' in df.columns:
            st.subheader("📍 Distribuzione per Area Trattata")
            
            # Logica per separare le aree se sono liste o stringhe con virgole
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
                
                # Definizione colori specifici
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
        st.info("Nessun dato pazienti trovato.")

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
                        area_stringa = ", ".join(aree_scelte)
                        save_paziente(nome, cognome, area_stringa, False)
                        st.success(f"✅ {nome} {cognome} salvato!")
                        # Ricarica per aggiornare la tabella
                        st.rerun()
                    except HTTPError as e:
                        st.error("❌ Errore di comunicazione con Airtable.")
                    except Exception as e:
                        st.error(f"❌ Errore generico: {e}")
                else:
                    st.warning("⚠️ Nome e Cognome sono obbligatori.")

    st.divider()
    
    # --- TABELLA INTERATTIVA ---
    st.subheader("Elenco e Modifica Rapida")
    
    df_original = get_data("Pazienti")
    
    if not df_original.empty:
        # 1. Gestione Disdetto (Default False se vuoto)
        if 'Disdetto' not in df_original.columns:
            df_original['Disdetto'] = False
        df_original['Disdetto'] = df_original['Disdetto'].fillna(False).infer_objects(copy=False)

        # 2. Pulizia Area per far funzionare i colori
        if 'Area' in df_original.columns:
             # Se è una lista prendi il primo elemento, se è stringa pulisci spazi
             df_original['Area'] = df_original['Area'].apply(
                 lambda x: x[0] if isinstance(x, list) and len(x) > 0 else (str(x) if x else "")
             ).str.strip() 

        # 3. Conversione a Category per Streamlit
        df_original['Area'] = df_original['Area'].astype("category")

        # Barra di Ricerca
        search_query = st.text_input("🔍 Cerca Paziente per Cognome", placeholder="Es. Rossi...")
        
        if search_query:
            df_filtered = df_original[df_original['Cognome'].astype(str).str.contains(search_query, case=False, na=False)]
        else:
            df_filtered = df_original

        # Colonne da mostrare
        cols_to_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'id']
        available_cols = [c for c in cols_to_show if c in df_filtered.columns]
        
        st.info("💡 Spunta la casella 'Disdetto' per cambiare stato. Poi clicca 'Salva Modifiche' in basso.")
        
        edited_df = st.data_editor(
            df_filtered[available_cols],
            column_config={
                "Disdetto": st.column_config.CheckboxColumn(
                    "Disdetto",
                    help="Spunta se il paziente ha disdetto",
                    default=False,
                ),
                # Configurazione Selectbox colorata
                "Area": st.column_config.SelectboxColumn(
                    "Area",
                    width="medium",
                    options=lista_aree, 
                    required=False,
                ),
                "id": None, # Nasconde la colonna ID
            },
            # Disabilitiamo modifica colonne anagrafiche (tranne checkbox)
            disabled=["Nome", "Cognome", "Area"], 
            hide_index=True,
            use_container_width=True,
            key="editor_pazienti"
        )

        # Bottone Salvataggio Modifiche
        if st.button("💾 Salva Modifiche su Airtable"):
            changes_count = 0
            
            for index, row in edited_df.iterrows():
                record_id = row['id']
                nuovo_stato = row['Disdetto']
                
                # Troviamo lo stato originale
                original_row = df_original[df_original['id'] == record_id]
                
                if not original_row.empty:
                    vecchio_stato = original_row.iloc[0]['Disdetto']
                    
                    # Normalizzazione booleana per confronto
                    is_vecchio_true = True if vecchio_stato in [True, 1, "True", "Checked"] else False
                    is_nuovo_true = True if nuovo_stato in [True, 1, "True", "Checked"] else False

                    if is_vecchio_true != is_nuovo_true:
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
        st.info("Database vuoto o connessione assente.")

# =========================================================
# SEZIONE 3: PREVENTIVI (AGGIORNATA CON TABELLA "Servizi")
# =========================================================
elif menu == "💰 Calcolo Preventivo":
    st.title("Generatore Preventivi")
    
    # 1. Carichiamo la tabella "Servizi" (Nome corretto da screenshot)
    df_listino = get_data("Servizi") 
    
    listino = {}
    
    if not df_listino.empty:
        # Verifichiamo esistenza colonne "Servizio" e "Prezzo" (Nomi corretti da screenshot)
        col_servizio = 'Servizio'
        col_prezzo = 'Prezzo'
        
        if col_servizio in df_listino.columns and col_prezzo in df_listino.columns:
            for index, row in df_listino.iterrows():
                nome_tratt = row[col_servizio]
                prezzo_tratt = row[col_prezzo]
                
                if nome_tratt:
                    if pd.isna(prezzo_tratt):
                        prezzo_tratt = 0
                    listino[str(nome_tratt)] = float(prezzo_tratt)
        else:
            st.error(f"⚠️ Errore Colonne: Non trovo '{col_servizio}' e '{col_prezzo}' in Airtable. Colonne trovate: {list(df_listino.columns)}")
    else:
        st.warning("⚠️ Tabella 'Servizi' vuota o non trovata. Controlla il nome su Airtable.")

    # 2. Selezione multipla
    c1, c2 = st.columns([2, 1])
    with c1: 
        # Ordiniamo le opzioni alfabeticamente
        opzioni_ordinate = sorted(list(listino.keys()))
        scelte = st.multiselect("Scegli Trattamenti", opzioni_ordinate)
        
    totale = 0
    if scelte:
        st.write("---")
        for t in scelte:
            qty = st.number_input(f"Sedute di {t}", 1, 20, 5, key=t)
            costo_unitario = listino[t]
            costo_totale = costo_unitario * qty
            st.write(f"▫️ {t}: {costo_unitario}€ x {qty} = **{costo_totale} €**")
            totale += costo_totale
        st.write("---")
        st.subheader(f"TOTALE: {totale} €")
        
        # Esempio sconto pacchetto se supera i 300 euro
        if totale > 300: 
            st.success(f"SCONTO PACCHETTO (10%): **{int(totale*0.9)} €**")

# =========================================================
# SEZIONE 4: SCADENZE
# =========================================================
elif menu == "📝 Scadenze Ufficio":
    st.title("Checklist Pagamenti")
    
    df_scad = get_data("Scadenze")
    
    if not df_scad.empty:
        if 'Data_Scadenza' in df_scad.columns:
            # Convertiamo in data vera per ordinare
            df_scad['Data_Scadenza'] = pd.to_datetime(df_scad['Data_Scadenza'], errors='coerce')
            df_scad = df_scad.sort_values("Data_Scadenza")
            # Riconvertiamo in stringa solo data per visualizzazione pulita
            df_scad['Data_Scadenza'] = df_scad['Data_Scadenza'].dt.strftime('%Y-%m-%d')
            
        st.dataframe(df_scad, use_container_width=True)
    else:
        st.info("Nessuna scadenza trovata.")
        
