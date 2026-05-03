import streamlit as st
from openai import OpenAI
import json, os, pandas as pd, base64, io, re
from datetime import datetime, timedelta

# ==========================================
# 1. API AYARLARI
# ==========================================
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"],
)

st.set_page_config(page_title="VC Strategic Planner Pro", layout="wide", page_icon="🏥")

# --- VERİ YÖNETİMİ ---
DB_FILE = "staff_data_v20.json"
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

# --- HEADER ---
st.markdown("<h1 style='color: #0077b6; text-align: center;'>🏥 Lyckeby Vårdcentral Planner <small style='color: grey; font-size: 15px;'>v51.0 Individual Assignments</small></h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["👥 Team & Foto", "📅 Planeringsperiod", "🚀 Generera Individuella Listor"])

# --- TAB 1: TEAM & PROFILER ---
with tab1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📸 Läs in från foto")
        uploaded_file = st.file_uploader("Ladda upp personallista (OCR)", type=["jpg", "png", "jpeg"])
        if uploaded_file and st.button("Analysera Bild"):
            base64_img = encode_image(uploaded_file)
            with st.spinner("AI läser dokumentet..."):
                try:
                    v_res = openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": [
                            {"type": "text", "text": "Hitta namn, grad (%) ve noter. Svara ENDAST som JSON: [{'namn': '...', 'oran': 100, 'noter': '', 'hyr': false, 'p_mott': 30, 'p_akut': 25, 'p_admin': 25, 'p_rec': 10, 'p_tel': 10}]"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                        ]}]
                    )
                    raw_content = v_res.choices[0].message.content
                    json_match = re.search(r'\[.*\]', raw_content, re.DOTALL)
                    if json_match:
                        st.session_state.staff_list.extend(json.loads(json_match.group(0)))
                        with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(st.session_state.staff_list, f)
                        st.rerun()
                except: st.error("Kunde inte läsa bilden.")

        st.divider()
        idx = st.session_state.edit_index
        with st.form("staff_form_v51"):
            namn = st.text_input("Namn", value=st.session_state.staff_list[idx]['namn'] if idx is not None else "")
            oran = st.slider("Grad (%)", 10, 100, st.session_state.staff_list[idx].get('oran', 100) if idx is not None else 100)
            st.write("**Individuell fördelning (%)**")
            pm = st.number_input("Mottagning", value=st.session_state.staff_list[idx].get('p_mott', 30) if idx is not None else 30)
            pa = st.number_input("Akut", value=st.session_state.staff_list[idx].get('p_akut', 25) if idx is not None else 25)
            pad = st.number_input("Admin", value=st.session_state.staff_list[idx].get('p_admin', 25) if idx is not None else 25)
            pr = st.number_input("Recept", value=st.session_state.staff_list[idx].get('p_rec', 10) if idx is not None else 10)
            pt = st.number_input("Telefon", value=st.session_state.staff_list[idx].get('p_tel', 10) if idx is not None else 10)
            noter = st.text_area("Noter", value=st.session_state.staff_list[idx].get('noter', '') if idx is not None else "")
            hyr = st.checkbox("Hyr-läkare", value=st.session_state.staff_list[idx].get('hyr', False) if idx is not None else False)
            if st.form_submit_button("Spara"):
                entry = {"namn": namn, "oran": oran, "noter": noter, "hyr": hyr, "p_mott": pm, "p_akut": pa, "p_admin": pad, "p_rec": pr, "p_tel": pt}
                if idx is not None: st.session_state.staff_list[idx] = entry
                else: st.session_state.staff_list.append(entry)
                st.session_state.edit_index = None
                with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(st.session_state.staff_list, f, ensure_ascii=False, indent=4)
                st.rerun()

    with c2:
        st.subheader("Aktuellt Team")
        for i, p in enumerate(st.session_state.staff_list):
            with st.expander(f"👤 {p['namn']} ({p['oran']}%)"):
                st.write(f"Mott: {p.get('p_mott')}% | Admin: {p.get('p_admin')}% | Rec: {p.get('p_rec')}% | Tel: {p.get('p_tel')}%")
                b1, b2 = st.columns(2)
                if b1.button("Redigera", key=f"ed_{i}"): st.session_state.edit_index = i; st.rerun()
                if b2.button("Radera", key=f"de_{i}"): 
                    st.session_state.staff_list.pop(i)
                    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(st.session_state.staff_list, f)
                    st.rerun()

# --- TAB 2: PERIOD ---
with tab2:
    st.subheader("📅 Planeringsperiod")
    c_cal, c_dur = st.columns(2)
    with c_cal:
        raw_date = st.date_input("Välj startdatum", value=datetime.now())
        start_monday = raw_date - timedelta(days=raw_date.weekday())
        v_start = start_monday.isocalendar()[1]
    with c_dur:
        duration = st.select_slider("Antal veckor", options=[1, 2, 3, 4, 5, 6])
        v_end = (start_monday + timedelta(weeks=duration-1)).isocalendar()[1]
    range_text = f"v.{v_start}" if duration == 1 else f"v.{v_start} - v.{v_end}"
    st.info(f"Planerar: {range_text}")

# --- TAB 3: GENERERA ---
with tab3:
    st.session_state.weekly_notes = st.text_area("Veckans justeringar (t.ex. ledighet, BVC):", value=st.session_state.weekly_notes)
    if st.button("🚀 GENERERA INDIVIDUELLA ARBETSUPPGIFTER", type="primary"):
        week_type = "JÄMN" if v_start % 2 == 0 else "UDDA"
        mtg_time = "08:00-10:00" if v_start % 2 == 0 else "08:00-09:00"
        with st.spinner("AI-agenterna skapar individuella arbetsplaner..."):
            try:
                prompt = f"""Du är en planeringschef. Skapa en detaljerad individuell arbetsplan för {range_text}.
                PERSONAL: {st.session_state.staff_list}
                NOTER: {st.session_state.weekly_notes}

                DIN UPPGIFT (FÖLJ STRIKT):
                1. INDIVIDUELL KALKYL: För VARJE person, beräkna exakt antal timmar per vecka för:
                   - Mottagning
                   - Röd Tid (Akut)
                   - Admin
                   - Recept
                   - Telefon
                   (Använd läkarens personliga %-profil. 100% tjänst = 40 timmar totalt).
                
                2. ROLLFÖRDELNING: Lista vilka specifika dagar varje person ska vara:
                   - ÖLI (10-12)
                   - DISPONIBEL FM (08:30-12:30)
                   - DISPONIBEL EM (12:30-17:00)
                
                3. REGLER ATT KONTROLLERA:
                   - Hyrläkare är DISPO torsdag FM.
                   - Inga patienter/rond/fika under dispo-tid.
                   - Torsdagsmöte {mtg_time} för ordinarie.
                
                PRESENTATIONSFORMAT (KRAV):
                Presentera resultatet person för person. Varje doktor ska ha en egen sektion med sina timmar och sina tilldelade specialdagar (ÖLI/DISPO)."""

                response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": "Du ger tydliga, personliga instruktioner för varje läkare."},
                              {"role": "user", "content": prompt}]
                )
                st.markdown(response.choices[0].message.content)
            except Exception as e: st.error(f"Hata: {e}")