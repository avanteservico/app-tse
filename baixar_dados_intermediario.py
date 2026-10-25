"""
Passo 1c: baixa os resultados do TSE para a Bahia entre 1994 e 2014 (o periodo "intermediario":
depois do historico de papel de 1960-1990, mas antes do layout atual de 2016-2026).

Nesse periodo o TSE ja tem votacao por MUNICIPIO E ZONA (um arquivo so, "votacao_candidato_munzona",
com todas as UFs - filtra-se a Bahia depois). Nao existe votacao por SECAO de forma confiavel e
uniforme em todos esses anos (o layout mudou varias vezes), nem nome/bairro/coordenadas da escola -
por isso o app, nesses anos, mostra o resultado por municipio, mas nao por escola nem no mapa.

Para rodar:
    python baixar_dados_intermediario.py

Para baixar tudo de novo:
    python baixar_dados_intermediario.py --atualizar
"""

import sys
import zipfile
from pathlib import Path

import requests

UF = "BA"
ANOS = ["1994", "1996", "1998", "2000", "2002", "2004", "2006", "2008", "2010", "2012", "2014"]
BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
PASTA_DADOS = Path("dados") / "intermediario"
ATUALIZAR = "--atualizar" in sys.argv


def baixar(nome, url, destino):
    if destino.exists() and not ATUALIZAR:
        print(f"[{nome}] já existe, pulando o download.")
        return True
    print(f"[{nome}] baixando {url}")
    parcial = destino.with_suffix(".part")
    try:
        with requests.get(url, stream=True, timeout=180) as resposta:
            resposta.raise_for_status()
            with open(parcial, "wb") as f:
                for pedaco in resposta.iter_content(chunk_size=1024 * 1024):
                    f.write(pedaco)
    except requests.exceptions.RequestException as erro:
        print(f"[{nome}] NAO consegui baixar: {erro}")
        if parcial.exists():
            parcial.unlink()
        return False
    parcial.replace(destino)
    print("   download concluido.")
    return True


def extrair_bahia(arquivo_zip):
    """O ZIP tem um CSV por UF (Brasil inteiro); extrai só o da Bahia."""
    with zipfile.ZipFile(arquivo_zip) as z:
        candidatos = [n for n in z.namelist() if n.upper().endswith(f"_{UF}.CSV")]
        if not candidatos:
            print(f"   aviso: nenhum CSV da Bahia dentro de {arquivo_zip.name}")
            return None
        nome_csv = candidatos[0]
        destino = PASTA_DADOS / Path(nome_csv).name
        if ATUALIZAR or not destino.exists():
            print(f"   extraindo {Path(nome_csv).name} ...")
            with z.open(nome_csv) as origem, open(destino, "wb") as saida:
                saida.write(origem.read())
    return destino


def main():
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    faltando = []
    for ano in ANOS:
        nome = f"Votação por candidato, município e zona - {ano}"
        url = f"{BASE}/votacao_candidato_munzona/votacao_candidato_munzona_{ano}.zip"
        destino = PASTA_DADOS / f"votacao_candidato_munzona_{ano}.zip"
        print()
        if not baixar(nome, url, destino):
            faltando.append(nome)
            continue
        extrair_bahia(destino)

    print()
    if faltando:
        print("Não foram baixados:")
        for nome in faltando:
            print(" -", nome)
    print("Agora rode: python preparar_dados_intermediario.py")


if __name__ == "__main__":
    main()
