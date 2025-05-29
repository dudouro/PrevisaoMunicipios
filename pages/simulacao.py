from extra import variaveis # Se você tiver este arquivo, mantenha. Caso contrário, remova ou adapte.
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
ARQUIVO_CLASSIFICACAO_POPULACAO = "Mesorregiao_com_populacao.xlsx" ### ADIÇÃO ###

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

### ADIÇÃO ###
def classificar_populacao(pop):
    if pop <= 20000:
        return "Pequeno Porte I"
    elif pop <= 50000:
        return "Pequeno Porte II"
    elif pop <= 100000:
        return "Médio Porte"
    elif pop <= 900000:
        return "Grande Porte"
    else:
        return "Metrópole"

def carregar_dados_2022():
    """Carrega os dados de referência de 2022 e os dados de classificação populacional"""
    try:
        caminho_financeiro = os.path.join(PASTA_DADOS, "janela_fixa", "22", "resultado_final22.xlsx")
        df_financeiro = pd.read_excel(caminho_financeiro)

        # Converter colunas numéricas que podem estar como strings
        for col in df_financeiro.columns:
            if df_financeiro[col].dtype == object:
                try:
                    # Evitar converter colunas que devem ser string, como 'id' ou 'IBGE'
                    if col.lower() != 'id' and col.upper() != 'IBGE' and col.upper() != 'MUNICÍPIOS':
                        df_financeiro[col] = pd.to_numeric(df_financeiro[col].astype(str).str.replace(',', '.', regex=False))
                except ValueError:
                    pass

        caminho_classificacao = ARQUIVO_CLASSIFICACAO_POPULACAO
        if not os.path.exists(caminho_classificacao):
            st.error(f"Arquivo de classificação '{ARQUIVO_CLASSIFICACAO_POPULACAO}' não encontrado. A comparação será feita com a média geral.")
            return df_financeiro

        df_classificacao = pd.read_excel(caminho_classificacao)

        ### ALTERAÇÃO AQUI: Usar 'id' para df_financeiro e 'IBGE' para df_classificacao ###
        coluna_ibge_financeiro = 'id' # Nome da coluna no df_financeiro
        coluna_ibge_classificacao = 'IBGE' # Nome da coluna no df_classificacao

        if coluna_ibge_financeiro not in df_financeiro.columns:
            st.error(f"Coluna '{coluna_ibge_financeiro}' não encontrada no arquivo financeiro. Não é possível mesclar com a classificação.")
            # Adicionar a coluna de classificação vazia para evitar erros posteriores, se df_financeiro for retornado
            df_financeiro['Classificação do Município'] = "Não Classificado"
            return df_financeiro
        if coluna_ibge_classificacao not in df_classificacao.columns:
            st.error(f"Coluna '{coluna_ibge_classificacao}' não encontrada no arquivo de classificação. Não é possível mesclar.")
            # Adicionar a coluna de classificação vazia para evitar erros posteriores, se df_financeiro for retornado
            df_financeiro['Classificação do Município'] = "Não Classificado"
            return df_financeiro

        try:
            # Garantir que ambas as colunas de merge sejam do mesmo tipo (ex: int)
            # Se seus códigos IBGE são numéricos (ex: 3100104)
            df_financeiro[coluna_ibge_financeiro] = df_financeiro[coluna_ibge_financeiro].astype(int)
            df_classificacao[coluna_ibge_classificacao] = df_classificacao[coluna_ibge_classificacao].astype(int)
            
            # Se seus códigos IBGE podem ter zeros à esquerda e são strings (ex: "0100100")
            # df_financeiro[coluna_ibge_financeiro] = df_financeiro[coluna_ibge_financeiro].astype(str)
            # df_classificacao[coluna_ibge_classificacao] = df_classificacao[coluna_ibge_classificacao].astype(str)

        except ValueError as e:
            st.error(f"Erro ao converter colunas de código IBGE ('{coluna_ibge_financeiro}', '{coluna_ibge_classificacao}') para o tipo de merge: {e}. Verifique os dados.")
            df_financeiro['Classificação do Município'] = "Não Classificado"
            return df_financeiro

        df_classificacao_selecionada = df_classificacao[[coluna_ibge_classificacao, 'Classificação do Município']].drop_duplicates(subset=[coluna_ibge_classificacao])

        # Merge usando left_on e right_on
        df_merged = pd.merge(
            df_financeiro,
            df_classificacao_selecionada,
            left_on=coluna_ibge_financeiro,
            right_on=coluna_ibge_classificacao,
            how="left"
        )

        # Se a coluna 'IBGE' do df_classificacao foi adicionada ao df_merged e você não a quer, pode removê-la
        # Isso acontece porque as colunas de junção têm nomes diferentes.
        if coluna_ibge_classificacao in df_merged.columns and coluna_ibge_classificacao != coluna_ibge_financeiro:
            df_merged = df_merged.drop(columns=[coluna_ibge_classificacao])
        
        if 'Classificação do Município' not in df_merged.columns:
            st.warning("A coluna 'Classificação do Município' não foi adicionada após o merge. Verifique os códigos IBGE e os nomes das colunas.")
            # Adiciona a coluna com um valor padrão para evitar quebras em outras partes do código
            df_merged['Classificação do Município'] = "Não Classificado"
        # else:
            # st.success("Dados de classificação populacional carregados e integrados!") # Para debug

        return df_merged

    except Exception as e:
        st.error(f"Erro ao carregar dados históricos: {str(e)}")
        # Tenta retornar um DataFrame com a coluna de classificação padrão em caso de erro grave
        # para que o resto da aplicação não quebre imediatamente.
        # Isso é opcional e depende de como você quer lidar com falhas no carregamento.
        df_fallback = pd.DataFrame()
        df_fallback['Classificação do Município'] = "Erro no Carregamento"
        return df_fallback # Ou return None e tratar o None em main()

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
    mapeamento_nomes = {
        "Despesa com pessoal": "despesa_com_pessoal",
        "Dívida Consolidada": "divida_consolidada",
        "Operações de crédito": "operacoes_credito"
    }
    
    try:
        features_esperadas = modelo.feature_names_in_
        dados_previsao = {}
        for feature in features_esperadas:
            if feature in indicadores:
                dados_previsao[feature] = [indicadores[feature]]
            elif feature in mapeamento_nomes.values():
                for original, padronizado in mapeamento_nomes.items():
                    if padronizado == feature and original in indicadores:
                        dados_previsao[feature] = [indicadores[original]]
                        break
            # else: # Para debug, caso alguma feature esperada não seja encontrada
            #     st.warning(f"Feature esperada pelo modelo não encontrada nos indicadores: {feature}")


        # Verificar se todas as features esperadas foram preenchidas
        if len(dados_previsao) != len(features_esperadas):
            st.error(f"Nem todas as features esperadas pelo modelo foram fornecidas. Esperadas: {len(features_esperadas)}, Fornecidas: {len(dados_previsao)}")
            # st.write("Features esperadas:", features_esperadas) # Debug
            # st.write("Dados para previsão (parcial):", dados_previsao) # Debug
            return None

        df_previsao = pd.DataFrame(dados_previsao, columns=features_esperadas)
        return modelo.predict(df_previsao)
    except Exception as e:
        st.error(f"Erro ao preparar dados para previsão: {str(e)}")
        return None
    
