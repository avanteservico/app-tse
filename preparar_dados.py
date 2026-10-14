"""
Passo 5a: prepara os dados para o app (anos 2016 a 2026, com bairro e coordenadas das escolas).

Gera, dentro da pasta "dados":
  1) votos_por_municipio.csv  -> resumo por município e ano (telas gerais)
  2) municipios/<codigo>.csv  -> votos por seção e escola de cada município (todos os anos),
                                 com bairro, latitude e longitude da escola
  3) municipios_indice.csv    -> código e nome de cada município

Rode DEPOIS do baixar_dados.py (pode levar alguns minutos):
    python preparar_dados.py
"""

import codecs
import shutil
from pathlib import Path

import pandas as pd

ANOS = ["2016", "2018", "2020", "2022", "2024", "2026"]
PASTA_DADOS = Path("dados")
PASTA_MUNICIPIOS = PASTA_DADOS / "municipios"
SAIDA_RESUMO = PASTA_DADOS / "votos_por_municipio.csv"
SAIDA_INDICE = PASTA_DADOS / "municipios_indice.csv"

COLUNAS_LEITURA = [
    "NR_TURNO", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO",
    "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS",
    "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO", "DS_LOCAL_VOTACAO_ENDERECO",
]
CHAVES_RESUMO = ["ANO", "NR_TURNO", "NM_MUNICIPIO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL"]
COLUNAS_SECAO = ["ANO"] + [c for c in COLUNAS_LEITURA if c != "NM_MUNICIPIO"]
COLUNAS_LOCAL = ["NM_BAIRRO", "NR_LATITUDE", "NR_LONGITUDE"]

# Limites do Brasil: coordenadas fora disso (ou "-1", "0") são tratadas como ausentes
LAT_MIN, LAT_MAX = -34.0, 6.0
LON_MIN, LON_MAX = -74.0, -34.0


def achar_arquivo(padrao):
    arquivos = sorted(PASTA_DADOS.glob(padrao))
    return arquivos[0] if arquivos else None


def detectar_encoding(caminho):
    """Arquivos antigos do TSE são latin-1; os novos podem ser UTF-8."""
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


def sem_zeros(serie):
    """'0012' e '12' viram a mesma coisa, para o cruzamento não falhar."""
    return serie.str.strip().str.lstrip("0").replace("", "0")


def limpar_coordenada(serie, minimo, maximo):
    """Texto -> número (aceita vírgula decimal). Fora dos limites vira vazio."""
    numero = pd.to_numeric(serie.str.strip().str.replace(",", ".", regex=False), errors="coerce")
    numero = numero.where(numero.between(minimo, maximo))
    return numero.map(lambda v: "" if pd.isna(v) else f"{v:.6f}")


