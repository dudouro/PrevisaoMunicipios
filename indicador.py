import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import numpy as np
import plotly.express as px
from extra import variaveis, mesoregiao

def criar_grafico_distribuicao(df, variavel, titulo, ano_selecionado, a):
    df_A = df[df[f'y_{a}'] == 'A']
    df_B = df[df[f'y_{a}'] == 'B']

    # Definir bins comuns
    min_val = min(df_A[variavel].min(), df_B[variavel].min())
    max_val = max(df_A[variavel].max(), df_B[variavel].max())
    bins = np.linspace(min_val, max_val, 20)  # 20 bins comuns

    hist_A, _ = np.histogram(df_A[variavel], bins=bins, density=True)
    hist_B, _ = np.histogram(df_B[variavel], bins=bins, density=True)

    # Ajuste da posição dos bins para exibição
    bin_centers = (bins[:-1] + bins[1:]) / 2  

    fig = go.Figure()
    
    fig.add_trace(go.Bar(x=bin_centers, y=hist_A, marker_color='blue', name='Situação A', opacity=0.75))
    fig.add_trace(go.Bar(x=bin_centers, y=-hist_B, marker_color='red', name='Situação B', opacity=0.75))

    fig.update_layout(
        title=f"{titulo} - 20{ano_selecionado} - {a}",
        xaxis_title=variavel,
        yaxis_title="Densidade",
        barmode='overlay',
        bargap=0,
        showlegend=True
    )

    st.plotly_chart(fig)


# Criando a interface Streamlit
st.title("Análise Financeira por Ano dos Municipios")

anos = [17, 18, 19, 20, 21, 22]

st.subheader("Distribuição dos Municipios por Variável")

# Seleção do ano
ano_selecionado = st.selectbox("Selecione o ano da previsão:", anos)

# Seleção da variável para análise
variavel_selecionada = st.selectbox("Selecione a variável para comparar:", variaveis)

# Caminho do arquivo
file_path = os.path.join("resultados", "janela_fixa", str(ano_selecionado), f"resultado_final{ano_selecionado}.xlsx")

# Verificando se o arquivo existe
if os.path.exists(file_path):
    # Ler arquivo Excel
    df = pd.read_excel(file_path)

    # Escolher a função de acordo com a opção selecionada
    criar_grafico_distribuicao(df, variavel_selecionada, f"Distribuição do {variavel_selecionada}", ano_selecionado, 'previsto')

else:
    st.error(f"Arquivo não encontrado: {file_path}")

from extra import mesoregiao, variaveis  
import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

st.subheader("Variáveis por Anos")

df_meso = mesoregiao()

municipios_selecionados = st.multiselect("Selecione os municípios:", df_meso["Municípios"].unique())

if municipios_selecionados:
    dados_municipios = []

    for ano in anos:
        file_path = os.path.join("resultados", "janela_fixa", str(ano), f"resultado_final{ano}.xlsx")

        if os.path.exists(file_path):
            df = pd.read_excel(file_path)

            df = df[df["id"].astype(str).isin(df_meso[df_meso["Municípios"].isin(municipios_selecionados)]["id"].astype(str))]

            if not df.empty:
                df["ano"] = f"20{ano}"
                dados_municipios.append(df)

    if dados_municipios:
        df_final = pd.concat(dados_municipios)

        variavel_selecionada = st.selectbox("Selecione a variável para comparar:", df_final.columns)
        
        fig = go.Figure()

        for municipio in municipios_selecionados:
            df_municipio = df_final[df_final["id"].astype(str).isin(df_meso[df_meso["Municípios"] == municipio]["id"].astype(str))]

            fig.add_trace(go.Scatter(
                x=df_municipio["ano"], 
                y=df_municipio[variavel_selecionada], 
                mode='lines+markers', 
                name=municipio
            ))

        fig.update_layout(title="Evolução dos Municípios ao Longo dos Anos",
                          xaxis_title="Ano",
                          yaxis_title=variavel_selecionada)

        st.plotly_chart(fig)

    else:
        st.warning("Nenhum dado disponível para os municípios selecionados.")

