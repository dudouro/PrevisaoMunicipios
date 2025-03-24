import pandas as pd
def mesoregiao():
    # Dicionário das mesorregiões de Minas Gerais
    mesoregiones_mg = {
        1: "Noroeste de Minas",
        2: "Norte de Minas",
        3: "Jequitinhonha",
        4: "Vale do Mucuri",
        5: "Triângulo Mineiro e Alto Paranaíba",
        6: "Central Mineira",
        7: "Metropolitana de Belo Horizonte",
        8: "Vale do Rio Doce",
        9: "Oeste de Minas",
        10: "Sul e Sudoeste de Minas",
        11: "Campo das Vertentes",
        12: "Zona da Mata"
    }
    
    df = pd.read_excel("Mesorregiao.xlsx")

    # Adicionar uma nova coluna ao DataFrame com o nome da mesorregião
    df["Mesorregião"] = df["v21"].map(mesoregiones_mg)

    return df

# Lista de variáveis disponíveis para o gráfico#
variaveis = [
    "receita_per_capita",
    "representatividade_da_receita_propria",
    "participacao_das_receitas_de_transferencias",
    "participacao_dos_gastos_operacionais",
    "cobertura_de_despesas",
    "recursos_para_cobertura_de_queda_de_arrecadacao",
    "recursos_para_cobertura_de_obrigacoes_de_curto_prazo",
    "comprometimento_das_receitas_correntes_com_as_obrigacoes_de_curto_prazo",
    "divida_per_capita",
    "comprometimento_das_receitas_correntes_com_o_endividamento",
    "Despesa com pessoal",
    "Dívida Consolidada",
    "Operações de crédito",
    "poupanca_corrente",
    "liquidez_relativa",
    "indicador_de_liquidez",
    "endividamento"
]