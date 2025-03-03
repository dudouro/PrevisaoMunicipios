from extra import mesoregiao
import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import os


# Título do aplicativo
st.title("Mapa de Assertividade por Mesorregião em Minas Gerais")

# 1. Carregar o arquivo GeoJSON com os contornos das mesorregiões
contorno_path = "pages/MG_Mesorregioes_Contorno.geojson"
mesorregioes_contorno = gpd.read_file(contorno_path)

# 2. Carregar os dados de assertividade
df_meso = mesoregiao()
anos = range(20, 24)  # Exemplo: anos de 2020 a 2023

# 3. Lista para armazenar os dados de assertividade
assertividade_data = []

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

        # Adicionar ao resultado
        assertividade_data.append(assertividade_mesorregiao)

if assertividade_data:
    # Concatenar os dados de assertividade de todos os anos
    assertividade_df = pd.concat(assertividade_data)

    # Calcular a assertividade média por mesorregião
    assertividade_media = assertividade_df.groupby("Mesorregião")["acerto"].mean().reset_index()
    assertividade_media.columns = ["Mesorregião", "Acerto (%)"]

    # 4. Unir os dados de assertividade com o GeoJSON das mesorregiões
    mesorregioes_contorno = mesorregioes_contorno.merge(
        assertividade_media,
        left_on="Nome_Mesorregiao",
        right_on="Mesorregião",
        how="left"
    )

    # 5. Criar o mapa interativo com Plotly
    fig = px.choropleth_mapbox(
        mesorregioes_contorno,
        geojson=mesorregioes_contorno.geometry,
        locations=mesorregioes_contorno.index,
        color='Acerto (%)',  # Coluna que define as cores (assertividade)
        hover_name='Nome_Mesorregiao',  # Nome da mesorregião ao passar o mouse
        hover_data={'Acerto (%)': True},
        color_continuous_scale='Blues',  # Escala de cores azuis
        mapbox_style="open-street-map",  # Estilo do mapa
        center={"lat": -18.5122, "lon": -44.5550},  # Centro do mapa (coordenadas de Minas Gerais)
        zoom=5,  # Nível de zoom
        opacity=0.7  # Opacidade do mapa
    )

    # 6. Atualizar o layout do mapa
    fig.update_layout(
        title="Assertividade por Mesorregião em Minas Gerais",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(title="Assertividade (%)")
    )

    # 7. Exibir o mapa no Streamlit
    st.plotly_chart(fig)

else:
    st.warning("Nenhuma assertividade disponível para as mesorregiões.")