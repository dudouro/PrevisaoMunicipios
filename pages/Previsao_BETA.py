from extra import variaveis
import streamlit as st
import numpy as np
import pandas as pd
import joblib

st.title("Previsão CAPAG+LRF (BETA)")

st.sidebar.header("Informe os valores das variáveis")

# Inicializar session_state para armazenar os valores dos inputs
if "inputs" not in st.session_state:
    st.session_state.inputs = {var: 0.0 for var in variaveis}

# Criar um dicionário para armazenar os inputs
dados = {}
for var in variaveis:
    dados[var] = st.sidebar.number_input(var, value=st.session_state.inputs[var], format="%.2f")

# Exibir os dados fornecidos
st.write("### Dados informados:")
df = pd.DataFrame([dados])
st.dataframe(df)

# Botão para realizar a previsão
if st.button("Fazer Previsão"):
    modelo = joblib.load('random_forest_saude_municipios.pkl')
    previsao = modelo.predict(pd.DataFrame([dados]))
    st.success(f"Previsão do modelo: {previsao[0]}")
