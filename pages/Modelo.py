import os
import pandas as pd
import plotly.express as px
import streamlit as st
from extra import variaveis

# Lista de anos a serem processados
anos = [17, 18, 19, 20, 21, 22]

def carregar_dados(janela):
    df_final = pd.DataFrame()
    for ano in anos:
        if janela == "janela_fixa":
            file_path = os.path.join("resultados", janela, str(ano), f"classification_report{ano}.xlsx")
        elif janela == "janela_extendida":
            file_path = os.path.join("resultados", janela, str(ano), f"ext_classification_report{ano}.xlsx")
        if os.path.exists(file_path):
            df = pd.read_excel(file_path, index_col=0)  # Define a primeira coluna como índice
            
            # Transformar o DataFrame em um dicionário de uma única linha
            df_transposed = df.T.unstack().to_frame().T
            df_transposed.columns = [f"{col}_{idx}" for idx, col in df_transposed.columns]
            
            # Garantir que colunas de ano e janela existam
            df_transposed["Ano"] = ano
            df_transposed["Janela"] = janela
            
            # Adicionar ao DataFrame final
            df_final = pd.concat([df_final, df_transposed], ignore_index=True)
        else:
            print(f"Arquivo não encontrado: {file_path}")
    return df_final

# Carregar os dois DataFrames
df_fixa = carregar_dados("janela_fixa")
df_extendida = carregar_dados("janela_extendida")

# Concatenar os dois DataFrames
df_final = pd.concat([df_fixa, df_extendida], ignore_index=True)

# Verificar se as colunas existem antes de reorganizar
if "Ano" in df_final.columns and "Janela" in df_final.columns:
    cols = ["Ano", "Janela"] + [col for col in df_final.columns if col not in ["Ano", "Janela"]]
    df_final = df_final[cols]

# Criar o gráfico com Plotly e Streamlit
st.title("Comportamento do Modelo")

# Seleção de métricas disponíveis
metricas_disponiveis = [col.split('_')[0] for col in df_final.columns if col not in ["Ano", "Janela"]]
metricas_disponiveis = list(set(metricas_disponiveis))

metrica_escolhida = st.selectbox("Escolha a métrica para visualização", metricas_disponiveis)
classes_disponiveis = [col.split('_')[1] for col in df_final.columns if metrica_escolhida in col]
classes_escolhidas = st.selectbox("Escolha a classe para comparação", classes_disponiveis)

colunas_selecionadas = [f"{metrica_escolhida}_{classe}" for classe in classes_disponiveis if classe == classes_escolhidas]

fig = px.line(df_final, x="Ano", y=colunas_selecionadas,
              color="Janela", markers=True,
              title=f"Evolução da métrica {metrica_escolhida} para a classe {classes_escolhidas} ao longo dos anos",
              labels={"value": metrica_escolhida, "variable": "Classe"})

st.plotly_chart(fig)

# Botão para exibir DataFrame
if st.button("Mostrar DataFrame"):
    st.write(df_final)

st.subheader("Importância das Variáveis - Gráfico de Linha")

# Adicionando a opção de selecionar todas as variáveis
selecionar_todas = st.checkbox("Selecionar todas as variáveis")

# Exibindo a lista de variáveis para o usuário selecionar
if selecionar_todas:
    variaveis_selecionadas = variaveis  # Seleciona todas automaticamente
else:
    variaveis_selecionadas = st.multiselect("Selecione as variáveis:", variaveis)

# Caso o usuário tenha selecionado alguma variável
if variaveis_selecionadas:
    # Lista para armazenar os dados de importância das variáveis
    feature_importance_data = []

    # Percorrendo os anos para carregar os dados
    for ano in anos:
        file_path = os.path.join("resultados", "janela_fixa", str(ano), f"feature_importances{ano}.xlsx")

        if os.path.exists(file_path):
            df = pd.read_excel(file_path)

            # Filtrando as variáveis selecionadas
            df = df[df['feature'].isin(variaveis_selecionadas)]

            # Adicionando coluna para o ano
            df["Ano"] = f"20{ano}"

            # Adicionando os dados de importâncias ao conjunto de dados
            feature_importance_data.append(df)

    if feature_importance_data:
        # Concatenar todos os dados de importâncias
        feature_importance_df = pd.concat(feature_importance_data)
        # Definir a paleta Paired (12-class)
        paired_colors = [
            "#a6cee3", "#1f78b4", "#b2df8a", "#33a02c",
            "#fb9a99", "#e31a1c", "#fdbf6f", "#ff7f00",
            "#cab2d6", "#6a3d9a", "#ffff99", "#b15928"
        ]
    
        # Criar gráfico de linha
        fig = px.line(feature_importance_df, x="Ano", y="importance", color="feature", 
                      labels={"importance": "Importância", "Ano": "Ano"}, 
                      title="Importância das Variáveis ao Longo dos Anos",color_discrete_sequence=paired_colors)

        fig.update_layout(xaxis_title="Ano", yaxis_title="Importância", title_x=0.5)

        # Exibir gráfico
        st.plotly_chart(fig)

    else:
        st.warning("Nenhuma importância das variáveis disponível para os anos selecionados.")

else:
    st.warning("Nenhuma variável selecionada.")
