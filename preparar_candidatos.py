"""
Passo 3b: fotos, partido e situação (eleito, suplente...) dos candidatos.

Lê o cadastro de candidatos (consulta_cand_<ano>_BA.csv) e as fotos do TSE
(foto_cand<ano>_BA_div.zip) e grava, na pasta dados_app:
  - candidatos.parquet          -> partido e situação de cada candidatura (sem fotos)
  - fotos/<ano>/<UE>.parquet    -> miniaturas das fotos. UE = "BA" nas eleições gerais
                                   e o código do município nas municipais (prefeito/vereador),
                                   para o app carregar só as fotos do município escolhido.

O compactar_dados.py já chama este script no final. Para rodar sozinho:
    python preparar_candidatos.py

Precisa da biblioteca Pillow para as fotos (uma vez só):
    pip install pillow
"""

import hashlib
import io
import re
import shutil
import zipfile
from pathlib import Path

import pandas as pd

from baixar_dados import ANOS, UF, detectar_encoding

PASTA_DADOS = Path("dados")
PASTA_APP = Path("dados_app")
DESTINO = PASTA_APP / "candidatos.parquet"
PASTA_FOTOS = PASTA_APP / "fotos"
TAMANHO_FOTO = (81, 108)    # largura x altura em pixels (o app mostra em 54 x 72, um pouco menor, para ficar nítida)
COLUNAS = ["NR_TURNO", "DS_CARGO", "SG_UE", "NR_CANDIDATO", "SQ_CANDIDATO", "SG_PARTIDO", "DS_SIT_TOT_TURNO"]
COL_TITULO = "NR_TITULO_ELEITORAL_CANDIDATO"


def id_pessoa(titulo):
    """Código que identifica a mesma pessoa em anos diferentes (o nome de urna pode mudar).
    Vem do título de eleitor (presente em todos os anos; o CPF não vem em 2024), mas não guarda o título."""
    titulo = titulo.strip().lstrip("0")
    if not titulo.isdigit():
        return ""
    return hashlib.sha256(f"eleicoes-ba|{titulo}".encode()).hexdigest()[:16]


def ler_cadastro(ano):
    csv = PASTA_DADOS / f"consulta_cand_{ano}_{UF}.csv"
    if not csv.exists():
        print(f"AVISO: {csv} não encontrado (rode python baixar_dados.py); {ano} fica sem fotos/situação.")
        return None
    df = pd.read_csv(csv, sep=";", encoding=detectar_encoding(csv), dtype=str, keep_default_na=False)
    faltando = [c for c in COLUNAS if c not in df.columns]
    if faltando:
        print(f"AVISO: {csv.name} não tem as colunas {faltando}; {ano} fica sem fotos/situação.")
        return None
    pessoa = df[COL_TITULO].map(id_pessoa) if COL_TITULO in df.columns else ""
    df = df[COLUNAS].copy()
    for coluna in COLUNAS:
        df[coluna] = df[coluna].str.strip()
    df["ID_PESSOA"] = pessoa
    df["SG_UE"] = df["SG_UE"].str.lstrip("0")   # mesmo formato do código de município no app
    df.insert(0, "ANO", ano)
    return df


def miniatura(dados):
    """Foto reduzida (bytes de um JPEG pequeno)."""
    from PIL import Image, ImageOps
    with Image.open(io.BytesIO(dados)) as foto:
        foto = ImageOps.fit(ImageOps.exif_transpose(foto).convert("RGB"), TAMANHO_FOTO, Image.LANCZOS)
        saida = io.BytesIO()
        foto.save(saida, "JPEG", quality=70, optimize=True)
    return saida.getvalue()


def ler_fotos(ano, procurados):
    """{SQ_CANDIDATO: foto (bytes)}, a partir do ZIP de fotos do TSE (só dos candidatos procurados)."""
    arquivo = PASTA_DADOS / f"foto_cand{ano}_{UF}_div.zip"
    if not arquivo.exists():
        print(f"AVISO: {arquivo} não encontrado (rode python baixar_dados.py); {ano} fica sem fotos.")
        return {}
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("AVISO: biblioteca Pillow não instalada; sem fotos. Instale com: pip install pillow")
        return {}
    fotos, com_erro = {}, 0
    with zipfile.ZipFile(arquivo) as z:
        nomes = z.namelist()
        for i, nome in enumerate(nomes, start=1):
            achou = re.match(rf"F{UF}(\d+)_div\.(jpe?g|png)$", Path(nome).name, re.IGNORECASE)
            if achou and achou.group(1) in procurados and achou.group(1) not in fotos:
                try:
                    fotos[achou.group(1)] = miniatura(z.read(nome))
                except Exception:   # foto corrompida: o candidato fica com as iniciais
                    com_erro += 1
            if i % 5000 == 0:
                print(f"   {ano}: {i} de {len(nomes)} fotos lidas")
    if com_erro:
        print(f"   {ano}: {com_erro} foto(s) não puderam ser lidas.")
    return fotos


def main():
    partes = []
    if PASTA_FOTOS.exists():
        shutil.rmtree(PASTA_FOTOS)
    for ano in ANOS:
        cadastro = ler_cadastro(ano)
        if cadastro is None:
            continue
        fotos = ler_fotos(ano, set(cadastro["SQ_CANDIDATO"]))
        por_sq = cadastro.drop_duplicates("SQ_CANDIDATO")[["SQ_CANDIDATO", "SG_UE"]]
        por_sq = por_sq.assign(FOTO=por_sq["SQ_CANDIDATO"].map(fotos)).dropna(subset=["FOTO"])
        (PASTA_FOTOS / ano).mkdir(parents=True, exist_ok=True)
        for ue, grupo in por_sq.groupby("SG_UE"):
            grupo[["SQ_CANDIDATO", "FOTO"]].sort_values("SQ_CANDIDATO").to_parquet(
                PASTA_FOTOS / ano / f"{ue}.parquet", index=False, compression="zstd",
            )
        print(f"{ano}: {len(cadastro)} candidaturas, {len(por_sq)} com foto.")
        partes.append(cadastro)
    if not partes:
        raise SystemExit("Nenhum cadastro de candidatos encontrado. Rode antes: python baixar_dados.py")
    PASTA_APP.mkdir(exist_ok=True)
    pd.concat(partes, ignore_index=True).to_parquet(DESTINO, index=False, compression="zstd")
    tamanho = DESTINO.stat().st_size + sum(f.stat().st_size for f in PASTA_FOTOS.rglob("*.parquet"))
    print(f"Pronto! {DESTINO} e {PASTA_FOTOS}: {tamanho / 1024 / 1024:.1f} MB.")


if __name__ == "__main__":
    main()