# Interface principal
def main():
    df_referencia = carregar_dados_2022()
    if df_referencia is None:
        st.stop()

    st.title("🏛 Previsão CAPAG+LRF - Análise Financeira Municipal")
    st.markdown("""
    **Versão BETA**  
    Simule diferentes cenários financeiros utilizando nosso modelo preditivo.
    """)

    col1, col2 = st.columns([1, 1]) # Mantive a proporção original, ajuste se necessário

    with col1:
        with st.container(border=True):
            st.markdown("### 💰 Informe os valores contábeis")
            grupos = {
                "📈 Receitas": [
                    "receita_total", "receita_propria",
                    "receita_transferencias", "populacao",
                    "receita_corrente_liquida"
                ],
                "📉 Despesas": [
                    "despesa_total", "despesa_com_pessoal",
                    "gastos_operacionais"
                ],
                "💼 Ativos": [
                    "disponibilidade_caixa", "ativo_circulante"
                ],
                "📋 Passivos": [
                    "obrigacoes_curto_prazo", "divida_consolidada",
                    "operacoes_credito"
                ]
            }

            dados = {}
            for grupo, variaveis_grupo in grupos.items(): # Renomeei 'variaveis' para 'variaveis_grupo' para evitar conflito
                with st.expander(grupo):
                    for var in variaveis_grupo:
                        label = var.replace("_", " ").title()
                        help_text = DESCRICOES_VARIAVEIS.get(var, "Informe o valor desta conta contábil")
                        dados[var] = st.number_input(
                            label=label,
                            min_value=0.0,
                            value=0.0, # Você pode querer valores default diferentes ou carregar de algum lugar
                            step=1000.0,
                            format="%.2f",
                            help=help_text,
                            key=f"input_{var}"
                        )
        
        ### ADIÇÃO: Classificar população informada ###
        porte_municipio_simulado = "Não classificado" # Default
        if dados.get("populacao", 0) > 0 : # Só classifica se a população for maior que zero
            porte_municipio_simulado = classificar_populacao(dados["populacao"])
            st.info(f"**Porte do Município Simulado:** {porte_municipio_simulado}")
        else:
            st.warning("Informe a população para classificar o porte do município e refinar a comparação.")


        try:
            indicadores = calcular_indicadores(dados)
            # Passar os dados brutos para que 'exibir_referencia' possa usar a população para classificação
            ### ALTERAÇÃO: Passar porte_municipio_simulado ###
            exibir_referencia(df_referencia, indicadores, porte_municipio_simulado)
        except Exception as e:
            st.error(f"Erro no cálculo de indicadores ou exibição de referência: {str(e)}")
            st.stop()
        
        if st.button("🎯 Executar Previsão", use_container_width=True):
            # Validar se a população foi informada, pois é uma feature importante
            if dados.get("populacao", 0) <= 0:
                st.error("Por favor, informe a população do município para realizar a previsão.")
            else:
                modelo = carregar_modelo()
                if modelo:
                    try:
                        # Precisamos garantir que 'indicadores' contenha todas as features que o modelo espera.
                        # A função fazer_previsao já lida com a ordem, mas os inputs devem estar lá.
                        # Adicionar os dados brutos que também são features diretas do modelo ao dict indicadores
                        # antes de passar para fazer_previsao.
                        # Assumindo que seu modelo usa os indicadores calculados E alguns dados brutos como 'populacao'.
                        # A função fazer_previsao já pega os valores de 'indicadores'
                        
                        # Vamos garantir que as features brutas que o modelo pode usar diretamente
                        # (e que não são indicadores calculados com nomes diferentes)
                        # estejam no dicionário 'indicadores' com os nomes esperados.
                        # A função `fazer_previsao` já tem um mapeamento para alguns casos.
                        # Para features como 'populacao', se o modelo usar 'populacao'
                        # ela já está em `dados` e deve ser adicionada a `indicadores` se não estiver.
                        
                        # Melhor abordagem: garantir que 'indicadores' tenha tudo que 'fazer_previsao' precisa.
                        # A função `calcular_indicadores` já adiciona alguns "dados brutos"
                        # como `despesa_com_pessoal` se forem features.
                        # Adicione 'populacao' explicitamente se o modelo a usar.
                        # Supondo que o modelo usa 'populacao' como feature:
                        indicadores_para_modelo = indicadores.copy() # Evitar modificar o dict original usado em outros lugares
                        if 'populacao' not in indicadores_para_modelo and 'populacao' in dados:
                             indicadores_para_modelo['populacao'] = dados['populacao']
                        # Adicione outras features brutas que seu modelo possa esperar e não estão nos indicadores calculados
                        # Exemplo:
                        # if 'receita_corrente_liquida' not in indicadores_para_modelo and 'receita_corrente_liquida' in dados:
                        #     indicadores_para_modelo['receita_corrente_liquida'] = dados['receita_corrente_liquida']


                        previsao = fazer_previsao(modelo, indicadores_para_modelo)
                        if previsao is not None:
                            # Interpretar a previsão (ex: CAPAG A, B, C, D ou LRF OK/Alerta/Violado)
                            # Isso depende de como seu modelo foi treinado para retornar as classes
                            st.success(f"**Resultado da Previsão:** {previsao[0]}")
                        else:
                            st.warning("Previsão não pôde ser realizada. Verifique as mensagens de erro acima.")
                    except Exception as e:
                        st.error(f"Erro na previsão: {str(e)}")

    with col2:
        if 'indicadores' in locals() and indicadores: # Verifica se indicadores existe e não é vazio
            exibir_indicadores(indicadores)
        else:
            st.warning("Preencha os dados na coluna esquerda para ver os indicadores e realizar a simulação.")


