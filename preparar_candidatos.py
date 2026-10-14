"""
Passo 3b: fotos, partido e situação (eleito, suplente...) dos candidatos.

Lê o cadastro de candidatos (consulta_cand_<ano>_BA.csv) e as fotos do TSE
(foto_cand<ano>_BA_div.zip), reduz cada foto para uma miniatura e grava tudo em
dados_app/candidatos.parquet (é este arquivo que o app usa).

O compactar_dados.py já chama este script no final. Para rodar sozinho:
    python preparar_candidatos.py

Precisa da biblioteca Pillow para as fotos (uma vez só):
    pip install pillow
"""

import base64
import io
import re
import zipfile
from pathlib import Path

import pandas as pd

from baixar_dados import ANOS, UF, detectar_encoding

PASTA_DADOS = Path("dados")
PASTA_APP = Path("dados_app")
DESTINO = PASTA_APP / "candidatos.parquet"
TAMANHO_FOTO = (108, 144)   # largura x altura em pixels (o app mostra na metade, para ficar nítida)
COLUNAS = ["NR_TURNO", "DS_CARGO", "NR_CANDIDATO", "SQ_CANDIDATO", "SG_PARTIDO", "DS_SIT_TOT_TURNO"]


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
    df = df[COLUNAS].copy()
    for coluna in COLUNAS:
        df[coluna] = df[coluna].str.strip()
    df.insert(0, "ANO", ano)
    return df


def miniatura(dados):
    """Foto reduzida (JPEG) em texto base64, pronta para o app mostrar."""
    from PIL import Image, ImageOps
    with Image.open(io.BytesIO(dados)) as foto:
        foto = ImageOps.fit(ImageOps.exif_transpose(foto).convert("RGB"), TAMANHO_FOTO, Image.LANCZOS)
        saida = io.BytesIO()
        foto.save(saida, "JPEG", quality=78, optimize=True)
    return base64.b64encode(saida.getvalue()).decode("ascii")


def ler_fotos(ano):
    """{SQ_CANDIDATO: foto em base64}, a partir do ZIP de fotos do TSE."""
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
        for nome in z.namelist():
            achou = re.match(rf"F{UF}(\d+)_div\.(jpe?g|png)$", Path(nome).name, re.IGNORECASE)
            if not achou:
                continue
            try:
                fotos[achou.group(1)] = miniatura(z.read(nome))
            except Exception:   # foto corrompida: o candidato fica com as iniciais
                com_erro += 1
    if com_erro:
        print(f"   {ano}: {com_erro} foto(s) não puderam ser lidas.")
    return fotos


def main():
    partes = []
    for ano in ANOS:
        cadastro = ler_cadastro(ano)
        if cadastro is None:
            continue
        fotos = ler_fotos(ano)
        cadastro["FOTO"] = cadastro["SQ_CANDIDATO"].map(fotos).fillna("")
        com_foto = (cadastro["FOTO"] != "").sum()
        print(f"{ano}: {len(cadastro)} candidaturas, {com_foto} com foto.")
        partes.append(cadastro)
    if not partes:
        raise SystemExit("Nenhum cadastro de candidatos encontrado. Rode antes: python baixar_dados.py")
    PASTA_APP.mkdir(exist_ok=True)
    pd.concat(partes, ignore_index=True).to_parquet(DESTINO, index=False, compression="zstd")
    print(f"Pronto! {DESTINO}: {DESTINO.stat().st_size / 1024 / 1024:.1f} MB.")


if __name__ == "__main__":
    main()