if municipios_selecionados:
    previsao_df = pd.DataFrame(index=municipios_selecionados, columns=[f"20{ano}" for ano in anos])

    for municipio in municipios_selecionados:
        for ano in anos:
            file_path = os.path.join("resultados", "janela_fixa", str(ano), f"resultado_final{ano}.xlsx")

            if os.path.exists(file_path):
                df = pd.read_excel(file_path)

                df_municipio = df[df["id"].astype(str).isin(df_meso[df_meso["Municípios"] == municipio]["id"].astype(str))]

                if not df_municipio.empty and 'y_previsto' in df_municipio.columns and 'y_real' in df_municipio.columns:
                    y_previsto = df_municipio['y_previsto'].iloc[0]
                    y_real = df_municipio['y_real'].iloc[0]

                    if y_previsto in ['A', 'B']:
                        emoji = "🟢" if y_previsto == y_real else "🔴"
                        previsao_df.loc[municipio, f"20{ano}"] = f"{y_previsto} ({emoji})"
                    else:
                        previsao_df.loc[municipio, f"20{ano}"] = 'Nulo'
                else:
                    previsao_df.loc[municipio, f"20{ano}"] = 'Nulo'

    st.write("Tabela de Previsões A e B ao Longo dos Anos")
    st.dataframe(previsao_df)
else:
    st.warning("Nenhum município selecionado.")


# Obtendo lista de municípios e IDs
df_meso = mesoregiao()

st.subheader("Assertividade por Mesorregião")

# Opção de selecionar todas as mesorregiões
opcoes_mesorregioes = df_meso["Mesorregião"].unique()
selecionar_todas = st.checkbox("Selecionar todas as mesorregiões")

if selecionar_todas:
    mesoregiao_selecionadas = list(opcoes_mesorregioes)  # Converter para lista
else:
    mesoregiao_selecionadas = st.multiselect("Selecione as mesorregiões para comparação:", opcoes_mesorregioes)

# Lista para armazenar os dados de assertividade
assertividade_data = []

# 🔹 Correção do erro: Verificar se há pelo menos uma mesorregião selecionada
if len(mesoregiao_selecionadas) > 0:
    for ano in anos:
        file_path = os.path.join("resultados", "janela_fixa", str(ano), f"resultado_final{ano}.xlsx")

        if os.path.exists(file_path):
            df = pd.read_excel(file_path)

            # Calcular a assertividade geral por mesorregião
            df["acerto"] = df["y_real"] == df["y_previsto"]
            
            # Agrupar os acertos por v21 (mesorregião) e calcular a média
            assertividade_mesorregiao = df.groupby("v21")["acerto"].mean() * 100
            
            # Resetar índice para juntar com df_meso
            assertividade_mesorregiao = assertividade_mesorregiao.reset_index()
            
            # Adicionar dados do ano
            assertividade_mesorregiao["Ano"] = f"20{ano}"

            # Merge com o dataframe de mesorregião para obter o nome da mesorregião
            assertividade_mesorregiao = assertividade_mesorregiao.merge(df_meso[["v21", "Mesorregião"]], on="v21", how="left")

            # Filtrar as mesorregiões selecionadas
            assertividade_mesorregiao = assertividade_mesorregiao[assertividade_mesorregiao["Mesorregião"].isin(mesoregiao_selecionadas)]

            # Adicionar ao resultado
            assertividade_data.append(assertividade_mesorregiao)

    if assertividade_data:
        # Concatenar os dados de assertividade de todos os anos
        assertividade_df = pd.concat(assertividade_data)

        # Selecionar as colunas necessárias
        assertividade_df = assertividade_df[["Mesorregião", "Ano", "acerto"]]
        assertividade_df.columns = ["Mesorregião", "Ano", "Acerto (%)"]

        # Plotar gráfico de assertividade por mesorregião
        fig = px.line(assertividade_df, x="Ano", y="Acerto (%)", color="Mesorregião", 
                      labels={"Acerto (%)": "Assertividade (%)", "Mesorregião": "Mesorregião"},
                      title="Assertividade do Modelo por Mesorregião ao Longo dos Anos")

        fig.update_layout(xaxis_title="Ano", yaxis_title="Assertividade (%)", title_x=0.5)
        st.plotly_chart(fig)

    else:
        st.warning("Nenhuma assertividade disponível para as mesorregiões selecionadas.")
else:
    st.warning("Selecione pelo menos uma mesorregião para comparação.")