def calcular_indicadores(dados):
    indicadores = {}
    populacao = dados.get("populacao", 0)
    populacao_div = populacao if populacao > 0 else 1 # Evitar divisão por zero, mas manter 0 para cálculo se pop for 0

    receita_total = dados.get("receita_total", 0)
    receita_propria = dados.get("receita_propria", 0)
    receita_transferencias = dados.get("receita_transferencias", 0)
    receita_corrente_liquida = dados.get("receita_corrente_liquida", 0)
    despesa_total = dados.get("despesa_total", 0)
    despesa_com_pessoal_input = dados.get("despesa_com_pessoal", 0) # Nome do input
    gastos_operacionais = dados.get("gastos_operacionais", 0)
    disponibilidade_caixa = dados.get("disponibilidade_caixa", 0)
    ativo_circulante = dados.get("ativo_circulante", 0)
    obrigacoes_curto_prazo = dados.get("obrigacoes_curto_prazo", 0)
    divida_consolidada_input = dados.get("divida_consolidada", 0) # Nome do input
    operacoes_credito_input = dados.get("operacoes_credito", 0) # Nome do input

    # Cálculos principais - padronizando os nomes
    indicadores["receita_per_capita"] = receita_total / populacao_div
    indicadores["representatividade_da_receita_propria"] = receita_propria / receita_total if receita_total != 0 else 0
    indicadores["participacao_das_receitas_de_transferencias"] = receita_transferencias / receita_total if receita_total != 0 else 0
    indicadores["participacao_dos_gastos_operacionais"] = gastos_operacionais / despesa_total if despesa_total != 0 else 0
    indicadores["cobertura_de_despesas"] = receita_total / despesa_total if despesa_total != 0 else 0
    indicadores["recursos_para_cobertura_de_queda_de_arrecadacao"] = disponibilidade_caixa / receita_total if receita_total != 0 else 0
    indicadores["recursos_para_cobertura_de_obrigacoes_de_curto_prazo"] = disponibilidade_caixa / obrigacoes_curto_prazo if obrigacoes_curto_prazo != 0 else 0
    indicadores["comprometimento_das_receitas_correntes_com_as_obrigacoes_de_curto_prazo"] = obrigacoes_curto_prazo / receita_corrente_liquida if receita_corrente_liquida != 0 else 0
    indicadores["divida_per_capita"] = divida_consolidada_input / populacao_div
    indicadores["comprometimento_das_receitas_correntes_com_o_endividamento"] = divida_consolidada_input / receita_corrente_liquida if receita_corrente_liquida != 0 else 0
    
    # Features diretas para o modelo (nomes padronizados snake_case)
    indicadores["Despesa com pessoal"] = despesa_com_pessoal_input
    indicadores["Dívida Consolidada"] = divida_consolidada_input
    indicadores["Operações de crédito"] = operacoes_credito_input

    
    indicadores["poupanca_corrente"] = receita_total - despesa_total
    indicadores["liquidez_relativa"] = obrigacoes_curto_prazo / disponibilidade_caixa if disponibilidade_caixa != 0 else 0
    indicadores["indicador_de_liquidez"] = ativo_circulante / obrigacoes_curto_prazo if obrigacoes_curto_prazo != 0 else 0 # Atenção aqui: invertido em relação à descrição "Passivo / Ativo Circulante"? Normalmente é Ativo Circ/Passivo Circ. Verifique sua fórmula.
    indicadores["endividamento"] = (divida_consolidada_input + operacoes_credito_input) / receita_corrente_liquida if receita_corrente_liquida != 0 else 0

    return indicadores

