import streamlit as st
from openai import OpenAI
import json, os, pandas as pd, base64, io, re
from datetime import datetime, timedelta

# ==========================================
# 1. API AYARLARI (Direct OpenAI)
# ==========================================
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="VC Strategic Planner Pro", layout="wide", page_icon="🏥")

# --- VERİ YÖNETİMİ ---
DB_FILE = "staff_backup_260504.json"
def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

if 'staff_list' not in st.session_state: st.session_state.staff_list = load_data()
if 'edit_index' not in st.session_state: st.session_state.edit_index = None
if 'weekly_notes' not in st.session_state: st.session_state.weekly_notes = ""

# --- VISION FONKSİYONU ---
def encode_image(image_file): return base64.b64encode(image_file.read()).decode('utf-8')

# --- SIDEBAR: TARİH VE HAFTA SEÇİMİ (İSTEDİĞİN ÖZELLİK) ---
st.sidebar.markdown("### 📅 Planeringsperiod")
raw_date = st.sidebar.date_input("Välj ett datum", value=datetime.now())
# Pazartesiye yuvarlama
start_monday = raw_date - timedelta(days=raw_date.weekday())
v_start = start_monday.isocalendar()[1]
duration = st.sidebar.select_slider("Antal veckor", options=[1, 2, 3, 4, 5, 6], value=1)
v_end = (start_monday + timedelta(weeks=duration-1)).isocalendar()[1]

range_text = f"v.{v_start}" if duration == 1 else f"v.{v_start} - v.{v_end}"

# AI için hatasız tarih listesi
date_list_text = ""
for w in range(duration):
    monday_of_week = start_monday + timedelta(weeks=w)
    v_num = monday_of_week.isocalendar()[1]
    date_list_text += f"Vecka {v_num}: "
    for i, d_name in enumerate(["Mån", "Tis", "Ons", "Tor", "Fre"]):
        actual_date = monday_of_week + timedelta(days=i)
        date_list_text += f"{d_name} {actual_date.strftime('%d %b')}, "
    date_list_text += "\n"

st.sidebar.info(f"Vald: {range_text}")

# --- HEADER ---
st.markdown(f"<h1 style='color: #0077b6; text-align: center;'>🏥 Lyckeby Vårdcentral Planner <small style='color: grey; font-size: 15px;'>v56.4 Pure GPT-4o Power</small></h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["👥 Team & Foto", "📋 Tidsplan Översikt", "🚀 Generera Strategisk Plan"])

# --- TAB 1: TEAM & PROFILER ---
with tab1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📸 Läs in från foto")
        uploaded_file = st.file_uploader("Ladda upp personallista", type=["jpg", "png", "jpeg"])
        if uploaded_file and st.button("Analysera Bild"):
            base64_img = encode_image(uploaded_file)
            with st.spinner("GPT-4o Vision läser dokumentet..."):
                try:
                    v_res = openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": [
                            {"type": "text", "text": "Hitta namn, grad (%) och noter. JSON: [{'namn': '...', 'oran': 100, 'noter': '', 'hyr': false, 'p_mott': 30, 'p_akut': 25, 'p_admin': 25, 'p_rec': 10, 'p_tel': 10}]"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                        ]}]
                    )
                    raw_content = v_res.choices[0].message.content
                    json_match = re.search(r'\[.*\]', raw_content, re.DOTALL)
                    if json_match:
                        st.session_state.staff_list.extend(json.loads(json_match.group(0)))
                        with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(st.session_state.staff_list, f)
                        st.rerun()
                except: st.error("Bildfel.")

        st.divider()
        idx = st.session_state.edit_index
        with st.form("staff_form_v56_4"):
            namn = st.text_input("Namn", value=st.session_state.staff_list[idx]['namn'] if idx is not None else "")
            oran = st.slider("Grad (%)", 10, 100, st.session_state.staff_list[idx].get('oran', 100) if idx is not None else 100)
            st.write("**Arbetsfördelning (%)**")
            pm = st.number_input("Mott (%)", value=st.session_state.staff_list[idx].get('p_mott', 30) if idx is not None else 30)
            pa = st.number_input("Akut (%)", value=st.session_state.staff_list[idx].get('p_akut', 25) if idx is not None else 25)
            pad = st.number_input("Admin (%)", value=st.session_state.staff_list[idx].get('p_admin', 25) if idx is not None else 25)
            pr = st.number_input("Rec (%)", value=st.session_state.staff_list[idx].get('p_rec', 10) if idx is not None else 10)
            pt = st.number_input("Tel (%)", value=st.session_state.staff_list[idx].get('p_tel', 10) if idx is not None else 10)
            noter = st.text_area("Önskemål/Noter", value=st.session_state.staff_list[idx].get('noter', '') if idx is not None else "")
            hyr = st.checkbox("Hyr-läkare", value=st.session_state.staff_list[idx].get('hyr', False) if idx is not None else False)
            if st.form_submit_button("Spara Profil"):
                entry = {"namn": namn, "oran": oran, "noter": noter, "hyr": hyr, "p_mott": pm, "p_akut": pa, "p_admin": pad, "p_rec": pr, "p_tel": pt}
                if idx is not None: st.session_state.staff_list[idx] = entry
                else: st.session_state.staff_list.append(entry)
                st.session_state.edit_index = None
                with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(st.session_state.staff_list, f, ensure_ascii=False, indent=4)
                st.rerun()

    with c2:
        st.subheader("Personalöversikt")
        for i, p in enumerate(st.session_state.staff_list):
            with st.expander(f"👤 {p['namn']} ({p['oran']}%) {'[HYR]' if p.get('hyr') else ''}"):
                st.write(f"Mott: {p.get('p_mott')}% | Rec: {p.get('p_rec')}% | Tel: {p.get('p_tel')}%")
                eb1, eb2 = st.columns(2)
                if eb1.button("Redigera", key=f"edit_{i}"): st.session_state.edit_index = i; st.rerun()
                if eb2.button("Radera", key=f"del_{i}"): 
                    st.session_state.staff_list.pop(i)
                    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(st.session_state.staff_list, f)
                    st.rerun()
        if st.session_state.staff_list:
            st.download_button("📥 Ladda ner Backup (JSON)", json.dumps(st.session_state.staff_list, indent=4), "staff_data_v20.json")

