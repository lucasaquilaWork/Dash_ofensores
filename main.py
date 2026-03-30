import streamlit as st
import pandas as pd
import gspread
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

# -----------------------------
# 📥 CARREGAR DADOS
# -----------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    sheet = client.open("Ofensores LSP_77 _ Guarulhos").worksheet("dsh-base")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = carregar_dados()

# -----------------------------
# 🧠 TRATAMENTO
# -----------------------------
df["ERROS"] = df["PACOTE EM ABERTO"] + df["OnHold"]
df["TAXA_ERRO"] = df["ERROS"] / df["Soma de pacotes"]

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
# 🏆 TOP VOLUME
# -----------------------------
st.subheader("🏆 Top 10 por Volume")

top_volume = df.sort_values("Soma de pacotes", ascending=False).head(10)

st.bar_chart(
    top_volume.set_index("NOME")["Soma de pacotes"]
)

# -----------------------------
# 🚨 TOP ERROS
# -----------------------------
st.subheader("🚨 Top 10 com Mais Erros")

top_erros = df.sort_values("ERROS", ascending=False).head(10)

st.bar_chart(
    top_erros.set_index("NOME")["ERROS"]
)

# -----------------------------
# 📋 TABELA
# -----------------------------
st.subheader("📋 Dados detalhados")
st.dataframe(df, use_container_width=True)
