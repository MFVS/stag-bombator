import os
import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import polars as pl
import httpx
from datetime import datetime, timedelta
from io import StringIO
import sqlite3 as sql

# FIXME: joining dataframes loses lots of rows

PLANY_CACHE_FPATH = "cache/plany.csv"
OBORY_CACHE_FPATH = "cache/obory.csv"
PROGRAMY_CACHE_FPATH = "cache/programy.csv"

st.set_page_config(
    page_title="Kontroly STAGU",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

try: # ensure cache directory exists
    os.mkdir("cache")
except:
    pass

# ciselnik_programy = httpx.get("https://ws.ujep.cz/ws/services/rest2/ciselniky/getCiselnik?domena=PROGRAM&outputFormatEncoding=utf-8&outputFormat=CSV")
ciselnik_plany = httpx.get("https://ws.ujep.cz/ws/services/rest2/ciselniky/getCiselnik?domena=PLAN&outputFormat=CSV&outputFormatEncoding=utf-8")
if ciselnik_plany.status_code != 200:
    st.error("Nepodařilo se načíst seznam studijních programů")
    st.error(f"Response code {ciselnik_plany.status_code}")
    st.stop()
ciselnik_plany_df = pd.read_csv(StringIO(ciselnik_plany.text), sep=";")
# @st.cache_resource
def create_db():
    return sql.connect("cache/ciselniky.db")
db = create_db()
table_name = 'ciselnik_plany'
data_types = {col: ciselnik_plany_df[col].dtype for col in ciselnik_plany_df.columns}
create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join([f'{col} {data_types[col]}' for col in ciselnik_plany_df.columns])});"
db.execute(create_table_query)
# create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name}_new ({', '.join([f'{col} {data_types[col]}' for col in ciselnik_plany_df.columns])});"
# db.execute(create_table_query)
ciselnik_plany_df.to_sql(f"{table_name}_new", db, index=False, if_exists='replace')

new_plany = db.execute(f"SELECT * FROM {table_name}_new JOIN {table_name} USING (key) WHERE key IS NULL",).fetchall()
st.table(new_plany)
db.execute(f"DELETE FROM {table_name}")
db.executemany(f"INSERT INTO {table_name} VALUES ({','.join(len(new_plany[0]))}", new_plany)
st.table(ciselnik_plany_df)

should_reload_cache = not os.path.exists(PROGRAMY_CACHE_FPATH)
should_reload_cache = should_reload_cache or datetime.fromtimestamp(os.path.getmtime(PROGRAMY_CACHE_FPATH)) < datetime.now() - timedelta(days=1)

if not os.path.exists(PROGRAMY_CACHE_FPATH) or should_reload_cache:
    should_reload_cache = True
    next_year = datetime.now().year + 1
    getStudijniProgramy = httpx.get(f"https://ws.ujep.cz/ws/services/rest2/programy/getStudijniProgramy?kod=%25&outputFormatEncoding=utf-8&outputFormat=CSV&rok={next_year}")
    if getStudijniProgramy.status_code != 200:
        st.error("Nepodařilo se načíst seznam studijních programů")
        st.error(f"Response code {getStudijniProgramy.status_code}")
        st.stop()
    programy = StringIO(getStudijniProgramy.text)
    df_obory = pd.read_csv(programy, sep=";")
    df_obory.to_csv(PROGRAMY_CACHE_FPATH)
df_programy = pd.read_csv(PROGRAMY_CACHE_FPATH)
if not os.path.exists(OBORY_CACHE_FPATH) or should_reload_cache:
    should_reload_cache = True
    with st.spinner("Načítám seznam oborů studijních programů..."):
        obory = []
        for index, row in df_programy.iterrows():
            stprIdno = row.get("stprIdno")
            getOboryStudijnihoProgramu = httpx.get(f"https://ws.ujep.cz/ws/services/rest2/programy/getOboryStudijnihoProgramu?outputFormatEncoding=utf-8&outputFormat=CSV&stprIdno={stprIdno}")
            oboryContents = StringIO(getOboryStudijnihoProgramu.text)
            if getOboryStudijnihoProgramu.status_code != 200:
                st.error("Nepodařilo se načíst seznam oborů studijního programu")
                st.error(f"Response code {getOboryStudijnihoProgramu.status_code}")
                st.stop()
            obor = pd.read_csv(oboryContents, sep=";")
            obor["stprIdno"] = [stprIdno] * len(obor)
            obory.append(obor)
        df_obory = pd.concat(obory)
        df_obory.to_csv(OBORY_CACHE_FPATH)
df_obory = pd.read_csv(OBORY_CACHE_FPATH)
if not os.path.exists(PLANY_CACHE_FPATH) or should_reload_cache:
    should_reload_cache = True
    with st.spinner("Načítám seznam plánů oborů..."):
        plany = []
        for index, row in df_obory.iterrows():
            oborIdno = row.get("oborIdno")
            getPlanyOboru = httpx.get(f"https://ws.ujep.cz/ws/services/rest2/programy/getPlanyOboru?oborIdno={oborIdno}&outputFormatEncoding=utf-8&outputFormat=CSV")
            planyContents = StringIO(getPlanyOboru.text)
            if getPlanyOboru.status_code != 200:
                st.error("Nepodařilo se načíst seznam plánů oboru")
                st.error(f"Response code {getPlanyOboru.status_code}")
                st.stop()
            plany.append(pd.read_csv(planyContents, sep=";"))
        df_plany = pd.concat(plany)
        df_plany.to_csv(PLANY_CACHE_FPATH)
df_plany = pd.read_csv(PLANY_CACHE_FPATH)
st.info("pocet planu: " + str(len(df_plany)))
def dataframe_with_selections(df):
    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    # Get dataframe row-selections from user with st.data_editor
    edited_df = st.data_editor(
        df_with_selections,
        hide_index=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns,
    )

    # Filter the dataframe using the temporary column, then drop the column
    selected_rows = edited_df[edited_df.Select]
    return selected_rows.drop("Select", axis=1)
df_fakulty = pd.DataFrame(df_obory["fakulta"].unique())
# st.dataframe(df_katedry)
df_vybrane_fakulty = dataframe_with_selections(df_fakulty)
# st.info(df_vybrane_fakulty)
# st.dataframe(df_vybrane_fakulty)
if df_vybrane_fakulty.empty:
    st.info("Nothing selected")
    df_vybrane_fakulty = df_fakulty.copy()
    # df_vybrane_fakulty = df_vybrane_fakulty[df_vybrane_fakulty == [True]] # FIXME:
    col1, col2 = st.columns(2)
    col1.dataframe(df_vybrane_fakulty)
    col2.dataframe(df_fakulty)

with st.spinner("Vykresluji seznam oborů..."):
    df_zobrazene = df_programy.join(df_obory, on="stprIdno", lsuffix="_programy", rsuffix="_obory")
    df_zobrazene = df_zobrazene.join(df_plany, on="oborIdno", rsuffix="_plany")
    st.info("Dataframe memory: "+str(df_zobrazene.memory_usage(deep=True).sum()/1_000_000)+" MB")
    filtr = df_zobrazene["fakulta_programy"].isin(df_vybrane_fakulty["0"])
    # st.info(filtr)
    # st.dataframe(df_zobrazene["fakulta_programy"])
    # st.dataframe(filtr)
    # st.info(list(filtr))
    # selection = dataframe_with_selections(df_zobrazene[filtr])
    selection = dataframe_with_selections(df_zobrazene[filtr])
    st.write("Počet záznamů: "+str(len(df_zobrazene[filtr])))
st.write("Váš výběr:")
st.write(selection)