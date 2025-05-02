from extra import variaveis
import streamlit as st
import numpy as np
import pandas as pd
import joblib
import os

# Configurações iniciais
st.set_page_config(page_title="Previsão CAPAG+LRF", page_icon="📊", layout="wide")

# Constantes
PASTA_DADOS = "resultados"
NOME_MODELO = "random_forest_saude_municipios.pkl"

# Dicionário de descrições para as variáveis (substitua com suas descrições reais)
DESCRICOES_VARIAVEIS = {
    "receita_total": "Receita total do município no período",
    "receita_propria": "Receita gerada pelo próprio município",
    "receita_transferencias": "Transferências de outros entes",
    "populacao": "População residente no município",
    "receita_corrente_liquida": "Receita corrente líquida (RCL)",
    "despesa_total": "Total de despesas do município",
    "despesa_com_pessoal": "Despesas com folha de pagamento",
    "gastos_operacionais": "Custos operacionais do município",
    "disponibilidade_caixa": "Disponibilidades financeiras",
    "ativo_circulante": "Ativos de curto prazo",
    "obrigacoes_curto_prazo": "Passivos de curto prazo",
    "divida_consolidada": "Dívida consolidada do município",
    "operacoes_credito": "Operações de crédito realizadas"
}

# Funções auxiliares
def carregar_dados_2022():
    """Carrega os dados de referência de 2022"""
    try:
        caminho = os.path.join(PASTA_DADOS, "janela_fixa", "22", "resultado_final22.xlsx")
        df = pd.read_excel(caminho)
        
        # Converter colunas numéricas que podem estar como strings
        for col in df.columns:
            if df[col].dtype == object:
                try:
                    df[col] = pd.to_numeric(df[col])
                except ValueError:
                    pass  # Mantém como string se não for conversível
                    
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados históricos: {str(e)}")
        return None

def carregar_modelo():
    """Carrega o modelo treinado"""
    try:
        return joblib.load(os.path.join(NOME_MODELO))
    except Exception as e:
        st.error(f"Erro ao carregar o modelo: {str(e)}")
        return None

def formatar_numero(valor, prefixo='R$'):
    """Formata valores numéricos para exibição"""
    if pd.isna(valor) or valor == 0:
        return "-"
    return f"{prefixo} {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fazer_previsao(modelo, indicadores):
    """Prepara os dados e faz a previsão garantindo a ordem correta das features"""
    # Mapeamento de nomes alternativos
    mapeamento_nomes = {
        "Despesa com pessoal": "despesa_com_pessoal",
        "Dívida Consolidada": "divida_consolidada",
        "Operações de crédito": "operacoes_credito"
    }
    
    # Cria um DataFrame com as colunas na ordem esperada pelo modelo
    try:
        # Primeiro verifica quais features o modelo espera
        features_esperadas = modelo.feature_names_in_
        
        # Cria um dicionário com os valores na ordem correta
        dados_previsao = {}
        for feature in features_esperadas:
            # Verifica se o nome existe no mapeamento ou nos indicadores
            if feature in indicadores:
                dados_previsao[feature] = [indicadores[feature]]
            elif feature in mapeamento_nomes.values():
                # Encontra a chave original no mapeamento
                for original, padronizado in mapeamento_nomes.items():
                    if padronizado == feature and original in indicadores:
                        dados_previsao[feature] = [indicadores[original]]
                        break
        
        # Cria o DataFrame garantindo a ordem das colunas
        df_previsao = pd.DataFrame(dados_previsao, columns=features_esperadas)
        
        return modelo.predict(df_previsao)
    except Exception as e:
        st.error(f"Erro ao preparar dados para previsão: {str(e)}")
        return None
    
