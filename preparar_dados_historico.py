"""
Passo 2b: prepara os resultados historicos (1960 a 1990) para a Bahia.

Diferente do preparar_dados.py (2016-2026), aqui NAO existe votacao por secao nem
por municipio: o TSE so tem o resultado consolidado do estado inteiro (por isso os
arquivos se chamam "..._UF"). Entao nao tem como mostrar escola, bairro ou mapa
nesses anos - so o ranking de candidatos, com votos e situacao (eleito/nao eleito).

Tambem nao existia "numero de urna" para Presidente/Governador antes de 1982 (a
eleicao era so pelo nome); por isso NR_VOTAVEL fica vazio nesses casos e o candidato
e identificado pelo nome de urna mesmo.

Gera, dentro de "dados/historico":
  1) votos_historico_ba.csv    -> uma linha por candidato, ano, turno e cargo
  2) resumo_estadual_ba.csv    -> comparecimento, abstencao, brancos e nulos, por ano/turno/cargo

Rode DEPOIS do baixar_dados_historico.py:
    python preparar_dados_historico.py
"""

import re
from pathlib import Path

import pandas as pd

PASTA = Path("dados") / "historico"
SAIDA_VOTOS = PASTA / "votos_historico_ba.csv"
SAIDA_RESUMO = PASTA / "resumo_estadual_ba.csv"
UF = "BA"
NOME_MUNICIPIO_UF = "BAHIA (resultado estadual, sem detalhe por municipio)"

# Sentinelas do TSE (ver Leia-me.pdf): "#NULO#"/-1 = informacao em branco;
# "#NE#"/-3 = a informacao nao era registrada pelos sistemas daquela epoca.
SENTINELAS = {"#NULO#", "#NE#", "-1", "-3"}

COLUNAS_CANDIDATO = [
    "DATA_GERACAO", "HORA_GERACAO", "ANO_ELEICAO", "NUM_TURNO", "DESCRICAO_ELEICAO",
    "SIGLA_UF", "SIGLA_UE", "CODIGO_CARGO", "NUMERO_CAND", "SQ_CANDIDATO",
    "NOME_CANDIDATO", "NOME_URNA_CANDIDATO", "DESCRICAO_CARGO",
    "COD_SIT_CAND_SUPERIOR", "DESC_SIT_CAND_SUPERIOR",
    "CODIGO_SIT_CANDIDATO", "DESC_SIT_CANDIDATO",
    "CODIGO_SIT_CAND_TOT", "DESC_SIT_CAND_TOT",
    "NUMERO_PARTIDO", "SIGLA_PARTIDO", "NOME_PARTIDO",
    "SEQUENCIAL_LEGENDA", "NOME_COLIGACAO", "COMPOSICAO_LEGENDA", "TOTAL_VOTOS",
]
COLUNAS_DETALHE = [
    "DATA_GERACAO", "HORA_GERACAO", "ANO_ELEICAO", "NUM_TURNO", "DESCRICAO_ELEICAO",
    "SIGLA_UF", "SIGLA_UE", "CODIGO_CARGO", "DESCRICAO_CARGO",
    "QTD_APTOS", "QTD_COMPARECIMENTO", "QTD_ABSTENCOES",
    "QTD_VOTOS_NOMINAIS", "QTD_VOTOS_BRANCOS", "QTD_VOTOS_NULOS", "QTD_VOTOS_LEGENDA",
    "QTD_VOTOS_ANULADOS_APU_SEP", "QTD_SECOES_TOT", "QTD_SECOES_ANULADAS",
    "QTD_SECOES_SEM_FUNCION", "QTD_ZONAS_ELEITORAIS", "QTD_JUNTAS_APURADORAS",
]


def achar_arquivo(ano, prefixos):
    """Os nomes dos TXT nem sempre batem exatamente com o nome do ZIP (ex.: CONSULTA_LEGENDA, nao LEGENDAS)."""
    for prefixo in prefixos:
        candidatos = sorted(PASTA.glob(f"{prefixo}*{ano}*.txt")) + sorted(PASTA.glob(f"{prefixo}*{ano}*.TXT"))
        if candidatos:
            return candidatos[0]
    return None


def ler_tabela(arquivo, colunas_esperadas):
    """Le um TXT do repositorio historico: sem cabecalho, ';', aspas, latin-1."""
    df = pd.read_csv(
        arquivo, sep=";", encoding="latin-1", header=None, dtype=str,
        keep_default_na=False, quotechar='"',
    )
    if len(df.columns) != len(colunas_esperadas):
        print(f"AVISO: {arquivo.name} tem {len(df.columns)} colunas; eu esperava {len(colunas_esperadas)}.")
        print("Primeira linha do arquivo:", df.iloc[0].tolist())
        raise SystemExit("Copie esta mensagem e cole no Claude para ajustar o script (o layout deste ano é diferente).")
    df.columns = colunas_esperadas
    return df


def limpar(serie):
    """Troca as sentinelas do TSE (#NULO#, #NE#, -1, -3) por vazio."""
    serie = serie.str.strip()
    return serie.where(~serie.isin(SENTINELAS), "")


