import streamlit as st
import pandas as pd
import plotly.express as px
import os
import geopandas as gpd
import traceback # Para logs de erro
import glob # Para encontrar os arquivos de receita dinamicamente

# Assumindo que 'extra' está acessível
try:
    from extra import variaveis, mesoregiao
    EXTRA_MODULO_DISPONIVEL = True
except ImportError:
    st.warning("Módulo 'extra' não encontrado. Algumas funcionalidades podem ser limitadas ou usar dados de fallback.")
    variaveis = [] # Fallback para lista de variáveis
    # Função dummy para mesoregiao para evitar erros fatais se 'extra' falhar
    def mesoregiao():
        # Tenta carregar 'mesoregiao.xlsx' localmente como fallback
        if os.path.exists("Mesorregiao.xlsx"):
            try:
                df = pd.read_excel("Mesorregiao.xlsx")
                # Garante colunas esperadas, mesmo que vazias
                if 'id' not in df.columns: df['id'] = None
                if 'Municípios' not in df.columns: df['Municípios'] = "Nome Indisponível"
                if 'Mesorregião' not in df.columns: df['Mesorregião'] = "Mesorregião Indisponível"
                if 'v21' not in df.columns: # v21 é usado para o mapa
                    # Tenta criar um v21 a partir do ID da mesoregião se possível ou um placeholder
                    # Esta parte pode precisar de ajuste dependendo da estrutura real do seu mesoregiao.xlsx
                    if 'IDMesorregiao' in df.columns: # Exemplo, ajuste conforme necessário
                         df['v21'] = df['IDMesorregiao'].astype(str)
                    else:
                         df['v21'] = df['id'].astype(str) # Fallback muito básico
                return df
            except Exception as e_fallback:
                st.error(f"Erro ao carregar 'mesoregiao.xlsx' como fallback: {e_fallback}")
                return pd.DataFrame(columns=['v21', 'Municípios', 'Mesorregião', 'id'])
        else:
            st.error("'mesoregiao.xlsx' não encontrado localmente para fallback.")
            return pd.DataFrame(columns=['v21', 'Municípios', 'Mesorregião', 'id'])
    EXTRA_MODULO_DISPONIVEL = False


# --- Configuração Inicial e Constantes ---
st.set_page_config(page_title="Comparativo Municipal e Regional", layout="wide", page_icon="📊")

# Constantes para Benchmark/Mapa
ANOS_INT_BENCHMARK = [17, 18, 19, 20, 21, 22]
ANOS_STR_BENCHMARK = [f"20{ano}" for ano in ANOS_INT_BENCHMARK]
GEOJSON_PATH = "pages/MG_Mesorregioes_Contorno.geojson" # Confirme este caminho
CORES_MAPA = 'Viridis'

# Constantes para Receitas
REVENUE_FILES_PATTERN = "receitas_anuais_dca_*.xlsx" # Padrão para encontrar arquivos de receita
MUNICIPIOS_INFO_FILE = "mesoregiao.xlsx" # Usado pela parte de receitas se o 'extra.mesoregiao' não for adequado ou para garantir consistência

