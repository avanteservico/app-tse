"""
Passo 2c: prepara os resultados de 1994 a 2014 para a Bahia (ver baixar_dados_intermediario.py).

Esse período já tem votação por MUNICÍPIO E ZONA (mais detalhado que o histórico de 1960-1990,
que só tinha o estado inteiro), mas ainda não tem seção, escola, bairro nem coordenadas. O arquivo
já vem com o nome de urna, partido e situação do candidato prontos (não precisa cruzar com cadastro
separado, como no período 2016-2026).

Gera, dentro de "dados/intermediario":
  votos_intermediario_ba.csv -> uma linha por candidato, ano, turno, município e cargo

Rode DEPOIS do baixar_dados_intermediario.py:
    python preparar_dados_intermediario.py
"""

import codecs
import re
from pathlib import Path

import pandas as pd

PASTA = Path("dados") / "intermediario"
SAIDA = PASTA / "votos_intermediario_ba.csv"

COLUNAS_LEITURA = [
    "NR_TURNO", "NM_MUNICIPIO", "DS_CARGO", "NR_CANDIDATO", "NM_CANDIDATO", "NM_URNA_CANDIDATO",
    "SG_PARTIDO", "NM_PARTIDO", "NM_COLIGACAO", "DS_COMPOSICAO_COLIGACAO",
    "DS_SIT_TOT_TURNO", "QT_VOTOS_NOMINAIS",
]


def detectar_encoding(caminho):
    """Mesma lógica do preparar_dados.py: tenta UTF-8, cai para latin-1 se não decodificar."""
    decodificador = codecs.getincrementaldecoder("utf-8")()
    with open(caminho, "rb") as f:
        while True:
            pedaco = f.read(8_000_000)
            if not pedaco:
                break
            try:
                decodificador.decode(pedaco, final=False)
            except UnicodeDecodeError:
                return "latin-1"
    return "utf-8-sig"


def processar_ano(arquivo, ano):
    encoding = detectar_encoding(arquivo)
    cabecalho = pd.read_csv(arquivo, sep=";", encoding=encoding, nrows=0).columns.tolist()
    faltando = [c for c in COLUNAS_LEITURA if c not in cabecalho]
    if faltando:
        print(f"AVISO: {arquivo.name} não tem as colunas {faltando}.")
        print("Colunas do arquivo:", cabecalho)
        raise SystemExit("Copie esta mensagem e cole no Claude para ajustar o script (layout diferente nesse ano).")

    extra = ["QT_VOTOS_NOMINAIS_VALIDOS"] if "QT_VOTOS_NOMINAIS_VALIDOS" in cabecalho else []
    df = pd.read_csv(
        arquivo, sep=";", encoding=encoding, usecols=COLUNAS_LEITURA + extra, dtype=str, keep_default_na=False,
    )
    df["QT_VOTOS_NOMINAIS"] = pd.to_numeric(df["QT_VOTOS_NOMINAIS"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    # em 1998 e 2000 o TSE deixou QT_VOTOS_NOMINAIS todo zerado e pôs os votos só em QT_VOTOS_NOMINAIS_VALIDOS
    if extra and df["QT_VOTOS_NOMINAIS"].sum() == 0:
        print(f"  {arquivo.name}: QT_VOTOS_NOMINAIS vem zerado; usando QT_VOTOS_NOMINAIS_VALIDOS.")
        df["QT_VOTOS_NOMINAIS"] = pd.to_numeric(df["QT_VOTOS_NOMINAIS_VALIDOS"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    df["DS_CARGO"] = df["DS_CARGO"].str.strip().str.title()
    nome_urna = df["NM_URNA_CANDIDATO"].str.strip()
    nome_urna = nome_urna.where(nome_urna != "", df["NM_CANDIDATO"].str.strip())

    tabela = pd.DataFrame({
        "ANO": ano,
        "NR_TURNO": df["NR_TURNO"],
        "NM_MUNICIPIO": df["NM_MUNICIPIO"].str.strip(),
        "DS_CARGO": df["DS_CARGO"],
        "NR_VOTAVEL": df["NR_CANDIDATO"].str.strip(),
        "NM_VOTAVEL": nome_urna,
        "NM_CANDIDATO": df["NM_CANDIDATO"].str.strip(),
        "SG_PARTIDO": df["SG_PARTIDO"].str.strip(),
        "NM_PARTIDO": df["NM_PARTIDO"].str.strip(),
        "NOME_COLIGACAO": df["NM_COLIGACAO"].str.strip(),
        "COMPOSICAO_LEGENDA": df["DS_COMPOSICAO_COLIGACAO"].str.strip(),
        "DS_SIT_TOT_TURNO": df["DS_SIT_TOT_TURNO"].str.strip(),
        "QT_VOTOS": df["QT_VOTOS_NOMINAIS"],
    })
    # o arquivo original tem uma linha por zona eleitoral; soma por município (igual ao preparar_dados.py)
    chaves = [c for c in tabela.columns if c != "QT_VOTOS"]
    tabela = tabela.groupby(chaves, as_index=False)["QT_VOTOS"].sum()
    # raríssimos casos de coligação retificada pelo TSE no mesmo turno (mesmo candidato, 2 registros):
    # fica o de maior votação, para não duplicar o candidato na lista
    chave_candidato = ["ANO", "NR_TURNO", "NM_MUNICIPIO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL"]
    tabela = tabela.sort_values("QT_VOTOS", ascending=False).drop_duplicates(chave_candidato, keep="first")
    return tabela


def main():
    if not PASTA.exists():
        raise SystemExit("Pasta dados/intermediario não encontrada. Rode antes: python baixar_dados_intermediario.py")

    # glob é insensível a maiúsculas/minúsculas no Windows: um padrão só já basta (e evita duplicar arquivos)
    arquivos = sorted(PASTA.glob("votacao_candidato_munzona_*_BA.csv"))
    if not arquivos:
        raise SystemExit("Nenhum arquivo encontrado em dados/intermediario. "
                          "Rode antes: python baixar_dados_intermediario.py")

    todos = []
    for arquivo in arquivos:
        ano = re.search(r"(\d{4})", arquivo.stem).group(1)
        tabela = processar_ano(arquivo, ano)
        todos.append(tabela)
        municipios = tabela["NM_MUNICIPIO"].nunique()
        print(f"  {ano}: {len(tabela)} candidaturas em {municipios} municípios "
              f"({', '.join(sorted(tabela['DS_CARGO'].unique()))})")

    tabela_final = pd.concat(todos, ignore_index=True)
    tabela_final.to_csv(SAIDA, index=False, encoding="utf-8")
    print(f"\nGravado {SAIDA} ({len(tabela_final)} linhas).")
    print(f"Pronto! Anos processados: {', '.join(sorted({t for t in tabela_final['ANO'].unique()}))}.")


if __name__ == "__main__":
    main()
