import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2.service_account import Credentials

# -----------------------------
# ⚙️ CONFIG
# -----------------------------
st.set_page_config(page_title="Dashboard Motoristas", layout="wide")
st.title("📊 Dashboard de Motoristas")

# -----------------------------
# 🔐 CONEXÃO GOOGLE SHEETS
# -----------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)
st.write(st.secrets["gcp_service_account"]["client_email"])
# -----------------------------
# 📥 CARREGAR DADOS
# -----------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    sheet = client.open_by_key("1fKdf4zNs5CjZm9wKv_FaBnZeiuR1isbP4Wby9lD40Lw").worksheet("dsh-base")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = carregar_dados()

# -----------------------------
# 🧠 TRATAMENTO
# -----------------------------
df["ERROS"] = df["PACOTE EM ABERTO"] + df["OnHold"]
df["TAXA_ERRO"] = df["ERROS"] / df["Soma de pacotes"]

# 🔥 STATUS DE PERFORMANCE
df["STATUS"] = df["TAXA_ERRO"].apply(
    lambda x: "🔴 Crítico" if x > 0.05 else "🟡 Atenção" if x > 0.02 else "🟢 OK"
)

# -----------------------------
# 📌 KPIs
# -----------------------------
col1, col2, col3 = st.columns(3)

col1.metric("📦 Total Pacotes", int(df["Soma de pacotes"].sum()))
col2.metric("⚠️ Total Erros", int(df["ERROS"].sum()))
col3.metric("📉 Taxa Média", f"{df['TAXA_ERRO'].mean():.2%}")

# -----------------------------
# 🔍 FILTRO
# -----------------------------
motoristas = st.multiselect(
    "Filtrar motoristas",
    df["NOME"].unique()
)

if motoristas:
    df = df[df["NOME"].isin(motoristas)]

# -----------------------------
# 🏆 TOP VOLUME (HORIZONTAL)
# -----------------------------
st.subheader("🏆 Top 10 por Volume")

top_volume = df.sort_values("Soma de pacotes", ascending=False).head(10)

fig_volume = px.bar(
    top_volume,
    y="NOME",
    x="Soma de pacotes",
    text="Soma de pacotes",
    color="STATUS",
    orientation="h",
    title="Top 10 Motoristas por Volume"
)

fig_volume.update_layout(
    yaxis={'categoryorder': 'total ascending'}
)

st.plotly_chart(fig_volume, use_container_width=True)

# -----------------------------
# 🚨 TOP ERROS (HORIZONTAL)
# -----------------------------
st.subheader("🚨 Top 10 com Mais Erros")

top_erros = df.sort_values("ERROS", ascending=False).head(10)

fig_erros = px.bar(
    top_erros,
    y="NOME",
    x="ERROS",
    text="ERROS",
    color="STATUS",
    orientation="h",
    title="Top 10 Motoristas com Mais Erros"
)

fig_erros.update_layout(
    yaxis={'categoryorder': 'total ascending'}
)

st.plotly_chart(fig_erros, use_container_width=True)

# -----------------------------
# 📋 TABELA
# -----------------------------
st.subheader("📋 Dados detalhados")
st.dataframe(df, use_container_width=True)
