import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import numpy as np
import geopandas as gpd
from extra import variaveis, mesoregiao

# Configuração inicial da página
st.set_page_config(page_title="Previsão Financeira Municipal", layout="wide", page_icon="🏙️")

# Constantes
ANOS = [17, 18, 19, 20, 21, 22]
COLORS = {'A': '#4B9CD3', 'B': '#FF6B6B'}
GEOJSON_PATH = "pages/MG_Mesorregioes_Contorno.geojson"
CSS = """
<style>
[data-testid="stMetricLabel"] {font-size: 1.1rem;}
[data-testid="stMarkdownContainer"] h3 {color: #2B3A42;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# Funções utilitárias
def load_data(ano):
    """Carrega os dados para um ano específico"""
    file_path = os.path.join("resultados", "janela_fixa", str(ano), f"resultado_final{ano}.xlsx")
    return pd.read_excel(file_path) if os.path.exists(file_path) else None

def create_distribution_chart(df, variable, title, year, tipo):
    """Cria gráfico de distribuição comparativa com contagens absolutas"""
    df_A = df[df[f'y_{tipo}'] == 'A']
    df_B = df[df[f'y_{tipo}'] == 'B']
    total = len(df_A) + len(df_B)

    min_val = df[variable].min()
    max_val = df[variable].max()
    bins = np.linspace(min_val, max_val, 20)
    bin_centers = (bins[:-1] + bins[1:]) / 2

    hist_A, _ = np.histogram(df_A[variable], bins=bins)
    hist_B, _ = np.histogram(df_B[variable], bins=bins)

    # Calcular porcentagens
    pct_A = (hist_A / total) * 100
    pct_B = (hist_B / total) * 100

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=bin_centers, 
        y=hist_A,
        marker_color=COLORS['A'], 
        name='Situação A',
        opacity=0.75,
        hovertemplate='Faixa: %{x:.2f}<br>A: %{y} municípios<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        x=bin_centers, 
        y=-hist_B,
        marker_color=COLORS['B'], 
        name='Situação B',
        opacity=0.75,
        hovertemplate='Faixa: %{x:.2f}<br>B: %{y} municípios<extra></extra>'
    ))

    range_text = f"Intervalo: {min_val:.2f} a {max_val:.2f}"
    fig.update_layout(
        title=f"{title} - 20{year} - {tipo}",
        xaxis_title=f"{variable} ({range_text})",
        yaxis_title="Quantidade de Municípios",
        barmode='overlay',
        bargap=0,
        hovermode='x unified',
        showlegend=True
    )
    return fig

def create_map(ano_selecionado, file_path):
    """Cria o mapa de assertividade para um ano específico"""
    try:
        if os.path.exists(file_path):
            # Verificar extensão e ler arquivo corretamente
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path, engine='openpyxl')
            elif file_path.endswith('.xls'):
                df = pd.read_excel(file_path, engine='xlrd')
            else:
                raise ValueError("Formato de arquivo não suportado")
            
            # Restante do código mantido igual
            df["acerto"] = df["y_real"] == df["y_previsto"]
            assertividade_mesorregiao = df.groupby("v21")["acerto"].mean() * 100
            assertividade_mesorregiao = assertividade_mesorregiao.reset_index()
            assertividade_mesorregiao["Ano"] = f"20{ano_selecionado}"

            df_meso = mesoregiao()  # Movido para dentro do bloco
            assertividade_mesorregiao = assertividade_mesorregiao.merge(
                df_meso[["v21", "Mesorregião"]], 
                on="v21", 
                how="left"
            )

            mesorregioes_contorno = gpd.read_file("pages/MG_Mesorregioes_Contorno.geojson")
            assertividade_media = assertividade_mesorregiao.groupby("Mesorregião")["acerto"].mean().reset_index()
            assertividade_media.columns = ["Mesorregião", "Acerto (%)"]

            mesorregioes_contorno = mesorregioes_contorno.merge(
                assertividade_media,
                left_on="Nome_Mesorregiao",
                right_on="Mesorregião",
                how="left"
            )

            fig = px.choropleth_mapbox(
                mesorregioes_contorno,
                geojson=mesorregioes_contorno.geometry,
                locations=mesorregioes_contorno.index,
                color='Acerto (%)',
                hover_name='Nome_Mesorregiao',
                hover_data={'Acerto (%)': ':.1f%'},
                color_continuous_scale='BuGn',
                mapbox_style="open-street-map",
                center={"lat": -18.5122, "lon": -44.5550},
                zoom=5,
                opacity=0.7
            )

            fig.update_layout(
                title=f"Assertividade por Mesorregião em Minas Gerais (20{ano_selecionado})",
                margin={"r":0,"t":30,"l":0,"b":0},
                coloraxis_colorbar=dict(title="Assertividade (%)")
            )

            return fig  # Retorna a figura em vez de plotar diretamente
            
        else:
            st.warning(f"Nenhum dado disponível para 20{ano_selecionado}")
            return None

    except Exception as e:
        st.error(f"Erro crítico: {str(e)}")
        return None

def create_metrics(df, municipios):
    """Cria métricas de resumo"""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Municípios Selecionados", len(municipios))
    with col2:
        st.metric("Média Acertos", f"{df['acerto'].mean():.1%}")
    with col3:
        st.metric("Último Ano", df['Ano'].max())

# Interface principal
st.title("📊 Previsão Financeira Municipal")

# Abas para organização
tab1, tab2, tab3, tab4 = st.tabs(["Distribuição", "Evolução Municipal", "Assertividade", "Mapa de Assertividade"])

with tab1:
    # Seção de distribuição
    selected_year = st.selectbox("Ano Base", ANOS, index=len(ANOS)-1)
    selected_variable = st.selectbox("Variável Principal", variaveis)
    df_year = load_data(selected_year)
    if df_year is not None:
        fig = create_distribution_chart(df_year, selected_variable, 
                                      f"Distribuição de {selected_variable}", 
                                      selected_year, 'real')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Dados não encontrados para 20{selected_year}")

with tab2:
    # Seção de evolução municipal
    df_meso = mesoregiao()
    municipios = st.multiselect("Selecione Municípios:", 
                              df_meso["Municípios"].unique(),
                              key='municipios_tab2')
    
    if municipios:
        # Criar mapeamento de município para ID
        mapa_ids = df_meso.set_index("Municípios")["id"].astype(str).to_dict()
        
        dados = []
        for ano in ANOS:
            df = load_data(ano)
            if df is not None:
                # Filtrar IDs dos municípios selecionados
                ids_selecionados = [mapa_ids[m] for m in municipios]
                df_filtered = df[df["id"].astype(str).isin(ids_selecionados)]
                
                if not df_filtered.empty:
                    df_filtered["Ano"] = f"20{ano}"
                    dados.append(df_filtered)
        
        if dados:
            df_final = pd.concat(dados)
            # Adicionar nome do município ao dataframe
            df_final["Município"] = df_final["id"].astype(str).map(
                {v: k for k, v in mapa_ids.items()}
            )
            
            variavel = st.selectbox("Variável para Análise:", 
                                  variaveis,
                                  key='var_tab2')
            
            fig = px.line(df_final, x="Ano", y=variavel, 
                        color=df_final["id"].map(df_meso.set_index("id")["Municípios"]),
                        markers=True, line_shape='spline',
                        title=f"Evolução de {variavel} por Município")
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela
            st.subheader("Histórico de Classificações - Previsto(Real)")
            
            # Função para colorir o texto
            def color_text(val):
                if isinstance(val, str) and '(' in val:
                    real, prev = val.split('(')
                    real = real.strip()
                    prev = prev.replace(')', '').strip()
                    return f'color: {"green" if real == prev else "red"}'
                return ''
            
            # Criar tabela dinamicamente
            df_table = df_final.pivot_table(
                index='Município',
                columns='Ano',
                values=['y_real', 'y_previsto'],
                aggfunc='first'
            )
            
            # Formatando os valores
            formatted_df = pd.DataFrame()
            for ano in [f"20{a}" for a in ANOS]:
                if ('y_real', ano) in df_table.columns:
                    formatted_df[ano] = df_table[('y_previsto', ano)].astype(str) + " (" + df_table[('y_real', ano)].astype(str) + ")"
            
            st.dataframe(
                formatted_df.style.applymap(color_text),
                use_container_width=True,
                height=min(400, 55 * len(municipios) + 3)
            )

with tab3:
    # Seção de assertividade
    df_meso = mesoregiao()
    todas_meso = st.checkbox("Todas Mesorregiões", value=True)
    meso_options = df_meso["Mesorregião"].unique()
    selected_meso = st.multiselect("Mesorregiões:", meso_options, 
                                 disabled=todas_meso,
                                 default=meso_options if todas_meso else [])
    
    if selected_meso:
        dados_acertos = []
        for ano in ANOS:
            df = load_data(ano)
            if df is not None:
                df["acerto"] = (df["y_real"] == df["y_previsto"]).astype(int)
                df_meso_filtered = df_meso[df_meso["Mesorregião"].isin(selected_meso)]
                merged = df.merge(df_meso_filtered, on="v21")
                if not merged.empty:
                    merged["Ano"] = f"20{ano}"
                    dados_acertos.append(merged)
        
        if dados_acertos:
            df_acertos = pd.concat(dados_acertos)
            create_metrics(df_acertos, selected_meso)
            
            fig = px.line(df_acertos.groupby(['Mesorregião', 'Ano'])['acerto']
                        .mean().reset_index(), 
                        x="Ano", y="acerto", color="Mesorregião",
                        title="Assertividade por Mesorregião",
                        labels={'acerto': 'Taxa de Acerto', 'Ano': ''})
            fig.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)
            
with tab4:
    ano_mapa = st.selectbox("Selecione o ano:", ANOS, key="map_year")
    
    file_path = os.path.join("resultados", "janela_fixa", str(ano_mapa), f"resultado_final{ano_mapa}.xlsx")
    
    if st.button("🗺️ Gerar Mapa", key="map_btn"):
        with st.spinner("Processando dados geográficos..."):
            fig = create_map(ano_mapa, file_path)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Não foi possível gerar o mapa para este ano")