def processar_ano(ano):
    arquivo_cand = achar_arquivo(ano, ["VOTACAO_CANDIDATO_UF"])
    arquivo_detalhe = achar_arquivo(ano, ["DETALHE_VOTACAO_UF"])
    if arquivo_cand is None:
        print(f"AVISO: resultados de {ano} não encontrados em dados/historico. Pulando {ano}.")
        return None, None

    cand = ler_tabela(arquivo_cand, COLUNAS_CANDIDATO)
    cand = cand[cand["SIGLA_UF"] == UF].copy()
    if cand.empty:
        print(f"AVISO: nenhum registro da Bahia em {arquivo_cand.name}.")
        return None, None

    for coluna in ["NUMERO_CAND", "NOME_CANDIDATO", "NOME_URNA_CANDIDATO", "DESC_SIT_CAND_TOT",
                   "SIGLA_PARTIDO", "NOME_PARTIDO", "NOME_COLIGACAO", "COMPOSICAO_LEGENDA"]:
        cand[coluna] = limpar(cand[coluna])
    cand["TOTAL_VOTOS"] = pd.to_numeric(cand["TOTAL_VOTOS"], errors="coerce").fillna(0).astype(int)
    cand["DESCRICAO_CARGO"] = cand["DESCRICAO_CARGO"].str.strip().str.title()
    cand["NOME_URNA_CANDIDATO"] = cand["NOME_URNA_CANDIDATO"].where(
        cand["NOME_URNA_CANDIDATO"] != "", cand["NOME_CANDIDATO"]
    )

    votos = pd.DataFrame({
        "ANO": ano,
        "NR_TURNO": cand["NUM_TURNO"],
        "NM_MUNICIPIO": NOME_MUNICIPIO_UF,
        "DS_CARGO": cand["DESCRICAO_CARGO"],
        "NR_VOTAVEL": cand["NUMERO_CAND"],
        "NM_VOTAVEL": cand["NOME_URNA_CANDIDATO"],
        "NM_CANDIDATO": cand["NOME_CANDIDATO"],
        "SG_PARTIDO": cand["SIGLA_PARTIDO"],
        "NM_PARTIDO": cand["NOME_PARTIDO"],
        "NOME_COLIGACAO": cand["NOME_COLIGACAO"],
        "COMPOSICAO_LEGENDA": cand["COMPOSICAO_LEGENDA"],
        "DS_SIT_TOT_TURNO": cand["DESC_SIT_CAND_TOT"],
        "QT_VOTOS": cand["TOTAL_VOTOS"],
    })

    resumo = None
    if arquivo_detalhe is not None:
        det = ler_tabela(arquivo_detalhe, COLUNAS_DETALHE)
        det = det[det["SIGLA_UF"] == UF].copy()
        if not det.empty:
            for coluna in ["QTD_APTOS", "QTD_COMPARECIMENTO", "QTD_ABSTENCOES", "QTD_VOTOS_NOMINAIS",
                           "QTD_VOTOS_BRANCOS", "QTD_VOTOS_NULOS", "QTD_VOTOS_LEGENDA",
                           "QTD_SECOES_TOT", "QTD_ZONAS_ELEITORAIS"]:
                det[coluna] = pd.to_numeric(limpar(det[coluna]), errors="coerce").fillna(0).astype(int)
            det["DESCRICAO_CARGO"] = det["DESCRICAO_CARGO"].str.strip().str.title()
            resumo = pd.DataFrame({
                "ANO": ano,
                "NR_TURNO": det["NUM_TURNO"],
                "DS_CARGO": det["DESCRICAO_CARGO"],
                "Eleitores_aptos": det["QTD_APTOS"],
                "Compareceram": det["QTD_COMPARECIMENTO"],
                "Abstencoes": det["QTD_ABSTENCOES"],
                "Votos_nominais": det["QTD_VOTOS_NOMINAIS"],
                "Votos_brancos": det["QTD_VOTOS_BRANCOS"],
                "Votos_nulos": det["QTD_VOTOS_NULOS"],
                "Votos_legenda": det["QTD_VOTOS_LEGENDA"],
                "Secoes_totalizadas": det["QTD_SECOES_TOT"],
                "Zonas_eleitorais": det["QTD_ZONAS_ELEITORAIS"],
            })
    else:
        print(f"AVISO: 'detalhe da apuração' de {ano} não encontrado; sem comparecimento/abstenção neste ano.")

    return votos, resumo


def main():
    if not PASTA.exists():
        raise SystemExit("Pasta dados/historico não encontrada. Rode antes: python baixar_dados_historico.py")

    arquivos_candidato = sorted(PASTA.glob("VOTACAO_CANDIDATO_UF*.txt")) + sorted(PASTA.glob("VOTACAO_CANDIDATO_UF*.TXT"))
    anos = sorted({re.search(r"(\d{4})", a.stem).group(1) for a in arquivos_candidato})
    if not anos:
        raise SystemExit("Nenhum arquivo de resultados encontrado em dados/historico. "
                          "Rode antes: python baixar_dados_historico.py")

    todos_votos, todos_resumos = [], []
    for ano in anos:
        votos, resumo = processar_ano(ano)
        if votos is not None:
            todos_votos.append(votos)
            print(f"  {ano}: {len(votos)} candidatos na Bahia ({', '.join(sorted(votos['DS_CARGO'].unique()))})")
        if resumo is not None:
            todos_resumos.append(resumo)

    if not todos_votos:
        raise SystemExit("Nenhum dado da Bahia encontrado em nenhum ano.")

    tabela_votos = pd.concat(todos_votos, ignore_index=True)
    tabela_votos.to_csv(SAIDA_VOTOS, index=False, encoding="utf-8")
    print(f"\nGravado {SAIDA_VOTOS} ({len(tabela_votos)} linhas).")

    if todos_resumos:
        tabela_resumo = pd.concat(todos_resumos, ignore_index=True)
        tabela_resumo.to_csv(SAIDA_RESUMO, index=False, encoding="utf-8")
        print(f"Gravado {SAIDA_RESUMO} ({len(tabela_resumo)} linhas).")

    print(f"\nPronto! Anos processados: {', '.join(anos)}.")


if __name__ == "__main__":
    main()