# Interface principal
def main():
    # Carregar dados de referência
    df_referencia = carregar_dados_2022()
    if df_referencia is None:
        st.stop()

    # Cabeçalho
    st.title("🏛 Previsão CAPAG+LRF - Análise Financeira Municipal")
    st.markdown("""
    **Versão BETA**  
    Simule diferentes cenários financeiros utilizando nosso modelo preditivo.
    """)

    # Sidebar - Entrada de dados
    with st.sidebar:
        st.header("📥 Dados de Entrada")
        st.markdown("Informe os valores contábeis do município:")
        
        grupos = {
            "Receitas": [
                "receita_total", "receita_propria",
                "receita_transferencias", "populacao",
                "receita_corrente_liquida"
            ],
            "Despesas": [
                "despesa_total", "despesa_com_pessoal",
                "gastos_operacionais"
            ],
            "Ativos": [
                "disponibilidade_caixa", "ativo_circulante"
            ],
            "Passivos": [
                "obrigacoes_curto_prazo", "divida_consolidada",
                "operacoes_credito"
            ]
        }

        dados = {}
        for grupo, variaveis in grupos.items():
            with st.expander(grupo):
                for var in variaveis:
                    label = var.replace("_", " ").title()
                    help_text = DESCRICOES_VARIAVEIS.get(var, "Informe o valor desta conta contábil")
                    dados[var] = st.number_input(
                        label=label,
                        min_value=0.0,
                        value=0.0,
                        step=1000.0,
                        format="%.2f",
                        help=help_text
                    )

    # Cálculo de indicadores
    try:
        indicadores = calcular_indicadores(dados)
    except Exception as e:
        st.error(f"Erro no cálculo de indicadores: {str(e)}")
        st.stop()

    # Seção de Resultados
    st.header("📈 Resultados da Simulação")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Exibição de indicadores com alertas
        exibir_indicadores(indicadores)
        
    with col2:
        # Comparação com referência
        exibir_referencia(df_referencia, indicadores)
        
        # Previsão do modelo
        if st.button("🎯 Executar Previsão", use_container_width=True):
            modelo = carregar_modelo()
            if modelo:
                try:
                    previsao = fazer_previsao(modelo, indicadores)
                    if previsao is not None:
                        st.success(f"**Resultado da Previsão:** {previsao[0]}")
                except Exception as e:
                    st.error(f"Erro na previsão: {str(e)}")

def calcular_indicadores(dados):
    """Calcula todos os indicadores financeiros com nomes padronizados"""
    indicadores = {}
    
    # Verificação de valores zero para divisão segura
    populacao = dados["populacao"] if dados["populacao"] != 0 else 1
    
    # Cálculos principais - padronizando os nomes
    indicadores["receita_per_capita"] = dados["receita_total"] / populacao
    indicadores["representatividade_da_receita_propria"] = dados["receita_propria"] / dados["receita_total"] if dados["receita_total"] != 0 else 0
    indicadores["participacao_das_receitas_de_transferencias"] = dados["receita_transferencias"] / dados["receita_total"] if dados["receita_total"] != 0 else 0
    indicadores["participacao_dos_gastos_operacionais"] = dados["gastos_operacionais"] / dados["despesa_total"] if dados["despesa_total"] != 0 else 0
    indicadores["cobertura_de_despesas"] = dados["receita_total"] / dados["despesa_total"] if dados["despesa_total"] != 0 else 0
    indicadores["recursos_para_cobertura_de_queda_de_arrecadacao"] = dados["disponibilidade_caixa"] / dados["receita_total"] if dados["receita_total"] != 0 else 0
    indicadores["recursos_para_cobertura_de_obrigacoes_de_curto_prazo"] = dados["disponibilidade_caixa"] / dados["obrigacoes_curto_prazo"] if dados["obrigacoes_curto_prazo"] != 0 else 0
    indicadores["comprometimento_das_receitas_correntes_com_as_obrigacoes_de_curto_prazo"] = dados["obrigacoes_curto_prazo"] / dados["receita_corrente_liquida"] if dados["receita_corrente_liquida"] != 0 else 0
    indicadores["divida_per_capita"] = dados["divida_consolidada"] / populacao
    indicadores["comprometimento_das_receitas_correntes_com_o_endividamento"] = dados["divida_consolidada"] / dados["receita_corrente_liquida"] if dados["receita_corrente_liquida"] != 0 else 0
    
    # Corrigindo os nomes problemáticos para o padrão snake_case:
    indicadores["despesa_com_pessoal"] = dados["despesa_com_pessoal"]  # Padronizado
    indicadores["divida_consolidada"] = dados["divida_consolidada"]  # Padronizado
    indicadores["operacoes_credito"] = dados["operacoes_credito"]  # Padronizado
    
    indicadores["poupanca_corrente"] = dados["receita_total"] - dados["despesa_total"]
    indicadores["liquidez_relativa"] = dados["obrigacoes_curto_prazo"] / dados["disponibilidade_caixa"] if dados["disponibilidade_caixa"] != 0 else 0
    indicadores["indicador_de_liquidez"] = dados["ativo_circulante"] / dados["obrigacoes_curto_prazo"] if dados["obrigacoes_curto_prazo"] != 0 else 0
    indicadores["endividamento"] = (dados["divida_consolidada"] + dados["operacoes_credito"]) / dados["receita_corrente_liquida"] if dados["receita_corrente_liquida"] != 0 else 0

    return indicadores

