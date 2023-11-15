import streamlit as st
import streamlit_modal as st_modal
import httpx
import polars as pl
import pandas as pd
import io
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Kontroly rozvrhů",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("Kontroly rozvrhů")

cols = [*st.columns([1, 2, 2, 2])]
infoMessage = st.empty()
errorMessage = st.empty()

with cols[0]:
    col1, col2 = st.columns(2)
    with col1:
        # Vzato z https://ws.ujep.cz/ws/web?pp_locale=en&pp_reqType=render&pp_page=webaccess
        nabidka = """
<option value="FF">FF - Faculty of Arts</option>
<option value="FSC">FSC - Faculty of Social and Economic Studies, Lifelong Education</option>
<option value="FSE">FSE - Faculty of Social and Economic Studies</option>
<option value="FSI">FSI - Faculty of Mechanical Engineering</option>
<option value="FUD">FUD - Faculty of Art and Design</option>
<option value="FZS">FZS - Faculty of Health Studies</option>
<option value="FŽP">FŽP - Faculty of Environment</option>
<option value="PF">PF - Faculty of Education</option>
<option value="PFC">PFC - Faculty of Education Centre of Lifelong Education</option>
<option value="PRF" selected="selected">PRF - Faculty of Science</option>
<option value="REK">REK - Jan Evangelista Purkyně University in Ústí nad Labem</option>
<option value="RZS">RZS - Jan Evangelista Purkyně University</option>
<option value="U3V">U3V - University of the Third Age</option>
<option value="UHS">UHS - Institute of Humanities</option>
<option value="UPV">UPV - Institute of Natural Science</option>
<option value="UZM">UZM - Institute of Health Studies</option>
<option value="UZS">UZS - Institute of Health Studies</option>
<option value="UZT">UZT - Institute of Health Studies</option>
<option value="UZU">UZU - Institute of Health Studies</option>
<option value="ÚTŘ">ÚTŘ - Institute of Production Technology and Management</option>
<option value="IVK" class="pv_option_not_valid">IVK - IVK</option>"""
        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(nabidka, 'html.parser')

        # Search for the element with id="REST_programy_getStudijniProgramy_GETfakulta"
        options = soup.find_all('option')
        if not options or len(options) == 0:
            # col1, col2 = errorMessage.columns([3,1])
            infoMessage.code(soup.prettify())
            # col2.error("Nepodařilo se načíst výčet fakult")
            errorMessage.error("Nepodařilo se načíst výčet fakult")
            st.stop()
        fakulty = map(lambda x: x.get("value"), options)
        st.selectbox("Fakulta", fakulty)
    with col2:
        st.button("filtr", key="filtrProgramu")
with cols[1]:
    col1, col2 = st.columns(2)
    with col1:
        getStudijniProgramy  = httpx.get("https://ws.ujep.cz/ws/services/rest2/programy/getStudijniProgramy?kod=%25&fakulta=PRF&outputFormat=JSON")
        if getStudijniProgramy.status_code != 200:
            st.error("Nepodařilo se načíst seznam studijních programů")
            st.stop()
        studijniProgramy = getStudijniProgramy.json().get("programInfo")
        selected = st.selectbox("Studijní program", map (lambda x: x.get("nazev"), studijniProgramy))
        selectedIdno = list(filter(lambda x: x.get("nazev") == selected, studijniProgramy))[0].get("stprIdno") # FIXME: nesmí mít více stejný název
        # vezmi vybrane strpIdno
    with col2:
        st.button("filtr", "studijniProgramFiltr")
with cols[2]:
    col1, col2 = st.columns(2)
    with col1:
        getOboryStudijnihoProgramu = httpx.get(f"https://ws.ujep.cz/ws/services/rest2/programy/getOboryStudijnihoProgramu?outputFormat=JSON&stprIdno={selectedIdno}")
        if getOboryStudijnihoProgramu.status_code != 200:
            st.error("Nepodařilo se načíst seznam oborů studijního programu")
            st.stop()
        obory = getOboryStudijnihoProgramu.json().get("oborInfo")
        oborNazvy = map(lambda x: x.get("nazev"), obory)
        st.selectbox("Obor", oborNazvy)
        # vezmi vybrane oborIdno
    with col2:
        st.button("filtr", key="oborFiltr")
with cols[3]:
    col1, col2 = st.columns(2)
    with col1:
        getPlanyOboru = httpx.get("https://ws.ujep.cz/ws/services/rest2/programy/getPlanyOboru?oborIdno=1739&outputFormat=JSON")
        if getPlanyOboru.status_code != 200:
            st.error("Nepodařilo se načíst seznam plánů oboru")
            st.stop()
        plany = getPlanyOboru.json().get("planInfo")
        planNazvy = map(lambda x: x.get("nazev"), plany)
        st.selectbox("Plán oboru", planNazvy)
        # vezmi vybrane stplIdno
    with col2:
        st.button("filtr", key="planOboruFiltr")

st.divider()
getSegmentyPlanu = httpx.get("https://ws.ujep.cz/ws/services/rest2/programy/getSegmentyPlanu?stplIdno=15660&outputFormat=JSON")
if getSegmentyPlanu.status_code != 200:
    st.error("Nepodařilo se načíst seznam segmentů plánu")
    st.stop()
segmentyPlanu = getSegmentyPlanu.json().get("segmentInfo")
for segment in segmentyPlanu:
    with st.spinner("Získávám data ze stagu..."):
        st.header(segment.get("nazev"))
        sespIdno = segment.get("sespIdno")
        getBlokySegmentu = httpx.get("https://ws.ujep.cz/ws/services/rest2/programy/getBlokySegmentu?sespIdno=28007&outputFormat=JSON")
        if getBlokySegmentu.status_code != 200:
            st.error("Nepodařilo se načíst seznam bloků segmentu")
            st.stop()
        # vyber blokIdno
        getPredmetyByBlokFullInfo = httpx.get("https://ws.ujep.cz/ws/services/rest2/predmety/getPredmetyByBlokFullInfo?blokIdno=42421&outputFormat=XLSX")
        if getPredmetyByBlokFullInfo.status_code != 200:
            st.error("Nepodařilo se načíst seznam předmětů bloku")
            st.stop()
        text = getPredmetyByBlokFullInfo.content
        # print(text.decode("utf-8"))
        df = pl.read_excel(io.BytesIO(text))
        st.dataframe(df.to_pandas())

st.divider()
st.header("Nalezené chyby:")
filtryChyb = [{"Nemá jednoho garanta":True}, {"Nemá rozvrh":False}, {"Nesedí vyučující do rozvrhu":True}, {"Učící vede seminář":True}, {"atd.":False}]
columns = [*st.columns(len(filtryChyb))]
for i, filtr in enumerate(filtryChyb):
    with columns[i]:
        for key, value in filtr.items():
            st.checkbox(key, value=value)
            break


st.warning("Předmět nemá název")
st.error("Garant nemá titul")

# TODO: analýza chyb