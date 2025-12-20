import streamlit as st
from pyairtable import Api
import pandas as pd
import altair as alt
from datetime import date, timedelta
from fpdf import FPDF
import io
import os

# =========================================================
# 1. CONFIGURAZIONE & CSS "STRATEGIC FIX"
# =========================================================
st.set_page_config(page_title="Gestionale Fisio Pro", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* SFONDO GALAXY */
    .stApp {
        background: radial-gradient(circle at top left, #1a202c, #0d1117);
        color: #e2e8f0;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
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

    /* ============================================================
       1. KPI CARDS -> STILE "SECONDARY" (Bottoni Normali)
       Li trasformiamo in CARD GIGANTI
       ============================================================ */
    
    /* Seleziona i bottoni "normali" dentro le colonne della dashboard */
    div[data-testid="column"] button[kind="secondary"] {
        background-color: #1e232e !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 16px !important;
        height: 150px !important; /* ALTEZZA FISSA GRANDE */
        width: 100% !important;
        padding: 0px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
        transition: transform 0.2s !important;
        white-space: pre-wrap !important; /* A capo */
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
    }

    /* Testo Gigante (Icona + Numero) */
    div[data-testid="column"] button[kind="secondary"] p {
        font-size: 42px !important; /* TESTO GIGANTE */
        font-weight: 800 !important;
        line-height: 1.2 !important;
        color: white !important;
        margin: 0 !important;
    }

    /* Hover */
    div[data-testid="column"] button[kind="secondary"]:hover {
        transform: translateY(-5px) !important;
        background-color: #2a2f3d !important;
        border-color: rgba(255,255,255,0.3) !important;
    }

    /* Bordi Colorati specifici per le 4 posizioni in alto */
    div[data-testid="column"]:nth-of-type(1) button[kind="secondary"] { border-left: 8px solid #4299e1 !important; } /* Blu */
    div[data-testid="column"]:nth-of-type(2) button[kind="secondary"] { border-left: 8px solid #e53e3e !important; } /* Rosso */
    div[data-testid="column"]:nth-of-type(3) button[kind="secondary"] { border-left: 8px solid #ed8936 !important; } /* Arancio */
    div[data-testid="column"]:nth-of-type(4) button[kind="secondary"] { border-left: 8px solid #38b2ac !important; } /* Verde */


    /* ============================================================
       2. PULSANTI AZIONE -> STILE "PRIMARY" (Bottoni Evidenziati)
       Li manteniamo PICCOLI e COMPATTI per gli avvisi
       ============================================================ */
    
    button[kind="primary"] {
        height: auto !important;
        min-height: 0px !important;
        padding: 6px 16px !important;
        font-size: 14px !important;
        background: linear-gradient(135deg, #3182ce, #2b6cb0) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2) !important;
        margin-top: 5px !important;
    }
    
    button[kind="primary"]:hover {
        box-shadow: 0 0 15px rgba(66, 153, 225, 0.5) !important;
        transform: scale(1.02) !important;
    }
    
    button[kind="primary"] p {
        font-size: 14px !important;
        font-weight: 600 !important;
    }

    /* ============================================================
       ALTRI ELEMENTI
       ============================================================ */
    
    /* Tabelle Trasparenti */
    div[data-testid="stDataFrame"] {
        background-color: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
    }
    div[data-testid="stDataFrame"] div[data-testid="stTable"] {
        background-color: transparent !important;
    }

    /* Navigazione */
    div.row-widget.stRadio > div { background-color: transparent; }
    div.row-widget.stRadio > div[role="radiogroup"] > label {
        background-color: transparent;
        color: #94a3b8;
        padding: 10px 15px;
        margin-bottom: 5px;
        border-radius: 10px;
        transition: all 0.2s;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
        color: #fff;
        background: rgba(255,255,255,0.03);
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background: rgba(66, 153, 225, 0.15);
        color: white;
        border: 1px solid #4299e1;
        font-weight: 600;
    }
    div.row-widget.stRadio div[role="radiogroup"] > label > div:first-child { display: none; }

    /* Input Fields */
    input, select, textarea {
        background-color: rgba(13, 17, 23, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: white !important;
        border-radius: 8px;
    }
    
    /* Alert Style */
    .alert-box {
        padding: 12px; 
        border-radius: 8px; 
        margin-bottom: 15px;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
    }
    .info { border-left: 4px solid #38b2ac; }
    .warn { border-left: 4px solid #ed8936; }
    .err { border-left: 4px solid #e53e3e; }
    .alert-title { font-weight: 800; font-size: 1.1em; display: block; margin-bottom: 5px;}

</style>
""", unsafe_allow_html=True)

# --- CONFIGURAZIONE CONNESSIONE ---
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    # Fallback per test locale se non ci sono secrets
    API_KEY = "tua_chiave"
    BASE_ID = "tuo_base_id"

api = Api(API_KEY)

# --- FUNZIONI ---
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
    table.create({"Nome": nome, "Cognome": cognome, "Area": area, "Disdetto": disdetto}, typecast=True)
    get_data.clear()

def update_generic(table_name, record_id, changes):
    clean = {}
    for k, v in changes.items():
        if "Data" in k: 
            if pd.isna(v) or str(v)=="NaT": clean[k] = None
            else: clean[k] = v.strftime('%Y-%m-%d')
        else: clean[k] = v
    api.table(BASE_ID, table_name).update(record_id, clean, typecast=True)
    get_data.clear()

def delete_generic(table_name, record_id):
    api.table(BASE_ID, table_name).delete(record_id)
    get_data.clear()

def save_prestito(p, o, d):
    api.table(BASE_ID, "Prestiti").create({"Paziente": p, "Oggetto": o, "Data_Prestito": str(d), "Restituito": False}, typecast=True)
    get_data.clear()

def save_prodotto(p, q):
    api.table(BASE_ID, "Inventario").create({"Prodotto": p, "Quantita": q}, typecast=True)
    get_data.clear()

def save_preventivo_temp(paziente, dettagli_str, totale, note):
    table = api.table(BASE_ID, "Preventivi_Salvati")
    record = {
        "Paziente": paziente, "Dettagli": dettagli_str, "Totale": totale, 
        "Note": note, "Data_Creazione": str(date.today())
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
            self.set_y(35); self.set_font('Arial', 'B', 12); self.set_text_color(80)
            self.cell(0, 10, 'PREVENTIVO RIABILITATIVO', 0, 1, 'C')
            self.line(20, self.get_y(), 190, self.get_y()); self.ln(10)
    pdf = PDF(); pdf.add_page(); pdf.set_text_color(0); pdf.set_font('Arial', '', 12)
    pdf.cell(95, 8, f'Paziente: {paziente}', 0, 1)
    pdf.cell(95, 8, f'Data: {date.today().strftime("%d/%m/%Y")}', 0, 1); pdf.ln(8)
    if note:
        pdf.set_font('Arial', 'I', 11)
        pdf.multi_cell(0, 6, note.replace("€", euro).encode('latin-1','replace').decode('latin-1')); pdf.ln(10)
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(240)
    pdf.cell(110, 10, ' Trattamento', 1, 0, 'L', 1); pdf.cell(30, 10, 'Q.ta', 1, 0, 'C', 1); pdf.cell(50, 10, 'Importo ', 1, 1, 'R', 1)
    pdf.set_font('Arial', '', 11)
    for r in righe_preventivo:
        pdf.cell(110, 10, str(r['nome'])[:55], 1); pdf.cell(30, 10, str(r['qty']), 1, 0, 'C'); pdf.cell(50, 10, f"{r['tot']} {euro}", 1, 1, 'R')
    pdf.ln(5); pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 12, f'TOTALE: {totale} {euro}', 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.title("Focus Rehab")
    menu = st.radio("Menu", ["⚡ Dashboard", "👥 Pazienti", "💳 Preventivi", "📦 Magazzino", "🔄 Prestiti", "📅 Scadenze"], label_visibility="collapsed")
    st.divider(); st.caption("v4.2 Full Code")

# =========================================================
# SEZIONE 1: DASHBOARD
# =========================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")
    if 'dash_filter' not in st.session_state: st.session_state.dash_filter = None
    
    df = get_data("Pazienti")
    if not df.empty:
        # Preprocessing
        for c in ['Disdetto','Visita_Esterna']: 
            if c not in df.columns: df[c] = False
            df[c] = df[c].fillna(False)
        for c in ['Data_Disdetta','Data_Visita']: 
            if c not in df.columns: df[c] = None
            df[c] = pd.to_datetime(df[c], errors='coerce')
        if 'Area' not in df.columns: df['Area'] = None

        totali = len(df)
        df_disdetti = df[(df['Disdetto']==True)|(df['Disdetto']==1)]
        cnt_attivi = totali - len(df_disdetti)
        
        oggi = pd.Timestamp.now().normalize()
        da_richiamare = df_disdetti[(df_disdetti['Data_Disdetta'].notna()) & (df_disdetti['Data_Disdetta'] <= (oggi - pd.Timedelta(days=10)))]
        
        df_visite = df[(df['Visita_Esterna']==True)]
        visite_imminenti = df_visite[(df_visite['Data_Visita'] >= today := pd.Timestamp.now().normalize())]
        visite_scadute = df_visite[(df_visite['Data_Visita'] < today)]

        # 1. KPI CARDS GIGANTI (TYPE="SECONDARY")
        # Il CSS rende i pulsanti "secondary" GIGANTI
        c1, c2, c3, c4 = st.columns(4)
        def kpi(i, n, t): return f"{i}  {n}\n\n{t}"
        
        with c1: 
            if st.button(kpi("👥", cnt_attivi, "ATTIVI"), key="k1", type="secondary"): st.session_state.dash_filter = "Attivi"
        with c2: 
            if st.button(kpi("📉", len(df_disdetti), "DISDETTI"), key="k2", type="secondary"): st.session_state.dash_filter = "Disdetti"
        with c3: 
            if st.button(kpi("📞", len(da_richiamare), "RECALL"), key="k3", type="secondary"): st.session_state.dash_filter = "Recall"
        with c4: 
            if st.button(kpi("🩺", len(visite_imminenti), "VISITE"), key="k4", type="secondary"): st.session_state.dash_filter = "Visite"

        st.write("")

        # 2. LISTA COMPARSA
        if st.session_state.dash_filter:
            with st.container(border=True):
                cl, cr = st.columns([9,1])
                cl.subheader(f"📋 {st.session_state.dash_filter}")
                # Il CSS rende i pulsanti "primary" PICCOLI
                if cr.button("❌", key="close", type="primary"): st.session_state.dash_filter = None; st.rerun()
                
                d_show = df[(df['Disdetto']==False)] if st.session_state.dash_filter == "Attivi" else (df_disdetti if st.session_state.dash_filter == "Disdetti" else (da_richiamare if st.session_state.dash_filter == "Recall" else visite_imminenti))
                if not d_show.empty: st.dataframe(d_show[['Nome','Cognome','Area','Data_Disdetta','Data_Visita']], use_container_width=True, height=250)
                else: st.info("Nessun dato.")
            st.divider()

        # 3. AVVISI & GRAFICO
        col_L, col_R = st.columns([1, 1.5], gap="large")
        
        with col_L:
            st.subheader("🔔 Avvisi Operativi")
            
            # Visite Scadute
            if not visite_scadute.empty:
                st.markdown('<div class="alert-box err"><span class="alert-title" style="color:#e53e3e">⚠️ Visite Scadute</span></div>', unsafe_allow_html=True)
                for i, r in visite_scadute.iterrows():
                    with st.container(border=True):
                        cn, cb = st.columns([2, 1])
                        cn.write(f"**{r['Nome']} {r['Cognome']}**")
                        # Pulsante PRIMARY -> Piccolo
                        if cb.button("Rientrato", key=f"v_{r['id']}", type="primary"):
                            update_generic("Pazienti", r['id'], {"Visita_Esterna": False, "Data_Visita": None}); st.rerun()

            # Recall Necessari
            if len(da_richiamare) > 0:
                st.markdown('<div class="alert-box warn"><span class="alert-title" style="color:#ed8936">📞 Recall Necessari</span></div>', unsafe_allow_html=True)
                for i, r in da_richiamare.iterrows():
                    with st.container(border=True):
                        cn, cb = st.columns([2, 1])
                        cn.write(f"**{r['Nome']} {r['Cognome']}**")
                        # Pulsante PRIMARY -> Piccolo
                        if cb.button("Fatto", key=f"r_{r['id']}", type="primary"):
                            update_generic("Pazienti", r['id'], {"Disdetto": False}); st.rerun()

            # Visite Imminenti
            if not visite_imminenti.empty:
                st.markdown('<div class="alert-box info"><span class="alert-title" style="color:#38b2ac">👨‍⚕️ Visite Imminenti</span></div>', unsafe_allow_html=True)
                for i, r in visite_imminenti.iterrows(): st.caption(f"• {r['Nome']} {r['Cognome']} ({r['Data_Visita'].strftime('%d/%m')})")

            if visite_scadute.empty and len(da_richiamare) == 0 and visite_imminenti.empty: st.success("✅ Tutto regolare.")

        with col_R:
            st.subheader("📈 Performance Aree")
            df_active = df[(df['Disdetto']==False)]
            areas = []
            if 'Area' in df_active.columns:
                for a in df_active['Area'].dropna():
                    if isinstance(a, list): areas.extend(a)
                    else: areas.extend([x.strip() for x in str(a).split(',')])
            if areas:
                cnt = pd.Series(areas).value_counts().reset_index(); cnt.columns = ['Area', 'Pazienti']
                dom = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
                rng = ["#33A1C9", "#F1C40F", "#2ECC71", "#9B59B6", "#E74C3C", "#7F8C8D"]
                ch = alt.Chart(cnt).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Pazienti', axis=None), y=alt.Y('Area', sort='-x', title=None),
                    color=alt.Color('Area', scale=alt.Scale(domain=dom, range=rng), legend=None), tooltip=['Area', 'Pazienti']
                ).properties(height=350).configure_view(strokeWidth=0).configure_axis(grid=False)
                st.altair_chart(ch, use_container_width=True)

# =========================================================
# SEZIONE 2: PAZIENTI
# =========================================================
elif menu == "👥 Pazienti":
    st.title("📂 Anagrafica Pazienti")
    
    with st.container(border=True):
        st.subheader("➕ Nuovo Paziente")
        with st.form("new_p"):
            c1, c2, c3 = st.columns([2,2,1])
            n = c1.text_input("Nome"); s = c2.text_input("Cognome")
            a = c3.multiselect("Area", ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"])
            if st.form_submit_button("Salva", type="primary", use_container_width=True):
                save_paziente(n, s, ",".join(a), False); st.success("Salvato!"); st.rerun()
    
    st.write("")
    df = get_data("Pazienti")
    if not df.empty:
        for c in ['Disdetto','Visita_Esterna','Data_Disdetta','Data_Visita']:
            if c not in df.columns: df[c] = None
        
        df['Disdetto'] = df['Disdetto'].fillna(False); df['Visita_Esterna'] = df['Visita_Esterna'].fillna(False)
        df['Data_Disdetta'] = pd.to_datetime(df['Data_Disdetta'], errors='coerce')
        df['Data_Visita'] = pd.to_datetime(df['Data_Visita'], errors='coerce')
        if 'Area' in df.columns: df['Area'] = df['Area'].apply(lambda x: x[0] if isinstance(x, list) and len(x)>0 else (str(x) if x else "")).str.strip()
        
        search = st.text_input("🔍 Cerca...", placeholder="Cognome...")
        df_filt = df[df['Cognome'].astype(str).str.contains(search, case=False, na=False)] if search else df
        
        ed = st.data_editor(
            df_filt[['Nome','Cognome','Area','Disdetto','Data_Disdetta','Visita_Esterna','Data_Visita','id']],
            key="paz_ed", hide_index=True, use_container_width=True,
            column_config={
                "Disdetto": st.column_config.CheckboxColumn("Disd.", width="small"),
                "Data_Disdetta": st.column_config.DateColumn("Data Disd."),
                "Visita_Esterna": st.column_config.CheckboxColumn("Visita", width="small"),
                "Data_Visita": st.column_config.DateColumn("Data Visita"),
                "Area": st.column_config.SelectboxColumn("Area", options=["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]),
                "id": None
            }
        )
        if st.button("💾 Salva Modifiche", type="primary"):
            for i, r in ed.iterrows():
                orig = df[df['id']==r['id']].iloc[0]
                changes = {}
                if r['Disdetto'] != orig['Disdetto']:
                    changes['Disdetto'] = r['Disdetto']
                    if r['Disdetto'] and pd.isna(r['Data_Disdetta']): changes['Data_Disdetta'] = pd.Timestamp.now()
                if str(r['Data_Disdetta']) != str(orig['Data_Disdetta']): changes['Data_Disdetta'] = r['Data_Disdetta']
                if r['Visita_Esterna'] != orig['Visita_Esterna']: changes['Visita_Esterna'] = r['Visita_Esterna']
                if str(r['Data_Visita']) != str(orig['Data_Visita']): changes['Data_Visita'] = r['Data_Visita']
                if r['Area'] != orig['Area']: changes['Area'] = r['Area']
                
                if changes: update_generic("Pazienti", r['id'], changes)
            st.success("Salvato!"); st.rerun()

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💳 Preventivi":
    st.title("Preventivi")
    t1, t2 = st.tabs(["📝 Generatore", "📂 Archivio"])
    df_s = get_data("Servizi"); df_p = get_data("Pazienti")
    
    with t1:
        c_p, c_s = st.columns([1, 2])
        paz_s = c_p.selectbox("Paziente", sorted([f"{r['Cognome']} {r['Nome']}" for i,r in df_p.iterrows()])) if not df_p.empty else None
        listino = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i,r in df_s.iterrows()}
        serv_s = c_s.multiselect("Servizi", sorted(list(listino.keys())))
        note = st.text_area("Note Percorso")
        
        if serv_s:
            st.divider(); tot = 0; righe = []
            for s in serv_s:
                c1, c2, c3 = st.columns([3,1,1])
                c1.write(f"**{s}**")
                q = c2.number_input("Q.tà", 1, 50, 1, key=f"q_{s}")
                cost = listino[s] * q; c3.write(f"**{cost} €**"); tot += cost
                righe.append({"nome":s, "qty":q, "tot":cost})
            
            st.divider()
            c_tot, c_b = st.columns([2,1])
            c_tot.metric("TOTALE", f"{tot} €")
            if c_b.button("💾 Salva PDF", type="primary", use_container_width=True):
                det = " | ".join([f"{r['nome']} x{r['qty']}" for r in righe])
                save_preventivo_temp(paz_s, det, tot, note); st.success("Salvato!")

    with t2:
        df_pr = get_data("Preventivi_Salvati")
        if not df_pr.empty:
            for i, r in df_pr.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3,1,1])
                    c1.write(f"**{r['Paziente']}**"); c1.caption(f"{r['Data_Creazione']} - {r['Totale']}€")
                    
                    righe_pdf = []
                    if not pd.isna(r['Dettagli']):
                        for item in r['Dettagli'].split(" | "):
                            parts = item.split(" x")
                            if len(parts)==2: righe_pdf.append({"nome":parts[0], "qty":parts[1], "tot":"-"})
                    
                    pdf = create_pdf(r['Paziente'], righe_pdf, r['Totale'], str(r.get('Note','')))
                    c2.download_button("📄 PDF", pdf, f"Prev_{r['id']}.pdf", use_container_width=True, type="primary")
                    if c3.button("🗑️", key=f"del_{r['id']}", type="primary", use_container_width=True):
                        delete_generic("Preventivi_Salvati", r['id']); st.rerun()

# =========================================================
# SEZIONE 4: MAGAZZINO
# =========================================================
elif menu == "📦 Magazzino":
    st.title("Magazzino")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("new_prod"):
            n = st.text_input("Prodotto"); q = st.number_input("Q.tà", 1)
            if st.form_submit_button("Aggiungi", type="primary", use_container_width=True): save_prodotto(n, q); st.rerun()
    with c2:
        df = get_data("Inventario")
        if not df.empty:
            ed = st.data_editor(df[['Prodotto','Quantita','id']], hide_index=True, use_container_width=True)
            if st.button("Aggiorna Stock", type="primary"):
                for i, r in ed.iterrows(): update_generic("Inventario", r['id'], {"Quantita": r['Quantita']})
                st.success("Aggiornato!"); st.rerun()

# =========================================================
# SEZIONE 5: PRESTITI
# =========================================================
elif menu == "🔄 Prestiti":
    st.title("Prestiti")
    with st.expander("➕ Nuovo Prestito"):
        with st.form("new_loan"):
            df_p = get_data("Pazienti"); df_i = get_data("Inventario")
            c1, c2 = st.columns(2)
            p = c1.selectbox("Chi?", df_p['Cognome'].tolist() if not df_p.empty else [])
            o = c2.selectbox("Cosa?", df_i['Prodotto'].tolist() if not df_i.empty else [])
            if st.form_submit_button("Salva", type="primary"): save_prestito(p, o, date.today()); st.rerun()
    
    df = get_data("Prestiti")
    if not df.empty:
        df['Restituito'] = df['Restituito'].fillna(False)
        act = df[df['Restituito']==False]
        if not act.empty:
            ed = st.data_editor(act[['Paziente','Oggetto','Restituito','id']], hide_index=True, use_container_width=True)
            if st.button("Conferma Resi", type="primary"):
                for i, r in ed.iterrows():
                    if r['Restituito']: update_generic("Prestiti", r['id'], {"Restituito": True})
                st.rerun()
        else: st.info("Nessun prestito attivo.")

# =========================================================
# SEZIONE 6: SCADENZE
# =========================================================
elif menu == "📅 Scadenze":
    st.title("Scadenze")
    df = get_data("Scadenze")
    if not df.empty:
        df['Data_Scadenza'] = pd.to_datetime(df['Data_Scadenza'])
        df = df.sort_values('Data_Scadenza')
        st.dataframe(df, use_container_width=True)
    else: st.info("Nessuna scadenza.")
        
