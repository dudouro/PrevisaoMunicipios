import os
import pandas as pd
import plotly.express as px
import streamlit as st
# Certifique-se que 'extra.variaveis' está acessível ou comente a importação
try:
    from extra import variaveis
except ImportError:
    # st.warning("Módulo 'extra' ou variável 'variaveis' não encontrados. Funcionalidades da Tab2 podem ser afetadas.")
    variaveis = [] # Define como lista vazia para evitar erros posteriores
from PIL import Image
import traceback # Para imprimir erros detalhados

# Configurações da página
st.set_page_config(page_title="Análise do Modelo", layout="wide", page_icon='📈')
st.title("📈 Análise do Desempenho do Modelo")

# Constantes e configurações
ANOS = list(range(17, 23))  # 2017 a 2022
CORES_GRAFICO_LINHA = px.colors.qualitative.T10 # Para Tab1
CORES_IMPORTANCIA = px.colors.qualitative.Plotly # Para Tab2
CSS = """
<style>
[data-testid="stMetricLabel"] {font-size: 1.1rem;}
div[data-testid="stExpander"] details {border: 1px solid #eee;}
.main .block-container { padding-top: 3rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- FUNÇÃO CARREGAR_DADOS_CLASSIFICACAO (Mantida como na versão anterior funcional) ---
@st.cache_data
def carregar_dados_classificacao(janela):
    """
    Carrega e processa dados de classificação dos arquivos Excel,
    filtrando as linhas 'A', 'B' e 'accuracy' e transformando para formato largo
    (Ex: A_precision, B_precision, accuracy_precision).
    Converte colunas de métricas para numérico. Usa nomes internos das métricas.
    """
    dfs = []
    prefixo_arquivo = "ext_" if janela == 'janela_extendida' else ""
    nome_base_arquivo = "classification_report"
    linhas_desejadas = ['A', 'B', 'accuracy']
    metricas_desejadas = ['precision', 'recall', 'f1-score', 'support'] # Nomes internos

    # print(f"--- Iniciando carregamento para Janela: {janela} ---") # Log

    for ano in ANOS:
        path_relativo = os.path.join("resultados", janela, str(ano), f"{prefixo_arquivo}{nome_base_arquivo}{ano}.xlsx")
        path = path_relativo
        if not os.path.exists(path): continue

        try:
            df = pd.read_excel(path, index_col=0)
            df.index = df.index.map(str)

            metricas_presentes_excel = [m for m in metricas_desejadas if m in df.columns]
            if not metricas_presentes_excel: continue
            df_metricas = df[metricas_presentes_excel]

            linhas_presentes_excel = df_metricas.index.intersection(linhas_desejadas)
            if linhas_presentes_excel.empty: continue
            df_filtrado = df_metricas.loc[linhas_presentes_excel]

            df_reset = df_filtrado.reset_index().rename(columns={'index': 'Linha'})
            df_melted = df_reset.melt(id_vars='Linha', var_name='Metrica', value_name='Valor')
            df_melted['ColunaFinal'] = df_melted['Linha'].astype(str) + '_' + df_melted['Metrica'].astype(str)
            df_melted['Valor'] = pd.to_numeric(df_melted['Valor'].astype(str).str.replace(',', '.', regex=False), errors='coerce')
            df_transformado = df_melted.pivot_table(index=None, columns='ColunaFinal', values='Valor')

            if df_transformado.empty: continue

            df_transformado["Ano"] = 2000 + ano
            df_transformado["Janela"] = janela
            dfs.append(df_transformado)

        except Exception as e:
            print(f"Erro ao processar o arquivo {path}: {e}")
            traceback.print_exc()

    # print(f"--- Fim do carregamento para Janela: {janela}. {len(dfs)} arquivos processados. ---") # Log

    if not dfs: return pd.DataFrame()

    try:
        df_final = pd.concat(dfs, ignore_index=True, sort=False)
        for col in df_final.columns:
             if '_' in col and col not in ['Ano', 'Janela']:
                 if not pd.api.types.is_numeric_dtype(df_final[col]):
                      df_final[col] = pd.to_numeric(df_final[col].astype(str).str.replace(',', '.', regex=False), errors='coerce')
        return df_final
    except Exception as e:
        print(f"Erro ao concatenar DataFrames para {janela}: {e}")
        traceback.print_exc()
        return pd.DataFrame()

# --- Funções carregar_arvores e carregar_importancias (Mantidas) ---
def carregar_arvores():
    arvores = {}
    for ano in ANOS:
        path = os.path.join("resultados", "janela_extendida", str(ano), f"ext_arvore{ano}.png")
        if os.path.exists(path): arvores[ano] = path
    return arvores

@st.cache_data
def carregar_importancias():
    dados = []
    for ano in ANOS:
        try:
            path = os.path.join("resultados", "janela_fixa", str(ano), f"feature_importances{ano}.xlsx")
            if os.path.exists(path):
                df = pd.read_excel(path); df["Ano"] = f"20{ano}"; dados.append(df)
        except Exception as e: st.error(f"Erro ao carregar feature_importances de 20{ano}: {str(e)}")
    return pd.concat(dados, ignore_index=True) if dados else pd.DataFrame()

# --- Interface principal ---
tab1, tab2, tab3 = st.tabs(["Métricas de Classificação", "Importância de Variáveis", "Exemplo de Árvore"])

# --- Tab 1: Métricas de Classificação (MODIFICADO COM TRADUÇÃO E GLOSSÁRIO) ---
with tab1:
    st.header("Desempenho do Modelo")

    # Carregar dados
    with st.spinner("Processando dados de classificação (Classes A, B e Acurácia)..."):
        df_fixa = carregar_dados_classificacao("janela_fixa")
        df_extendida = carregar_dados_classificacao("janela_extendida")

        dfs_para_concatenar = []
        if isinstance(df_fixa, pd.DataFrame) and not df_fixa.empty: dfs_para_concatenar.append(df_fixa)
        if isinstance(df_extendida, pd.DataFrame) and not df_extendida.empty: dfs_para_concatenar.append(df_extendida)

        if dfs_para_concatenar:
            try:
                df_classificacao_completo = pd.concat(dfs_para_concatenar, ignore_index=True, sort=False)
            except Exception as e:
                st.error("Erro ao concatenar os resultados das janelas na Tab1:"); st.exception(e)
                df_classificacao_completo = pd.DataFrame()
        else: df_classificacao_completo = pd.DataFrame()

    if df_classificacao_completo.empty:
        st.error("Nenhum dado de classificação válido (Classes A, B ou Acurácia) foi carregado.")
    else:
        # --- Mapeamentos para Nomes Amigáveis ---
        mapa_linhas_nomes = {'A': 'Classe A', 'B': 'Classe B', 'accuracy': 'Acurácia Modelo'}
        mapa_linhas_nomes_inverso = {v: k for k, v in mapa_linhas_nomes.items()}
        mapa_janela_nomes = {'janela_fixa': 'Janela Fixa', 'janela_extendida': 'Janela Extendida'}
        mapa_janela_nomes_inverso = {v: k for k, v in mapa_janela_nomes.items()}
        # MODIFICADO: Mapeamento de Métricas
        mapa_metricas_nomes = {
            'precision': 'Precisão',
            'recall': 'Sensibilidade (Recall)', # Nome mais completo
            'f1-score': 'F1-Score',
            'support': 'Suporte'
        }
        mapa_metricas_nomes_inverso = {v: k for k, v in mapa_metricas_nomes.items()}

        # --- Widgets de Seleção ---
        col1, col2, col3 = st.columns(3)

        # Extrai opções disponíveis do DataFrame completo
        janelas_disponiveis_orig = df_classificacao_completo['Janela'].unique().tolist()
        opcoes_janela_select = [mapa_janela_nomes.get(j, j) for j in janelas_disponiveis_orig]

        linhas_permitidas_config = ['A', 'B', 'accuracy'] # Nomes internos
        metricas_permitidas_config = list(mapa_metricas_nomes.keys()) # Nomes internos das métricas mapeadas
        colunas_disponiveis_todas = df_classificacao_completo.columns.tolist()

        # Extrai opções de LINHAS disponíveis (usa nomes amigáveis)
        linhas_reais_orig = sorted([l for l in linhas_permitidas_config if any(c.startswith(f"{l}_") for c in colunas_disponiveis_todas)])
        opcoes_linhas_select = [mapa_linhas_nomes.get(l, l) for l in linhas_reais_orig]

        # Extrai opções de MÉTRICAS disponíveis (usa nomes amigáveis)
        metricas_reais_orig = sorted([m for m in metricas_permitidas_config if any(c.endswith(f"_{m}") for c in colunas_disponiveis_todas)])
        opcoes_metrica_select = [mapa_metricas_nomes.get(m, m) for m in metricas_reais_orig]


        if not opcoes_linhas_select or not opcoes_metrica_select:
             st.error(f"Não foi possível extrair opções válidas de Linhas/Métricas das colunas carregadas.")
        else:
            # Coloca os widgets nas colunas
            with col1:
                linhas_selecionadas_nomes = st.multiselect(
                    "Selecione Classe(s) / Acurácia:", options=opcoes_linhas_select,
                    default=[nome for nome in opcoes_linhas_select if nome in ['Classe A', 'Classe B']] # Default A e B
                )
                linhas_selecionadas_orig = [mapa_linhas_nomes_inverso.get(nome, nome) for nome in linhas_selecionadas_nomes]

            with col2:
                 # MODIFICADO: Usa nomes traduzidos nas opções
                metrica_selecionada_nome = st.selectbox(
                    "Selecione a Métrica:", options=opcoes_metrica_select,
                    # Encontra o índice do nome traduzido para 'f1-score'
                    index=opcoes_metrica_select.index(mapa_metricas_nomes.get('f1-score', 'F1-Score'))
                          if mapa_metricas_nomes.get('f1-score', 'F1-Score') in opcoes_metrica_select else 0
                )
                # Obtém o nome interno da métrica selecionada para usar nos dados
                metrica_selecionada_orig = mapa_metricas_nomes_inverso.get(metrica_selecionada_nome, metrica_selecionada_nome)

            with col3:
                janelas_selecionadas_nomes = st.multiselect(
                    "Selecione a(s) Janela(s):", options=opcoes_janela_select,
                    default=opcoes_janela_select
                )
                janelas_selecionadas_orig = [mapa_janela_nomes_inverso.get(nome, nome) for nome in janelas_selecionadas_nomes]


            # --- Filtragem e Plotagem ---
            if not linhas_selecionadas_orig or not janelas_selecionadas_orig:
                st.warning("Por favor, selecione pelo menos uma Classe/Acurácia e uma Janela.")
            else:
                # 1. FILTRAR por Janela
                df_filtrado_janela = df_classificacao_completo[
                    df_classificacao_completo['Janela'].isin(janelas_selecionadas_orig)
                ].copy()

                if df_filtrado_janela.empty:
                    st.warning("Nenhum dado encontrado para a(s) janela(s) selecionada(s).")
                else:
                    # 2. Construir lista de colunas alvo usando NOMES INTERNOS
                    colunas_alvo = [f"{lin}_{metrica_selecionada_orig}" for lin in linhas_selecionadas_orig
                                    if f"{lin}_{metrica_selecionada_orig}" in df_filtrado_janela.columns]

                    if not colunas_alvo:
                        st.error(f"Nenhuma coluna encontrada para a métrica '{metrica_selecionada_nome}' ({metrica_selecionada_orig}) "
                                 f"e as linhas selecionadas ({', '.join(linhas_selecionadas_nomes)}) "
                                 f"na(s) janela(s) filtrada(s).")
                    else:
                        # 3. Selecionar colunas e derreter (melt)
                        colunas_para_melt = ['Ano', 'Janela'] + colunas_alvo
                        df_subset = df_filtrado_janela[colunas_para_melt].copy()

                        try:
                            df_melted = pd.melt(
                                df_subset, id_vars=['Ano', 'Janela'], value_vars=colunas_alvo,
                                var_name='Coluna_Original', value_name='Valor'
                            )
                            df_melted.dropna(subset=['Valor'], inplace=True)

                            if df_melted.empty:
                                 st.warning(f"Não há valores numéricos válidos para a métrica '{metrica_selecionada_nome}' nas seleções feitas.")
                            else:
                                # 4. Preparar para plotagem (usando nomes amigáveis)
                                df_melted['Linha_Orig'] = df_melted['Coluna_Original'].str.split('_').str[0]
                                df_melted['Linha_Nome'] = df_melted['Linha_Orig'].map(mapa_linhas_nomes).fillna(df_melted['Linha_Orig'])
                                df_melted['Janela_Nome'] = df_melted['Janela'].map(mapa_janela_nomes).fillna(df_melted['Janela'])
                                df_melted['Grupo'] = df_melted['Linha_Nome'] + ' - ' + df_melted['Janela_Nome']
                                df_melted['Ano'] = df_melted['Ano'].astype(str)

                                # 5. Plotar (usando nome traduzido da métrica)
                                is_support = metrica_selecionada_orig == 'support' # Usa nome interno para lógica
                                formato_y = ".0f" if is_support else ".1%"
                                # Usa nome TRADUZIDO para label do eixo Y
                                label_y = f"{metrica_selecionada_nome}" if is_support else f"{metrica_selecionada_nome} (%)"

                                fig = px.line(
                                    df_melted.sort_values("Ano"),
                                    x="Ano", y="Valor", color="Grupo",
                                    markers=True, line_shape="spline",
                                    # Usa nome TRADUZIDO no título
                                    title=f"Evolução da Métrica '{metrica_selecionada_nome}' por Item e Janela",
                                    labels={"Valor": label_y, "Ano": "Ano de Referência", "Grupo": "Item - Janela"},
                                    color_discrete_sequence=CORES_GRAFICO_LINHA
                                )
                                fig.update_layout(
                                    hovermode="x unified", yaxis_tickformat=formato_y,
                                    xaxis_title=None, legend_title_text="Item - Janela"
                                )
                                fig.update_xaxes(type='category')
                                st.plotly_chart(fig, use_container_width=True)

                                # 6. NOVO: Glossário de Métricas
                                with st.expander("📖 Glossário de Métricas", expanded=False):
                                    st.markdown(f"""
                                    *   **Precisão (Precision):** De todas as vezes que o modelo previu uma classe específica (ex: Classe A), quantas vezes ele acertou? (Verdadeiros Positivos / (Verdadeiros Positivos + Falsos Positivos)). *Foca em evitar classificações incorretas como sendo da classe.*
                                    *   **Sensibilidade (Recall ou Revocação):** De todas as instâncias que *realmente* pertenciam a uma classe (ex: Classe A), quantas o modelo conseguiu identificar corretamente? (Verdadeiros Positivos / (Verdadeiros Positivos + Falsos Negativos)). *Foca em encontrar todas as instâncias da classe.*
                                    *   **F1-Score:** Média harmônica entre Precisão e Sensibilidade. Útil para um balanço entre as duas, especialmente quando as classes são desbalanceadas. Varia de 0 a 1 (melhor).
                                    *   **Suporte (Support):** Número real de ocorrências de cada classe nos dados de teste. Ajuda a entender a relevância das métricas (métricas de classes com baixo suporte podem ser menos confiáveis).
                                    *   **Acurácia Modelo:** Percentual geral de acertos do modelo considerando todas as classes. (Total de Acertos / Total de Previsões). Pode ser enganosa em dados desbalanceados.
                                    """)

                                # 7. Expander com dados brutos (mantido)
                                with st.expander("📊 Visualizar Dados Brutos do Gráfico", expanded=False):
                                    fmt = "{:.0f}" if is_support else "{:.2%}"
                                    st.dataframe(
                                        df_melted[['Ano', 'Janela_Nome', 'Linha_Nome', 'Valor', 'Grupo']]
                                        .sort_values(["Grupo", "Ano"])
                                        .rename(columns={'Janela_Nome': 'Janela', 'Linha_Nome': 'Item'})
                                        .style.format({'Valor': fmt}, na_rep="-"),
                                        height=400, use_container_width=True, hide_index=True
                                    )

                        except Exception as e:
                             st.error("Erro ao preparar ou plotar os dados (melt/processamento):"); st.exception(e)


# --- Tab 2: Importância de Variáveis (Mantida como na versão anterior funcional) ---
with tab2:
    st.header("Análise de Importância de Variáveis")
    with st.spinner("Carregando dados de importância..."):
        df_importancias = carregar_importancias()
    if not df_importancias.empty:
        df_importancias['Ano'] = df_importancias['Ano'].astype(str)
        anos_disponiveis = sorted(df_importancias['Ano'].unique())
        opcoes_variaveis = ['Todas'] + (variaveis if variaveis else sorted(df_importancias['feature'].unique()))
        with st.container(border=True):
            st.subheader("Configurações")
            col1_t2, col2_t2 = st.columns(2)
            with col1_t2:
                selecionadas_t2 = st.multiselect("Selecione as variáveis:", options=opcoes_variaveis, default=['Todas'], key="vars_multiselect")
                variaveis_filtrar = variaveis if 'Todas' in selecionadas_t2 else [v for v in selecionadas_t2 if v != 'Todas']
                if not variaveis_filtrar and 'Todas' in selecionadas_t2: variaveis_filtrar = sorted(df_importancias['feature'].unique())
            with col2_t2:
                anos_selecionados = st.multiselect("Filtrar por ano:", options=anos_disponiveis, default=anos_disponiveis, key="anos_multiselect")
        st.divider(); st.subheader("Visualização Temporal")
        df_filtrado_t2 = df_importancias[df_importancias['feature'].isin(variaveis_filtrar) & df_importancias['Ano'].isin(anos_selecionados)].copy()
        if not df_filtrado_t2.empty:
            df_filtrado_t2['importance'] = pd.to_numeric(df_filtrado_t2['importance'], errors='coerce')
            df_filtrado_t2.dropna(subset=['importance'], inplace=True)
            if not df_filtrado_t2.empty:
                fig_imp = px.line(df_filtrado_t2.sort_values("Ano"), x="Ano", y="importance", color="feature", line_shape="spline", markers=True, labels={"importance": "Importância Média", "Ano": "Ano de Referência", "feature": "Variável"}, color_discrete_sequence=CORES_IMPORTANCIA)
                fig_imp.update_layout(yaxis_tickformat=".1%", legend_title_text="Variáveis", hovermode="x unified", height=500, xaxis_title=None)
                fig_imp.update_xaxes(type='category'); st.plotly_chart(fig_imp, use_container_width=True)
                st.divider(); st.subheader("Análise Detalhada")
                col_analise1, col_analise2 = st.columns(2)
                with col_analise1:
                    with st.expander("🔝 Top 5 Variáveis (Média no Período)", expanded=True):
                        top5 = (df_filtrado_t2.groupby('feature')['importance'].mean().sort_values(ascending=False).head(5).reset_index())
                        st.dataframe(top5.style.format({'importance': '{:.2%}'}), hide_index=True, height=250, use_container_width=True)
                with col_analise2:
                     with st.expander("📈 Tendências Gerais", expanded=True):
                        media_geral = df_filtrado_t2['importance'].mean(); media_anual = df_filtrado_t2.groupby('Ano')['importance'].mean(); variacao_media_anual = media_anual.diff().mean()
                        cols_stats = st.columns(2)
                        with cols_stats[0]: st.metric("Média Geral", f"{media_geral:.2%}" if pd.notna(media_geral) else "N/A", help="Média de importância considerando os anos e variáveis selecionadas.")
                        with cols_stats[1]: st.metric("Variação Anual Média", f"{variacao_media_anual:.2%}" if pd.notna(variacao_media_anual) else "N/A", help="Variação percentual média na importância de um ano para o outro.")
                with st.expander("📁 Visualizar Dados Completos (Importância Média por Ano)"):
                     df_pivot = df_filtrado_t2.pivot_table(index='Ano', columns='feature', values='importance', aggfunc='mean')
                     st.dataframe(df_pivot.style.format("{:.2%}", na_rep="-"), use_container_width=True)
            else: st.warning("Nenhum dado numérico de importância disponível após limpeza para os filtros selecionados.")
        else: st.warning("Nenhum dado de importância disponível para os filtros selecionados.")
    else: st.error("Nenhum dado de importância de variáveis foi encontrado.")

# --- Tab 3: Exemplo de Árvore (Mantida como na versão anterior funcional) ---
with tab3:
    st.header("🌳 Visualização de Árvore de Decisão (Exemplo)")
    arvores = carregar_arvores()
    if arvores:
        anos_arvore_disponiveis = sorted(arvores.keys(), reverse=True)
        ano_arvore_selecionado = st.selectbox("Selecione o ano para visualizar a árvore:", options=anos_arvore_disponiveis, format_func=lambda x: f"20{x}", key="arvore_select")
        if ano_arvore_selecionado:
            img_path = arvores[ano_arvore_selecionado]
            try:
                image = Image.open(img_path); col1_img, col2_img, col3_img = st.columns([1, 4, 1])
                with col2_img:
                    st.image(image, caption=f"Árvore de Decisão - 20{ano_arvore_selecionado}", use_container_width=True)
                    st.caption(f"Arquivo: ...{os.sep}{os.path.basename(os.path.dirname(img_path))}{os.sep}{os.path.basename(img_path)}")
                    try:
                        with open(img_path, "rb") as file: st.download_button(label="Baixar imagem da árvore", data=file, file_name=f"arvore_20{ano_arvore_selecionado}.png", mime="image/png")
                    except Exception as e: st.error(f"Não foi possível ler o arquivo da imagem para download: {e}")
            except FileNotFoundError: st.error(f"Arquivo da imagem da árvore não encontrado em: {img_path}")
            except Exception as e: st.error(f"Erro ao carregar ou exibir a imagem da árvore: {e}")
    else: st.error("Nenhum arquivo de imagem de árvore ('ext_arvore*.png') encontrado.")
    st.markdown("""
    ---
    **Interpretação (Geral):**
    - Cada **nó** representa uma decisão baseada em uma variável e um limiar.
    - As **arestas** indicam o fluxo da decisão.
    - Os **valores** ou `samples` mostram quantos dados chegaram ali e como se distribuem entre as classes.
    - A **profundidade** pode indicar a complexidade.
    - As **cores** geralmente indicam a classe majoritária ou a pureza do nó.
    """)
