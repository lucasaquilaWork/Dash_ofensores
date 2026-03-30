import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np
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
    sheet = client.open_by_key("1rzpOtOm8IvYICGOABtyJfbu7WdLhamt8aWoju01YLwY").worksheet("dsh-base")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = carregar_dados()

# -----------------------------
# 🧠 TRATAMENTO
# -----------------------------
df["ERROS"] = df["PACOTE EM ABERTO"] + df["OnHold"]

df["TAXA_ERRO"] = df.apply(
    lambda x: x["ERROS"] / x["Soma de pacotes"] if x["Soma de pacotes"] > 0 else 0,
    axis=1
)

df["RECORRENCIA"] = df.apply(
    lambda x: x["Vezes"] / x["Atribuicoes"] if x["Atribuicoes"] > 0 else 0,
    axis=1
)

# 🔥 SCORE INTELIGENTE
df["SCORE"] = df["RECORRENCIA"] * np.log1p(df["Soma de pacotes"])

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
# 🏆 TOP 10 VOLUME
# -----------------------------
st.subheader("🏆 Top 10 por Volume")

top10_volume = df.sort_values("Soma de pacotes", ascending=False).head(10)

fig_volume = px.bar(
    top10_volume,
    y="NOME",
    x="Soma de pacotes",
    text="Soma de pacotes",
    color="STATUS",
    orientation="h"
)

fig_volume.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_volume, use_container_width=True, key=f"top10_volume_{len(df)}")

# -----------------------------
# 📉 TOP 10 RECORRÊNCIA (INTELIGENTE)
# -----------------------------
st.subheader("📉 Top 10 Recorrência (Ponderado)")

top10_score = df.sort_values("SCORE", ascending=False).head(10)

fig_score10 = px.bar(
    top10_score,
    y="NOME",
    x="SCORE",
    orientation="h",
    text=top10_score["RECORRENCIA"].apply(lambda x: f"{x:.1%}"),
    color="STATUS"
)

fig_score10.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_score10, use_container_width=True, key=f"top10_score_{len(df)}")

# -----------------------------
# 🏆 TOP 20 VOLUME
# -----------------------------
st.subheader("🏆 Top 20 por Volume")

top20_volume = df.sort_values("Soma de pacotes", ascending=False).head(20)

fig_top20 = px.bar(
    top20_volume,
    y="NOME",
    x="Soma de pacotes",
    orientation="h",
    text="Soma de pacotes",
    color="STATUS"
)

fig_top20.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_top20, use_container_width=True, key=f"top20_volume_{len(df)}")

# -----------------------------
# 📉 TOP 20 RECORRÊNCIA (INTELIGENTE)
# -----------------------------
st.subheader("📉 Top 20 Recorrência (Ponderado)")

top20_score = df.sort_values("SCORE", ascending=False).head(20)

fig_score20 = px.bar(
    top20_score,
    y="NOME",
    x="SCORE",
    orientation="h",
    text=top20_score["RECORRENCIA"].apply(lambda x: f"{x:.1%}"),
    color="STATUS"
)

fig_score20.update_layout(yaxis={'categoryorder': 'total ascending'})
st.plotly_chart(fig_score20, use_container_width=True, key=f"top20_score_{len(df)}")

# -----------------------------
# 🕒 RECORRÊNCIA POR TURNO
# -----------------------------
st.subheader("🕒 Recorrência por Turno")

total_atr = df["Atribuicoes"].sum()

turno = pd.DataFrame({
    "Turno": ["SD", "AM"],
    "Recorrência": [
        df["SD"].sum() / total_atr if total_atr > 0 else 0,
        df["AM"].sum() / total_atr if total_atr > 0 else 0
    ]
})

fig_turno = px.bar(
    turno,
    x="Turno",
    y="Recorrência",
    text=turno["Recorrência"].apply(lambda x: f"{x:.1%}")
)

st.plotly_chart(fig_turno, use_container_width=True, key=f"turno_{len(df)}")

# -----------------------------
# 🔎 ANÁLISE INDIVIDUAL
# -----------------------------
if len(motoristas) == 1:
    st.subheader("🔎 Análise do Motorista")

    motorista_df = df[df["NOME"] == motoristas[0]]

    total_pacotes = motorista_df["Soma de pacotes"].sum()
    total_vezes = motorista_df["Vezes"].sum()
    total_aberto = motorista_df["PACOTE EM ABERTO"].sum()
    total_onhold = motorista_df["OnHold"].sum()
    total_atr = motorista_df["Atribuicoes"].sum()

    recorrencia = total_vezes / total_atr if total_atr > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("📦 Pacotes", total_pacotes)
    col2.metric("🔁 Vezes Ofensor", total_vezes)
    col3.metric("📉 Recorrência", f"{recorrencia:.2%}")
    col4.metric("🚨 Erros", total_aberto + total_onhold)

    st.subheader("📊 Detalhamento de Erros")

    detalhe = pd.DataFrame({
        "Tipo": ["Pacote em Aberto", "OnHold"],
        "Quantidade": [total_aberto, total_onhold]
    })

    fig_det = px.bar(detalhe, x="Tipo", y="Quantidade", text="Quantidade")
    st.plotly_chart(fig_det, use_container_width=True, key=f"det_{motoristas[0]}")

# -----------------------------
# 📋 TABELA
# -----------------------------
st.subheader("📋 Dados detalhados")
st.dataframe(df, use_container_width=True)
