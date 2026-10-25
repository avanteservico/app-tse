"""
Copia os bairros informados para o banco da VPS (PostgreSQL).

Uso na VPS:
    sudo -u eleicoes /opt/app-tse/.venv/bin/python /opt/app-tse/vps/importar_bairros.py
        -> pergunta o endereço (SUPABASE_URL) e a chave (SUPABASE_KEY) do Supabase e copia tudo de lá
    sudo -u eleicoes /opt/app-tse/.venv/bin/python /opt/app-tse/vps/importar_bairros.py arquivo.csv
        -> copia de um CSV (exportado do Supabase ou o dados/bairros_informados.csv)

Pode rodar mais de uma vez: o que já existe é atualizado, nada é duplicado.
"""

import csv
import sys
import tomllib
from pathlib import Path

import psycopg
import requests

SEGREDOS = Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml"
COLUNAS = ["cd_municipio", "nr_zona", "nm_local_n", "nm_local_votacao", "bairro"]


def do_supabase():
    url = input("Cole o SUPABASE_URL (ex.: https://xxxx.supabase.co): ").strip().rstrip("/")
    chave = input("Cole a SUPABASE_KEY (a chave service_role): ").strip()
    linhas, inicio = [], 0
    while True:   # o Supabase devolve no máximo 1000 linhas por vez
        resposta = requests.get(
            f"{url}/rest/v1/bairros_informados", timeout=60,
            params={"select": ",".join(COLUNAS), "order": "cd_municipio,nr_zona,nm_local_n",
                    "offset": inicio, "limit": 1000},
            headers={"apikey": chave, "Authorization": f"Bearer {chave}"},
        )
        resposta.raise_for_status()
        parte = resposta.json()
        linhas += parte
        if len(parte) < 1000:
            return linhas
        inicio += 1000


def do_csv(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return [{c.lower(): (v or "") for c, v in linha.items()} for linha in csv.DictReader(f)]


def main():
    linhas = do_csv(sys.argv[1]) if len(sys.argv) > 1 else do_supabase()
    faltando = [c for c in COLUNAS if linhas and c not in linhas[0]]
    if faltando:
        raise SystemExit(f"O arquivo não tem as colunas {faltando}. Colunas encontradas: {list(linhas[0])}")
    url_banco = tomllib.loads(SEGREDOS.read_text(encoding="utf-8"))["DATABASE_URL"]
    with psycopg.connect(url_banco) as conexao:
        conexao.cursor().executemany(
            "insert into bairros_informados (cd_municipio, nr_zona, nm_local_n, nm_local_votacao, bairro) "
            "values (%s, %s, %s, %s, %s) on conflict (cd_municipio, nr_zona, nm_local_n) "
            "do update set nm_local_votacao = excluded.nm_local_votacao, bairro = excluded.bairro",
            [tuple(str(l[c] or "").strip() for c in COLUNAS) for l in linhas],
        )
        total = conexao.execute("select count(*) from bairros_informados").fetchone()[0]
    print(f"Pronto! {len(linhas)} bairro(s) copiado(s). O banco da VPS tem agora {total} escola(s) com bairro informado.")


if __name__ == "__main__":
    main()
