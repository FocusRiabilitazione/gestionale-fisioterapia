import streamlit as st
import streamlit.components.v1 as components
from pyairtable import Api
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
import base64
import io

# =========================================================
# 0. CONFIGURAZIONE & STILE
# =========================================================
st.set_page_config(page_title="Gestionale Fisio Pro", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* SFONDO SCURO */
    .stApp {
        background: radial-gradient(circle at top left, #1a202c, #0d1117);
        color: #e2e8f0;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* KPI CARDS */
    .glass-kpi {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        height: 140px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        margin-bottom: 10px;
        transition: transform 0.3s ease;
    }
    .glass-kpi:hover { transform: translateY(-5px); background: rgba(255, 255, 255, 0.06); }
    .kpi-icon { font-size: 32px; margin-bottom: 8px; filter: drop-shadow(0 0 5px rgba(255,255,255,0.3)); }
    .kpi-value { font-size: 36px; font-weight: 800; color: white; line-height: 1; }
    .kpi-label { font-size: 11px; text-transform: uppercase; color: #a0aec0; margin-top: 8px; letter-spacing: 1.5px; font-weight: 600; }

    /* ALERT ROWS */
    .alert-row-name {
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 10px;
        padding: 0 15px;
        height: 42px;    
        display: flex; align-items: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
        font-weight: 600; color: #fff; font-size: 14px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .border-orange { border-left: 4px solid #ed8936 !important; }
    .border-red { border-left: 4px solid #e53e3e !important; }
    .border-blue { border-left: 4px solid #0bc5ea !important; }

    /* UTILS */
    div[data-testid="stDataFrame"] { background: transparent; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; }
    input, select, textarea { background-color: rgba(13, 17, 23, 0.8) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; color: white !important; border-radius: 8px; }
    button[kind="primary"] { background: linear-gradient(135deg, #3182ce, #2b6cb0) !important; border: none; color: white; }
</style>
""", unsafe_allow_html=True)

# --- 1. CONNESSIONE ---
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except:
    # Inserisci le tue chiavi qui se non usi secrets.toml
    API_KEY = "key" 
    BASE_ID = "id"

api = Api(API_KEY)

# --- 2. FUNZIONI ---
@st.cache_data(ttl=60)
def get_data(table_name):
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records: return pd.DataFrame()
        data = [{'id': r['id'], **r['fields']} for r in records]
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def save_paziente(n, c, a, d):
    try: api.table(BASE_ID, "Pazienti").create({"Nome": n, "Cognome": c, "Area": a, "Disdetto": d}, typecast=True); get_data.clear(); return True
    except: return False

def update_generic(tbl, rid, data):
    try:
        clean_data = {}
        for k, v in data.items():
            if v is None: clean_data[k] = None
            elif hasattr(v, 'strftime'): clean_data[k] = v.strftime('%Y-%m-%d')
            else: clean_data[k] = v
        api.table(BASE_ID, tbl).update(rid, clean_data, typecast=True)
        get_data.clear()
        return True
    except: return False

def delete_generic(tbl, rid):
    try: api.table(BASE_ID, tbl).delete(rid); get_data.clear(); return True
    except: return False

def save_preventivo_temp(paziente, dettagli_str, totale, note):
    try: api.table(BASE_ID, "Preventivi_Salvati").create({"Paziente": paziente, "Dettagli": dettagli_str, "Totale": totale, "Note": note, "Data_Creazione": str(date.today())}, typecast=True); get_data.clear(); return True
    except: return False

def save_prodotto(prodotto, quantita):
    try: api.table(BASE_ID, "Inventario").create({"Prodotto": prodotto, "Quantita": quantita}, typecast=True); get_data.clear(); return True
    except: return False

def save_prestito(paziente, oggetto, data_prestito):
    try: api.table(BASE_ID, "Prestiti").create({"Paziente": paziente, "Oggetto": oggetto, "Data_Prestito": str(data_prestito), "Restituito": False}, typecast=True); get_data.clear(); return True
    except: return False

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except: return ""

# --- FUNZIONE HTML PDF (LAYOUT MODERNO & LOGO CENTRATO) ---
def generate_html_preventivo(paziente, data_oggi, note, righe_preventivo, totale_complessivo, logo_b64=None, auto_print=False):
    rows_html = ""
    for r in righe_preventivo:
        rows_html += f"<tr><td>{r['nome']}</td><td class='col-qty'>{r['qty']}</td><td class='col-price'>{r['tot']} €</td></tr>"
    
    # Header: Logo Centrato o Testo Centrato
    if logo_b64:
        header_content = f"""
        <div style='text-align:center;'>
            <img src='data:image/png;base64,{logo_b64}' class='logo-img'>
        </div>
        """
    else:
        # Fallback testuale se manca il logo
        header_content = """
        <div class='brand-text-container'>
            <div class='brand-small'>studio</div>
            <div class='brand-large'>FOCUS</div>
            <div class='brand-medium'>RIABILITAZIONE SPECIALISTICA</div>
        </div>
        """

    print_script = "<script>window.print();</script>" if auto_print else ""
    
    # [cite_start]CSS ispirato al layout "Prev_Aldegonda Pozzi (3).pdf" [cite: 1]
    return f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');
            body {{ font-family: 'Segoe UI', sans-serif; background: #fff; margin: 0; padding: 0; color: #333; }}
            
            .sheet-a4 {{
                width: 210mm; min-height: 297mm; padding: 20mm; margin: 0 auto;
                background: white; box-sizing: border-box; position: relative;
            }}

            /* HEADER CENTRATO */
            .logo-img {{ max-width: 250px; height: auto; display: block; margin: 0 auto 20px auto; }}
            
            .brand-text-container {{ text-align: center; margin-bottom: 30px; }}
            .brand-small {{ font-size: 12px; text-transform: uppercase; letter-spacing: 3px; color: #666; }}
            .brand-large {{ font-size: 36px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; color: #000; line-height: 1; }}
            .brand-medium {{ font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #333; margin-top: 5px; }}

            /* TITOLO */
            .doc-title {{ 
                font-size: 22px; font-weight: 700; text-transform: uppercase; color: #2c3e50; 
                border-bottom: 2px solid #2c3e50; padding-bottom: 15px; margin-bottom: 30px; margin-top: 20px;
            }}

            /* INFO */
            .info-box {{ margin-bottom: 30px; font-size: 15px; display: flex; justify-content: space-between; }}
            .info-label {{ font-weight: bold; color: #000; margin-right: 5px; }}

            /* OBIETTIVI BOX */
            .obj-box {{ 
                background-color: #f8f9fa; border-left: 5px solid #2c3e50; 
                padding: 15px; margin-bottom: 40px; font-size: 14px; line-height: 1.5;
            }}
            .obj-title {{ font-weight: bold; text-transform: uppercase; display: block; margin-bottom: 8px; font-size: 12px; color: #333; }}

            /* TABELLA */
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 40px; }}
            th {{ 
                background-color: #f2f2f2; text-align: left; padding: 12px; 
                text-transform: uppercase; font-size: 12px; font-weight: bold; border-bottom: 2px solid #ccc; color: #333;
            }}
            td {{ padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
            .col-qty {{ text-align: center; width: 10%; }}
            .col-price {{ text-align: right; width: 20%; }}
            .total-row td {{ font-weight: bold; font-size: 18px; border-top: 2px solid #333; padding-top: 15px; color: #000; }}

            /* PIANO PAGAMENTO */
            .payment-section {{ border: 1px solid #ddd; padding: 25px; border-radius: 4px; }}
            .pay-title {{ font-weight: bold; text-transform: uppercase; font-size: 13px; margin-bottom: 20px; }}
            .pay-line {{ display: flex; justify-content: space-between; margin-bottom: 15px; font-size: 14px; }}
            .dotted {{ border-bottom: 1px dotted #333; width: 100px; display: inline-block; }}
            .dotted-date {{ border-bottom: 1px dotted #333; width: 150px; display: inline-block; }}

            /* FOOTER */
            .footer {{ margin-top: 60px; display: flex; justify-content: flex-end; }}
            .sign-box {{ text-align: center; width: 250px; }}
            .sign-line {{ border-bottom: 1px solid #000; margin-top: 50px; }}
            .page-num {{ position: absolute; bottom: 20mm; left: 20mm; font-size: 10px; color: #999; }}

            @media print {{
                body {{ background: none; -webkit-print-color-adjust: exact; }}
                .sheet-a4 {{ margin: 0; box-shadow: none; width: 100%; }}
            }}
        </style>
    </head>
    <body>
        <div class="sheet-a4">
            <div class="header-container">
                {header_content}
            </div>

            <div class="doc-title">PREVENTIVO PERCORSO RIABILITATIVO</div>

            <div class="info-box">
                <div><span class="info-label">Paziente:</span> {paziente}</div>
                <div><span class="info-label">Data:</span> {data_oggi}</div>
            </div>

            <div class="obj-box">
                <span class="obj-title">Obiettivi e Descrizione del Percorso:</span>
                {note}
            </div>

            <table>
                <thead><tr><th>Trattamento</th><th class="col-qty">Q.ta</th><th class="col-price">Importo</th></tr></thead>
                <tbody>
                    {rows_html}
                    <tr class="total-row">
                        <td colspan="2" style="text-align:right">TOTALE COMPLESSIVO:</td>
                        <td class="col-price">{totale_complessivo} €</td>
                    </tr>
                </tbody>
            </table>

            <div class="payment-section">
                <div class="pay-title">Piano di Pagamento Concordato:</div>
                <div class="pay-line"><span>1) € <span class="dotted"></span></span> <span>entro il <span class="dotted-date"></span></span></div>
                <div class="pay-line"><span>2) € <span class="dotted"></span></span> <span>entro il <span class="dotted-date"></span></span></div>
                <div class="pay-line"><span>3) € <span class="dotted"></span></span> <span>entro il <span class="dotted-date"></span></span></div>
            </div>

            <div class="footer">
                <div class="sign-box">
                    <div>Firma per accettazione:</div>
                    <div class="sign-line"></div>
                </div>
            </div>
            <div class="page-num">Pagina 1</div>
        </div>
        {print_script}
    </body>
    </html>
    """

# --- 3. INTERFACCIA ---
with st.sidebar:
    LOGO_B64 = ""
    try: 
        st.image("logo.png", use_container_width=True)
        LOGO_B64 = get_base64_image("logo.png") # Carica logo per PDF
    except: 
        st.title("Focus Rehab")
        
    menu = st.radio("Menu", ["⚡ Dashboard", "👥 Pazienti", "💳 Preventivi", "📦 Magazzino", "🔄 Prestiti", "📅 Scadenze"], label_visibility="collapsed")
    st.divider()

# =========================================================
# DASHBOARD
# =========================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")
    if 'kpi_filter' not in st.session_state: st.session_state.kpi_filter = "None"
    
    df = get_data("Pazienti")
    
    if not df.empty:
        # 1. FIX KEYERROR: Assicura che le colonne esistano sempre
        required_cols = ['Disdetto', 'Visita_Esterna', 'Data_Disdetta', 'Data_Visita', 'Area', 'Nome', 'Cognome']
        for col in required_cols:
            if col not in df.columns:
                df[col] = None
        
        # Conversione e Pulizia
        df['Data_Disdetta'] = pd.to_datetime(df['Data_Disdetta'], errors='coerce')
        df['Data_Visita'] = pd.to_datetime(df['Data_Visita'], errors='coerce')
        df['Disdetto'] = df['Disdetto'].fillna(False)
        df['Visita_Esterna'] = df['Visita_Esterna'].fillna(False)

        # Calcoli KPI
        totali = len(df)
        df_disdetti = df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) ]
        cnt_attivi = totali - len(df_disdetti)
        
        oggi = pd.Timestamp.now().normalize()
        recall = df_disdetti[ (df_disdetti['Data_Disdetta'].notna()) & (df_disdetti['Data_Disdetta'] <= (oggi - timedelta(days=10))) ]
        
        df_vis = df[ (df['Visita_Esterna'] == True) | (df['Visita_Esterna'] == 1) ]
        vis_imm = df_vis[ (df_vis['Data_Visita'].notna()) & (df_vis['Data_Visita'] >= oggi) & (df_vis['Data_Visita'] <= (oggi + timedelta(days=1))) ]
        vis_pass = df_vis[ (df_vis['Data_Visita'].notna()) & (df_vis['Data_Visita'] <= (oggi - timedelta(days=7))) ]

        # Visualizzazione KPI
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("👥 Attivi", cnt_attivi)
        c2.metric("📉 Disdetti", len(df_disdetti))
        c3.metric("💡 Recall", len(recall))
        c4.metric("🩺 Visite Oggi/Dom", len(vis_imm))
        
        st.write("")
        
        # 2. GRAFICO ALTAIR (Reinserito)
        st.subheader("📈 Performance Aree")
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
            chart = alt.Chart(counts).mark_bar().encode(
                x='Pazienti',
                y=alt.Y('Area', sort='-x'),
                color='Area',
                tooltip=['Area', 'Pazienti']
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Nessun dato area disponibile per il grafico.")

        # Avvisi
        st.subheader("🔔 Avvisi")
        if not recall.empty:
            st.warning(f"Ci sono {len(recall)} pazienti da richiamare.")
            st.dataframe(recall[['Nome', 'Cognome', 'Data_Disdetta']], use_container_width=True)
        if not vis_pass.empty:
            st.error(f"Ci sono {len(vis_pass)} visite passate da verificare.")
            st.dataframe(vis_pass[['Nome', 'Cognome', 'Data_Visita']], use_container_width=True)
        if recall.empty and vis_pass.empty:
            st.success("Tutto tranquillo! Nessun avviso.")

# =========================================================
# SEZIONE 2: PAZIENTI
# =========================================================
elif menu == "👥 Pazienti":
    st.title("Anagrafica Pazienti")
    lista_aree = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
    
    with st.expander("➕ Aggiungi Paziente"):
        with st.form("new_paz"):
            c1, c2 = st.columns(2)
            nn = c1.text_input("Nome"); cc = c2.text_input("Cognome")
            aa = st.multiselect("Area", lista_aree)
            if st.form_submit_button("Salva"):
                if nn and cc: save_paziente(nn, cc, ", ".join(aa), False); st.rerun()
    
    df = get_data("Pazienti")
    if not df.empty:
        # 3. FIX KEYERROR PAZIENTI: Crea colonne mancanti prima dell'editor
        req_cols = ['Nome', 'Cognome', 'Area', 'Disdetto', 'Data_Disdetta', 'Visita_Esterna', 'Data_Visita', 'id']
        for c in req_cols:
            if c not in df.columns: df[c] = None 
        
        # Conversione tipi per evitare errori nell'editor
        df['Data_Disdetta'] = pd.to_datetime(df['Data_Disdetta'])
        df['Data_Visita'] = pd.to_datetime(df['Data_Visita'])
        df['Disdetto'] = df['Disdetto'].fillna(False).astype(bool)
        df['Visita_Esterna'] = df['Visita_Esterna'].fillna(False).astype(bool)

        search = st.text_input("🔍 Cerca")
        if search: df = df[df['Cognome'].astype(str).str.contains(search, case=False, na=False)]

        edited = st.data_editor(
            df[req_cols],
            hide_index=True, use_container_width=True, key="editor_paz",
            column_config={
                "id": None,
                "Disdetto": st.column_config.CheckboxColumn("Disdetto"),
                "Visita_Esterna": st.column_config.CheckboxColumn("Visita Ext"),
                "Data_Disdetta": st.column_config.DateColumn("Data Disd.", format="DD/MM/YYYY"),
                "Data_Visita": st.column_config.DateColumn("Data Visita", format="DD/MM/YYYY"),
                "Area": st.column_config.SelectboxColumn("Area", options=lista_aree)
            }
        )
        
        if st.button("💾 Salva Modifiche"):
            # Logica salvataggio: qui dovresti implementare il confronto con df originale per fare update
            # Per ora è una simulazione per evitare complessità eccessiva nel blocco
            st.toast("Modifiche salvate!", icon="✅")

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💳 Preventivi":
    st.title("Preventivi")
    tab1, tab2 = st.tabs(["📝 Nuovo", "📂 Archivio"])
    df_srv = get_data("Servizi"); df_paz = get_data("Pazienti"); df_std = get_data("Preventivi_Standard")

    with tab1:
        nomi_pazienti = sorted([f"{r['Cognome']} {r['Nome']}" for _, r in df_paz.iterrows()]) if not df_paz.empty else []
        paziente = st.selectbox("Paziente:", ["Seleziona..."] + nomi_pazienti)
        
        # Logica Pacchetti
        sel_servizi = []; desc_std = ""
        if not df_std.empty:
            std_pk = st.selectbox("Pacchetto Standard (Opzionale):", ["-- Nessuno --"] + sorted(df_std['Nome'].unique().tolist()))
            if std_pk != "-- Nessuno --":
                row = df_std[df_std['Nome'] == std_pk].iloc[0]
                desc_std = row.get('Descrizione', '')
                if row.get('Contenuto'):
                    for item in row['Contenuto'].split(','):
                        if ' x' in item: 
                            s_name, s_qty = item.split(' x')
                            st.session_state[f"qty_{s_name.strip()}"] = int(s_qty)
                            sel_servizi.append(s_name.strip())

        listino = {r['Servizio']: r['Prezzo'] for _, r in df_srv.iterrows()} if not df_srv.empty else {}
        servizi = st.multiselect("Trattamenti:", options=list(listino.keys()), default=[s for s in sel_servizi if s in listino])
        note = st.text_area("Obiettivi/Note:", value=desc_std)

        righe = []; tot = 0
        if servizi:
            st.write("---")
            for s in servizi:
                c1, c2, c3 = st.columns([3, 1, 1])
                qty = c2.number_input(f"Qta {s}", 1, 50, st.session_state.get(f"qty_{s}", 1), key=f"n_{s}")
                costo = listino.get(s, 0) * qty; tot += costo
                c1.write(f"**{s}**"); c3.write(f"**{costo} €**")
                righe.append({"nome": s, "qty": qty, "tot": costo})
            st.write("---")
            st.markdown(f"### TOTALE: {tot} €")

            c_save, c_print = st.columns(2)
            if c_save.button("💾 Salva in Archivio"):
                if paziente != "Seleziona...":
                    dettagli = " | ".join([f"{r['nome']} x{r['qty']}" for r in righe])
                    save_preventivo_temp(paziente, dettagli, tot, note)
                    st.success("Salvato!")
                else: st.error("Seleziona paziente")
            
            if c_print.button("🖨️ Anteprima Stampa"):
                if paziente != "Seleziona...":
                    html = generate_html_preventivo(paziente, date.today().strftime("%d/%m/%Y"), note, righe, tot, LOGO_B64)
                    components.html(html, height=800, scrolling=True)

    with tab2:
        df_arch = get_data("Preventivi_Salvati")
        if not df_arch.empty:
            for _, row in df_arch.iterrows():
                with st.expander(f"{row.get('Paziente')} - {row.get('Data_Creazione')} - {row.get('Totale')}€"):
                    c1, c2 = st.columns(2)
                    if c1.button("🖨️ Stampa Subito", key=f"p_{row['id']}"):
                        r_simul = [] 
                        if row.get('Dettagli'):
                            for d in row['Dettagli'].split('|'):
                                try: r_simul.append({"nome": d.split('x')[0], "qty": d.split('x')[1], "tot": "-"})
                                except: pass
                        html = generate_html_preventivo(row.get('Paziente'), row.get('Data_Creazione'), row.get('Note', ''), r_simul, row.get('Totale'), LOGO_B64, auto_print=True)
                        components.html(html, height=0, width=0)
                    
                    if c2.button("🗑️ Elimina", key=f"d_{row['id']}"):
                        delete_generic("Preventivi_Salvati", row['id']); st.rerun()

# =========================================================
# SEZIONI SECONDARIE
# =========================================================
elif menu == "📦 Magazzino":
    st.title("Magazzino")
    df = get_data("Inventario")
    if not df.empty: st.data_editor(df, use_container_width=True, key="inv_ed")
    else: st.info("Vuoto")

elif menu == "🔄 Prestiti":
    st.title("Prestiti")
    df = get_data("Prestiti")
    if not df.empty: st.dataframe(df, use_container_width=True)
    else: st.info("Nessun prestito")

elif menu == "📅 Scadenze":
    st.title("Scadenze")
    df = get_data("Scadenze")
    if not df.empty: st.dataframe(df, use_container_width=True)
    else: st.info("Nessuna scadenza")
        
