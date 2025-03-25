from extra import mesoregiao, variaveis  
import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import os

# Título do aplicativo
st.title("Mapa de Variáveis por Mesorregião em Minas Gerais")

# 1. Carregar o arquivo GeoJSON com os contornos das mesorregiões
contorno_path = "pages/MG_Mesorregioes_Contorno.geojson"
mesorregioes_contorno = gpd.read_file(contorno_path)

# 2. Carregar os dados das mesorregiões
df_meso = mesoregiao()
anos = [17, 18, 19, 20, 21, 22]

# 3. Selecionar a variável desejada
variavel_selecionada = st.selectbox("Selecione a variável para análise:", variaveis)
ano_selecionado = st.selectbox("Selecione o ano:", anos)

def plot_variavel_por_ano(ano, variavel_selecionada, df_meso, mesorregioes_contorno):
    file_path = os.path.join("resultados", "janela_fixa", str(ano), f"resultado_final{ano}.xlsx")
    variavel_data = []
    
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        
        if variavel_selecionada in df.columns:
            variavel_mesorregiao = df.groupby("v21")[variavel_selecionada].mean().reset_index()
            variavel_mesorregiao["Ano"] = f"20{ano}"
            variavel_mesorregiao = variavel_mesorregiao.merge(df_meso[["v21", "Mesorregião"]], on="v21", how="left")
            variavel_data.append(variavel_mesorregiao)
    
    if variavel_data:
        variavel_df = pd.concat(variavel_data)
        variavel_media = variavel_df.groupby("Mesorregião")[variavel_selecionada].mean().reset_index()
        variavel_media.columns = ["Mesorregião", f"Média de {variavel_selecionada}"]
        
        mesorregioes_contorno = mesorregioes_contorno.merge(
            variavel_media,
            left_on="Nome_Mesorregiao",
            right_on="Mesorregião",
            how="left"
        )
        
        fig = px.choropleth_mapbox(
            mesorregioes_contorno,
            geojson=mesorregioes_contorno.geometry,
            locations=mesorregioes_contorno.index,
            color=f"Média de {variavel_selecionada}",
            hover_name='Nome_Mesorregiao',
            hover_data={f"Média de {variavel_selecionada}": True},
            color_continuous_scale='Viridis',
            mapbox_style="open-street-map",
            center={"lat": -18.5122, "lon": -44.5550},
            zoom=5,
            opacity=0.7
        )
        
        fig.update_layout(
            title=f"Distribuição de {variavel_selecionada} por Mesorregião - {ano}",
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            coloraxis_colorbar=dict(title=f"{variavel_selecionada}")
        )
        
        st.plotly_chart(fig)
    else:
        st.warning("Nenhum dado disponível para a variável selecionada.")

plot_variavel_por_ano(ano_selecionado, variavel_selecionada, df_meso, mesorregioes_contorno)