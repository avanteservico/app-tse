"""
Passo 1b: baixa os resultados historicos do TSE para a Bahia (eleicoes de 1960 a 1990).

Esses anos nao tem votacao por secao nem por municipio: o TSE so disponibiliza o
resultado consolidado por UF (estado inteiro), porque os dados vieram da digitalizacao
de atas e mapas de apuracao em papel. Por isso os arquivos aqui sao outros, diferentes
dos que o baixar_dados.py baixa para 2016-2026.

Para cada ano, baixa (Brasil todo; filtra-se a Bahia depois, no preparar):
  - Votacao nominal por candidato, por UF (votacao_candidato_uf)
  - Detalhe da apuracao por UF: comparecimento, abstencao, brancos, nulos (detalhe_votacao_uf)
  - Votacao por partido/coligacao, por UF (votacao_partido_uf)
  - Vagas em disputa, por UF (consulta_vagas)
  - Legendas/coligacoes registradas (consulta_legendas)

Antes de rodar, instale as bibliotecas (uma vez so):
    pip install requests

Para rodar:
    python baixar_dados_historico.py

Para baixar tudo de novo:
    python baixar_dados_historico.py --atualizar
"""

import sys
import zipfile
from pathlib import Path

import requests

ANOS = ["1960", "1962", "1965", "1966", "1970", "1974", "1978", "1982", "1986", "1989", "1990"]
TIPOS = [
    ("votacao_candidato_uf", "Votacao nominal por candidato (por UF)"),
    ("detalhe_votacao_uf", "Detalhe da apuracao (comparecimento, abstencao) por UF"),
    ("votacao_partido_uf", "Votacao por partido/coligacao (por UF)"),
    ("consulta_vagas", "Vagas em disputa (por UF)"),
    ("consulta_legendas", "Legendas e coligacoes registradas"),
]
BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"
PASTA_DADOS = Path("dados") / "historico"
UF = "BA"
ATUALIZAR = "--atualizar" in sys.argv


def lista_de_arquivos():
    """(nome para mostrar, endereco no TSE, onde salvar)"""
    arquivos = []
    for ano in ANOS:
        for tipo, descricao in TIPOS:
            arquivos.append((
                f"{descricao} - {ano}",
                f"{BASE}/{tipo}/{tipo}_{ano}.zip",
                PASTA_DADOS / f"{tipo}_{ano}.zip",
            ))
    return arquivos


def baixar(nome, url, destino):
    """Baixa o ZIP. Devolve True se o arquivo esta disponivel no computador."""
    if destino.exists() and not ATUALIZAR:
        print(f"[{nome}] ja existe, pulando o download.")
        return True
    print(f"[{nome}] baixando {url}")
    parcial = destino.with_suffix(".part")
    try:
        with requests.get(url, stream=True, timeout=120) as resposta:
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


def descompactar(arquivo_zip):
    """Descompacta o ZIP e devolve o caminho do .txt da Bahia.

    Alguns anos trazem um .txt só (Brasil inteiro, ex.: 1960, 1989, 1990);
    outros trazem um .txt por UF (ex.: ..._BA.txt) - nesse caso tem que
    escolher o da Bahia, senão pega o primeiro da lista (sempre "AC").
    """
    with zipfile.ZipFile(arquivo_zip) as z:
        txts = [n for n in z.namelist() if n.lower().endswith(".txt")]
        if not txts:
            print(f"   aviso: nenhum TXT dentro de {arquivo_zip.name}")
            return None
        da_bahia = [n for n in txts if n.upper().endswith(f"_{UF}.TXT")]
        nome_txt = (da_bahia or txts)[0]
        destino = PASTA_DADOS / Path(nome_txt).name
        if ATUALIZAR or not destino.exists():
            print(f"   descompactando {Path(nome_txt).name} ...")
            with z.open(nome_txt) as origem, open(destino, "wb") as saida:
                saida.write(origem.read())
    return destino


def main():
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    faltando = []
    for nome, url, destino in lista_de_arquivos():
        print()
        if not baixar(nome, url, destino):
            faltando.append(nome)
            continue
        descompactar(destino)

    print()
    if faltando:
        print("Nao foram baixados:")
        for nome in faltando:
            print(" -", nome)
        print("Voce pode rodar de novo mais tarde; os que ja foram baixados sao reaproveitados.")
    print("Agora rode: python preparar_dados_historico.py")


if __name__ == "__main__":
    main()
