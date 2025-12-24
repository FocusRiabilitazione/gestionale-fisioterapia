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
# 1. CONFIGURAZIONE PAGINA
# ==============================================================================
st.set_page_config(
    page_title="Gestionale Fisio Pro",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. CSS AVANZATO (GHOST UI - FORZATURA TRASPARENZA)
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* SFONDO SCURO GALAXY */
    .stApp {
        background: radial-gradient(circle at top left, #1a202c, #0d1117);
        color: #e2e8f0;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }

    /* ============================================================
       KPI CARDS (HTML)
       ============================================================ */
    .glass-kpi {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 15px;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 140px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin-bottom: 0px; 
    }
    .kpi-icon { font-size: 28px; margin-bottom: 5px; opacity: 0.9; }
    .kpi-value { font-size: 34px; font-weight: 800; color: white; line-height: 1.1; }
    .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #a0aec0; margin-top: 5px; }

    /* ============================================================
       PULSANTI GHOST (QUELLI SOTTO LE CARD)
       Usiamo !important per sovrascrivere lo stile blu di Streamlit
       ============================================================ */
    
    /* Seleziona i bottoni dentro le colonne della dashboard */
    div[data-testid="column"] button {
        background-color: transparent !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        color: #718096 !important; /* Grigio scuro elegante */
        box-shadow: none !important;
        font-size: 12px !important;
        font-weight: 400 !important;
        padding: 2px 0px !important;
        height: auto !important;
        min-height: 0px !important;
        margin-top: -10px !important; /* Li avvicina alla card */
        width: 100% !important;
        transition: all 0.2s ease !important;
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
    
    /* Eccezione per i pulsanti Ghost sopra che potrebbero essere in vertical block */
    /* Non serve se usiamo la gerarchia corretta, ma per sicurezza: */
    div[data-testid="column"] div[data-testid="stVerticalBlock"] button {
         /* Reset per evitare conflitti */
    }

    /* Override specifico per i pulsanti 'Primary' (es. Salva Modifiche) */
    button[kind="primary"] {
        background: linear-gradient(135deg, #3182ce, #2b6cb0) !important;
        border: none !important;
        color: white !important;
    }

    /* TABELLE TRASPARENTI */
    div[data-testid="stDataFrame"] {
        background-color: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
    }

    /* ALERT BOX */
    .alert-box {
        padding: 15px; border-radius: 12px; margin-bottom: 10px;
        border-left: 4px solid; background: rgba(255,255,255,0.03);
    }
    
    /* INPUT FIELDS */
    input, select, textarea {
        background-color: rgba(13, 17, 23, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: white !important;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. CONNESSIONE DATI
# ==============================================================================
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except:
    API_KEY = "key"
    BASE_ID = "id"

api = Api(API_KEY)

# ==============================================================================
# 4. FUNZIONI UTILITY (DATABASE & PDF)
# ==============================================================================
@st.cache_data(ttl=30)
def get_data(tbl):
    try:
        records = api.table(BASE_ID, tbl).all()
        return pd.DataFrame([{'id': r['id'], **r['fields']} for r in records]) if records else pd.DataFrame()
    except: return pd.DataFrame()

def save_paziente(n, c, a, d):
    try: api.table(BASE_ID, "Pazienti").create({"Nome": n, "Cognome": c, "Area": a, "Disdetto": d, "Data_Inserimento": str(date.today())}, typecast=True); get_data.clear(); return True
    except: return False

def update_generic(tbl, rid, data):
    try:
        cl = {k: (v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else v) for k,v in data.items()}
        api.table(BASE_ID, tbl).update(rid, cl, typecast=True); get_data.clear(); return True
    except: return False

def create_generic(tbl, data):
    try: api.table(BASE_ID, tbl).create(data, typecast=True); get_data.clear(); return True
    except: return False

def delete_generic(tbl, rid):
    try: api.table(BASE_ID, tbl).delete(rid); get_data.clear(); return True
    except: return False

# Wrapper specifici
def save_preventivo_temp(paziente, dettagli_str, totale, note):
    return create_generic("Preventivi_Salvati", {
        "Paziente": paziente, "Dettagli": dettagli_str, "Totale": totale, 
        "Note": note, "Data_Creazione": str(date.today())
    })

def save_prodotto(prodotto, quantita):
    return create_generic("Inventario", {"Prodotto": prodotto, "Quantita": quantita})

def save_prestito(paziente, oggetto, data_prestito):
    return create_generic("Prestiti", {
        "Paziente": paziente, "Oggetto": oggetto, 
        "Data_Prestito": str(data_prestito), "Restituito": False
    })

def create_pdf(paz, righe, tot, note=""):
    euro = chr(128)
    class PDF(FPDF):
        def header(self):
            if os.path.exists("logo.png"):
                try: self.image('logo.png', 75, 10, 60)
                except: pass
            self.set_y(35); self.set_font('Arial', 'B', 14); self.set_text_color(50)
            self.cell(0, 10, 'PREVENTIVO PERCORSO RIABILITATIVO', 0, 1, 'C')
            self.line(20, self.get_y(), 190, self.get_y()); self.ln(10)
            
        def footer(self):
            self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128)
            self.cell(0, 10, f'Pagina {self.page_no()} - Studio Focus', 0, 0, 'C')

    pdf = PDF(); pdf.add_page(); pdf.set_text_color(0); pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, f'Paziente: {paz}', 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f'Data: {date.today().strftime("%d/%m/%Y")}', 0, 1); pdf.ln(5)
    
    if note:
        pdf.set_font('Arial', 'I', 11); pdf.set_text_color(80)
        clean_note = note.replace("€", euro).encode('latin-1','replace').decode('latin-1')
        pdf.multi_cell(0, 6, clean_note); pdf.ln(8)
        
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(240); pdf.set_text_color(0)
    pdf.cell(110, 10, ' Trattamento', 1, 0, 'L', 1); pdf.cell(30, 10, 'Q.ta', 1, 0, 'C', 1); pdf.cell(50, 10, 'Importo', 1, 1, 'R', 1)
    
    pdf.set_font('Arial', '', 11)
    for r in righe:
        nome = str(r['nome'])[:55]
        qty = str(r['qty'])
        tot_r = f"{r['tot']} {euro}"
        pdf.cell(110, 10, f" {nome}", 1); pdf.cell(30, 10, qty, 1, 0, 'C'); pdf.cell(50, 10, tot_r, 1, 1, 'R')
        
    pdf.ln(5); pdf.set_font('Arial', 'B', 14)
    pdf.cell(140, 12, 'TOTALE:', 0, 0, 'R'); pdf.cell(50, 12, f'{tot} {euro}', 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.title("Focus Rehab")
    st.write("")
    menu = st.radio("Menu", ["⚡ Dashboard", "👥 Pazienti", "💳 Preventivi", "📦 Magazzino", "🔄 Prestiti", "📅 Scadenze"], label_visibility="collapsed")
    st.divider(); st.caption("V41 - Ghost Complete")

# =========================================================
# DASHBOARD
# =========================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")
    st.write("")
    
    # Check connessione
    if not API_KEY or not BASE_ID: st.warning("Chiavi API non trovate. Verifica i Secrets."); st.stop()

    if 'dash_filter' not in st.session_state: st.session_state.dash_filter = None
    
    df = get_data("Pazienti")
    if not df.empty:
        # Preprocessing
        for c in ['Disdetto','Visita_Esterna']: df[c] = df[c].fillna(False)
        for c in ['Data_Disdetta','Data_Visita']: df[c] = pd.to_datetime(df[c], errors='coerce')
        if 'Area' not in df.columns: df['Area'] = None

        tot = len(df)
        disdetti = df[(df['Disdetto']==True)]
        attivi = tot - len(disdetti)
        
        # Logica date sicura
        today = pd.Timestamp.now().normalize()
        limit_recall = today - pd.Timedelta(days=10)
        
        recall = disdetti[(disdetti['Data_Disdetta'].notna()) & (disdetti['Data_Disdetta'] <= limit_recall)]
        visite = df[(df['Visita_Esterna']==True)]
        vis_imm = visite[(visite['Data_Visita'] >= today)]
        vis_scad = visite[(visite['Data_Visita'] < today)]

        # --- KPI CARDS + LINK GHOST ---
        c1, c2, c3, c4 = st.columns(4)
        
        def draw_kpi(col, icon, num, label, color, key):
            with col:
                st.markdown(f"""
                <div class="glass-kpi" style="border-bottom: 4px solid {color};">
                    <div class="kpi-icon" style="color:{color}">{icon}</div>
                    <div class="kpi-value">{num}</div>
                    <div class="kpi-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)
                # Il CSS renderà questo bottone trasparente
                if st.button("› vedi dettagli", key=f"btn_{key}"):
                    st.session_state.dash_filter = key

        draw_kpi(c1, "👥", attivi, "ATTIVI", "#4299e1", "Attivi")
        draw_kpi(c2, "📉", len(disdetti), "DISDETTI", "#e53e3e", "Disdetti")
        draw_kpi(c3, "💡", len(recall), "RECALL", "#ed8936", "Recall")
        draw_kpi(c4, "🩺", len(vis_imm), "VISITE", "#38b2ac", "Visite")

        st.write("")

        # Lista comparsa
        if st.session_state.dash_filter:
            with st.container(border=True):
                cl, cr = st.columns([9,1])
                cl.subheader(f"📋 Dettaglio: {st.session_state.dash_filter}")
                # Questo bottone è 'secondary' ma essendo in una colonna potrebbe subire il CSS ghost
                # Usiamo primary o un'icona per sicurezza
                if cr.button("❌", key="close_list", type="primary"): st.session_state.dash_filter = None; st.rerun()
                
                d_show = df[(df['Disdetto']==False)] if st.session_state.dash_filter == "Attivi" else (disdetti if st.session_state.dash_filter == "Disdetti" else (recall if st.session_state.dash_filter == "Recall" else vis_imm))
                if not d_show.empty: st.dataframe(d_show[['Nome','Cognome','Area','Data_Disdetta','Data_Visita']], use_container_width=True, height=250)
                else: st.info("Nessun dato.")
            st.divider()

        # Avvisi e Grafico
        col_L, col_R = st.columns([1, 1.5], gap="large")
        
        with col_L:
            st.subheader("🔔 Avvisi")
            
            if not vis_scad.empty:
                st.markdown(f"<div class='alert-box' style='border-color:#e53e3e; color:#e53e3e'><strong>⚠️ Visite Scadute</strong></div>", unsafe_allow_html=True)
                for i, r in vis_scad.iterrows():
                    with st.container(border=True):
                        cn, cb = st.columns([2, 1])
                        cn.write(f"**{r['Nome']} {r['Cognome']}**")
                        # Questo bottone sarà COLORATO perché dentro stVerticalBlock
                        if cb.button("Rientrato", key=f"v_{r['id']}"):
                            update_generic("Pazienti", r['id'], {"Visita_Esterna": False, "Data_Visita": None}); st.rerun()

            if len(recall) > 0:
                st.markdown(f"<div class='alert-box' style='border-color:#ed8936; color:#ed8936'><strong>📞 Recall Necessari</strong></div>", unsafe_allow_html=True)
                for i, r in recall.iterrows():
                    with st.container(border=True):
                        cn, cb = st.columns([2, 1])
                        cn.write(f"**{r['Nome']} {r['Cognome']}**")
                        if cb.button("Fatto", key=f"r_{r['id']}"):
                            update_generic("Pazienti", r['id'], {"Disdetto": False}); st.rerun()

            if not vis_imm.empty:
                st.markdown(f"<div class='alert-box' style='border-color:#38b2ac; color:#38b2ac'><strong>👨‍⚕️ Visite Imminenti</strong></div>", unsafe_allow_html=True)
                for i, r in vis_imm.iterrows(): st.caption(f"• {r['Nome']} {r['Cognome']} ({r['Data_Visita'].strftime('%d/%m')})")

            if vis_scad.empty and len(recall) == 0 and vis_imm.empty: st.success("✅ Tutto regolare.")

        with col_R:
            st.subheader("📈 Aree")
            active = df[(df['Disdetto']==False)]
            areas = []
            if 'Area' in active.columns:
                for a in active['Area'].dropna():
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
# ALTRE PAGINE (LOGICA COMPLETA)
# =========================================================
elif menu == "👥 Pazienti":
    st.title("Anagrafica")
    with st.expander("➕ Nuovo"):
        c1,c2,c3 = st.columns(3); n=c1.text_input("Nome"); s=c2.text_input("Cognome"); a=c3.multiselect("Area", ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"])
        if st.button("Salva", type="primary"): save_paziente(n, s, ",".join(a), False); st.success("Ok"); st.rerun()
    df = get_data("Pazienti")
    if not df.empty:
        df['Disdetto'] = df['Disdetto'].fillna(False)
        ed = st.data_editor(df[['Nome','Cognome','Area','Disdetto','id']], hide_index=True, use_container_width=True)
        if st.button("Salva Modifiche", type="primary"):
            for i, r in ed.iterrows():
                update_generic("Pazienti", r['id'], {"Disdetto": r['Disdetto']})
            st.success("Fatto"); st.rerun()

elif menu == "💳 Preventivi":
    st.title("Preventivi")
    t1, t2 = st.tabs(["📝 Crea", "📂 Archivio"])
    paz = get_data("Pazienti"); srv = get_data("Servizi")
    with t1:
        c1,c2 = st.columns(2); p = c1.selectbox("Paziente", sorted([f"{r['Cognome']} {r['Nome']}" for i,r in paz.iterrows()])) if not paz.empty else None
        s = c2.multiselect("Servizi", srv['Servizio'].unique() if not srv.empty else [])
        if st.button("Crea Preventivo", type="primary"): 
            create_generic("Preventivi_Salvati", {"Paziente": p, "Dettagli": str(s), "Totale": 0, "Data_Creazione": str(date.today())}); st.success("Creato!")
    with t2:
        prv = get_data("Preventivi_Salvati")
        if not prv.empty:
            for i,r in prv.iterrows():
                with st.container(border=True):
                    c1,c2 = st.columns([3,1]); c1.write(f"**{r['Paziente']}**"); c2.download_button("PDF", create_pdf(r['Paziente'], [], 0), f"P_{r['id']}.pdf")
                    if c2.button("🗑️", key=f"d_{r['id']}", type="primary"): delete_generic("Preventivi_Salvati", r['id']); st.rerun()

elif menu == "📦 Magazzino":
    st.title("Magazzino")
    with st.form("np"):
        n=st.text_input("Prod"); q=st.number_input("Qta",1); 
        if st.form_submit_button("Aggiungi", type="primary"): save_prodotto(n, q); st.rerun()
    df = get_data("Inventario")
    if not df.empty:
        ed = st.data_editor(df[['Prodotto','Quantita','id']], hide_index=True)
        if st.button("Aggiorna", type="primary"):
            for i,r in ed.iterrows(): update_generic("Inventario", r['id'], {"Quantita": r['Quantita']})
            st.rerun()

elif menu == "🔄 Prestiti":
    st.title("Prestiti")
    with st.expander("➕ Nuovo"):
        p = st.selectbox("Chi", get_data("Pazienti")['Cognome'].tolist() if not get_data("Pazienti").empty else [])
        o = st.text_input("Cosa")
        if st.button("Presta", type="primary"): save_prestito(p, o, date.today()); st.rerun()
    df = get_data("Prestiti")
    if not df.empty:
        df['Restituito'] = df['Restituito'].fillna(False)
        ed = st.data_editor(df[['Paziente','Oggetto','Restituito','id']], hide_index=True)
        if st.button("Salva Resi", type="primary"):
            for i,r in ed.iterrows(): 
                if r['Restituito']: update_generic("Prestiti", r['id'], {"Restituito": True})
            st.rerun()

elif menu == "📅 Scadenze":
    st.title("Scadenze")
    df = get_data("Scadenze")
    if not df.empty: st.dataframe(df, use_container_width=True)
        
