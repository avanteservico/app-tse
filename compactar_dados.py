"""
Passo 3 (para publicar na internet): compacta os dados do app no formato Parquet.

Lê o que o preparar_dados.py gerou na pasta "dados" e grava versões bem menores na
pasta "dados_app" (é esta pasta que vai para o GitHub e para o app publicado).

Rode DEPOIS do preparar_dados.py:
    python compactar_dados.py

Precisa da biblioteca pyarrow (uma vez só):
    pip install pyarrow
"""

import shutil
from pathlib import Path

import pandas as pd

import preparar_candidatos

PASTA_DADOS = Path("dados")
PASTA_APP = Path("dados_app")
LIMITE_MB = 90   # o GitHub recusa arquivos acima de 100 MB


def compactar(origem, destino):
    df = pd.read_csv(origem, dtype=str, keep_default_na=False)
    df.to_parquet(destino, index=False, compression="zstd")
    return destino.stat().st_size


def main():
    resumo = PASTA_DADOS / "votos_por_municipio.csv"
    indice = PASTA_DADOS / "municipios_indice.csv"
    municipios = sorted((PASTA_DADOS / "municipios").glob("*.csv"))
    if not resumo.exists() or not indice.exists() or not municipios:
        raise SystemExit("Dados não encontrados. Rode antes: python preparar_dados.py")

    # começa do zero para não sobrar arquivo velho
    if PASTA_APP.exists():
        shutil.rmtree(PASTA_APP)
    (PASTA_APP / "municipios").mkdir(parents=True)

    total = compactar(resumo, PASTA_APP / "votos_por_municipio.parquet")
    shutil.copy(indice, PASTA_APP / "municipios_indice.csv")
    grandes = []
    for i, arquivo in enumerate(municipios, start=1):
        tamanho = compactar(arquivo, PASTA_APP / "municipios" / f"{arquivo.stem}.parquet")
        total += tamanho
        if tamanho > LIMITE_MB * 1024 * 1024:
            grandes.append((arquivo.stem, tamanho))
        if i % 50 == 0 or i == len(municipios):
            print(f"  {i} de {len(municipios)} municípios compactados")

    print("\nFotos, partido e situação dos candidatos:")
    preparar_candidatos.main()
    total += sum(f.stat().st_size for f in [PASTA_APP / "candidatos.parquet", *(PASTA_APP / "fotos").rglob("*.parquet")])

    print(f"\nPronto! Pasta {PASTA_APP}: {total / 1024 / 1024:.0f} MB no total.")
    for codigo, tamanho in grandes:
        print(f"ATENÇÃO: o município {codigo} ficou com {tamanho / 1024 / 1024:.0f} MB "
              f"(o GitHub não aceita arquivos acima de 100 MB).")


if __name__ == "__main__":
    main()
