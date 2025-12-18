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
# 0. CONFIGURAZIONE & STILE (DARK I-TECH)
# =========================================================
st.set_page_config(page_title="Gestionale Fisio", page_icon="🏥", layout="wide")

# CSS PERSONALIZZATO PER LOOK "DARK I-TECH"
st.markdown("""
<style>
    /* 1. FONT MODERNO */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* 2. SFONDO E CONTENITORI SCURI */
    .stApp {
        background-color: #0E1117; /* Nero/Blu scuro Streamlit */
        color: #FAFAFA;
    }
    
    /* 3. METRICHE (KPI) STILE CARD SCURA */
    div[data-testid="stMetric"] {
        background-color: #262730; /* Grigio Antracite */
        border: 1px solid #41444C;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: #FF4B2B; /* Effetto glow rosso al passaggio */
    }
    
    /* Testo delle metriche bianco */
    div[data-testid="stMetricLabel"] {
        color: #BDC1C6;
    }
    div[data-testid="stMetricValue"] {
        color: #FFFFFF;
    }

    /* 4. PULSANTI I-TECH (Gradienti) */
    div.stButton > button {
        background: linear-gradient(90deg, #FF4B2B 0%, #FF416C 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #FF416C 0%, #FF4B2B 100%);
        box-shadow: 0 0 15px rgba(255, 65, 108, 0.6); /* Glow Effect */
        color: white;
        border: none;
    }

    /* 5. SIDEBAR SCURA */
    section[data-testid="stSidebar"] {
        background-color: #161920; /* Leggermente più chiaro del fondo */
        border-right: 1px solid #333;
    }
    
    /* 6. TABELLE DATAFRAME */
    div[data-testid="stDataFrame"] {
        background-color: #262730;
        border-radius: 10px;
        border: 1px solid #41444C;
    }

    /* 7. ESPANSIONI E INPUT */
    .streamlit-expanderHeader {
        background-color: #262730;
        border-radius: 8px;
        color: white;
    }
    
    /* Input fields background */
    input, select, textarea {
        background-color: #1E1E1E !important;
        color: white !important;
    }
    
    /* 8. TITOLI */
    h1, h2, h3 {
        color: #FFFFFF !important;
        font-weight: 700;
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

# --- 2. FUNZIONI (Logica invariata) ---

@st.cache_data(ttl=60)
def get_data(table_name):
    """Scarica i dati da Airtable e li converte in DataFrame"""
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
    table = api.table(BASE_ID, "Pazienti")
    record = {"Nome": nome, "Cognome": cognome, "Area": area, "Disdetto": disdetto}
    get_data.clear()
    table.create(record, typecast=True)

def update_generic(table_name, record_id, dati_aggiornati):
    table = api.table(BASE_ID, table_name)
    fields_to_send = {}
    for k, v in dati_aggiornati.items():
        if "Data" in k: 
            if pd.isna(v) or str(v) == "NaT" or v == "":
                fields_to_send[k] = None
            else:
                if hasattr(v, 'strftime'):
                    fields_to_send[k] = v.strftime('%Y-%m-%d')
                else:
                    fields_to_send[k] = str(v)
        else:
            fields_to_send[k] = v
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

# --- FUNZIONI PER PREVENTIVI ---

def save_preventivo_temp(paziente, dettagli_str, totale):
    """Salva il preventivo nella tabella temporanea"""
    table = api.table(BASE_ID, "Preventivi_Salvati")
    record = {
        "Paziente": paziente,
        "Dettagli": dettagli_str,
        "Totale": totale,
        "Data_Creazione": str(date.today())
    }
    get_data.clear()
    table.create(record, typecast=True)

def create_pdf(paziente, righe_preventivo, totale):
    """Genera il file PDF in memoria"""
    class PDF(FPDF):
        def header(self):
            if os.path.exists("logo.png"):
                try:
                    self.image('logo.png', 10, 8, 30)
                except: pass
            
            self.set_font('Arial', 'B', 16)
            self.cell(40) 
            self.cell(0, 10, 'Focus Riabilitazione', 0, 1, 'L')
            self.set_font('Arial', 'I', 10)
            self.cell(40)
            self.cell(0, 5, 'Preventivo Trattamenti Fisioterapici', 0, 1, 'L')
            self.ln(15)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    
    # Info
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f'Gentile Paziente: {paziente}', 0, 1)
    pdf.cell(0, 8, f'Data emissione: {date.today().strftime("%d/%m/%Y")}', 0, 1)
    pdf.ln(5)
    
    # Tabella
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(100, 10, 'Trattamento', 1, 0, 'L', 1)
    pdf.cell(30, 10, 'Q.ta', 1, 0, 'C', 1)
    pdf.cell(40, 10, 'Importo', 1, 0, 'R', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 12)
    for riga in righe_preventivo:
        nome = str(riga.get('nome', '-'))[:45]
        qty = str(riga.get('qty', '0'))
        tot_riga = str(riga.get('tot', '0'))
        
        pdf.cell(100, 10, nome, 1)
        pdf.cell(30, 10, qty, 1, 0, 'C')
        pdf.cell(40, 10, f"{tot_riga} E", 1, 0, 'R')
        pdf.ln()
        
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(130, 10, 'TOTALE PREVENTIVO:', 0, 0, 'R')
    pdf.cell(40, 10, f'{totale} Euro', 1, 1, 'R')
    pdf.ln(10)

    # Rate
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'PIANO DI PAGAMENTO RATEIZZATO (Da compilare se applicabile):', 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, '1) Importo E _______________ entro il _______________', 0, 1)
    pdf.cell(0, 8, '2) Importo E _______________ entro il _______________', 0, 1)
    pdf.cell(0, 8, '3) Importo E _______________ entro il _______________', 0, 1)
    pdf.ln(15)

    # Firma
    pdf.set_font('Arial', '', 12)
    y_pos = pdf.get_y()
    pdf.cell(90, 10, f'Data: {date.today().strftime("%d/%m/%Y")}', 0, 0, 'L')
    pdf.cell(90, 10, 'Firma per accettazione:', 0, 1, 'L')
    pdf.set_xy(100, y_pos + 10)
    pdf.cell(80, 0, '', 'T')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 3. INTERFACCIA GRAFICA ---

with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.title("Focus Rehab")
    
    st.markdown("### Menu Principale")
    menu = st.radio(
        "", 
        ["📊 Dashboard", "👥 Gestione Pazienti", "💰 Preventivi & Pacchetti", "📦 Inventario", "🤝 Prestiti", "📝 Scadenze"],
        label_visibility="collapsed"
    )
    st.divider()
    st.caption("App v2.1 - Dark Tech")

# =========================================================
# SEZIONE 1: DASHBOARD
# =========================================================
if menu == "📊 Dashboard":
    st.title("📊 Dashboard Studio")
    st.markdown("Panoramica attività in tempo reale")
    st.write("")

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

        # KPI Metrics
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

        # 1. RIGA KPI (Cards Dark)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pazienti Attivi", cnt_attivi, "Totale")
        col2.metric("Disdetti Storico", len(df_disdetti), help="Totale disdette nel tempo")
        col3.metric("Da Richiamare", len(da_richiamare), delta_color="inverse", help="Disdetti da > 10gg")
        col4.metric("Visite Imminenti", len(visite_imminenti), "Oggi/Domani")

        st.write("")
        st.write("")

        # 2. ALLARMI E GRAFICI
        c_left, c_right = st.columns([1, 1.5], gap="large")

        with c_left:
            st.subheader("🔔 Avvisi Urgenti")
            
            if not visite_imminenti.empty:
                with st.container(border=True):
                    st.warning(f"👨‍⚕️ **Visite Mediche ({len(visite_imminenti)})**")
                    for i, row in visite_imminenti.iterrows():
                        d_vis = row['Data_Visita'].strftime('%d/%m')
                        st.write(f"• **{row['Nome']} {row['Cognome']}** ({d_vis})")

            if not visite_passate.empty:
                with st.container(border=True):
                    st.error(f"📅 **Visite Passate (> 1 Settimana)**")
                    for i, row in visite_passate.iterrows():
                        rec_id = row['id']
                        d_vis = row['Data_Visita'].strftime('%d/%m')
                        c1, c2 = st.columns([3, 1])
                        c1.caption(f"**{row['Nome']} {row['Cognome']}** ({d_vis})")
                        if c2.button("Rientrato", key=f"rientro_{rec_id}", type="primary"):
                            update_generic("Pazienti", rec_id, {"Visita_Esterna": False, "Data_Visita": None})
                            st.rerun()

            if len(da_richiamare) > 0:
                with st.container(border=True):
                    st.info(f"📞 **Recall Disdette ({len(da_richiamare)})**")
                    for i, row in da_richiamare.iterrows():
                        st.caption(f"• {row['Nome']} {row['Cognome']} (dal {row['Data_Disdetta'].strftime('%d/%m')})")

            if visite_imminenti.empty and visite_passate.empty and len(da_richiamare) == 0:
                st.success("Nessun allarme attivo. Tutto regolare!")

        with c_right:
            st.subheader("📈 Analisi Aree")
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
                # Palette Vivida per Dark Mode
                domain = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
                range_ = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#F7B731", "#A3CB38", "#D980FA"]
                
                chart = alt.Chart(counts).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Pazienti', title=None), 
                    y=alt.Y('Area', sort='-x', title=None),
                    color=alt.Color('Area', scale=alt.Scale(domain=domain, range=range_), legend=None),
                    tooltip=['Area', 'Pazienti']
                ).properties(height=350).configure_axis(
                    grid=False, 
                    labelColor='white', 
                    titleColor='white'
                ).configure_view(strokeWidth=0)
                
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("Il grafico apparirà popolando le Aree.")

# =========================================================
# SEZIONE 2: PAZIENTI
# =========================================================
elif menu == "👥 Gestione Pazienti":
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
                    st.success("Salvato!")
                    st.rerun()
    
    st.write("")
    df_original = get_data("Pazienti")
    
    if not df_original.empty:
        # Preprocessing Dataframe
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
        with col_search:
            search = st.text_input("🔍 Cerca per Cognome...", placeholder="Es. Rossi")

        df_filt = df_original[df_original['Cognome'].astype(str).str.contains(search, case=False, na=False)] if search else df_original

        cols_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'Data_Disdetta', 'Visita_Esterna', 'Data_Visita', 'Dimissione', 'id']
        valid_cols = [c for c in cols_show if c in df_filt.columns]

        # Tabella
        edited = st.data_editor(
            df_filt[valid_cols],
            column_config={
                "Disdetto": st.column_config.CheckboxColumn("Disdetto", width="small"),
                "Data_Disdetta": st.column_config.DateColumn("Data Disd.", format="DD/MM/YYYY"),
                "Visita_Esterna": st.column_config.CheckboxColumn("Visita Ext.", width="small"),
                "Data_Visita": st.column_config.DateColumn("Data Visita", format="DD/MM/YYYY"),
                "Dimissione": st.column_config.CheckboxColumn("🗑️", help="Elimina definitivamente"),
                "Area": st.column_config.SelectboxColumn("Area", options=lista_aree),
                "id": None
            },
            disabled=["Nome", "Cognome"], hide_index=True, use_container_width=True, key="editor_main", num_rows="fixed"
        )

        st.caption("Doppio click sulle celle per modificare.")
        if st.button("💾 Salva Modifiche Tabella", type="primary"):
            count_upd = 0
            count_del = 0
            for i, row in edited.iterrows():
                rec_id = row['id']
                if row.get('Dimissione') == True:
                    delete_generic("Pazienti", rec_id)
                    count_del += 1
                    continue

                orig = df_original[df_original['id'] == rec_id].iloc[0]
                changes = {}
                
                if row['Disdetto'] != (orig['Disdetto'] in [True, 1]): changes['Disdetto'] = row['Disdetto']
                d_dis = row['Data_Disdetta']
                if row['Disdetto'] and (pd.isna(d_dis) or str(d_dis) == "NaT"): 
                    d_dis = pd.Timestamp.now().normalize()
                    changes['Data_Disdetta'] = d_dis
                elif str(d_dis) != str(orig['Data_Disdetta']):
                    changes['Data_Disdetta'] = d_dis

                if row['Visita_Esterna'] != (orig['Visita_Esterna'] in [True, 1]): changes['Visita_Esterna'] = row['Visita_Esterna']
                if str(row['Data_Visita']) != str(orig['Data_Visita']): changes['Data_Visita'] = row['Data_Visita']
                if row['Area'] != orig['Area']: changes['Area'] = row['Area']

                if changes:
                    update_generic("Pazienti", rec_id, changes)
                    count_upd += 1

            if count_upd > 0 or count_del > 0:
                get_data.clear()
                st.toast("Database aggiornato con successo!", icon="✅")
                st.rerun()

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💰 Preventivi & Pacchetti":
    st.title("💰 Gestione Preventivi")

    tab1, tab2 = st.tabs(["📝 Generatore", "📂 Archivio Salvati"])

    df_srv = get_data("Servizi")
    df_paz = get_data("Pazienti")
    df_std = get_data("Preventivi_Standard")

    with tab1:
        # A. LISTINO
        with st.expander("📋 Vedi Listino Prezzi", expanded=False):
            if not df_srv.empty and 'Area' in df_srv.columns:
                aree_uniche = df_srv['Area'].dropna().unique()
                cols = st.columns(len(aree_uniche) if len(aree_uniche) <= 3 else 3)
                for i, area in enumerate(aree_uniche):
                    with cols[i % 3]:
                        st.markdown(f"**📍 {area}**")
                        items = df_srv[df_srv['Area'] == area]
                        for _, r in items.iterrows():
                            prz = f"{r['Prezzo']}€" if 'Prezzo' in r else "-"
                            st.caption(f"{r['Servizio']}: **{prz}**")
            else:
                st.warning("Configura la colonna 'Area' in Servizi.")

        # B. GENERATORE
        with st.container(border=True):
            st.subheader("Nuovo Preventivo")
            
            selected_services_default = []
            if not df_std.empty and 'Nome' in df_std.columns:
                c_filtro, c_pack = st.columns(2)
                
                with c_filtro:
                    if 'Area' in df_std.columns:
                        aree_std = ["Tutte"] + sorted(list(df_std['Area'].astype(str).unique()))
                        filtro_area = st.selectbox("Filtra Area Pacchetti:", aree_std)
                        df_std_filt = df_std[df_std['Area'].astype(str) == filtro_area] if filtro_area != "Tutte" else df_std
                    else:
                        df_std_filt = df_std

                with c_pack:
                    opt_std = ["-- Seleziona --"] + sorted(list(df_std_filt['Nome'].unique()))
                    scelta_std = st.selectbox("Carica Pacchetto Standard:", opt_std)
                
                if scelta_std != "-- Seleziona --":
                    row_std = df_std_filt[df_std_filt['Nome'] == scelta_std].iloc[0]
                    content = row_std.get('Contenuto', '')
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
            with col_paz:
                paziente_scelto = st.selectbox("Intestato a:", nomi_pazienti)
            
            listino_dict = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i, r in df_srv.iterrows() if r.get('Servizio')}
            valid_defaults = [s for s in selected_services_default if s in listino_dict]
            
            with col_serv:
                servizi_scelti = st.multiselect("Trattamenti:", sorted(list(listino_dict.keys())), default=valid_defaults)

            righe_preventivo = []
            totale = 0

            if servizi_scelti:
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
                with col_tot:
                    st.metric("TOTALE PREVENTIVO", f"{totale} €")
                with col_btn:
                    st.write("") 
                    if st.button("💾 Salva e Genera", type="primary", use_container_width=True):
                        dettagli_str = " | ".join([f"{r['nome']} x{r['qty']} ({r['tot']}€)" for r in righe_preventivo])
                        save_preventivo_temp(paziente_scelto, dettagli_str, totale)
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
                tot = row.get('Totale', 0)
                data_c = row.get('Data_Creazione', '')

                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**{paz}**")
                        st.caption(f"Emesso il: {data_c} • Totale: **{tot} €**")
                    
                    with c2:
                        righe_pdf = []
                        if dett:
                            items = dett.split(" | ")
                            for it in items:
                                try:
                                    parts = it.split(" x")
                                    nome = parts[0]
                                    rest = parts[1].split(" (")
                                    qty = rest[0]
                                    prz = rest[1].replace("€)", "")
                                    righe_pdf.append({"nome": nome, "qty": qty, "tot": prz})
                                except:
                                    righe_pdf.append({"nome": it, "qty": "-", "tot": "-"})
                        pdf_bytes = create_pdf(paz, righe_pdf, tot)
                        st.download_button("📄 PDF", data=pdf_bytes, file_name=f"Prev_{paz}.pdf", mime="application/pdf", key=f"pdf_{rec_id}", use_container_width=True)
                    
                    with c3:
                        if st.button("✅ Ok", key=f"conf_{rec_id}", use_container_width=True):
                            delete_generic("Preventivi_Salvati", rec_id)
                            st.rerun()
        else:
            st.info("Nessun preventivo salvato.")

# =========================================================
# SEZIONE 4: INVENTARIO
# =========================================================
elif menu == "📦 Inventario":
    st.title("📦 Magazzino")
    
    col_add, col_tab = st.columns([1, 2])
    
    with col_add:
        with st.container(border=True):
            st.subheader("Nuovo Prodotto")
            with st.form("add_prod"):
                new_prod = st.text_input("Nome")
                new_qty = st.number_input("Quantità", 0, 1000, 1)
                if st.form_submit_button("Aggiungi", use_container_width=True):
                    save_prodotto(new_prod, new_qty)
                    st.rerun()

    with col_tab:
        df_inv = get_data("Inventario")
        if not df_inv.empty:
            if 'Prodotto' in df_inv.columns: df_inv = df_inv.sort_values('Prodotto')
            
            edited_inv = st.data_editor(
                df_inv[['Prodotto', 'Quantita', 'id']],
                column_config={
                    "Prodotto": st.column_config.TextColumn("Prodotto", disabled=True),
                    "Quantita": st.column_config.NumberColumn("Quantità", min_value=0, step=1),
                    "id": None
                },
                hide_index=True,
                use_container_width=True
            )
            
            st.caption("Modifica le quantità direttamente nella tabella.")
            if st.button("🔄 Aggiorna Stock", type="primary"):
                cnt = 0
                for i, row in edited_inv.iterrows():
                    rec_id = row['id']
                    orig_qty = df_inv[df_inv['id']==rec_id].iloc[0]['Quantita']
                    if row['Quantita'] != orig_qty:
                        update_generic("Inventario", rec_id, {"Quantita": row['Quantita']})
                        cnt += 1
                if cnt > 0:
                    get_data.clear()
                    st.success("Stock aggiornato!")
                    st.rerun()
        else:
            st.info("Magazzino vuoto.")

# =========================================================
# SEZIONE 5: PRESTITI
# =========================================================
elif menu == "🤝 Prestiti":
    st.title("🤝 Registro Prestiti")
    
    df_paz = get_data("Pazienti")
    df_inv = get_data("Inventario")
    
    with st.expander("➕ Registra Nuovo Prestito", expanded=True):
        nomi_pazienti = sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows() if r.get('Cognome')]) if not df_paz.empty else []
        nomi_prodotti = sorted([r['Prodotto'] for i, r in df_inv.iterrows() if r.get('Prodotto')]) if not df_inv.empty else []

        with st.form("form_prestito"):
            c1, c2, c3 = st.columns(3)
            paz_scelto = c1.selectbox("Chi?", nomi_pazienti)
            prod_scelto = c2.selectbox("Cosa?", nomi_prodotti)
            data_prestito = c3.date_input("Quando?", date.today())
            if st.form_submit_button("Registra Prestito", use_container_width=True):
                save_prestito(paz_scelto, prod_scelto, data_prestito)
                st.success("Registrato!")
                st.rerun()

    st.subheader("Attualmente fuori")
    df_pres = get_data("Prestiti")
    
    if not df_pres.empty:
        if 'Restituito' not in df_pres.columns: df_pres['Restituito'] = False
        df_pres['Restituito'] = df_pres['Restituito'].fillna(False)
        if 'Data_Prestito' not in df_pres.columns: df_pres['Data_Prestito'] = None
        df_pres['Data_Prestito'] = pd.to_datetime(df_pres['Data_Prestito'], errors='coerce')
        
        active_loans = df_pres[df_pres['Restituito'] != True].copy()
        
        if not active_loans.empty:
            edited_loans = st.data_editor(
                active_loans[['Paziente', 'Oggetto', 'Data_Prestito', 'Restituito', 'id']],
                column_config={
                    "Paziente": st.column_config.TextColumn("Paziente", disabled=True),
                    "Oggetto": st.column_config.TextColumn("Oggetto", disabled=True),
                    "Data_Prestito": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True), 
                    "Restituito": st.column_config.CheckboxColumn("Restituito?", help="Spunta se è rientrato"),
                    "id": None
                },
                hide_index=True, use_container_width=True
            )
            if st.button("💾 Conferma Restituzioni", type="primary"):
                cnt = 0
                for i, row in edited_loans.iterrows():
                    if row['Restituito'] == True: 
                        update_generic("Prestiti", row['id'], {"Restituito": True})
                        cnt += 1
                if cnt > 0:
                    get_data.clear()
                    st.success("Inventario aggiornato!")
                    st.rerun()
        else:
            st.success("Tutti i materiali sono in sede!")

# =========================================================
# SEZIONE 6: SCADENZE
# =========================================================
elif menu == "📝 Scadenze":
    st.title("🗓️ Checklist Scadenze")
    
    df_scad = get_data("Scadenze")
    if not df_scad.empty and 'Data_Scadenza' in df_scad.columns:
        df_scad['Data_Scadenza'] = pd.to_datetime(df_scad['Data_Scadenza'], errors='coerce')
        df_scad = df_scad.sort_values("Data_Scadenza")
        
        st.dataframe(
            df_scad,
            column_config={
                "Data_Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"),
                "Importo": st.column_config.NumberColumn("Importo", format="%d €")
            },
            use_container_width=True
        )
    else:
        st.info("Nessuna scadenza imminente.")
        