# --- TAB 2: ÖVERSIKT ---
with tab2:
    st.info(f"Period: **{range_text}**")
    st.text(f"Datumlista:\n{date_list_text}")

# --- TAB 3: GENERERA ---
with tab3:
    st.session_state.weekly_notes = st.text_area("Veckans justeringar:", value=st.session_state.weekly_notes)
    if st.button("🚀 GENERERA STRATEGISK PLAN", type="primary"):
        week_type = "JÄMN" if v_start % 2 == 0 else "UDDA"
        mtg_time = "08:00-10:00" if v_start % 2 == 0 else "08:00-09:00"
        
        with st.spinner("GPT-4o optimerar klinikens resurser..."):
            try:
                prompt = f"""Du är en strategisk chefsplanerare. Skapa en plan för dessa exakta datum:
                {date_list_text}
                
                PERSONAL: {st.session_state.staff_list}
                NOTER: {st.session_state.weekly_notes}

                DINA 9 STRIKTA REGLER:
                1. ÖLI 10-12: Exakt 1 person per dag (får ej vara dispo samma dag).
                2. DISPO FM (08:30-12:30): Exakt 1 person per dag.
                3. DISPO EM (12:30-17:00): Exakt 1 person per dag.
                4. TORSDAG FM: Hyrläkaren SKA vara DISPONIBEL FM. Inga ordinarie på dispo då.
                5. DISPO-UPPGIFT: FM-dispo har Tel/Rec/Admin på EM. EM-dispo har Tel/Rec/Admin na FM.
                6. STUDENTSTÖD: Kopplas till alla Dispo-pass.
                7. BVC: Planera BVC ons/tor ENDAST om det står 'BVC' i noter.
                8. RONDTID 11:30: För alla utom dispo, bvc, öli.
                9. MÖTE: Torsdag morgon ({mtg_time}) för alla ordinarie.

                KALKYL: Beräkna exakt antal timmar per vecka för Mott, Akut, Admin, Rec, Tel utifrån de individuella %-profilerna för VARJE läkare.
                FORMAT: Presentera 'Veckokalkyl per person' och 'Dagliga strategiska roller' tydligt."""

                response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": "Du är en expert på rättvis klinikplanering. Skapa inga standardmallar, variera rollerna rättvist per vecka."},
                              {"role": "user", "content": prompt}]
                )
                st.markdown(response.choices[0].message.content)
            except Exception as e: st.error(f"Hata: {e}")