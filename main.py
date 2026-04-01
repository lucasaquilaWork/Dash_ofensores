import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import numpy as np
from google.oauth2.service_account import Credentials

# -----------------------------
# ⚙️ CONFIG
# -----------------------------
st.set_page_config(page_title="Dashboard Mensal Motoristas", layout="wide")
st.title("📊 Dashboard Mensal de Motoristas")

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
    sheet = client.open_by_key("1fKdf4zNs5CjZm9wKv_FaBnZeiuR1isbP4Wby9lD40Lw").worksheet("dsh-base")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = carregar_dados()

# -----------------------------
# 🧠 TRATAMENTO
# -----------------------------
df["RECORRENCIA"] = df.apply(
    lambda x: x["Vezes"] / x["Atribuicoes"] if x["Atribuicoes"] > 0 else 0,
    axis=1
)

# PERFIL
df["PERFIL"] = df.apply(
    lambda x: "🔥 Recorrente"
    if x["RECORRENCIA"] > 0.4 and x["Atribuicoes"] > 10
    else "⚠️ Pontual"
    if x["RECORRENCIA"] > 0.4
    else "✅ Estável",
    axis=1
)

# CONSISTÊNCIA
df["CONSISTENCIA"] = df["RECORRENCIA"]

# PESO POR TURNO
df["PESO_SD"] = df["SD"] / df["Atribuicoes"]
df["PESO_AM"] = df["AM"] / df["Atribuicoes"]

# SCORE / RANKING MENSAL
df["RANK_MENSAL"] = (
    df["RECORRENCIA"] * 0.5 +
    (df["Vezes"] / df["Vezes"].max()) * 0.3 +
    (df["Soma de pacotes"] / df["Soma de pacotes"].max()) * 0.2
)

# STATUS
def definir_status(x):
    if x > 0.5:
        return "Crítico"
    elif x > 0.3:
        return "Atenção"
    else:
        return "OK"

df["STATUS"] = df["RECORRENCIA"].apply(definir_status)

color_map = {
    "Crítico": "#B91C1C",
    "Atenção": "#D97706",
    "OK": "#1D4ED8"
}

# -----------------------------
# 📌 KPIs
# -----------------------------
col1, col2, col3 = st.columns(3)

col1.metric("📦 Total Pacotes", int(df["Soma de pacotes"].sum()))
col2.metric("🔁 Total Ofensas", int(df["Vezes"].sum()))
col3.metric("📉 Recorrência Média", f"{df['RECORRENCIA'].mean():.2%}")

# -----------------------------
# 🔍 FILTRO
# -----------------------------
motoristas = st.multiselect("Filtrar motoristas", df["NOME"].unique())

if motoristas:
    df = df[df["NOME"].isin(motoristas)]

st.caption(f"{len(df)} motoristas analisados no mês")

# -----------------------------
# 🔎 ANÁLISE INDIVIDUAL
# -----------------------------
if len(motoristas) == 1:
    st.subheader("🔎 Análise do Motorista")

    m = df[df["NOME"] == motoristas[0]]

    col1, col2, col3 = st.columns(3)

    col1.metric("📦 Pacotes", int(m["Soma de pacotes"].sum()))
    col2.metric("🔁 Ofensas", int(m["Vezes"].sum()))
    col3.metric("📉 Recorrência", f"{(m['Vezes'].sum()/m['Atribuicoes'].sum()):.2%}")

    st.subheader("📊 Distribuição de Erros")

    detalhe = pd.DataFrame({
        "Tipo": ["Pacote em Aberto", "OnHold"],
        "Quantidade": [
            m["PACOTE EM ABERTO"].sum(),
            m["OnHold"].sum()
        ]
    }).sort_values("Quantidade", ascending=False)

    st.plotly_chart(px.bar(detalhe, x="Tipo", y="Quantidade", text="Quantidade"), use_container_width=True)

# -----------------------------
# 🚨 PIORES DO MÊS
# -----------------------------
st.subheader("🚨 Piores do Mês")

piores = df.sort_values("RANK_MENSAL", ascending=False).head(15)
st.dataframe(piores)

# -----------------------------
# 💬 INSIGHTS AUTOMÁTICOS
# -----------------------------
st.subheader("💬 Insights Operacionais")

for _, row in piores.head(5).iterrows():
    st.write(
        f"{row['NOME']} → {row['RECORRENCIA']:.0%} de recorrência em {row['Atribuicoes']} carregamentos"
    )

# -----------------------------
# 🏆 TOP 20 VOLUME
# -----------------------------
st.subheader("🏆 Top 20 por Volume")

top20_volume = df.sort_values("Soma de pacotes", ascending=False).head(20)

st.plotly_chart(
    px.bar(top20_volume, y="NOME", x="Soma de pacotes", orientation="h",
           color="STATUS", color_discrete_map=color_map),
    use_container_width=True
)

# -----------------------------
# 📉 TOP OFENSORES
# -----------------------------
st.subheader("📉 Top Ofensores do Mês")

top_of = df.sort_values("RANK_MENSAL", ascending=False).head(20)

st.plotly_chart(
    px.bar(top_of, y="NOME", x="RECORRENCIA", orientation="h",
           color="STATUS", color_discrete_map=color_map),
    use_container_width=True
)

# -----------------------------
# 📊 VISÃO COMPLETA
# -----------------------------
st.subheader("📊 Visão Completa")

full = df.sort_values("RECORRENCIA", ascending=False)

st.plotly_chart(
    px.bar(full, y="NOME", x="RECORRENCIA", orientation="h",
           color="STATUS", color_discrete_map=color_map, height=800),
    use_container_width=True
)

# -----------------------------
# 🕒 TURNOS
# -----------------------------
st.subheader("🕒 Análise por Turno")

turno = pd.DataFrame({
    "Turno": ["SD", "AM"],
    "Participação": [
        df["SD"].sum() / df["Atribuicoes"].sum(),
        df["AM"].sum() / df["Atribuicoes"].sum()
    ]
})

st.plotly_chart(
    px.bar(turno, x="Turno", y="Participação", text="Participação"),
    use_container_width=True
)

# -----------------------------
# 📋 TABELA FINAL
# -----------------------------
st.subheader("📋 Dados completos")
st.dataframe(df, use_container_width=True)
