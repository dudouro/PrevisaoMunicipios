from extra import variaveis
import streamlit as st
import numpy as np
import pandas as pd
import joblib
import os

# Função para carregar dados do ano de 2022
def carregar_dados_2022():
    file_path = os.path.join("resultados", "janela_fixa", "22", "resultado_final22.xlsx")
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    else:
        st.error("Arquivo de dados de 2022 não encontrado!")
        return None

# Carregar dados
df_referencia = carregar_dados_2022()
if df_referencia is None:
    st.stop()

st.title("Previsão CAPAG+LRF (BETA)")

st.sidebar.header("Informe os valores das variáveis")

# Inicializar session_state para armazenar os valores dos inputs
if "inputs" not in st.session_state:
    st.session_state.inputs = {var: 0.0 for var in variaveis}

# Função para verificar alertas CAPAG e LRF
def verificar_alerta(var, valor, rcl):
    # LRF - Despesa com Pessoal
    if var == "Despesa com pessoal":
        if valor / rcl >= 0.6:
            st.sidebar.error("🚨 Violação da LRF: Despesa com pessoal ultrapassa 60% da RCL!")
        elif valor / rcl >= 0.54:
            st.sidebar.warning("⚠️ Alerta LRF: Despesa com pessoal próxima ao limite (≥ 54% da RCL).")

    # LRF - Dívida Consolidada
    if var == "divida_consolidada":
        if valor / rcl > 1.2:
            st.sidebar.error("🚨 Violação da LRF: Dívida consolidada ultrapassa 1,2x a RCL!")

    # CAPAG - Endividamento
    if var == "endividamento":
        if valor / rcl > 1.6:
            st.sidebar.error("🚨 Endividamento muito elevado (> 1,6x RCL) — Categoria D.")
        elif valor / rcl > 1.2:
            st.sidebar.warning("⚠️ Endividamento elevado (> 1,2x RCL) — Categoria C.")

    # CAPAG - Poupança Corrente
    if var == "poupanca_corrente" and valor < 0:
        st.sidebar.warning("⚠️ Déficit na poupança corrente (valor < 0).")

    # CAPAG - Liquidez Relativa
    if var == "indicador_de_liquidez" and valor > 1:
        st.sidebar.warning("⚠️ Liquidez relativa acima do adequado (> 1).")

# Coletar dados via sliders dinâmicos
rcl = st.sidebar.slider(
            "Receita Corrente Líquida (RCL)",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            format="%.2f"
        )
dados = {}
for var in variaveis:
    if var in df_referencia.columns:
        media = df_referencia[var].mean()
        minimo = df_referencia[var].min()
        maximo = df_referencia[var].max()

        valor = st.sidebar.slider(
            var,
            min_value=float(minimo),
            max_value=float(maximo),
            value=float(media),
            format="%.2f"
        )
        dados[var] = valor
        verificar_alerta(var, valor, rcl)

# Botão para realizar a previsão
if st.button("Fazer Previsão"):
    modelo = joblib.load('random_forest_saude_municipios.pkl')
    previsao = modelo.predict(pd.DataFrame([dados]))
    st.success(f"✅ Previsão do modelo: {previsao[0]}")

# Exibir os dados fornecidos de forma mais bonita
st.write("### 📊 Dados informados:")

df = pd.DataFrame([dados])

# Agrupar variáveis
receitas = [
    "receita_per_capita",
    "representatividade_da_receita_propria",
    "participacao_das_receitas_de_transferencias"
]

despesas = [
    "participacao_dos_gastos_operacionais",
    "Despesa com pessoal",
    "cobertura_de_despesas"
]

liquidez_poupanca = [
    "liquidez_relativa",
    "indicador_de_liquidez",
    "poupanca_corrente",
    "recursos_para_cobertura_de_queda_de_arrecadacao",
    "recursos_para_cobertura_de_obrigacoes_de_curto_prazo"
]

endividamento = [
    "divida_per_capita",
    "comprometimento_das_receitas_correntes_com_o_endividamento",
    "Dívida Consolidada",
    "Operações de crédito",
    "endividamento",
    "comprometimento_das_receitas_correntes_com_as_obrigacoes_de_curto_prazo"
]

# Criar colunas para as métricas
st.markdown("#### Receitas")
col1, col2, col3 = st.columns(3)
for i, var in enumerate(receitas):
    with [col1, col2, col3][i % 3]:
        st.metric(label=var.replace("_", " ").title(), value=f"{df[var].values[0]:,.2f}")

st.markdown("#### Despesas")
col1, col2, col3 = st.columns(3)
for i, var in enumerate(despesas):
    with [col1, col2, col3][i % 3]:
        st.metric(label=var.replace("_", " ").title(), value=f"{df[var].values[0]:,.2f}")

st.markdown("#### Liquidez & Poupança")
col1, col2, col3 = st.columns(3)
for i, var in enumerate(liquidez_poupanca):
    with [col1, col2, col3][i % 3]:
        st.metric(label=var.replace("_", " ").title(), value=f"{df[var].values[0]:,.2f}")

st.markdown("#### Endividamento")
col1, col2, col3 = st.columns(3)
for i, var in enumerate(endividamento):
    with [col1, col2, col3][i % 3]:
        st.metric(label=var.replace("_", " ").title(), value=f"{df[var].values[0]:,.2f}")


