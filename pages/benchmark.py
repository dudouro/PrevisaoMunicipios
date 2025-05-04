import streamlit as st
import pandas as pd
import plotly.express as px
import os
import geopandas as gpd
import traceback # Para logs de erro
# Assumindo que 'extra' está acessível
try:
    from extra import variaveis, mesoregiao
except ImportError:
    st.warning("Módulo 'extra' não encontrado. Usando valores padrão/vazios.")
    variaveis = []
    # Função dummy para evitar erros fatais
    def mesoregiao(): return pd.DataFrame(columns=['v21', 'Municípios', 'Mesorregião', 'id'])

# --- Configuração Inicial e Constantes ---
st.set_page_config(page_title="Comparativo Municipal e Regional", layout="wide", page_icon="🗺️")

ANOS_INT = [17, 18, 19, 20, 21, 22]
ANOS_STR = [f"20{ano}" for ano in ANOS_INT]
GEOJSON_PATH = "pages/MG_Mesorregioes_Contorno.geojson" # Confirme este caminho
CORES_MAPA = 'Viridis' # Escolha uma escala de cores (ex: 'Viridis', 'Plasma', 'BuGn')

# --- CSS (Opcional, pode remover se não quiser customizar) ---
CSS = """
<style>
    div[data-testid="stExpander"] details { border: 1px solid #e0e0e0; border-radius: 5px; margin-bottom: 10px; }
    div[data-testid="stExpander"] summary { font-weight: 500; }
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- Funções de Carregamento de Dados com Cache ---

@st.cache_data
def load_all_data(anos):
    """Carrega e concatena dados de resultado_final de todos os anos disponíveis."""
    all_data = []
    print("Executando load_all_data (cache pode estar ativo)...") # Log
    for ano in anos:
        file_path = os.path.join("resultados", "janela_fixa", str(ano), f"resultado_final{ano}.xlsx")
        if os.path.exists(file_path):
            try:
                df = pd.read_excel(file_path)
                df['Ano'] = f"20{ano}"
                # Converte colunas relevantes para string para evitar erros de tipo
                if 'id' in df.columns: df['id'] = df['id'].astype(str)
                if 'v21' in df.columns: df['v21'] = df['v21'].astype(str)
                all_data.append(df)
            except Exception as e:
                st.warning(f"Erro ao carregar dados de 20{ano}: {e}")
        else:
            st.warning(f"Arquivo não encontrado para 20{ano}: {file_path}")
    if not all_data: return pd.DataFrame()
    return pd.concat(all_data, ignore_index=True)

@st.cache_data
def load_mesoregiao_data():
    """Carrega e prepara dados de mesoregião."""
    print("Executando load_mesoregiao_data (cache pode estar ativo)...") # Log
    try:
        df_meso = mesoregiao();
        if 'v21' in df_meso.columns: df_meso['v21'] = df_meso['v21'].astype(str)
        if 'id' in df_meso.columns: df_meso['id'] = df_meso['id'].astype(str)
        return df_meso
    except Exception as e:
        st.error(f"Erro ao executar a função mesoregiao(): {e}")
        return pd.DataFrame(columns=['v21', 'Municípios', 'Mesorregião', 'id'])

@st.cache_data
def load_geojson(path):
    """Carrega o arquivo GeoJSON."""
    print("Executando load_geojson (cache pode estar ativo)...") # Log
    if not os.path.exists(path): st.error(f"Arquivo GeoJSON não encontrado: {path}"); return None
    try: return gpd.read_file(path)
    except Exception as e: st.error(f"Erro ao carregar GeoJSON: {e}"); return None

# --- Funções Auxiliares ---
def merge_data_for_map(all_data_df, df_meso_info, geojson_gdf, selected_year, selected_variable):
    """Filtra dados do ano, calcula média por mesoregião e faz merge com GeoJSON."""
    if all_data_df.empty or selected_variable not in all_data_df.columns:
        st.warning(f"Dados ou variável '{selected_variable}' indisponíveis.")
        return None

    df_year = all_data_df[all_data_df['Ano'] == selected_year].copy()
    if df_year.empty:
        st.warning(f"Nenhum dado encontrado para o ano {selected_year}.")
        return None

    if 'v21' not in df_year.columns:
         st.error("Coluna 'v21' (identificador de mesoregião) não encontrada nos dados de resultado.")
         return None

    # Calcula média da variável por v21 (código da mesoregião)
    variavel_meso_avg = df_year.groupby("v21")[selected_variable].mean().reset_index()

    # Adiciona nome da Mesorregião usando df_meso_info
    if not df_meso_info.empty and 'v21' in df_meso_info.columns and 'Mesorregião' in df_meso_info.columns:
        variavel_meso_avg = variavel_meso_avg.merge(
            df_meso_info[['v21', 'Mesorregião']].drop_duplicates(subset=['v21']),
            on="v21", how="left"
        )
    else:
        st.warning("Não foi possível adicionar nomes das mesorregiões (dados de 'mesoregiao()' ausentes ou incompletos).")
        variavel_meso_avg['Mesorregião'] = 'ID ' + variavel_meso_avg['v21'] # Fallback

    # Merge com o GeoJSON
    if geojson_gdf is None or 'Nome_Mesorregiao' not in geojson_gdf.columns:
        st.error("GeoJSON não carregado ou não contém a coluna 'Nome_Mesorregiao'.")
        return None

    # Renomeia coluna da média para clareza
    coluna_media = f"Média {selected_variable}"
    variavel_meso_avg.rename(columns={selected_variable: coluna_media}, inplace=True)

    gdf_merged = geojson_gdf.merge(
        variavel_meso_avg[['Mesorregião', coluna_media]],
        left_on="Nome_Mesorregiao",
        right_on="Mesorregião",
        how="left" # Mantém todas as geometrias
    )

    # Trata NaNs que podem surgir do merge (mesorregiões no mapa sem dados)
    gdf_merged[coluna_media].fillna(gdf_merged[coluna_media].min(), inplace=True) # Preenche com o mínimo para ter cor, ou pode ser 0

    return gdf_merged, coluna_media


# --- Interface Principal ---
st.title("🗺️ Comparativo Municipal e Regional")
st.markdown("Explore variáveis e compare municípios ou regiões.")

# Carrega dados essenciais uma vez
all_df = load_all_data(ANOS_INT)
df_meso = load_mesoregiao_data()
geojson_data = load_geojson(GEOJSON_PATH)

if all_df.empty:
    st.error("Não foi possível carregar dados de resultados (`resultado_final*.xlsx`). A aplicação não pode continuar.")
# Só continua se os dados principais foram carregados
else:
    # Abas
    tab1, tab2 = st.tabs([
        "Mapa Regional de Variáveis",
        "Comparativo entre Municípios (Em Construção)"
    ])

    # --- Tab 1: Mapa Regional de Variáveis ---
    with tab1:
        st.header("Mapa de Variáveis por Mesorregião")
        st.markdown("Visualize a média de uma variável distribuída pelas mesorregiões de Minas Gerais para um ano específico.")

        col1_t1, col2_t1 = st.columns(2)

        with col1_t1:
            # Garante que a lista 'variaveis' exista
            if variaveis:
                variavel_selecionada_t1 = st.selectbox(
                    "Selecione a variável para análise:",
                    options=variaveis,
                    key='var_mapa',
                    index=0 # Padrão
                )
            else:
                st.error("Lista de variáveis ('variaveis') não disponível.")
                variavel_selecionada_t1 = None

        with col2_t1:
            ano_selecionado_t1 = st.selectbox(
                "Selecione o ano:",
                options=ANOS_STR, # Usa anos como string
                key='ano_mapa',
                index=len(ANOS_STR) - 1 # Último ano como padrão
            )

        # Só tenta gerar o mapa se a variável foi selecionada
        if variavel_selecionada_t1:
            with st.spinner(f"Gerando mapa para '{variavel_selecionada_t1}' em {ano_selecionado_t1}..."):
                # Chama a função para preparar os dados do mapa
                gdf_mapa_data, nome_coluna_media = merge_data_for_map(
                    all_df, df_meso, geojson_data, ano_selecionado_t1, variavel_selecionada_t1
                )

                if gdf_mapa_data is not None and not gdf_mapa_data.empty:
                    try:
                        # Cria o mapa
                        fig_map = px.choropleth_mapbox(
                            gdf_mapa_data,
                            geojson=gdf_mapa_data.geometry,
                            locations=gdf_mapa_data.index,
                            color=nome_coluna_media, # Usa a coluna da média calculada
                            hover_name='Nome_Mesorregiao',
                            hover_data={nome_coluna_media: ':.2f'}, # Formata o hover
                            color_continuous_scale=CORES_MAPA,
                            mapbox_style="carto-positron", # Estilo mais limpo
                            center={"lat": -18.5122, "lon": -44.5550},
                            zoom=5,
                            opacity=0.75 # Um pouco mais opaco
                        )

                        fig_map.update_layout(
                            title=f"Distribuição Média de '{variavel_selecionada_t1}' por Mesorregião - {ano_selecionado_t1}",
                            margin={"r": 0, "t": 40, "l": 0, "b": 0}, # Margem para o título
                            coloraxis_colorbar=dict(
                                title=variavel_selecionada_t1.replace('_',' ').capitalize() # Título mais limpo para a legenda
                            )
                        )
                        st.plotly_chart(fig_map, use_container_width=True)

                        # Mantém a nota sobre acessibilidade se desejar
                        # st.caption("...")

                    except Exception as e:
                        st.error(f"Erro ao gerar o mapa: {e}")
                        # print(traceback.format_exc()) # Para debug no terminal
                else:
                    # Mensagens de erro/aviso já devem ter sido mostradas por merge_data_for_map
                    st.info("Não foi possível gerar o mapa com os dados e seleções atuais.")

    # --- Tab 2: Comparativo entre Municípios (Em Construção) ---
    with tab2:
        st.header("Comparativo Detalhado entre Municípios")
        st.info("🚧 Este painel está em construção! 🚧")
        st.markdown("""
        Em breve, você poderá:
        *   Selecionar múltiplos municípios.
        *   Escolher diversas variáveis para comparação.
        *   Visualizar a evolução temporal dessas variáveis lado a lado.
        *   Analisar dados em tabelas comparativas.

        Volte em breve para conferir as novidades!
        """)
        # Adicionar um espaço reservado ou imagem, se desejar
        # st.image("url_da_imagem_em_construcao.png")
