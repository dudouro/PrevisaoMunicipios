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

# 2. Carregar os dados de mesorregião
df_meso = mesoregiao()
anos = [17, 18, 19, 20, 21, 22]

# Seleção do ano
ano_selecionado = st.selectbox("Selecione o ano da previsão:", anos)

# 3. Caminho do arquivo do ano selecionado
file_path = os.path.join("resultados", "janela_fixa", str(ano_selecionado), f"resultado_final{ano_selecionado}.xlsx")

# 4. Verificar se o arquivo existe
if os.path.exists(file_path):
    df = pd.read_excel(file_path)

    # Calcular a assertividade geral por mesorregião
    df["acerto"] = df["y_real"] == df["y_previsto"]
    
    # Agrupar os acertos por v21 (mesorregião) e calcular a média
    assertividade_mesorregiao = df.groupby("v21")["acerto"].mean() * 100
    
    # Resetar índice para juntar com df_meso
    assertividade_mesorregiao = assertividade_mesorregiao.reset_index()
    
    # Adicionar dados do ano
    assertividade_mesorregiao["Ano"] = f"20{ano_selecionado}"

    # Merge com o dataframe de mesorregião para obter o nome da mesorregião
    assertividade_mesorregiao = assertividade_mesorregiao.merge(df_meso[["v21", "Mesorregião"]], on="v21", how="left")

    # Calcular a assertividade média por mesorregião
    assertividade_media = assertividade_mesorregiao.groupby("Mesorregião")["acerto"].mean().reset_index()
    assertividade_media.columns = ["Mesorregião", "Acerto (%)"]

    # 5. Unir os dados de assertividade com o GeoJSON das mesorregiões
    mesorregioes_contorno = mesorregioes_contorno.merge(
        assertividade_media,
        left_on="Nome_Mesorregiao",
        right_on="Mesorregião",
        how="left"
    )

    # 6. Criar o mapa interativo com Plotly
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

    # 7. Atualizar o layout do mapa
    fig.update_layout(
        title=f"Assertividade por Mesorregião em Minas Gerais ({ano_selecionado})",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(title="Assertividade (%)")
    )

    # 8. Exibir o mapa no Streamlit
    st.plotly_chart(fig)

else:
    st.warning(f"Nenhum dado disponível para o ano {ano_selecionado}.")
