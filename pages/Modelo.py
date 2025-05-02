import os
import pandas as pd
import plotly.express as px
import streamlit as st
from extra import variaveis

# Configurações da página
st.set_page_config(page_title="Análise do Modelo", layout="wide")
st.title("📈 Análise do Desempenho do Modelo")

# Constantes e configurações
ANOS = list(range(17, 23))  # 2017 a 2022
CORES = px.colors.qualitative.Plotly
CSS = """
<style>
[data-testid="stMetricLabel"] {font-size: 1.1rem;}
div[data-testid="stExpander"] details {border: 1px solid #eee;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

@st.cache_data
def carregar_dados_classificacao(janela):
    """Carrega e processa dados de classificação de forma otimizada"""
    dfs = []
    for ano in ANOS:
        try:
            file_name = f"{'ext_' if janela == 'janela_extendida' else ''}classification_report{ano}.xlsx"
            path = os.path.join("resultados", janela, str(ano), file_name)
            
            if os.path.exists(path):
                df = pd.read_excel(path, index_col=0)
                df = df.T.unstack().to_frame().T
                df.columns = [f"{col[0]}_{col[1]}" for col in df.columns]
                df["Ano"] = 2000 + ano
                df["Janela"] = janela.capitalize()
                dfs.append(df)
        except Exception as e:
            st.error(f"Erro ao carregar {path}: {str(e)}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

@st.cache_data
def carregar_importancias():
    """Carrega dados de importância de variáveis com cache"""
    dados = []
    for ano in ANOS:
        try:
            path = os.path.join("resultados", "janela_fixa", str(ano), f"feature_importances{ano}.xlsx")
            if os.path.exists(path):
                df = pd.read_excel(path)
                df["Ano"] = f"20{ano}"
                dados.append(df)
        except Exception as e:
            st.error(f"Erro no arquivo {path}: {str(e)}")
    return pd.concat(dados) if dados else pd.DataFrame()

# Interface principal
tab1, tab2 = st.tabs(["Métricas de Classificação", "Importância de Variáveis"])

with tab1:
    st.header("Desempenho do Modelo por Janela Temporal")
    
    # Carregar dados
    with st.spinner("Processando dados de classificação..."):
        df_fixa = carregar_dados_classificacao("janela_fixa")
        df_extendida = carregar_dados_classificacao("janela_extendida")
        df_classificacao = pd.concat([df_fixa, df_extendida])

    if not df_classificacao.empty:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            metricas = sorted({col.split('_')[0] for col in df_classificacao.columns if '_' in col})
            # Verifica se 'precision' existe na lista, senão usa o primeiro item
            default_idx = metricas.index('precision') if 'precision' in metricas else 0
            metrica = st.selectbox("Selecione a Métrica:", metricas, index=default_idx)
        with col2:
            classes = sorted({col.split('_')[1] for col in df_classificacao.columns if '_' in col})
            # Verifica se existe a classe 'A' ou usa a primeira disponível
            default_cls = 'A' if 'A' in classes else classes[0] if classes else None
            classe = st.selectbox("Selecione a Classe:", classes, index=classes.index(default_cls) if default_cls else 0)
        with col3:
            st.metric("Total de Anos Analisados", len(ANOS))

        # Processar dados para visualização
        coluna_alvo = f"{metrica}_{classe}"
        dados_plot = df_classificacao[["Ano", "Janela", coluna_alvo]].dropna()
        
        if not dados_plot.empty:
            fig = px.line(
                dados_plot, x="Ano", y=coluna_alvo, color="Janela",
                markers=True, line_shape="spline", 
                title=f"Evolução da {metrica.capitalize()} - Classe {classe}",
                labels={coluna_alvo: f"{metrica} (%)", "Ano": ""},
                color_discrete_sequence=CORES
            )
            fig.update_layout(hovermode="x unified", yaxis_tickformat=".1%")
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("📊 Visualizar Dados Brutos"):
                st.dataframe(
                    dados_plot.style.format({coluna_alvo: "{:.2%}"}),
                    height=300
                )
        else:
            st.warning("Dados insuficientes para a seleção atual")
    else:
        st.error("Nenhum dado de classificação encontrado")

with tab2:
    st.header("Análise de Importância de Variáveis")
    
    # Carregar dados
    with st.spinner("Carregando dados de importância..."):
        df_importancias = carregar_importancias()
    
    if not df_importancias.empty:
        # Adicionar opção 'Todas' na lista de variáveis
        opcoes_variaveis = ['Todas'] + variaveis
        
        # Seção de Configurações
        with st.container(border=True):
            st.subheader("Configurações")
            
            col1, col2 = st.columns(2)
            with col1:
                # Multiselect com opção 'Todas'
                selecionadas = st.multiselect(
                    "Selecione as variáveis:",
                    options=opcoes_variaveis,
                    default=['Todas'],
                    help="Selecione 'Todas' para incluir todas as variáveis"
                )
                
                # Lógica de seleção automática
                if 'Todas' in selecionadas:
                    variaveis_selecionadas = variaveis
                else:
                    variaveis_selecionadas = [v for v in selecionadas if v != 'Todas']
            
            with col2:
                anos_disponiveis = sorted(df_importancias['Ano'].unique())
                anos_selecionados = st.multiselect(
                    "Filtrar por ano:",
                    options=anos_disponiveis,
                    default=anos_disponiveis,
                    help="Selecione os anos para análise"
                )
        # Seção do Gráfico
        st.divider()
        st.subheader("Visualização Temporal")
        
        df_filtrado = df_importancias[
            df_importancias['feature'].isin(variaveis_selecionadas) & 
            df_importancias['Ano'].isin(anos_selecionados)
        ]
        
        if not df_filtrado.empty:
            fig = px.line(
                df_filtrado, 
                x="Ano", 
                y="importance", 
                color="feature",
                line_shape="spline", 
                markers=True,
                labels={"importance": "Importância", "Ano": ""},
                color_discrete_sequence=CORES
            )
            
            fig.update_layout(
                yaxis_tickformat=".0%",
                legend_title_text="Variáveis",
                hovermode="x unified",
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # Seção de Análise
            st.divider()
            st.subheader("Análise Detalhada")
            
            col_analise1, col_analise2 = st.columns(2)
            
            with col_analise1:
                with st.expander("🔝 Top Variáveis", expanded=True):
                    top5 = (df_filtrado.groupby('feature')['importance'].mean()
                           .sort_values(ascending=False).head(5)
                           .reset_index())
                    
                    st.dataframe(
                        top5.style.format({'importance': '{:.2%}'}),
                        hide_index=True,
                        height=250,
                        use_container_width=True
                    )
            
            with col_analise2:
                with st.expander("📈 Tendências", expanded=True):
                    cols_stats = st.columns(2)
                    with cols_stats[0]:
                        st.metric("Média Geral", 
                                 f"{df_filtrado['importance'].mean():.2%}",
                                 help="Média de importância considerando todos os anos e variáveis selecionadas")
                    
                    with cols_stats[1]:
                        st.metric("Variação Anual", 
                                 f"{df_filtrado.groupby('Ano')['importance'].mean().diff().mean():.2%}",
                                 help="Variação média anual entre os períodos selecionados")

            # Seção de Dados Brutos
            with st.expander("📁 Visualizar Dados Completos"):
                st.dataframe(
                    df_filtrado.pivot_table(
                        index='Ano',
                        columns='feature',
                        values='importance',
                        aggfunc='mean'
                    ).style.format("{:.2%}"),
                    use_container_width=True
                )
        
        else:
            st.warning("Nenhum dado disponível para os filtros selecionados")
    
    else:
        st.error("Dados de importância não encontrados")
