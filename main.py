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
    sheet = client.open_by_key("1fKdf4zNs5CjZm9wKv_FaBnZeiuR1isbP4Wby9lD40Lw").worksheet("dsh-base")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = carregar_dados()

# 🔥 limpa nomes de coluna (evita erro de Turno)
df.columns = df.columns.str.strip()

# -----------------------------
# 🧠 TRATAMENTO
# -----------------------------
df["RECORRENCIA"] = df.apply(
    lambda x: x["Vezes"] / x["Atribuicoes"] if x["Atribuicoes"] > 0 else 0,
    axis=1
)

df["IMPACTO"] = df["RECORRENCIA"] * np.log1p(df["Soma de pacotes"])

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
# -----------------------------
# 🔍 FILTROS
# -----------------------------
col_f1, col_f2 = st.columns(2)

motoristas = col_f1.multiselect(
    "Filtrar motoristas",
    df["NOME"].unique()
)

# 🔥 FILTRO DE TURNO
turnos = col_f2.multiselect(
    "Filtrar turno",
    df["Turno"].dropna().unique()
)

# Aplica filtros
if motoristas:
    df = df[df["NOME"].isin(motoristas)]

if turnos:
    df = df[df["Turno"].isin(turnos)]

st.caption(f"{len(df)} motoristas analisados")

# -----------------------------
# 🔎 ANÁLISE INDIVIDUAL
# -----------------------------
if len(motoristas) == 1:
    st.subheader("🔎 Análise do Motorista")

    motorista_df = df[df["NOME"] == motoristas[0]]

    total_pacotes = motorista_df["Soma de pacotes"].sum()
    total_vezes = motorista_df["Vezes"].sum()
    total_atr = motorista_df["Atribuicoes"].sum()

    recorrencia = total_vezes / total_atr if total_atr > 0 else 0

    col1, col2, col3 = st.columns(3)

    col1.metric("📦 Pacotes", total_pacotes)
    col2.metric("🔁 Vezes Ofensor", total_vezes)
    col3.metric("📉 Recorrência", f"{recorrencia:.2%}")

    st.subheader("📊 Distribuição de Erros")

    detalhe = pd.DataFrame({
        "Tipo": ["Pacote em Aberto", "OnHold"],
        "Quantidade": [
            motorista_df["PACOTE EM ABERTO"].sum(),
            motorista_df["OnHold"].sum()
        ]
    }).sort_values("Quantidade", ascending=False)

    fig_det = px.bar(detalhe, x="Tipo", y="Quantidade", text="Quantidade")
    fig_det.update_traces(textposition="outside")
    st.plotly_chart(fig_det, use_container_width=True)

# -----------------------------
# 🏆 TÍTULOS DINÂMICOS
# -----------------------------
if motoristas:
    titulo_volume = "🏆 Ranking por Volume (Filtro Aplicado)"
    titulo_ofensor = "📉 Ranking de Ofensores (Filtro Aplicado)"
else:
    titulo_volume = "🏆 Top 20 por Volume"
    titulo_ofensor = "📉 Top 20 Ofensores (Impacto Real)"

# -----------------------------
# 🏆 TOP 20 VOLUME
# -----------------------------
st.subheader(titulo_volume)

top20_volume = df.sort_values("Soma de pacotes", ascending=False).head(20)

fig_top20 = px.bar(
    top20_volume,
    y="NOME",
    x="Soma de pacotes",
    orientation="h",
    text="Soma de pacotes",
    color="STATUS",
    color_discrete_map=color_map
)

fig_top20.update_traces(textposition="outside")
fig_top20.update_layout(yaxis={'categoryorder': 'total ascending'})

st.plotly_chart(fig_top20, use_container_width=True)

# -----------------------------
# 📊 VISÃO COMPLETA (TODOS)
# -----------------------------
st.subheader("📊 Visão Completa - Volume Total")

full_volume = df.sort_values("Soma de pacotes", ascending=False)

fig_full_volume = px.bar(
    full_volume,
    y="NOME",
    x="Soma de pacotes",
    orientation="h",
    color="STATUS",
    color_discrete_map=color_map
)

fig_full_volume.update_layout(
    yaxis={'categoryorder': 'total ascending'},
    height=800
)

st.plotly_chart(fig_full_volume, use_container_width=True)

# -----------------------------
# 📉 TOP 20 OFENSORES
# -----------------------------
st.subheader(titulo_ofensor)

top20 = df.sort_values(["IMPACTO", "Soma de pacotes"], ascending=False).head(20)

fig_score = px.bar(
    top20,
    y="NOME",
    x="RECORRENCIA",
    orientation="h",
    text=top20["RECORRENCIA"].apply(lambda x: f"{x:.1%}"),
    color="STATUS",
    color_discrete_map=color_map
)

fig_score.update_traces(textposition="outside")

fig_score.update_layout(
    yaxis=dict(
        categoryorder="array",
        categoryarray=top20.sort_values("RECORRENCIA")["NOME"]
    )
)

st.plotly_chart(fig_score, use_container_width=True)

# -----------------------------
# 📊 VISÃO COMPLETA OFENSORES
# -----------------------------
st.subheader("📊 Visão Completa - Todos Ofensores")

full_ofensor = df.sort_values("RECORRENCIA", ascending=False)

fig_full_of = px.bar(
    full_ofensor,
    y="NOME",
    x="RECORRENCIA",
    orientation="h",
    color="STATUS",
    color_discrete_map=color_map
)

fig_full_of.update_layout(
    yaxis={'categoryorder': 'total ascending'},
    height=800
)

st.plotly_chart(fig_full_of, use_container_width=True)

# -----------------------------
# 🕒 RECORRÊNCIA POR TURNO (CORRETO AGORA)
# -----------------------------
st.subheader("🕒 Distribuição de Ofensores por Turno")

# Conta quantos ofensores por turno
resumo_turno = df.groupby("Turno").agg(
    ofensores=("NOME", "count")
).reset_index()

# Calcula %
total = resumo_turno["ofensores"].sum()
resumo_turno["Percentual"] = resumo_turno["ofensores"] / total

# Gráfico
fig_turno = px.bar(
    resumo_turno,
    x="Turno",
    y="Percentual",
    text=resumo_turno["Percentual"].apply(lambda x: f"{x:.1%}"),
    color="Turno"
)

fig_turno.update_traces(textposition="outside")

st.plotly_chart(fig_turno, use_container_width=True)

# -----------------------------
# 📋 TABELA
# -----------------------------
st.subheader("📋 Dados detalhados")
st.dataframe(df, use_container_width=True)