def exibir_indicadores(indicadores):
    """Exibe os indicadores com formatação e alertas"""
    REGRAS_ALERTAS = {
        "receita_per_capita": {
            "mensagem": lambda v: "🔴 Baixa receita per capita!" if v < 1000 else "🟢 Receita per capita adequada."
        },
        "representatividade_da_receita_propria": {
            "mensagem": lambda v: "🔴 Baixa dependência de receita própria!" if v < 0.2 else "🟢 Boa representatividade da receita própria."
        },
        "participacao_das_receitas_de_transferencias": {
            "mensagem": lambda v: "🟡 Alta dependência de transferências." if v > 0.5 else "🟢 Nível equilibrado de transferências."
        },
        "participacao_dos_gastos_operacionais": {
            "mensagem": lambda v: "🟡 Gastos operacionais elevados." if v > 0.6 else "🟢 Gastos operacionais controlados."
        },
        "cobertura_de_despesas": {
            "mensagem": lambda v: "🔴 Receita insuficiente para cobrir despesas!" if v < 1 else "🟢 Cobertura adequada das despesas."
        },
        "recursos_para_cobertura_de_queda_de_arrecadacao": {
            "mensagem": lambda v: "🔴 Pouca reserva de caixa!" if v < 0.05 else "🟢 Reserva de caixa satisfatória."
        },
        "recursos_para_cobertura_de_obrigacoes_de_curto_prazo": {
            "mensagem": lambda v: "🔴 Risco de não cumprir obrigações imediatas!" if v < 1 else "🟢 Cobertura adequada das obrigações."
        },
        "comprometimento_das_receitas_correntes_com_as_obrigacoes_de_curto_prazo": {
            "mensagem": lambda v: "🔴 Alto comprometimento com curto prazo!" if v > 0.5 else "🟢 Comprometimento controlado."
        },
        "divida_per_capita": {
            "mensagem": lambda v: "🟡 Dívida per capita moderada." if v > 1000 else "🟢 Dívida per capita sob controle."
        },
        "comprometimento_das_receitas_correntes_com_o_endividamento": {
            "mensagem": lambda v: "🔴 Endividamento elevado!" if v > 1 else "🟢 Endividamento aceitável."
        },
        "liquidez_relativa": {
            "mensagem": lambda v: "🔴 Baixa liquidez relativa!" if v > 1 else "🟢 Liquidez adequada."
        },
        "indicador_de_liquidez": {
            "mensagem": lambda v: "🔴 Ativo circulante insuficiente!" if v < 1 else "🟢 Boa liquidez."
        },
        "endividamento": {
            "mensagem": lambda v: "🔴 Alto nível de endividamento!" if v > 1 else "🟢 Endividamento sob controle."
        }
    }
    
    for nome, valor in indicadores.items():
        with st.container():
            cols = st.columns([3, 1, 4])
            cols[0].markdown(f"**{nome.replace('_', ' ').title()}**")
            cols[1].markdown(f"`{valor:.2f}`")
            
            if nome in REGRAS_ALERTAS:
                alerta = REGRAS_ALERTAS[nome]["mensagem"](valor)
                cor = 'red' if '🔴' in alerta else 'orange' if '🟡' in alerta else 'green'
                cols[2].markdown(f"<span style='color:{cor}'>{alerta}</span>", unsafe_allow_html=True)
            st.divider()

def exibir_referencia(df_referencia, indicadores):
    """Exibe comparação com dados históricos"""
    with st.expander("🔍 Comparação com Média 2022"):
        # Seleciona apenas colunas numéricas para cálculo da média
        df_numerico = df_referencia.select_dtypes(include=['number'])
        media_2022 = df_numerico.mean()
        
        for k, v in indicadores.items():
            if k in media_2022:
                ref = media_2022[k]
                if ref != 0:
                    diff = ((v - ref)/ref)*100
                    st.metric(
                        label=k.replace("_", " ").title(),
                        value=f"{v:.2f}",
                        delta=f"{diff:.1f}% vs 2022"
                    )
                else:
                    st.metric(
                        label=k.replace("_", " ").title(),
                        value=f"{v:.2f}",
                        delta="Sem referência (divisão por zero)"
                    )
            else:
                st.metric(
                    label=k.replace("_", " ").title(),
                    value=f"{v:.2f}",
                    delta="Indicador não encontrado nos dados de 2022"
                )
                


if __name__ == "__main__":
    main()
