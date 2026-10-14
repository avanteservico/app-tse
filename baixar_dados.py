"""
Passo 1 (versão 3): baixa os dados do TSE para a Bahia - eleições de 2018, 2022 e 2026.

Para cada ano, baixa:
  - Votação por seção eleitoral (BA)
  - Eleitorado por local de votação (Brasil todo; é daqui que vem o BAIRRO das escolas)
  - Cadastro de candidatos (Brasil todo; é daqui que vem o NOME DE URNA)
  - Fotos dos candidatos (BA)

Antes de rodar, instale as bibliotecas (uma vez só):
    pip install requests pandas

Para rodar:
    python baixar_dados.py

Para baixar tudo de novo (por exemplo, depois do 2º turno, quando o TSE atualiza os arquivos):
    python baixar_dados.py --atualizar
"""

import codecs
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

UF = "BA"
ANOS = ["2018", "2022", "2026"]
BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
PASTA_DADOS = Path("dados")
ATUALIZAR = "--atualizar" in sys.argv


def lista_de_arquivos():
    """(nome para mostrar, endereço no TSE, onde salvar)"""
    arquivos = []
    for ano in ANOS:
        arquivos.append((
            f"Votação por seção {ano} ({UF})",
            f"{BASE}/votacao_secao/votacao_secao_{ano}_{UF}.zip",
            PASTA_DADOS / f"votacao_secao_{ano}_{UF}.zip",
        ))
        arquivos.append((
            f"Eleitorado por local de votação {ano} (traz o bairro)",
            f"{BASE}/eleitorado_locais_votacao/eleitorado_local_votacao_{ano}.zip",
            PASTA_DADOS / f"eleitorado_local_votacao_{ano}.zip",
        ))
        arquivos.append((
            f"Cadastro de candidatos {ano} (traz o nome de urna)",
            f"{BASE}/consulta_cand/consulta_cand_{ano}.zip",
            PASTA_DADOS / f"consulta_cand_{ano}.zip",
        ))
        arquivos.append((
            f"Fotos dos candidatos {ano} ({UF})",
            f"https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes{ano}/fotos/foto_cand{ano}_{UF}_div.zip",
            PASTA_DADOS / f"foto_cand{ano}_{UF}_div.zip",
        ))
    return arquivos


def baixar(nome, url, destino):
    """Baixa o ZIP. Devolve True se o arquivo está disponível no computador."""
    if destino.exists() and not ATUALIZAR:
        print(f"[{nome}] já existe, pulando o download.")
        return True
    print(f"[{nome}] baixando {url}")
    print("   (arquivos grandes podem levar alguns minutos)")
    parcial = destino.with_suffix(".part")
    try:
        with requests.get(url, stream=True, timeout=120) as resposta:
            resposta.raise_for_status()
            with open(parcial, "wb") as f:
                for pedaco in resposta.iter_content(chunk_size=1024 * 1024):
                    f.write(pedaco)
    except requests.exceptions.RequestException as erro:
        print(f"[{nome}] NÃO consegui baixar: {erro}")
        print("   (se for 2026, o TSE pode ainda não ter publicado este arquivo)")
        if parcial.exists():
            parcial.unlink()
        return False
    parcial.replace(destino)
    print("   download concluído.")
    return True


def descompactar(arquivo_zip):
    """Descompacta o ZIP e devolve o caminho do CSV."""
    with zipfile.ZipFile(arquivo_zip) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not csvs:
            print(f"   aviso: nenhum CSV dentro de {arquivo_zip.name}")
            return None
        # se o ZIP tiver um CSV por estado (ex.: consulta_cand_2022_BA.csv), pega só o da Bahia
        preferidos = [n for n in csvs if n.upper().endswith(f"_{UF}.CSV")]
        nome_csv = (preferidos or csvs)[0]
        destino = PASTA_DADOS / nome_csv
        if ATUALIZAR or not destino.exists():
            print(f"   descompactando {nome_csv} ...")
            z.extract(nome_csv, PASTA_DADOS)
    return destino


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


def mostrar_resumo(csv):
    encoding = detectar_encoding(csv)
    amostra = pd.read_csv(csv, sep=";", encoding=encoding, dtype=str, nrows=3)
    print(f"   colunas ({len(amostra.columns)}): " + ", ".join(amostra.columns))
    if "NR_TURNO" in amostra.columns:
        turnos = {}
        leitor = pd.read_csv(csv, sep=";", encoding=encoding, usecols=["NR_TURNO"],
                             dtype=str, chunksize=1_000_000)
        for parte in leitor:
            for turno, qtd in parte["NR_TURNO"].value_counts().items():
                turnos[turno] = turnos.get(turno, 0) + int(qtd)
        for turno in sorted(turnos):
            print(f"   {turno}º turno: {turnos[turno]:,} linhas")


def main():
    PASTA_DADOS.mkdir(exist_ok=True)
    faltando = []
    for nome, url, destino in lista_de_arquivos():
        print()
        if not baixar(nome, url, destino):
            faltando.append(nome)
            continue
        if destino.name.startswith("foto_cand"):   # fotos: quem usa é o preparar_candidatos.py
            continue
        csv = descompactar(destino)
        if csv is not None:
            mostrar_resumo(csv)

    print()
    if faltando:
        print("Não foram baixados:")
        for nome in faltando:
            print(" -", nome)
        print("Você pode rodar de novo mais tarde; os que já foram baixados são reaproveitados.")
    print("Agora rode: python preparar_dados.py")


if __name__ == "__main__":
    main()
