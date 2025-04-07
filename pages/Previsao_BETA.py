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
def verificar_alerta(var, valor):
    # CAPAG
    if var == "poupanca_corrente" and valor <= 0:
        st.sidebar.warning("⚠️ Déficit na poupança corrente (valor ≤ 0).")
    if var == "indicador_de_liquidez" and valor > 1:
        st.sidebar.warning("⚠️ Indicador de liquidez acima do adequado (> 1).")
    if var == "endividamento" and valor > 90:
        st.sidebar.warning("⚠️ Endividamento elevado (acima de 90% da RCL).")
    
    # LRF
    if var == "Despesa com pessoal" and valor > 60:
        st.sidebar.warning("⚠️ Despesa com pessoal acima do limite da LRF (> 60% da RCL).")
    if var == "Dívida Consolidada" and valor > 120:
        st.sidebar.warning("⚠️ Dívida consolidada acima de 120% da RCL (limite LRF).")
    if var == "Operações de crédito" and valor > 16:
        st.sidebar.warning("⚠️ Operações de crédito elevadas, atente-se ao limite prudencial.")
    if var == "comprometimento_das_receitas_correntes_com_as_obrigacoes_de_curto_prazo" and valor > 30:
        st.sidebar.warning("⚠️ Comprometimento das receitas com obrigações de curto prazo acima de 30%.")
    if var == "comprometimento_das_receitas_correntes_com_o_endividamento" and valor > 20:
        st.sidebar.warning("⚠️ Comprometimento das receitas com endividamento elevado (> 20%).")

# Coletar dados via sliders dinâmicos
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
        verificar_alerta(var, valor)

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

# Resumo rápido
st.markdown("#### 📌 Resumo geral")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Total de Variáveis", value=len(variaveis))
with col2:
    st.metric(label="Média dos Valores Informados", value=f"{df.mean(axis=1).values[0]:.2f}")