def exibir_indicadores(indicadores):
    st.markdown("### 📊 Indicadores Financeiros Calculados")
    REGRAS_ALERTAS = {
        # ... (suas regras de alerta existentes, sem alterações aqui) ...
        "receita_per_capita": {
            "mensagem": lambda v: "🔴 Baixa receita per capita!" if v < 1000 else "🟢 Receita per capita adequada.",
            "formula": "Receita Total / População"
        },
        "representatividade_da_receita_propria": {
            "mensagem": lambda v: "🔴 Baixa dependência de receita própria!" if v < 0.2 else "🟢 Boa representatividade da receita própria.",
            "formula": "Receita Própria / Receita Total"
        },
        "participacao_das_receitas_de_transferencias": {
            "mensagem": lambda v: "🟡 Alta dependência de transferências." if v > 0.5 else "🟢 Nível equilibrado de transferências.",
            "formula": "Receitas de Transferências / Receita Total"
        },
        "participacao_dos_gastos_operacionais": {
            "mensagem": lambda v: "🟡 Gastos operacionais elevados." if v > 0.6 else "🟢 Gastos operacionais controlados.",
            "formula": "Gastos Operacionais / Despesa Total"
        },
        "cobertura_de_despesas": {
            "mensagem": lambda v: "🔴 Receita insuficiente para cobrir despesas!" if v < 1 else "🟢 Cobertura adequada das despesas.",
            "formula": "Receita Total / Despesa Total"
        },
        "recursos_para_cobertura_de_queda_de_arrecadacao": {
            "mensagem": lambda v: "🔴 Pouca reserva de caixa!" if v < 0.05 else "🟢 Reserva de caixa satisfatória.",
            "formula": "Disponibilidade de Caixa / Receita Total"
        },
        "recursos_para_cobertura_de_obrigacoes_de_curto_prazo": {
            "mensagem": lambda v: "🔴 Risco de não cumprir obrigações imediatas!" if v < 1 else "🟢 Cobertura adequada das obrigações.",
            "formula": "Disponibilidade de Caixa / Obrigações de Curto Prazo"
        },
        "comprometimento_das_receitas_correntes_com_as_obrigacoes_de_curto_prazo": {
            "mensagem": lambda v: "🔴 Alto comprometimento com curto prazo!" if v > 0.5 else "🟢 Comprometimento controlado.",
            "formula": "Obrigações de Curto Prazo / Receita Corrente Líquida"
        },
        "divida_per_capita": {
            "mensagem": lambda v: "🟡 Dívida per capita moderada." if v > 1000 else "🟢 Dívida per capita sob controle.",
            "formula": "Dívida Consolidada / População"
        },
        "comprometimento_das_receitas_correntes_com_o_endividamento": {
            "mensagem": lambda v: "🔴 Endividamento elevado!" if v > 1 else "🟢 Endividamento aceitável.",
            "formula": "Dívida Consolidada / Receita Corrente Líquida"
        },
        "despesa_com_pessoal": { # Este é o valor absoluto, a regra de LRF usa RCL
            "mensagem": lambda v: "🟡 Avaliar em relação à RCL.", # Mensagem genérica, pois depende da RCL
            "formula": "Valor absoluto da Despesa com Pessoal",
            "fiscal": lambda v, rcl_indicador: [ # Usa rcl_indicador que é passado
                ("🚨 Violação LRF: >60% RCL", "red") if rcl_indicador > 0 and v/rcl_indicador >= 0.6 else None,
                ("⚠️ Alerta LRF: ≥54% e <60% RCL", "orange") if rcl_indicador > 0 and 0.54 <= v/rcl_indicador < 0.6 else None,
                ("🟢 Prudencial LRF: ≥51.3% e <54% RCL", "yellow") if rcl_indicador > 0 and 0.513 <= v/rcl_indicador < 0.54 else None,
                ("🔵 Abaixo do Limite Prudencial LRF", "green") if rcl_indicador > 0 and v/rcl_indicador < 0.513 else None,
                 ("RCL não informada ou zero para cálculo LRF", "gray") if rcl_indicador == 0 else None
            ]
        },
        "divida_consolidada": { # Valor absoluto
            "mensagem": lambda v: "🟡 Avaliar em relação à RCL.",
            "formula": "Valor absoluto da Dívida Consolidada",
            "fiscal": lambda v, rcl_indicador: [
                ("🚨 Violação LRF (Dívida): >1.2x RCL", "red") if rcl_indicador > 0 and v/rcl_indicador > 1.2 else None,
                ("🔵 Dívida dentro do limite LRF", "green") if rcl_indicador > 0 and v/rcl_indicador <= 1.2 else None,
                ("RCL não informada ou zero para cálculo LRF", "gray") if rcl_indicador == 0 else None
            ]
        },
        "operacoes_credito": {
            "mensagem": lambda v: "🟡 Avaliar em relação à RCL.",
            "formula": "Valor absoluto das operações de crédito",
            # Adicionar regras fiscais se aplicável, ex: limite de 16% da RCL para novas operações no ano
        },
        "liquidez_relativa": {
            "mensagem": lambda v: "🔴 Baixa liquidez relativa (Obrigações > Caixa)!" if v > 1 else "🟢 Liquidez adequada.",
            "formula": "Obrigações de Curto Prazo / Disponibilidade de Caixa"
        },
        "indicador_de_liquidez": { # Normalmente Ativo Circulante / Passivo Circulante
            "mensagem": lambda v: "🟢 Boa liquidez geral." if v > 1 else "🔴 Baixa liquidez geral (Ativo Circ. < Obrigações C.P.)!",
            "formula": "Ativo Circulante / Obrigações de Curto Prazo", # Verifique se é essa a sua intenção
            "fiscal": lambda v, _: [ # O '_' indica que rcl não é usado aqui
                ("⚠️ CAPAG: Liquidez > 1 (Idealmente)", "orange") if v <= 1 else None # Ajuste a lógica CAPAG conforme necessário
            ]
        },
        "endividamento": { # (DC + OC) / RCL
            "mensagem": lambda v: "🔴 Muito elevado" if v > 1.0 else "⚠️ Elevado" if v > 0.8 else "🟢 Controlado", # Ajuste os limites conforme STN/LRF
            "formula": "(Dívida Consolidada + Operações de Crédito) / RCL",
            "fiscal": lambda v, rcl_indicador: [ # rcl_indicador é passado
                 ("🚨 CAPAG Endividamento D (>100% RCL para Municípios)", "red") if v > 1.0 else None, # Exemplo, verifique os limites corretos
                 ("⚠️ CAPAG Endividamento C (entre X% e Y% RCL)", "orange") if 0.8 < v <= 1.0 else None, # Exemplo
                 ("🟢 CAPAG Endividamento A ou B", "green") if v <= 0.8 else None # Exemplo
            ]
        },
        "poupanca_corrente": {
            "mensagem": lambda v: "🔴 Déficit Corrente" if v < 0 else "🟢 Superávit Corrente",
            "formula": "Receita Total - Despesa Total", # Ou Receitas Correntes - Despesas Correntes
            "fiscal": lambda v, _: [
                ("⚠️ CAPAG Poupança Corrente: Negativa", "orange") if v < 0 else None
            ]
        }
    }
    
    rcl_atual = indicadores.get("receita_corrente_liquida", 0) # Pega a RCL atual para os alertas fiscais

    for nome, valor in indicadores.items():
        # Não exibir indicadores que são apenas inputs diretos para o modelo e não métricas de análise
        # a menos que tenham regras de alerta específicas.
        # Ex: 'populacao' pode não precisar ser exibida aqui se não tiver regra.
        # if nome in ['populacao', 'receita_corrente_liquida'] and nome not in REGRAS_ALERTAS:
        #    continue

        with st.container(): # Use border=True se quiser bordas
            cols = st.columns([3, 2, 4]) # Ajuste de tamanho para melhor visualização
            cols[0].markdown(f"**{nome.replace('_', ' ').title()}**")
            
            # Formatar como percentual se for o caso, ou monetário
            if "representatividade" in nome or "participacao" in nome or "comprometimento" in nome or "endividamento" == nome:
                cols[1].markdown(f"`{valor:.2%}`")
            elif isinstance(valor, (int, float)):
                 cols[1].markdown(f"`{formatar_numero(valor, prefixo='R$' if 'receita' in nome or 'despesa' in nome or 'divida' in nome or 'caixa' in nome else '')}`")
            else:
                cols[1].markdown(f"`{valor}`") # Caso não seja numérico
            
            if nome in REGRAS_ALERTAS:
                regras = REGRAS_ALERTAS[nome]
                
                # Passar rcl_atual para a função mensagem se ela aceitar dois argumentos
                try:
                    alerta = regras["mensagem"](valor, rcl_atual)
                except TypeError: # Se a função mensagem só aceita um argumento
                    alerta = regras["mensagem"](valor)
                
                formula = regras["formula"]
                
                cor = 'red' if '🔴' in alerta else 'orange' if '🟡' in alerta else 'yellow' if '⚠️' in alerta else 'green' if '🟢' in alerta else 'blue' if '🔵' in alerta else 'gray'
                cols[2].markdown(f"<span style='color:{cor}'>{alerta}</span>", unsafe_allow_html=True)
                
                st.markdown(f"<div style='font-size:small; color:gray; margin-left: 10px;'><i>Fórmula: {formula}</i></div>", 
                           unsafe_allow_html=True)
                
                if "fiscal" in regras:
                    # rcl_para_fiscal = indicadores.get("receita_corrente_liquida", 0) # Pega a RCL para os alertas fiscais
                    # if rcl_para_fiscal == 0 and ("RCL" in formula or "RCL" in str(regras["fiscal"])):
                    #     st.markdown("<div style='font-size:small; color:red; margin-left:10px;'>⚠️ RCL não informada ou zero, cálculos fiscais podem estar incorretos.</div>", 
                    #                unsafe_allow_html=True)
                    
                    # Passa rcl_atual para a função fiscal
                    fiscal_messages = regras["fiscal"](valor, rcl_atual)
                    if fiscal_messages: # Garante que não é None
                        for msg_tuple in fiscal_messages: # fiscal_messages é uma lista de tuplas
                            if msg_tuple: # Se a regra não retornou None
                                msg_text, msg_color = msg_tuple
                                st.markdown(f"<div style='font-size:small; color:{msg_color}; margin-left:10px;'><b>{msg_text}</b></div>", 
                                           unsafe_allow_html=True)
            st.divider()
