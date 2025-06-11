import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import numpy as np
import geopandas as gpd
import traceback # Adicionado para melhor log de erro se necessário
# Assume que estas importações funcionam ou ajusta os fallbacks
try:
    from extra import variaveis, mesoregiao
except ImportError:
    variaveis = []
    def mesoregiao(): return pd.DataFrame(columns=['v21', 'Municípios', 'Mesorregião', 'id'])
    st.warning("Módulo 'extra' não carregado. Usando fallbacks.")


# --- Configuração Inicial e Constantes ---
st.set_page_config(page_title="Previsão Financeira Municipal", layout="wide", page_icon="🏙️")

ANOS_INT = [17, 18, 19, 20, 21, 22]
ANOS_STR = [f"20{ano}" for ano in ANOS_INT] # Lista de anos como string para filtros/labels
CORES_SITUACAO = {'A': '#4B9CD3', 'B': '#FF6B6B'} # Cores para A/B
CORES_MAPA = 'BuGn' # Escala de cores para o mapa
GEOJSON_PATH = "pages/MG_Mesorregioes_Contorno.geojson" # Caminho para o GeoJSON

# --- CSS Customizado (Mantido da versão anterior) ---
CSS = """
<style>
    [data-testid="stMetricLabel"] { font-size: 1.1rem; color: #333; }
    div[data-testid="stExpander"] details { border: 1px solid #e0e0e0; border-radius: 5px; margin-bottom: 10px; }
    div[data-testid="stExpander"] summary { font-weight: 500; }
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- Funções de Carregamento de Dados com Cache (Mantidas da versão anterior) ---

@st.cache_data
def load_all_data(anos):
    """Carrega e concatena dados de todos os anos disponíveis."""
    all_data = []
    print("Executando load_all_data...") # Log
    for ano in anos:
        file_path = os.path.join("resultados", "janela_fixa", str(ano), f"resultado_final{ano}.xlsx")
        if os.path.exists(file_path):
            try:
                df = pd.read_excel(file_path)
                df['Ano'] = f"20{ano}"; df['acerto'] = df["y_real"] == df["y_previsto"]
                if 'id' in df.columns: df['id'] = df['id'].astype(str)
                if 'v21' in df.columns: df['v21'] = df['v21'].astype(str)
                all_data.append(df)
            except Exception as e: st.warning(f"Erro ao carregar dados de 20{ano}: {e}")
        else: st.warning(f"Arquivo não encontrado para 20{ano}: {file_path}")
    if not all_data: return pd.DataFrame()
    return pd.concat(all_data, ignore_index=True)

@st.cache_data
def load_mesoregiao_data():
    """Carrega e prepara dados de mesoregião."""
    print("Executando load_mesoregiao_data...") # Log
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
    print("Executando load_geojson...") # Log
    if not os.path.exists(path): st.error(f"Arquivo GeoJSON não encontrado: {path}"); return None
    try: return gpd.read_file(path)
    except Exception as e: st.error(f"Erro ao carregar GeoJSON: {e}"); return None

# --- Funções de Geração de Gráficos e UI (Mantidas/Recriadas) ---

def create_distribution_chart(df_filtered, variable, title_prefix, year_str):
    if df_filtered.empty or variable not in df_filtered.columns:
        return None

    # Remover valores nulos da variável e da classificação
    df_filtered = df_filtered.dropna(subset=[variable, 'y_real'])
    if df_filtered.empty:
        return None

    # Remoção de outliers usando IQR
    Q1 = df_filtered[variable].quantile(0.25)
    Q3 = df_filtered[variable].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    df_filtered = df_filtered[(df_filtered[variable] >= lower_bound) & (df_filtered[variable] <= upper_bound)]
    if df_filtered.empty:
        return None

    # Separar em grupos A e B
    df_A = df_filtered[df_filtered['y_real'] == 'A']
    df_B = df_filtered[df_filtered['y_real'] == 'B']

    min_val, max_val = df_filtered[variable].min(), df_filtered[variable].max()
    if pd.isna(min_val) or pd.isna(max_val) or min_val == max_val:
        return None

    bins = np.linspace(min_val, max_val, 20)
    bin_centers = (bins[:-1] + bins[1:]) / 2

    hist_A, _ = np.histogram(df_A[variable].dropna(), bins=bins)
    hist_B, _ = np.histogram(df_B[variable].dropna(), bins=bins)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=bin_centers, y=hist_A, name='Situação A',
        marker_color=CORES_SITUACAO['A'], opacity=0.8,
        hovertemplate=f'<b>{variable} (faixa)</b>: %{{x:.2f}}<br><b>Municípios A</b>: %{{y}}<extra></extra>'
    ))

    fig.add_trace(go.Bar(
        x=bin_centers, y=-hist_B, name='Situação B',
        marker_color=CORES_SITUACAO['B'], opacity=0.8,
        hovertemplate=f'<b>{variable} (faixa)</b>: %{{x:.2f}}<br><b>Municípios B</b>: %{{customdata[0]}}<extra></extra>',
        customdata=np.array([hist_B]).T
    ))

    fig.update_layout(
        title=f"{title_prefix} - {year_str}",
        xaxis_title=f"{variable}",
        yaxis_title="Quantidade de Municípios",
        barmode='relative',
        bargap=0.1,
        legend_title_text='Situação Real',
        hovermode='x unified',
        annotations=[
            dict(
                xref='paper', yref='paper', x=1, y=1.05, showarrow=False,
                text=f'Range {variable} (sem outliers): {min_val:.2f} a {max_val:.2f}',
                font=dict(size=10, color='grey')
            )
        ]
    )

    fig.update_yaxes(hoverformat='.0f')
    return fig

# Função de formatação da tabela para Tab 2 (Mantida da versão anterior)
def format_classification_table(df_pivot):
    def color_text(val_str):
        if isinstance(val_str, str) and '(' in val_str and ')' in val_str:
            parts = val_str.split('('); prev = parts[0].strip(); real = parts[1].replace(')', '').strip()
            if prev in ['A', 'B'] and real in ['A', 'B']:
                color = 'green' if real == prev else 'red'; return f'color: {color}; font-weight: bold;'
        return ''
    styled_df = df_pivot.style.map(color_text); return styled_df

# Função create_metrics RECRiada para Tab 3 original
def create_metrics(df_acertos_tab3, mesoregioes_selecionadas_tab3):
    """Cria métricas de resumo para a Tab 3 (versão original)."""
    # Certifica que df_acertos_tab3 não está vazio e tem as colunas necessárias
    if df_acertos_tab3.empty or 'acerto' not in df_acertos_tab3.columns or 'Ano' not in df_acertos_tab3.columns:
        st.warning("Dados insuficientes para calcular métricas de acurácia.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        # Usa o número de mesoregiões únicas presentes nos *dados filtrados*
        mesos_nos_dados = df_acertos_tab3['Mesorregião'].nunique() if 'Mesorregião' in df_acertos_tab3.columns else 0
        st.metric("Mesorregiões Analisadas", mesos_nos_dados)
    with col2:
        media_geral = df_acertos_tab3['acerto'].mean()
        st.metric("Acurácia Média Geral", f"{media_geral:.1%}" if pd.notna(media_geral) else "N/A")
    with col3:
        ultimo_ano_disponivel = df_acertos_tab3['Ano'].max()
        if pd.notna(ultimo_ano_disponivel):
            media_ultimo = df_acertos_tab3[df_acertos_tab3['Ano'] == ultimo_ano_disponivel]['acerto'].mean()
            st.metric(f"Acurácia Média ({ultimo_ano_disponivel})", f"{media_ultimo:.1%}" if pd.notna(media_ultimo) else "N/A")
        else:
            st.metric("Acurácia Último Ano", "N/A")


# Função para Mapa (Tab 4 - Atualizada com escala fixa)
def create_map_chart(gdf_merged, year_str):
    if gdf_merged is None or gdf_merged.empty or 'Acerto (%)' not in gdf_merged.columns: 
        return None

    fig = px.choropleth_mapbox(
        gdf_merged, 
        geojson=gdf_merged.geometry, 
        locations=gdf_merged.index, 
        color='Acerto (%)', 
        hover_name='Nome_Mesorregiao', 
        hover_data={'Acerto (%)': ':.1f'}, 
        color_continuous_scale=CORES_MAPA, 
        range_color=(50, 100),  # <- Escala fixa entre 50% e 100%
        mapbox_style="carto-positron", 
        center={"lat": -18.5122, "lon": -44.5550}, 
        zoom=5, 
        opacity=0.7, 
        labels={'Acerto (%)':'Acurácia'}
    )

    fig.update_layout(
        title=f"Acurácia Média por Mesorregião - {year_str}", 
        margin={"r":0,"t":40,"l":0,"b":0},
        coloraxis_colorbar=dict(
            title="Acurácia (%)", 
            tickvals=np.linspace(50, 100, 5),  # <- Ticks também fixos
            tickformat=".0f"
        )
    )

    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>Acurácia: %{z:.1f}%<extra></extra>"
    )

    return fig

# --- Carregamento Principal e Merge (Mantido da versão anterior) ---
all_df = load_all_data(ANOS_INT)
df_meso = load_mesoregiao_data()
geojson_data = load_geojson(GEOJSON_PATH)

# Adiciona informações de mesoregião aos dados principais (se possível)
if not all_df.empty and not df_meso.empty and 'v21' in all_df.columns and 'v21' in df_meso.columns:
    # Garante que 'Mesorregião' e 'Municípios' não sejam duplicadas se já existirem em all_df
    # Define as colunas potenciais a serem trazidas de df_meso
    potential_cols_from_meso = ['v21', 'Municípios', 'Mesorregião', 'id']
    # Filtra pelas colunas que realmente existem em df_meso
    cols_available_in_meso = [col for col in potential_cols_from_meso if col in df_meso.columns]

    # Identifica quais dessas colunas (exceto a chave 'v21') já existem em all_df
    cols_already_in_all_df = [
        col for col in cols_available_in_meso
        if col in all_df.columns and col != 'v21'
    ]

    # Define as colunas finais a serem selecionadas de df_meso para o merge:
    # Inclui a chave 'v21' e as colunas disponíveis que NÃO estão já em all_df
    cols_to_select_for_merge = ['v21'] + [
        col for col in cols_available_in_meso
        if col != 'v21' and col not in cols_already_in_all_df
    ]

    # Só faz o merge se houver alguma coluna NOVA a ser adicionada (além da chave 'v21')
    if len(cols_to_select_for_merge) > 1:
        print(f"Colunas a serem selecionadas de df_meso para merge: {cols_to_select_for_merge}") # Log útil
        try:
            # Prepara o lado direito do merge: seleciona colunas e garante unicidade da chave 'v21'
            df_meso_subset = df_meso[cols_to_select_for_merge].drop_duplicates(subset=['v21'])

            # Realiza o merge
            all_df = pd.merge(
                all_df,
                df_meso_subset, # Usa o subset preparado
                on="v21",       # Chave do merge
                how="left"      # Mantém todas as linhas de all_df
            )
            print("Merge com df_meso realizado com sucesso.") # Log
        except Exception as e:
            st.warning(f"Erro ao mesclar dados de mesoregião: {e}")
            print(f"Traceback do erro de merge: {traceback.format_exc()}") # Log detalhado
    else:
        print("Nenhuma coluna nova para mesclar de df_meso.") # Log

# Fallbacks se o merge falhou ou não aconteceu (mantido igual)
if 'Mesorregião' not in all_df.columns: all_df['Mesorregião'] = 'Desconhecida'
if 'Municípios' not in all_df.columns:
    if not df_meso.empty and 'id' in all_df.columns and 'id' in df_meso.columns and 'Municípios' in df_meso.columns:
        id_to_municipio = df_meso.set_index('id')['Municípios'].to_dict()
        all_df['Municípios'] = all_df['id'].map(id_to_municipio).fillna('Desconhecido')
    else: all_df['Municípios'] = 'Desconhecido'


# --- Interface Principal ---
st.title("📊 Previsão e Análise Financeira Municipal")

if all_df.empty:
    st.error("Não foi possível carregar nenhum dado de resultado (`resultado_final*.xlsx`). Verifique os arquivos e caminhos.")
else:
    # Abas para organização
    tab1, tab2, tab3, tab4 = st.tabs([
        "Visão Geral (Distribuição)", # Tab 1 Mantida
        "Análise Municipal",          # Tab 2 Revertida/Adaptada
        "Análise de Acurácia",   # Tab 3 Revertida/Adaptada
        "Mapa de Acurácia"       # Tab 4 Mantida
    ])

    # --- Tab 1: Distribuição (Mantida da versão anterior) ---
    with tab1:
        st.subheader("Distribuição de Variável por Situação (A/B)")
        col1_t1, col2_t1 = st.columns(2)
        with col1_t1:
            selected_year_t1 = st.selectbox("Selecione o Ano:", options=ANOS_STR, index=len(ANOS_STR)-1, key='year_tab1', help="Ano dos dados a serem visualizados.")
        with col2_t1:
            if variaveis: selected_variable_t1 = st.selectbox("Selecione a Variável:", options=variaveis, index=0, key='var_tab1', help="Variável a ser analisada na distribuição.")
            else: st.warning("Nenhuma variável disponível para seleção."); selected_variable_t1 = None

        df_year_t1 = all_df[all_df['Ano'] == selected_year_t1].copy()
        if not df_year_t1.empty and selected_variable_t1:
            with st.spinner(f"Gerando gráfico de distribuição para {selected_variable_t1} em {selected_year_t1}..."):
                fig_dist = create_distribution_chart(df_year_t1, selected_variable_t1, f"Distribuição de '{selected_variable_t1}'", selected_year_t1)
                if fig_dist: st.plotly_chart(fig_dist, use_container_width=True)
        elif selected_variable_t1: st.warning(f"Não há dados disponíveis para o ano {selected_year_t1}.")

    # --- Tab 2: Evolução Municipal (Lógica Revertida/Adaptada) ---
    with tab2:
        st.subheader("Evolução Histórica por Município")
        st.markdown("Acompanhe a evolução de uma variável e a classificação (prevista vs. real) para os municípios selecionados ao longo dos anos.")

        municipios_disponiveis_t2 = sorted(all_df['Municípios'].unique()) if 'Municípios' in all_df.columns else []
        if not municipios_disponiveis_t2:
            st.warning("Nenhum nome de município disponível.")
            selected_municipios_t2 = []
        else:
            selected_municipios_t2 = st.multiselect(
                 "Selecione um ou mais Municípios:",
                 options=municipios_disponiveis_t2,
                 # Removido default para não poluir inicialmente
                 key='municipios_tab2_reverted',
                 help="Digite para buscar ou selecione na lista."
             )

        if not selected_municipios_t2:
            st.info("Selecione pelo menos um município.")
        else:
            # Seleção da variável (usando a lista global 'variaveis')
            if variaveis:
                 selected_variable_t2 = st.selectbox(
                     "Variável para Análise:",
                     options=variaveis,
                     key='var_tab2_reverted'
                 )
            else:
                 st.warning("Lista de variáveis não disponível.")
                 selected_variable_t2 = None

            # Filtrar o DataFrame GERAL `all_df` pelos municípios selecionados
            # Este substitui o loop e concatenação da versão original
            df_final_t2 = all_df[all_df['Municípios'].isin(selected_municipios_t2)].copy()

            if not df_final_t2.empty and selected_variable_t2:
                # Gerar gráfico de evolução (usando Plotly Express diretamente como na versão original)
                with st.spinner(f"Gerando gráfico de evolução para {selected_variable_t2}..."):
                    try:
                         fig_evol_t2 = px.line(
                             df_final_t2.sort_values('Ano'), # Garante ordem correta
                             x="Ano", y=selected_variable_t2,
                             color="Municípios", # Usa a coluna que já veio do merge
                             markers=True, line_shape='spline',
                             title=f"Evolução de '{selected_variable_t2}' por Município"
                         )
                         st.plotly_chart(fig_evol_t2, use_container_width=True)
                    except Exception as e:
                         st.error(f"Erro ao gerar gráfico de evolução: {e}")

                # Tabela de Classificações (lógica da versão original mantida)
                st.markdown("---")
                st.subheader("Histórico de Classificações")
                st.markdown("Valores mostram `Previsto (Real)`. <span style='color:green; font-weight:bold;'>Verde</span> indica acerto, <span style='color:red; font-weight:bold;'>Vermelho</span> indica erro.", unsafe_allow_html=True)

                with st.spinner("Gerando tabela de classificações..."):
                    try:
                        df_pivot_t2 = df_final_t2.pivot_table(
                            index='Municípios', columns='Ano',
                            values=['y_real', 'y_previsto'], aggfunc='first'
                        )
                        df_formatted_t2 = pd.DataFrame(index=df_pivot_t2.index)
                        for ano in ANOS_STR:
                            col_real = ('y_real', ano); col_prev = ('y_previsto', ano)
                            if col_real in df_pivot_t2.columns and col_prev in df_pivot_t2.columns:
                                df_formatted_t2[ano] = (df_pivot_t2[col_prev].fillna('-').astype(str) + " (" + df_pivot_t2[col_real].fillna('-').astype(str) + ")")
                            else: df_formatted_t2[ano] = "N/A"

                        styled_table = format_classification_table(df_formatted_t2)
                        st.dataframe(styled_table, use_container_width=True, height=min(400, (len(selected_municipios_t2) + 1) * 35 + 3))
                    except Exception as e: st.error(f"Erro ao gerar tabela de classificações: {e}")

            elif not selected_variable_t2: pass # Aviso já dado
            else: st.warning("Nenhum dado encontrado para os municípios selecionados.")


    # --- Tab 3: Assertividade (Lógica Revertida/Adaptada) ---
    with tab3:
        st.subheader("Análise da Acurácia do Modelo por Mesorregião")
        st.markdown("Avalie a taxa de acerto do modelo ao longo do tempo para as mesorregiões selecionadas.")

        # Seleção de Mesorregiões (lógica da versão original)
        meso_disponiveis_t3 = sorted(all_df['Mesorregião'].unique()) if 'Mesorregião' in all_df.columns else []
        if not meso_disponiveis_t3 or 'Desconhecida' in meso_disponiveis_t3:
             st.warning("Nomes de mesorregião não disponíveis ou inválidos.")
             selected_meso_t3 = []
        else:
            todas_meso = st.checkbox("Selecionar Todas as Mesorregiões", value=True, key='all_meso_tab3_reverted')
            meso_options_t3 = meso_disponiveis_t3
            if todas_meso:
                 selected_meso_t3 = meso_options_t3
                 st.multiselect("Mesorregiões Selecionadas:", options=meso_options_t3, default=meso_options_t3, disabled=True, key='meso_tab3_reverted_disabled')
            else:
                 selected_meso_t3 = st.multiselect("Selecione uma ou mais Mesorregiões:", options=meso_options_t3, default=meso_options_t3[0] if meso_options_t3 else None, key='meso_tab3_reverted_enabled')

        if not selected_meso_t3:
            st.info("Selecione pelo menos uma mesorregião.")
        else:
            # Filtrar o DataFrame GERAL `all_df` pelas mesorregiões selecionadas
            # Este substitui o loop e concatenação da versão original
            df_acertos_t3 = all_df[all_df['Mesorregião'].isin(selected_meso_t3)].copy()

            if not df_acertos_t3.empty:
                # Usar a função create_metrics recriada
                create_metrics(df_acertos_t3, selected_meso_t3)

                # Gráfico de Assertividade (lógica de groupby da versão original)
                with st.spinner("Gerando gráfico de Acurácia..."):
                    try:
                        assertividade_plot_df = df_acertos_t3.groupby(['Mesorregião', 'Ano'])['acerto'].mean().reset_index()
                        assertividade_plot_df.rename(columns={'acerto': 'Taxa de Acerto'}, inplace=True) # Renomeia para label

                        fig_assert_t3 = px.line(
                            assertividade_plot_df.sort_values('Ano'),
                            x="Ano", y="Taxa de Acerto", color="Mesorregião",
                            markers=True, # Adiciona marcadores como na original
                            title="Acurácia Média por Mesorregião",
                            labels={'Taxa de Acerto': 'Taxa de Acerto', 'Ano': 'Ano'}
                         )
                        fig_assert_t3.update_yaxes(tickformat=".0%") # Formato percentual
                        st.plotly_chart(fig_assert_t3, use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro ao gerar gráfico de assertividade: {e}")
            else:
                st.warning("Nenhum dado encontrado para as mesorregiões selecionadas.")


    # --- Tab 4: Mapa de Assertividade (Mantida da versão anterior) ---
    with tab4:
        st.subheader("Mapa de Acurácia Média por Mesorregião")
        st.markdown("Visualize a distribuição geográfica da taxa média de acerto do modelo em um ano específico.")
        selected_year_t4 = st.selectbox("Selecione o Ano para o Mapa:", options=ANOS_STR, index=len(ANOS_STR)-1, key='year_tab4')

        if geojson_data is None: st.error("Dados geográficos não carregados. Mapa indisponível.")
        else:
            df_year_t4 = all_df[all_df['Ano'] == selected_year_t4].copy()
            if not df_year_t4.empty and 'Mesorregião' in df_year_t4.columns:
                assertividade_media_ano = df_year_t4.groupby("Mesorregião")["acerto"].mean().reset_index()
                assertividade_media_ano["Acerto (%)"] = assertividade_media_ano["acerto"] * 100
                if 'Nome_Mesorregiao' in geojson_data.columns:
                     gdf_merged_t4 = geojson_data.merge(assertividade_media_ano[['Mesorregião', 'Acerto (%)']], left_on="Nome_Mesorregiao", right_on="Mesorregião", how="left")
                     gdf_merged_t4['Acerto (%)'].fillna(0, inplace=True)
                     with st.spinner("Gerando mapa de Acurácia..."):
                         fig_map = create_map_chart(gdf_merged_t4, selected_year_t4)
                         if fig_map: st.plotly_chart(fig_map, use_container_width=True)
                else: st.error("Coluna 'Nome_Mesorregiao' não encontrada no GeoJSON.")
            else: st.warning(f"Não há dados de classificação ou mesorregião para {selected_year_t4}.")