def processar_resultados():
    """Lê a votação por seção de cada ano. Devolve (resumo, pares código/nome, anos lidos)."""
    resumos, pares, anos_ok = [], set(), []
    for ano in ANOS:
        csv = achar_arquivo(f"votacao_secao_{ano}_*.csv")
        if csv is None:
            print(f"AVISO: resultados de {ano} não encontrados na pasta 'dados'. Pulando {ano}.")
            continue
        encoding = detectar_encoding(csv)
        cabecalho = pd.read_csv(csv, sep=";", encoding=encoding, nrows=0).columns.tolist()
        faltando = [c for c in COLUNAS_LEITURA if c not in cabecalho]
        if faltando:
            print(f"Colunas que eu esperava em {csv.name} e não encontrei:", faltando)
            print("Colunas do arquivo:", cabecalho)
            raise SystemExit("Copie esta mensagem e cole no Claude para ajustar o script.")

        # nome de urna: cruza SQ_CANDIDATO (arquivo de votação) com o cadastro de candidatos
        urnas = ler_nomes_de_urna(ano)
        colunas_lidas = list(COLUNAS_LEITURA)
        if urnas is not None:
            if "SQ_CANDIDATO" in cabecalho:
                colunas_lidas.append("SQ_CANDIDATO")
            else:
                print(f"AVISO: {csv.name} não tem a coluna SQ_CANDIDATO; mantendo os nomes do arquivo de votação.")
                urnas = None
        cand_total = cand_urna = 0

        print(f"Lendo resultados de {ano} ({csv.name}) em partes ...")
        leitor = pd.read_csv(
            csv, sep=";", encoding=encoding, usecols=colunas_lidas,
            dtype=str, keep_default_na=False, chunksize=500_000,
        )
        for i, parte in enumerate(leitor, start=1):
            parte["QT_VOTOS"] = pd.to_numeric(parte["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
            parte["ANO"] = ano
            parte["DS_CARGO"] = parte["DS_CARGO"].str.strip().str.title()   # 2016 vem "PREFEITO"; os outros, "Prefeito"

            if urnas is not None:
                sq = parte["SQ_CANDIDATO"].str.strip()
                nome_urna = sq.map(urnas)
                achou = nome_urna.notna()
                parte.loc[achou, "NM_VOTAVEL"] = nome_urna[achou]
                eh_candidato = pd.to_numeric(sq, errors="coerce") > 0   # branco/nulo/legenda não têm SQ válido
                cand_total += int(eh_candidato.sum())
                cand_urna += int((eh_candidato & achou).sum())

            resumos.append(parte.groupby(CHAVES_RESUMO, as_index=False)["QT_VOTOS"].sum())

            for codigo, nome in parte[["CD_MUNICIPIO", "NM_MUNICIPIO"]].drop_duplicates().itertuples(index=False):
                pares.add((codigo, nome))
            for codigo, grupo in parte.groupby("CD_MUNICIPIO"):
                arquivo = PASTA_MUNICIPIOS / f"{codigo}.csv"
                grupo[COLUNAS_SECAO].to_csv(
                    arquivo, mode="a", header=not arquivo.exists(), index=False, encoding="utf-8"
                )
            print(f"  {ano}: parte {i} processada")
        if urnas is not None and cand_total:
            print(f"  {ano}: nome de urna aplicado em {cand_urna / cand_total:.0%} dos registros de candidatos"
                  + ("" if cand_urna == cand_total else " (os demais ficam com o nome do arquivo de votação)"))
        anos_ok.append(ano)

    if not anos_ok:
        raise SystemExit("Nenhum arquivo de resultados encontrado. Rode antes: python baixar_dados.py")
    resumo = pd.concat(resumos).groupby(CHAVES_RESUMO, as_index=False)["QT_VOTOS"].sum()
    return resumo, pares, anos_ok


def primeira_coluna(cabecalho, candidatas, trecho):
    """Acha a coluna pelo nome esperado; se não achar, procura qualquer coluna que contenha o trecho."""
    for nome in candidatas:
        if nome in cabecalho:
            return nome
    achadas = [c for c in cabecalho if trecho in c.upper()]
    return achadas[0] if achadas else None


def ler_nomes_de_urna(ano):
    """Dicionário SQ_CANDIDATO -> nome de urna, lido do cadastro de candidatos (consulta_cand)."""
    arquivos = sorted(PASTA_DADOS.glob(f"consulta_cand_{ano}*.csv"))
    if not arquivos:
        print(f"AVISO: cadastro de candidatos de {ano} (consulta_cand_{ano}*.csv) não encontrado; "
              "os nomes ficam como vêm no arquivo de votação.")
        return None
    urnas = {}
    for arquivo in arquivos:
        encoding = detectar_encoding(arquivo)
        cabecalho = pd.read_csv(arquivo, sep=";", encoding=encoding, nrows=0).columns.tolist()
        coluna_urna = primeira_coluna(cabecalho, ["NM_URNA_CANDIDATO"], "URNA")
        if "SQ_CANDIDATO" not in cabecalho or coluna_urna is None:
            print(f"AVISO: não achei SQ_CANDIDATO / nome de urna em {arquivo.name}.")
            print("Colunas do arquivo:", cabecalho)
            print("Copie esta lista e cole no Claude para ajustar o script.")
            continue
        df = pd.read_csv(
            arquivo, sep=";", encoding=encoding, usecols=["SQ_CANDIDATO", coluna_urna],
            dtype=str, keep_default_na=False,
        )
        for sq, nome in zip(df["SQ_CANDIDATO"].str.strip(), df[coluna_urna].str.strip()):
            if nome and not nome.startswith("#") and sq not in urnas:
                urnas[sq] = nome
    return urnas or None


def ler_locais(codigos_municipios, anos):
    """Lê 'Eleitorado por local de votação': uma linha por escola/ano com bairro e coordenadas."""
    quadros = []
    obrigatorias = ["CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"]
    alvo = {c.lstrip("0") or "0" for c in codigos_municipios}
    for ano in anos:
        arquivo = achar_arquivo(f"eleitorado_local_votacao_{ano}*.csv")
        if arquivo is None:
            print(f"AVISO: 'eleitorado por local de votação' de {ano} não encontrado; sem bairro/mapa em {ano}.")
            continue
        encoding = detectar_encoding(arquivo)
        cabecalho = pd.read_csv(arquivo, sep=";", encoding=encoding, nrows=0).columns.tolist()
        achadas = {
            "NM_BAIRRO": primeira_coluna(cabecalho, ["NM_BAIRRO", "DS_BAIRRO", "NM_BAIRRO_LOCAL_VOTACAO", "BAIRRO"], "BAIRRO"),
            "NR_LATITUDE": primeira_coluna(cabecalho, ["NR_LATITUDE", "LATITUDE", "NM_LATITUDE"], "LATITUDE"),
            "NR_LONGITUDE": primeira_coluna(cabecalho, ["NR_LONGITUDE", "LONGITUDE", "NM_LONGITUDE"], "LONGITUDE"),
        }
        achadas = {novo: velho for novo, velho in achadas.items() if velho}
        faltando = [c for c in obrigatorias if c not in cabecalho]
        if faltando or not achadas:
            print(f"AVISO: não achei as colunas necessárias em {arquivo.name} (faltam {faltando or 'bairro/coordenadas'}).")
            print("Colunas do arquivo:", cabecalho)
            print("Copie esta lista e cole no Claude para ajustar o script.")
            continue
        for novo in COLUNAS_LOCAL:
            if novo not in achadas:
                print(f"AVISO: coluna de {novo} não encontrada em {arquivo.name}; {ano} ficará sem isso.")
        print(f"Lendo bairros e coordenadas de {ano} ({arquivo.name}; colunas {', '.join(achadas.values())}) ...")

        leitor = pd.read_csv(
            arquivo, sep=";", encoding=encoding, usecols=obrigatorias + list(achadas.values()),
            dtype=str, keep_default_na=False, chunksize=500_000,
        )
        for parte in leitor:
            parte = parte.rename(columns={velho: novo for novo, velho in achadas.items()})
            parte["_m"] = sem_zeros(parte["CD_MUNICIPIO"])
            parte = parte[parte["_m"].isin(alvo)].copy()
            if parte.empty:
                continue
            for novo in COLUNAS_LOCAL:
                if novo not in parte.columns:
                    parte[novo] = ""
            parte["_z"] = sem_zeros(parte["NR_ZONA"])
            parte["_l"] = sem_zeros(parte["NR_LOCAL_VOTACAO"])
            parte["NM_BAIRRO"] = parte["NM_BAIRRO"].str.strip()
            parte.loc[parte["NM_BAIRRO"].str.startswith("#"), "NM_BAIRRO"] = ""  # ex.: #NULO#
            parte["NR_LATITUDE"] = limpar_coordenada(parte["NR_LATITUDE"], LAT_MIN, LAT_MAX)
            parte["NR_LONGITUDE"] = limpar_coordenada(parte["NR_LONGITUDE"], LON_MIN, LON_MAX)
            sem_par = (parte["NR_LATITUDE"] == "") | (parte["NR_LONGITUDE"] == "")
            parte.loc[sem_par, ["NR_LATITUDE", "NR_LONGITUDE"]] = ""  # só vale se tiver as duas
            parte["ANO"] = ano
            quadros.append(parte[["ANO", "_m", "_z", "_l"] + COLUNAS_LOCAL].drop_duplicates())
    if not quadros:
        return None
    tabela = pd.concat(quadros)
    # uma linha por escola/ano; para cada campo fica o primeiro valor preenchido
    tabela[COLUNAS_LOCAL] = tabela[COLUNAS_LOCAL].replace("", pd.NA)
    tabela = tabela.groupby(["ANO", "_m", "_z", "_l"], as_index=False)[COLUNAS_LOCAL].first()
    tabela[COLUNAS_LOCAL] = tabela[COLUNAS_LOCAL].fillna("")
    return tabela


def juntar_locais(locais):
    """Acrescenta bairro e coordenadas em cada arquivo de município."""
    total = com_bairro = com_coordenada = 0
    for arquivo in sorted(PASTA_MUNICIPIOS.glob("*.csv")):
        df = pd.read_csv(arquivo, dtype=str, keep_default_na=False)
        if locais is not None:
            df["_m"] = sem_zeros(df["CD_MUNICIPIO"])
            df["_z"] = sem_zeros(df["NR_ZONA"])
            df["_l"] = sem_zeros(df["NR_LOCAL_VOTACAO"])
            antes = len(df)
            df = df.merge(locais, on=["ANO", "_m", "_z", "_l"], how="left")
            assert len(df) == antes, "o cruzamento com os locais de votação duplicou linhas"
            df[COLUNAS_LOCAL] = df[COLUNAS_LOCAL].fillna("")
            df = df.drop(columns=["_m", "_z", "_l"])
        else:
            for coluna in COLUNAS_LOCAL:
                df[coluna] = ""
        total += len(df)
        com_bairro += int((df["NM_BAIRRO"] != "").sum())
        com_coordenada += int((df["NR_LATITUDE"] != "").sum())
        df.to_csv(arquivo, index=False, encoding="utf-8")
    return total, com_bairro, com_coordenada


def main():
    # Começa do zero para não duplicar dados se você rodar de novo
    if PASTA_MUNICIPIOS.exists():
        shutil.rmtree(PASTA_MUNICIPIOS)
    PASTA_MUNICIPIOS.mkdir(parents=True)

    resumo, pares, anos_ok = processar_resultados()
    resumo.to_csv(SAIDA_RESUMO, index=False, encoding="utf-8")
    pd.DataFrame(sorted(pares), columns=["CD_MUNICIPIO", "NM_MUNICIPIO"]).to_csv(
        SAIDA_INDICE, index=False, encoding="utf-8"
    )

    locais = ler_locais({codigo for codigo, _ in pares}, anos_ok)
    total, com_bairro, com_coordenada = juntar_locais(locais)

    print(f"\nPronto! Anos: {', '.join(anos_ok)}. {len(resumo):,} linhas no resumo, "
          f"{len({c for c, _ in pares})} municípios.")
    if total:
        print(f"Bairro encontrado em {com_bairro / total:.0%} das linhas por seção.")
        print(f"Coordenadas válidas em {com_coordenada / total:.0%} das linhas por seção.")
    if com_bairro == 0:
        print("ATENÇÃO: nenhum bairro foi encontrado. O app vai funcionar, mas sem o filtro de bairro.")
    if com_coordenada == 0:
        print("ATENÇÃO: nenhuma coordenada válida foi encontrada. O app vai funcionar, mas sem os mapas.")


if __name__ == "__main__":
    main()