def formatar_numero(valor, prefixo='R$'):
    if pd.isna(valor) or valor == 0: # Modificado para retornar '-' para zero também, como no seu exemplo
        return "-"
    # Garantir que 'valor' seja numérico para formatação.
    # Se for string, tentar converter, mas idealmente já deve ser numérico.
    try:
        val_num = float(valor)
    except (ValueError, TypeError):
        return str(valor) # Retorna como string se não puder ser convertido

    return f"{prefixo} {val_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def exibir_referencia(df_referencia_original, indicadores, porte_simulado):
    ano_referencia = 2022 # Conforme seu código original

    # Função auxiliar interna para renderizar um expander de comparação
    def _renderizar_expander_comparativo(df_para_comparar, titulo_do_expander, tipo_comparacao_msg):
        with st.expander(titulo_do_expander):
            if df_para_comparar.empty:
                st.write(f"Não há dados de referência para a comparação {tipo_comparacao_msg}.")
                return

            # Considerar apenas colunas que são chaves nos indicadores
            # e existem no df_para_comparar para cálculo da média.
            colunas_para_media = [
                col for col in indicadores.keys()
                if col in df_para_comparar.columns
            ]
            
            df_numerico_ref = df_para_comparar[colunas_para_media].select_dtypes(include=np.number)

            if df_numerico_ref.empty:
                st.write(f"Não há dados numéricos nos municípios de referência para calcular a média {tipo_comparacao_msg}.")
                # Ainda assim, exibimos os valores simulados sem delta
                media_referencia_calculada = pd.Series(dtype=float)
            else:
                media_referencia_calculada = df_numerico_ref.mean()
                if media_referencia_calculada.empty and not df_numerico_ref.empty:
                    st.warning(f"Cálculo da média de referência {tipo_comparacao_msg} resultou em valores vazios, embora dados numéricos existam.")
                    media_referencia_calculada = pd.Series(dtype=float)

            num_indicadores = len(indicadores)
            cols_per_row = 3
            indicadores_keys = list(indicadores.keys())

            for i in range(0, num_indicadores, cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < num_indicadores:
                        key_idx = i + j
                        k = indicadores_keys[key_idx] # Nome do indicador (ex: "receita_per_capita")
                        v_simulado = indicadores[k]  # Valor simulado para este indicador

                        # Formatar valor principal
                        valor_formatado = f"{v_simulado:.2f}"
                        # Ajuste para nomes de indicadores com espaços, como "Despesa com pessoal"
                        # A lógica de formatação original pode não capturar esses se não tiverem "receita", "despesa", etc.
                        is_currency_like = any(term in k.lower() for term in ['receita', 'despesa', 'divida', 'caixa'])
                        if k in ["Despesa com pessoal", "Dívida Consolidada", "Operações de crédito"]: # Adicionar outros se necessário
                            is_currency_like = True
                        
                        if any(term in k for term in ["representatividade", "participacao", "comprometimento"]) or "endividamento" == k:
                            valor_formatado = f"{v_simulado:.2%}"
                        elif isinstance(v_simulado, (int, float)) and not ("per_capita" in k or "liquidez" in k):
                             valor_formatado = formatar_numero(v_simulado, prefixo='R$' if is_currency_like else '')
                        elif isinstance(v_simulado, (int, float)) and ("per_capita" in k or "liquidez" in k): # Para per capitas e liquidez sem R$
                             valor_formatado = formatar_numero(v_simulado, prefixo='')


                        delta_texto = "N/A"
                        delta_color = "normal"

                        # k deve corresponder ao nome da coluna no df_referencia
                        if k in media_referencia_calculada and not pd.isna(media_referencia_calculada[k]):
                            ref_val = media_referencia_calculada[k]
                            if ref_val != 0:
                                diff = ((v_simulado - ref_val) / abs(ref_val)) * 100
                                delta_texto = f"{diff:.1f}% vs Média {tipo_comparacao_msg}"
                                if diff > 5: delta_color = "normal"
                                elif diff < -5: delta_color = "inverse"
                                else: delta_color = "off"
                            else:
                                delta_texto = f"Média {tipo_comparacao_msg} é 0"
                                delta_color = "off"
                        elif k in media_referencia_calculada and pd.isna(media_referencia_calculada[k]):
                            delta_texto = f"Média {tipo_comparacao_msg} N/A"
                            delta_color = "off"
                        else:
                            # Este caso ocorre se o indicador 'k' não está entre as colunas numéricas
                            # do df_para_comparar ou não estava em 'colunas_para_media'.
                            delta_texto = f"Não na Média {tipo_comparacao_msg}"
                            delta_color = "off"
                        
                        # Usar o nome original do indicador (k) para o label, formatando-o
                        label_metrica = k.replace("_", " ").title()

                        cols[j].metric(
                            label=label_metrica,
                            value=valor_formatado,
                            delta=delta_texto,
                            delta_color=delta_color
                        )
    # --- Fim da função auxiliar interna ---

    if df_referencia_original is None or df_referencia_original.empty:
        st.info(f"Não há dados de referência de {ano_referencia} carregados para realizar comparações.")
        return

    # 1. Comparação com municípios de mesmo porte
    mostrar_comparacao_porte = False
    if 'Classificação do Município' in df_referencia_original.columns:
        if porte_simulado != "Não classificado" and porte_simulado and str(porte_simulado).strip():
            # Usar .loc para evitar SettingWithCopyWarning e garantir que é uma cópia
            df_filtrado_por_porte = df_referencia_original.loc[
                df_referencia_original["Classificação do Município"] == porte_simulado
            ].copy()

            if not df_filtrado_por_porte.empty:
                num_munic_porte = len(df_filtrado_por_porte)
                titulo_porte = f"📊 Comparação com Média {ano_referencia} (Porte: {porte_simulado} - {num_munic_porte} munic.)"
                _renderizar_expander_comparativo(df_filtrado_por_porte, titulo_porte, f"Porte {porte_simulado}")
                mostrar_comparacao_porte = True
            else:
                st.info(f"Não foram encontrados municípios de porte '{porte_simulado}' nos dados de referência de {ano_referencia} para comparação específica por porte. A comparação geral será mostrada abaixo.")
        elif porte_simulado == "Não classificado" or not porte_simulado or not str(porte_simulado).strip():
            st.info(f"População não informada ou porte não classificado para simulação. A comparação específica por porte não será exibida. A comparação geral será mostrada abaixo.")
    
    elif porte_simulado != "Não classificado" and porte_simulado and str(porte_simulado).strip():
        # Este caso é quando a coluna 'Classificação do Município' não existe, mas um porte foi simulado.
        st.warning(f"Coluna 'Classificação do Município' não encontrada nos dados de referência de {ano_referencia}. Não é possível comparar por porte. A comparação geral será mostrada abaixo.")

    # 2. Comparação com TODOS os municípios (Média Geral)
    num_munic_total = len(df_referencia_original)
    titulo_geral = f"🌍 Comparação com Média {ano_referencia} (Todas as Cidades - {num_munic_total} munic.)"
    _renderizar_expander_comparativo(df_referencia_original, titulo_geral, "Geral")
    
### ALTERAÇÃO: Adicionar porte_simulado como parâmetro ###
def exibir_referencia2(df_referencia, indicadores, porte_simulado):
    # Título do expander dinâmico
    titulo_expander = "🔍 Comparação com Média 2022"
    df_comparacao = df_referencia # Por padrão, usa todos os dados

    if 'Classificação do Município' in df_referencia.columns and porte_simulado != "Não classificado":
        # Filtrar o DataFrame de referência para o porte do município simulado
        df_filtrado_por_porte = df_referencia[df_referencia["Classificação do Município"] == porte_simulado]
        
        if not df_filtrado_por_porte.empty:
            titulo_expander = f"🔍 Comparação com Média 2022 (Porte: {porte_simulado})"
            df_comparacao = df_filtrado_por_porte
            # st.caption(f"Comparando com {len(df_filtrado_por_porte)} municípios de porte '{porte_simulado}' de 2022.") # Para debug
        else:
            st.warning(f"Não foram encontrados municípios de porte '{porte_simulado}' nos dados de referência de 2022. Comparando com a média geral.")
            # st.caption(f"Comparando com todos os {len(df_referencia)} municípios de 2022.") # Para debug
    elif 'Classificação do Município' not in df_referencia.columns:
         st.warning("Coluna 'Classificação do Município' não encontrada nos dados de referência. Comparando com a média geral.")
    else: # Caso porte_simulado seja "Não classificado" (população não informada)
        st.info("População não informada para simulação. Comparando com a média geral de 2022.")


    with st.expander(titulo_expander):
        if df_comparacao.empty:
            st.write("Não há dados de referência para comparação.")
            return

        df_numerico = df_comparacao.select_dtypes(include=np.number)
        if df_numerico.empty:
            st.write("Não há dados numéricos para calcular a média de referência.")
            return
            
        media_referencia = df_numerico.mean()
        
        # Criar colunas para melhor layout das métricas
        num_indicadores = len(indicadores)
        cols_per_row = 3 # Quantas métricas por linha
        
        # Lista de chaves dos indicadores para iterar
        indicadores_keys = list(indicadores.keys())

        for i in range(0, num_indicadores, cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < num_indicadores:
                    key_idx = i + j
                    k = indicadores_keys[key_idx]
                    v = indicadores[k]
                    
                    # Formatar valor principal
                    valor_formatado = f"{v:.2f}"
                    if "representatividade" in k or "participacao" in k or "comprometimento" in k or "endividamento" == k :
                        valor_formatado = f"{v:.2%}"
                    elif isinstance(v, (int, float)) and not ("per_capita" in k or "liquidez" in k): # Não formatar como R$ per capita ou índices puros
                         valor_formatado = formatar_numero(v, prefixo='R$' if 'receita' in k or 'despesa' in k or 'divida' in k or 'caixa' in k else '')


                    delta_texto = "N/A"
                    delta_color = "normal" # ou "inverse" ou "off"

                    if k in media_referencia:
                        ref = media_referencia[k]
                        if not pd.isna(ref) and ref != 0:
                            diff = ((v - ref) / abs(ref)) * 100 # Usar abs(ref) para evitar problemas com ref negativo
                            delta_texto = f"{diff:.1f}% vs Média"
                            # Definir cor do delta (opcional, mas melhora a visualização)
                            # Se maior é melhor para o indicador k, então diff > 0 é verde.
                            # Ex: para 'receita_per_capita', maior é melhor. Para 'endividamento', menor é melhor.
                            # Esta lógica pode ser complexa e específica para cada indicador.
                            # Simplificando:
                            if diff > 5: delta_color = "normal" # Verde se positivo e bom
                            elif diff < -5: delta_color = "inverse" # Vermelho se negativo e ruim
                            else: delta_color = "off" # Cinza se próximo
                        elif pd.isna(ref):
                            delta_texto = "Média 2022 N/A"
                            delta_color = "off"
                        else: # ref é 0
                            delta_texto = "Média 2022 é 0"
                            delta_color = "off"
                    else:
                        delta_texto = "Não na Média 2022"
                        delta_color = "off"
                    
                    cols[j].metric(
                        label=k.replace("_", " ").title(),
                        value=valor_formatado,
                        delta=delta_texto,
                        delta_color=delta_color
                    )
                else:
                    # Preencher colunas vazias se o número de indicadores não for múltiplo de cols_per_row
                    pass
                    # cols[j].empty() # Ou não fazer nada

if __name__ == "__main__":
    # Para testar localmente, você pode precisar simular o 'extra.variaveis'
    # Se 'extra.variaveis' não existir ou não for necessário, comente a importação.
    try:
        from extra import variaveis
    except ImportError:
        # st.warning("Módulo 'extra.variaveis' não encontrado. Algumas funcionalidades podem ser limitadas.")
        variaveis = None # Define como None para o código não quebrar se ele for referenciado.
    main()