# --- CSS (Opcional) ---
CSS = """
<style>
    div[data-testid="stExpander"] details { border: 1px solid #e0e0e0; border-radius: 5px; margin-bottom: 10px; }
    div[data-testid="stExpander"] summary { font-weight: 500; }
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- Funções de Carregamento de Dados com Cache ---

# Funções do Benchmark
@st.cache_data
def load_benchmark_data(anos):
    """Carrega e concatena dados de resultado_final de todos os anos disponíveis."""
    all_data = []
    # st.write("Debug: Carregando dados de benchmark...") # Para depuração
    for ano in anos:
        file_path = os.path.join("resultados", "janela_fixa", str(ano), f"resultado_final{ano}.xlsx")
        if os.path.exists(file_path):
            try:
                df = pd.read_excel(file_path)
                df['Ano'] = f"20{ano}"
                if 'id' in df.columns: df['id'] = df['id'].astype(str)
                if 'v21' in df.columns: df['v21'] = df['v21'].astype(str)
                all_data.append(df)
            except Exception as e:
                st.warning(f"Erro ao carregar dados de benchmark de 20{ano}: {e}")
        else:
            st.warning(f"Arquivo de benchmark não encontrado para 20{ano}: {file_path}")
    if not all_data: return pd.DataFrame()
    return pd.concat(all_data, ignore_index=True)

@st.cache_data
def load_mesoregiao_info():
    """Carrega e prepara dados de mesoregião (de 'extra' ou fallback)."""
    # st.write("Debug: Carregando dados de mesoregião...") # Para depuração
    try:
        df_meso = mesoregiao() # Chama a função definida no início (do 'extra' ou fallback)
        # Garante que as colunas 'id' e 'v21' sejam strings
        if 'id' in df_meso.columns:
            df_meso['id'] = df_meso['id'].astype(str)
        else:
            st.error("Coluna 'id' não encontrada nos dados de mesoregião.")
            df_meso['id'] = None # Adiciona coluna vazia para evitar erros posteriores

        if 'v21' in df_meso.columns:
            df_meso['v21'] = df_meso['v21'].astype(str)
        elif 'id' in df_meso.columns: # Fallback: se v21 não existe, usa id como v21 para o mapa (pode não ser ideal)
            st.warning("Coluna 'v21' não encontrada nos dados de mesoregião. Usando 'id' como substituto para 'v21'.")
            df_meso['v21'] = df_meso['id'].astype(str)
        else:
            st.error("Colunas 'v21' e 'id' não encontradas nos dados de mesoregião.")
            df_meso['v21'] = None

        if 'Municípios' not in df_meso.columns:
            st.error("Coluna 'Municípios' não encontrada nos dados de mesoregião.")
            df_meso['Municípios'] = "Nome Indisponível"

        if 'Mesorregião' not in df_meso.columns:
            st.warning("Coluna 'Mesorregião' não encontrada nos dados de mesoregião.")
            df_meso['Mesorregião'] = "Mesorregião Indisponível"

        return df_meso
    except Exception as e:
        st.error(f"Erro crítico ao carregar dados de mesoregião: {e}")
        return pd.DataFrame(columns=['v21', 'Municípios', 'Mesorregião', 'id'])


@st.cache_data
def load_geojson_map_data(path):
    """Carrega o arquivo GeoJSON."""
    # st.write("Debug: Carregando GeoJSON...") # Para depuração
    if not os.path.exists(path): st.error(f"Arquivo GeoJSON não encontrado: {path}"); return None
    try: return gpd.read_file(path)
    except Exception as e: st.error(f"Erro ao carregar GeoJSON: {e}"); return None

# Funções para a Aba de Receitas
@st.cache_data
def load_all_revenue_data(file_pattern):
    """Carrega, combina e processa os arquivos de receita encontrados na pasta."""
    revenue_files = glob.glob(file_pattern)
    if not revenue_files:
        st.warning(f"Nenhum arquivo de receita encontrado com o padrão: {file_pattern} na pasta atual.")
        return pd.DataFrame()

    all_dfs = []
    # st.sidebar.write("Arquivos de receita encontrados:") # Removido da sidebar para não poluir
    for filepath in revenue_files:
        # st.sidebar.caption(f"- {os.path.basename(filepath)}")
        try:
            df = pd.read_excel(filepath)
            if 'Ano' not in df.columns:
                try:
                    filename = os.path.basename(filepath)
                    year_from_filename = filename.split('_')[-1].split('.')[0]
                    df['Ano'] = int(year_from_filename)
                except Exception:
                    st.warning(f"Não foi possível determinar o ano para o arquivo {filename}. Pulando este arquivo.")
                    continue
            
            # A coluna de ID do município nos arquivos de receita deve ser 'IBGE'
            if 'IBGE' not in df.columns:
                st.warning(f"Arquivo {os.path.basename(filepath)} não contém a coluna 'IBGE'. Pulando este arquivo.")
                continue
            df['IBGE'] = df['IBGE'].astype(str)
            all_dfs.append(df)
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo de receita {os.path.basename(filepath)}: {e}")
            continue

    if not all_dfs:
        return pd.DataFrame()

    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # Colunas de receita esperadas
    revenue_cols_expected = ['IPTU', 'ISSQN', 'ITBI', 'FPM', 'ICMS (Cota-Parte)', 'IPVA (Cota-Parte)']
    base_cols = ['IBGE', 'Ano']
    
    existing_revenue_cols = [col for col in revenue_cols_expected if col in combined_df.columns]
    if not existing_revenue_cols:
        st.error("Nenhuma das colunas de receita esperadas (IPTU, ISSQN, etc.) foi encontrada nos arquivos de receita carregados.")
        return pd.DataFrame()
        
    final_cols_to_select = base_cols + existing_revenue_cols
    
    # Verifica se as colunas base existem
    for col in base_cols:
        if col not in combined_df.columns:
            st.error(f"Coluna obrigatória '{col}' ausente nos dados de receita combinados.")
            return pd.DataFrame()

    return combined_df[final_cols_to_select]


# --- Funções Auxiliares (Benchmark/Mapa) ---
def merge_data_for_map(benchmark_df, mesoregiao_df, geojson_gdf, selected_year, selected_variable):
    """Filtra dados do ano, calcula média por mesoregião e faz merge com GeoJSON."""
    if benchmark_df.empty or selected_variable not in benchmark_df.columns:
        st.warning(f"Dados de benchmark ou variável '{selected_variable}' indisponíveis para o mapa.")
        return None, None

    df_year = benchmark_df[benchmark_df['Ano'] == selected_year].copy()
    if df_year.empty:
        st.warning(f"Nenhum dado de benchmark encontrado para o ano {selected_year}.")
        return None, None

    if 'v21' not in df_year.columns or 'id' not in df_year.columns:
         st.error("Coluna 'v21' ou 'id' (identificador de município/mesoregião) não encontrada nos dados de benchmark.")
         return None, None

    # Calcula média da variável por v21 (código da mesoregião)
    # Assegura que a variável selecionada seja numérica para a média
    if not pd.api.types.is_numeric_dtype(df_year[selected_variable]):
        try:
            df_year[selected_variable] = pd.to_numeric(df_year[selected_variable], errors='coerce')
        except Exception as e:
            st.error(f"Não foi possível converter a variável '{selected_variable}' para numérica: {e}")
            return None, None
    
    # Remove NaNs antes de agrupar para evitar erros ou resultados inesperados
    df_year_cleaned = df_year.dropna(subset=[selected_variable, 'v21'])
    if df_year_cleaned.empty:
        st.warning(f"Nenhum dado válido para '{selected_variable}' após remover NaNs no ano {selected_year}.")
        return None, None

    variavel_meso_avg = df_year_cleaned.groupby("v21")[selected_variable].mean().reset_index()

    if not mesoregiao_df.empty and 'v21' in mesoregiao_df.columns and 'Mesorregião' in mesoregiao_df.columns:
        # Mantém apenas uma entrada por v21 para evitar duplicatas no merge
        meso_unique_names = mesoregiao_df[['v21', 'Mesorregião']].drop_duplicates(subset=['v21'])
        variavel_meso_avg = variavel_meso_avg.merge(
            meso_unique_names,
            on="v21", how="left"
        )
        # Se 'Mesorregião' ainda tiver NaNs após o merge (v21 não encontrado em mesoregiao_df)
        variavel_meso_avg['Mesorregião'].fillna('ID ' + variavel_meso_avg['v21'].astype(str), inplace=True)
    else:
        st.warning("Não foi possível adicionar nomes das mesorregiões (dados de 'mesoregiao_info' ausentes ou incompletos).")
        variavel_meso_avg['Mesorregião'] = 'ID ' + variavel_meso_avg['v21'].astype(str)

    if geojson_gdf is None or 'Nome_Mesorregiao' not in geojson_gdf.columns:
        st.error("GeoJSON não carregado ou não contém a coluna 'Nome_Mesorregiao'.")
        return None, None

    coluna_media = f"Média {selected_variable}"
    variavel_meso_avg.rename(columns={selected_variable: coluna_media}, inplace=True)

    # Merge com o GeoJSON
    # Certifique-se que a coluna de merge no geojson_gdf (Nome_Mesorregiao) e em variavel_meso_avg (Mesorregião)
    # tenham correspondência. Pode ser necessário normalizar os nomes.
    gdf_merged = geojson_gdf.merge(
        variavel_meso_avg[['Mesorregião', coluna_media]], # Seleciona apenas as colunas necessárias
        left_on="Nome_Mesorregiao",
        right_on="Mesorregião",
        how="left"
    )
    # Preenche NaNs na coluna de média (mesorregiões no mapa sem dados) com um valor neutro ou o mínimo
    # para que ainda apareçam no mapa com alguma cor.
    if coluna_media in gdf_merged.columns:
        min_val = gdf_merged[coluna_media].min() if not gdf_merged[coluna_media].dropna().empty else 0
        gdf_merged[coluna_media].fillna(min_val, inplace=True)
    else: # Se a coluna_media não foi criada por algum motivo
        st.warning(f"Coluna '{coluna_media}' não encontrada no GeoDataFrame após o merge.")
        return None, None


    return gdf_merged, coluna_media


# --- Interface Principal ---
st.title("📊 Comparativo Municipal e Regional 🗺️")

# Carrega dados essenciais uma vez
df_benchmark_all = load_benchmark_data(ANOS_INT_BENCHMARK)
df_mesoregiao_geral = load_mesoregiao_info() # Carrega de 'extra' ou fallback
gdf_geojson = load_geojson_map_data(GEOJSON_PATH)

# Carrega dados de receita para a segunda aba
df_revenues_all = load_all_revenue_data(REVENUE_FILES_PATTERN)


# Abas
tab_receitas, tab_mapa  = st.tabs(["📈 Comparativo de Receitas Municipais",
                                   "🗺️ Mapa Regional de Variáveis" 
])
# --- Tab 1: Comparativo de Receitas Municipais ---
with tab_receitas:
    df_benchmark_all = load_benchmark_data(ANOS_INT_BENCHMARK)
    df_mesoregiao_geral = load_mesoregiao_info()
    gdf_geojson = load_geojson_map_data(GEOJSON_PATH)
    df_revenues_all = load_all_revenue_data(REVENUE_FILES_PATTERN)

    st.header("Comparativo de Receitas Municipais")

    if df_revenues_all.empty:
        st.error("Não foi possível carregar dados de receita (`receitas_anuais_dca_*.xlsx`). A funcionalidade de comparação de receitas está indisponível.")
    elif df_mesoregiao_geral.empty:
        st.error("Não foi possível carregar informações dos municípios (`mesoregiao`). A funcionalidade de comparação de receitas pode estar limitada.")
    else:
        if 'id' not in df_mesoregiao_geral.columns or 'Municípios' not in df_mesoregiao_geral.columns:
            st.error("Dados de mesoregião incompletos (faltam 'id' ou 'Municípios'). Não é possível associar nomes aos municípios para as receitas.")
            df_revenues_merged_with_names = pd.DataFrame()
        else:
            df_meso_for_revenue = df_mesoregiao_geral[['id', 'Municípios']].copy()
            df_meso_for_revenue.rename(columns={'id': 'IBGE', 'Municípios': 'Nome_Municipio'}, inplace=True)
            df_revenues_all['IBGE'] = df_revenues_all['IBGE'].astype(str)
            df_meso_for_revenue['IBGE'] = df_meso_for_revenue['IBGE'].astype(str)
            df_revenues_merged_with_names = pd.merge(
                df_revenues_all,
                df_meso_for_revenue,
                on="IBGE",
                how="left"
            )
            df_revenues_merged_with_names['Nome_Municipio'].fillna(df_revenues_merged_with_names['IBGE'], inplace=True)

        if df_revenues_merged_with_names.empty:
            st.warning("Nenhum dado de receita disponível após tentativa de combinação com nomes de municípios.")
        else:
            col1_t2, col2_t2 = st.columns(2)
            
            with col1_t2:
                municipios_disponiveis_receita = sorted(df_revenues_merged_with_names['Nome_Municipio'].unique())
                if not municipios_disponiveis_receita:
                    st.warning("Nenhum município disponível para seleção na aba de receitas.")
                    selected_municipios_receita = []
                else:
                    default_selection_municipios = municipios_disponiveis_receita[:2] if len(municipios_disponiveis_receita) >= 2 else municipios_disponiveis_receita
                    selected_municipios_receita = st.multiselect(
                        "Selecione os Municípios para Comparar Receitas:",
                        options=municipios_disponiveis_receita,
                        default=default_selection_municipios,
                        key='municipios_receita'
                    )

            available_revenue_types = sorted([col for col in df_revenues_merged_with_names.columns if col not in ['IBGE', 'Ano', 'Nome_Municipio']])
            
            with col2_t2:
                if not available_revenue_types:
                    st.warning("Nenhum tipo de receita disponível para seleção.")
                    selected_revenue_types = []
                else:
                    default_selection_revenue = available_revenue_types[:1] if available_revenue_types else []
                    selected_revenue_types = st.multiselect(
                        "Selecione o(s) Tipo(s) de Receita:",
                        options=available_revenue_types,
                        default=default_selection_revenue,
                        key='revenue_types_receita'
                    )

            if not selected_municipios_receita:
                st.info("Por favor, selecione pelo menos um município para visualizar os gráficos de receita.")
            elif not selected_revenue_types:
                st.info("Por favor, selecione pelo menos um tipo de receita.")
            else:
                df_filtered_by_municipio = df_revenues_merged_with_names[
                    df_revenues_merged_with_names['Nome_Municipio'].isin(selected_municipios_receita)
                ].copy()

                cols_to_melt = ['Ano', 'Nome_Municipio'] + selected_revenue_types
                df_subset_for_melt = df_filtered_by_municipio[cols_to_melt]

                df_melted_receita = pd.melt(
                    df_subset_for_melt,
                    id_vars=['Ano', 'Nome_Municipio'],
                    value_vars=selected_revenue_types,
                    var_name='Tipo_Receita',
                    value_name='Valor_Arrecadado'
                )
                # garantir que "Ano" seja numérico
                df_melted_receita['Ano'] = pd.to_numeric(df_melted_receita['Ano'], errors='coerce')

                if df_melted_receita.empty:
                    st.warning(f"Nenhum dado de receita encontrado para os municípios e tipos de receita selecionados.")
                else:
                    revenue_types_str = ', '.join(selected_revenue_types)
                    st.subheader(f"Comparativo de Arrecadação: {revenue_types_str}")

                    # Gráfico de Linhas
                    try:
                        fig_line_receita = px.line(
                            df_melted_receita, x='Ano', y='Valor_Arrecadado',
                            color='Nome_Municipio',
                            line_dash='Tipo_Receita',
                            title=f"Evolução Anual das Receitas Selecionadas",
                            markers=True,
                            labels={'Ano': 'Ano', 'Valor_Arrecadado': 'Valor Arrecadado',
                                    'Nome_Municipio': 'Município', 'Tipo_Receita': 'Tipo de Receita'}
                        )
                        fig_line_receita.update_layout(legend_title_text='Legenda')
                        st.plotly_chart(fig_line_receita, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro ao gerar o gráfico de linhas de receita: {e}\n{traceback.format_exc()}")

                    # Gráfico de Barras Empilhado por Tipo de Receita, facetado por Município
                    st.subheader(f"Composição Detalhada da Receita por Ano e Município") ## ALTERAÇÃO ##: Título
                    try:
                        num_municipios_selecionados = len(selected_municipios_receita)
                        facet_col_wrap_val = 0 # Auto-wrap by default
                        if num_municipios_selecionados > 1:
                            if num_municipios_selecionados <= 3: # If 1, 2 or 3 municipalities, show them in one row
                                facet_col_wrap_val = num_municipios_selecionados
                            elif num_municipios_selecionados == 4: # If 4, show 2x2
                                facet_col_wrap_val = 2
                            else: # For more than 4, maybe 3 per row
                                facet_col_wrap_val = 3 
                        
                        fig_bar_receita = px.bar(
                            df_melted_receita, 
                            x='Ano', 
                            y='Valor_Arrecadado',
                            color='Tipo_Receita',      # ## ALTERAÇÃO ##: Cor pelos Tipos de Receita para empilhamento
                            barmode='stack',           # ## ALTERAÇÃO ##: Barras empilhadas
                            facet_col='Nome_Municipio',# ## ALTERAÇÃO ##: Um subplot por município
                            facet_col_wrap=facet_col_wrap_val, # Controla o número de subplots por linha
                            title=f"Composição da Receita por Ano (Agrupado por Município)", # ## ALTERAÇÃO ##: Título
                            labels={'Ano': 'Ano', 'Valor_Arrecadado': 'Valor Arrecadado Total', # Y é o total empilhado
                                    'Nome_Municipio': 'Município', 'Tipo_Receita': 'Tipo de Receita'}
                        )
                        # Renomeia os títulos das facetas para apenas o nome do município
                        fig_bar_receita.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
                        fig_bar_receita.update_layout(legend_title_text='Tipo de Receita') # ## ALTERAÇÃO ##: Legenda
                        st.plotly_chart(fig_bar_receita, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro ao gerar o gráfico de barras de receita: {e}\n{traceback.format_exc()}")

                    # Tabela de Dados Filtrados
                    st.subheader("Dados Detalhados de Receita (Filtrados)")
                    cols_to_display_receita = ['Ano', 'Nome_Municipio']
                    for rt in selected_revenue_types:
                        if rt in df_filtered_by_municipio.columns:
                            cols_to_display_receita.append(rt)
                    cols_to_display_receita = sorted(list(set(cols_to_display_receita)), key=lambda x: (x != 'Ano', x != 'Nome_Municipio', x))
                    format_cols_numeric_receita = [col for col in selected_revenue_types if col in df_filtered_by_municipio.columns and pd.api.types.is_numeric_dtype(df_filtered_by_municipio[col])]
                    format_dict_receita = {col: '{:,.2f}' for col in format_cols_numeric_receita}
                    
                    try:
                        st.dataframe(
                            df_filtered_by_municipio[cols_to_display_receita]
                            .sort_values(by=['Nome_Municipio', 'Ano'])
                            .style.format(format_dict_receita, na_rep="-"),
                            use_container_width=True
                        )
                    except KeyError as e:
                        st.error(f"Erro ao tentar exibir a tabela de dados: Coluna não encontrada - {e}. Verifique se os tipos de receita selecionados existem nos dados.")
                        st.dataframe(df_filtered_by_municipio.sort_values(by=['Nome_Municipio', 'Ano']), use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro ao exibir a tabela de dados de receita: {e}\n{traceback.format_exc()}")
                        st.dataframe(df_filtered_by_municipio[cols_to_display_receita].sort_values(by=['Nome_Municipio', 'Ano']), use_container_width=True)

# --- Tab 2: Mapa Regional de Variáveis (Benchmark) ---
with tab_mapa:
    st.header("Mapa de Variáveis por Mesorregião")
    st.markdown("Visualize a média de uma variável de benchmark distribuída pelas mesorregiões de Minas Gerais para um ano específico.")

    if df_benchmark_all.empty:
        st.error("Não foi possível carregar dados de benchmark (`resultado_final*.xlsx`). O mapa não pode ser gerado.")
    elif df_mesoregiao_geral.empty:
        st.error("Não foi possível carregar dados de mesorregião. O mapa não pode ser gerado.")
    elif gdf_geojson is None:
        st.error("Não foi possível carregar o arquivo GeoJSON do mapa. O mapa não pode ser gerado.")
    else:
        col1_t1, col2_t1 = st.columns(2)
        with col1_t1:
            if EXTRA_MODULO_DISPONIVEL and variaveis: # 'variaveis' vem do módulo 'extra'
                variavel_selecionada_t1 = st.selectbox(
                    "Selecione a variável de benchmark:",
                    options=variaveis, key='var_mapa', index=0
                )
            elif not EXTRA_MODULO_DISPONIVEL and not variaveis:
                # Se 'extra' não carregou e 'variaveis' está vazia, tenta pegar colunas do df_benchmark_all
                # Exclui colunas não numéricas ou de identificação comuns
                default_cols_to_exclude = ['id', 'Ano', 'v21', 'Municípios', 'Mesorregião'] # Adicione outras se necessário
                potential_vars = [col for col in df_benchmark_all.columns if col not in default_cols_to_exclude and pd.api.types.is_numeric_dtype(df_benchmark_all[col])]
                if potential_vars:
                    variavel_selecionada_t1 = st.selectbox(
                        "Selecione a variável de benchmark (detectada):",
                        options=potential_vars, key='var_mapa_detectada', index=0
                    )
                else:
                    st.error("Lista de variáveis de benchmark ('variaveis') não disponível e nenhuma variável numérica detectada nos dados.")
                    variavel_selecionada_t1 = None
            else: # Caso 'variaveis' esteja vazia mesmo com EXTRA_MODULO_DISPONIVEL
                 st.error("Lista de variáveis de benchmark ('variaveis') está vazia.")
                 variavel_selecionada_t1 = None


        with col2_t1:
            ano_selecionado_t1 = st.selectbox(
                "Selecione o ano para o mapa:",
                options=ANOS_STR_BENCHMARK, key='ano_mapa', index=len(ANOS_STR_BENCHMARK) - 1
            )

        if variavel_selecionada_t1 and ano_selecionado_t1:
            with st.spinner(f"Gerando mapa para '{variavel_selecionada_t1}' em {ano_selecionado_t1}..."):
                gdf_map_display_data, nome_col_media_mapa = merge_data_for_map(
                    df_benchmark_all, df_mesoregiao_geral, gdf_geojson,
                    ano_selecionado_t1, variavel_selecionada_t1
                )

                if gdf_map_display_data is not None and not gdf_map_display_data.empty and nome_col_media_mapa:
                    try:
                        fig_map = px.choropleth_mapbox(
                            gdf_map_display_data,
                            geojson=gdf_map_display_data.geometry,
                            locations=gdf_map_display_data.index, # Usa o índice do GeoDataFrame
                            color=nome_col_media_mapa,
                            hover_name='Nome_Mesorregiao', # Do GeoJSON
                            hover_data={nome_col_media_mapa: ':.2f', 'Mesorregião': True},
                            color_continuous_scale=CORES_MAPA,
                            mapbox_style="carto-positron",
                            center={"lat": -18.5122, "lon": -44.5550}, zoom=5, opacity=0.75
                        )
                        fig_map.update_layout(
                            title=f"Distribuição Média de '{variavel_selecionada_t1}' por Mesorregião - {ano_selecionado_t1}",
                            margin={"r":0, "t":40, "l":0, "b":0},
                            coloraxis_colorbar=dict(title=variavel_selecionada_t1.replace('_',' ').capitalize())
                        )
                        st.plotly_chart(fig_map, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro ao gerar o mapa: {e}")
                        # st.write(traceback.format_exc()) # Para debug detalhado
                else:
                    st.info("Não foi possível gerar o mapa com os dados e seleções atuais. Verifique os avisos acima.")

