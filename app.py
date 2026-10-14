"""
Passo 4b: o app, com bairro/localidade e comparação entre anos (2022 x 2026).
Bahia. Fonte: Portal de Dados Abertos do TSE.

Para rodar:
    streamlit run app.py

Sempre mostra a votação NOMINAL: sem votos brancos, nulos e de legenda.
"""

import html
import math
import time
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st

PASTA = Path("dados")
PASTA_APP = Path("dados_app")   # versão compactada (compactar_dados.py); é a usada no app publicado
ARQ_INDICE = PASTA_APP / "municipios_indice.csv" if (PASTA_APP / "municipios_indice.csv").exists() \
    else PASTA / "municipios_indice.csv"
ARQ_BAIRROS = PASTA / "bairros_informados.csv"   # bairros que você informa (têm prioridade sobre o TSE)
TABELA_BAIRROS = "bairros_informados"            # mesma coisa, no Supabase (quando o app está na internet)
COLS_BAIRROS = ["CD_MUNICIPIO", "NR_ZONA", "NM_LOCAL_N", "NM_LOCAL_VOTACAO", "BAIRRO"]
TELA_VOTACAO = "Votação"
TELA_CADASTRO = "Cadastrar bairros das escolas"
COL_INFORMADO = "Bairro informado por você"

TODOS = "Todos os municípios"
TODOS_BAIRROS = "Todos os bairros/localidades"
TODAS_ESCOLAS = "Todas as escolas"
TODAS_SECOES = "Todas as seções"
SEM_BAIRRO = "(sem bairro informado)"
MODO_NOME = "Nome da escola + zona"
MODO_NUMERO = "Número do local + zona"
ESCOLHER = "(escolher)"
NAO_COMPARAR = "Não comparar"
LIMITE_GRAUS = 1.2   # escola a mais de ~130 km do centro do município = coordenada errada
centro_mun = None    # (latitude, longitude) mediana das escolas do município escolhido

st.set_page_config(page_title="Eleições - Bahia", layout="wide")

# ------------------------------------------------------------- aparência
ESTILO = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Jost:wght@400;500;600;700&display=swap');
:root {
  --fundo: #f3f1ea; --cartao: #faf9f5; --borda: #e3ded3; --texto: #2a2723; --suave: #6b665d;
  --verde: #1e7b45; --trilho: #e7e3da; --escuro: #2a2622; --faixa: #ebe3d7; --azul: #2456a6;
}
html, body, [class*="st-"], .stMarkdown, button, input, textarea, select {
  font-family: 'Jost', system-ui, sans-serif;
}
h1, h2, h3 { font-family: 'Jost', system-ui, sans-serif !important; font-weight: 600 !important; color: var(--texto); }
[data-testid="stSidebar"] { background: #ebe7de; border-right: 1px solid var(--borda); }

/* cartões: métricas, expansores, tabelas, gráficos */
[data-testid="stMetric"] {
  background: var(--cartao); border: 1px solid var(--borda); border-radius: 14px; padding: 14px 18px;
}
[data-testid="stMetricValue"] { font-weight: 600; }
[data-testid="stExpander"] details {
  background: var(--cartao); border: 1px solid var(--borda) !important; border-radius: 14px !important;
}
[data-testid="stDataFrame"], [data-testid="stVegaLiteChart"], [data-testid="stDeckGlJsonChart"] {
  border: 1px solid var(--borda); border-radius: 14px; overflow: hidden; background: var(--cartao);
}

/* campos de texto e listas de escolha arredondados */
[data-testid="stTextInput"] div[data-baseweb="input"],
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  border-radius: 12px !important; background: var(--cartao) !important; border-color: var(--borda) !important;
}
[data-testid="stTextInput"] input { padding: 12px 14px; font-size: 1.05rem; }

/* botões escuros */
.stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {
  background: var(--escuro); color: #fff; border: 0; border-radius: 12px; font-weight: 600; padding: 8px 20px;
}
.stButton button:hover, .stDownloadButton button:hover, [data-testid="stFormSubmitButton"] button:hover {
  background: #000; color: #fff;
}
[data-testid="stForm"] { border: 0; padding: 0; }

/* faixa de contexto (eleição · ano · cargo · local) */
.faixa {
  background: var(--faixa); border: 1px solid var(--borda); border-left: 3px solid var(--azul);
  border-radius: 8px; padding: 8px 14px; margin: 6px 0 14px; color: var(--texto); font-size: .95rem;
}
.faixa b.eleicao { color: var(--azul); }
.faixa .sep { color: var(--suave); margin: 0 6px; }

/* lista de candidatos */
.lista { background: var(--cartao); border: 1px solid var(--borda); border-radius: 14px; padding: 6px 16px 4px; }
.lista-topo { color: var(--suave); font-size: .92rem; padding: 10px 0 4px; }
.lista-topo b { color: var(--texto); }
.cand {
  display: grid; grid-template-columns: 54px 30px 1fr auto; column-gap: 12px; row-gap: 10px;
  padding: 12px 0 12px; border-bottom: 1px solid var(--borda); align-items: start;
}
.cand:last-child { border-bottom: 0; }
.cand-foto {
  width: 54px; height: 70px; border-radius: 6px; background: #e4ddcf; color: #6b5f4b;
  display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 1.1rem;
  border: 1px solid var(--borda); overflow: hidden;
}
.cand-foto img { width: 100%; height: 100%; object-fit: cover; border-radius: 5px; display: block; }
.selo {
  display: inline-block; padding: 1px 8px; border-radius: 6px; font-weight: 600; font-size: .85rem;
  margin-right: 4px; color: #fff; background: var(--verde);
}
.selo.turno2 { background: var(--azul); }
.selo.suplente { background: #e4ddcf; color: #5a5245; }
.cand-pos { color: var(--suave); padding-top: 3px; text-align: center; }
.cand-nome { font-size: 1.12rem; font-weight: 500; color: var(--texto); line-height: 1.3; }
.cand-meta { color: #4a463f; font-size: .92rem; margin-top: 14px; }
.cand-votos { text-align: right; white-space: nowrap; }
.cand-votos b { display: block; font-size: 1.1rem; font-weight: 600; color: var(--texto); }
.cand-votos span { color: var(--suave); font-size: .9rem; }
.cand-barra { grid-column: 1 / -1; height: 3px; background: var(--trilho); border-radius: 2px; }
.cand-barra span { display: block; height: 3px; background: var(--verde); border-radius: 2px; min-width: 2px; }
@media (max-width: 640px) {
  .cand { grid-template-columns: 40px 22px 1fr auto; column-gap: 8px; }
  .cand-foto { width: 40px; height: 52px; font-size: .9rem; }
  .cand-nome { font-size: 1rem; }
  .cand-meta { margin-top: 6px; }
}
</style>
"""
st.markdown(ESTILO, unsafe_allow_html=True)

st.title("Eleições - Bahia")
st.caption(
    "Fonte: Portal de Dados Abertos do TSE (dadosabertos.tse.jus.br). "
    "Mostrando apenas a votação nominal (sem brancos, nulos e votos de legenda). "
    "Candidatos identificados pelo nome de urna."
)


# ---------------------------------------------------------------- utilitários
def normalizar(texto):
    """Maiúsculas e sem acento, para comparar e pesquisar textos."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.upper().split())


def so_nominais(df):
    """Mantém só votos em candidatos (tira branco, nulo e voto de legenda)."""
    numero = df["NR_VOTAVEL"].astype(str)
    mascara = ~numero.isin(["95", "96", "97", "98"])
    deputado = df["DS_CARGO"].str.contains("deputado", case=False, na=False)
    mascara &= ~(deputado & (numero.str.len() <= 2))  # legenda = número do partido (2 dígitos)
    return df[mascara]


def formatar(n):
    return f"{int(n):,}".replace(",", ".")


def formatar_pct(p):
    return f"{p:.2f}".replace(".", ",") + "%"


# nome do partido (como vem no voto de legenda do TSE, normalizado) -> sigla
SIGLAS = {
    "REPUBLICANOS": "REPUBLICANOS", "PROGRESSISTAS": "PP", "PARTIDO DEMOCRATICO TRABALHISTA": "PDT",
    "PARTIDO DOS TRABALHADORES": "PT", "PARTIDO TRABALHISTA BRASILEIRO": "PTB", "PARTIDO MISSAO": "MISSÃO",
    "MOVIMENTO DEMOCRATICO BRASILEIRO": "MDB", "REDE SUSTENTABILIDADE": "REDE", "PODEMOS": "PODE",
    "PARTIDO SOCIAL CRISTAO": "PSC", "PARTIDO COMUNISTA BRASILEIRO": "PCB", "PARTIDO LIBERAL": "PL",
    "CIDADANIA": "CIDADANIA", "DEMOCRACIA CRISTA": "DC", "PARTIDO RENOVADOR TRABALHISTA BRASILEIRO": "PRTB",
    "PARTIDO NOVO": "NOVO", "PARTIDO DA MOBILIZACAO NACIONAL": "MOBILIZA", "MOBILIZACAO NACIONAL": "MOBILIZA",
    "PARTIDO DA MULHER BRASILEIRA": "PMB", "AGIR": "AGIR", "PARTIDO SOCIALISTA BRASILEIRO": "PSB",
    "PARTIDO VERDE": "PV", "UNIAO BRASIL": "UNIÃO", "PARTIDO DA SOCIAL DEMOCRACIA BRASILEIRA": "PSDB",
    "PATRIOTA": "PATRIOTA", "PARTIDO SOCIAL DEMOCRATICO": "PSD", "PARTIDO COMUNISTA DO BRASIL": "PCdoB",
    "AVANTE": "AVANTE", "SOLIDARIEDADE": "SOLIDARIEDADE", "UNIDADE POPULAR": "UP",
    "PARTIDO REPUBLICANO DA ORDEM SOCIAL": "PROS", "PARTIDO SOCIALISMO E LIBERDADE": "PSOL",
    "PARTIDO RENOVACAO DEMOCRATICA": "PRD", "PARTIDO SOCIALISTA DOS TRABALHADORES UNIFICADO": "PSTU",
    "PARTIDO DA CAUSA OPERARIA": "PCO",
}
# partidos que às vezes não têm candidato a deputado (então não aparecem nos votos de legenda)
SIGLAS_POR_NUMERO = {"16": "PSTU", "21": "PCB", "29": "PCO"}


def iniciais(nome):
    partes = [p for p in str(nome).split() if p[:1].isalpha()]
    if not partes:
        return "?"
    return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()


def faixa_contexto(itens):
    """Faixa com borda azul: 'Eleição Geral · 2026 · Deputado Federal · Bahia (BA)'."""
    sep = '<span class="sep">·</span>'
    partes = ['<b class="eleicao">Eleição Geral</b>']
    for texto, destaque in itens:
        texto = html.escape(str(texto))
        partes.append(f"<b>{texto}</b>" if destaque else texto)
    st.markdown(f'<div class="faixa">{sep.join(partes)}</div>', unsafe_allow_html=True)


SELOS = {"Eleito": "", "2º turno": "turno2", "Suplente": "suplente"}


def lista_candidatos(tabela, total, aviso, fotos):
    """Lista no estilo 'ranking': foto, posição, nome, situação, partido · nº, votos, % e barra verde."""
    linhas = []
    for c in tabela.itertuples(index=False):
        pct = c.Votos / total * 100 if total else 0
        meta = [html.escape(c.Partido)] if c.Partido else []
        meta.append(f"nº {html.escape(c.Número)}")
        meta = " · ".join(meta)
        if c.Situação in SELOS:
            meta = f'<span class="selo {SELOS[c.Situação]}">{c.Situação}</span>· {meta}'
        foto = fotos.get(c.Número)
        foto = (f'<img src="data:image/jpeg;base64,{foto}" alt="" loading="lazy">' if foto
                else html.escape(iniciais(c.Candidato)))
        linhas.append(
            '<div class="cand">'
            f'<div class="cand-foto">{foto}</div>'
            f'<div class="cand-pos">{c.Pos}</div>'
            f'<div><div class="cand-nome">{html.escape(c.Candidato)}</div><div class="cand-meta">{meta}</div></div>'
            f'<div class="cand-votos"><b>{formatar(c.Votos)}</b><span>{formatar_pct(pct)}</span></div>'
            f'<div class="cand-barra"><span style="width:{min(pct, 100):.2f}%"></span></div>'
            "</div>"
        )
    st.markdown(
        f'<div class="lista"><div class="lista-topo">{aviso}</div>{"".join(linhas)}</div>',
        unsafe_allow_html=True,
    )


def arquivo_resumo():
    compactado = PASTA_APP / "votos_por_municipio.parquet"
    return compactado if compactado.exists() else PASTA / "votos_por_municipio.csv"


def arquivo_municipio(codigo):
    compactado = PASTA_APP / "municipios" / f"{codigo}.parquet"
    return compactado if compactado.exists() else PASTA / "municipios" / f"{codigo}.csv"


def ler_tabela(caminho):
    """Lê o arquivo compactado (Parquet) ou o CSV, sempre com todas as colunas como texto."""
    if caminho.suffix == ".parquet":
        return pd.read_parquet(caminho)   # compactar_dados.py já grava tudo como texto
    return pd.read_csv(caminho, dtype=str, keep_default_na=False)


@st.cache_data
def carregar_resumo():
    df = ler_tabela(arquivo_resumo())
    df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
    return so_nominais(df)


SITUACOES = {
    "ELEITO": "Eleito", "ELEITO POR QP": "Eleito", "ELEITO POR MEDIA": "Eleito",
    "2O TURNO": "2º turno", "2 TURNO": "2º turno", "SUPLENTE": "Suplente", "NAO ELEITO": "Não eleito",
}


@st.cache_data
def carregar_candidatos():
    """{(ano, turno, cargo, número): (sigla do partido, situação, foto em base64)} - feito pelo preparar_candidatos.py."""
    arquivo = PASTA_APP / "candidatos.parquet"
    if not arquivo.exists():
        return {}
    df = pd.read_parquet(arquivo)
    return {
        (a, t, normalizar(c), n): (p, SITUACOES.get(normalizar(s).replace("º", "O"), ""), f)
        for a, t, c, n, p, s, f in zip(
            df["ANO"], df["NR_TURNO"], df["DS_CARGO"], df["NR_CANDIDATO"],
            df["SG_PARTIDO"], df["DS_SIT_TOT_TURNO"], df["FOTO"],
        )
    }


@st.cache_data
def carregar_partidos():
    """{(ano, número do partido): sigla}, a partir dos votos de legenda dos cargos de deputado."""
    df = ler_tabela(arquivo_resumo())
    legenda = df[
        df["DS_CARGO"].str.contains("deputado", case=False, na=False)
        & (df["NR_VOTAVEL"].str.len() == 2)
        & ~df["NR_VOTAVEL"].isin(["95", "96", "97", "98"])
    ].drop_duplicates(["ANO", "NR_VOTAVEL"])
    return {
        (a, n): SIGLAS.get(normalizar(nome), str(nome).upper())
        for a, n, nome in zip(legenda["ANO"], legenda["NR_VOTAVEL"], legenda["NM_VOTAVEL"])
    }


@st.cache_data
def carregar_indice():
    df = pd.read_csv(ARQ_INDICE, dtype=str)
    return dict(zip(df["NM_MUNICIPIO"], df["CD_MUNICIPIO"]))


def segredo(nome):
    """Configuração secreta do app publicado (Streamlit Cloud > Settings > Secrets). Vazio no computador."""
    try:
        return str(st.secrets.get(nome, "")).strip()
    except Exception:   # sem arquivo de segredos
        return ""


SUPABASE_URL = segredo("SUPABASE_URL").rstrip("/")
SUPABASE_KEY = segredo("SUPABASE_KEY")
USA_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)


def supabase(metodo, parametros=None, corpo=None, cabecalhos=None):
    """Chamada à tabela de bairros no Supabase (API REST)."""
    import requests
    resposta = requests.request(
        metodo, f"{SUPABASE_URL}/rest/v1/{TABELA_BAIRROS}", params=parametros, json=corpo, timeout=30,
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", **(cabecalhos or {})},
    )
    resposta.raise_for_status()
    return resposta.json() if resposta.content else None


def ler_bairros_informados():
    """Bairros que o usuário informou (Supabase, no app publicado; senão dados/bairros_informados.csv)."""
    if USA_SUPABASE:
        linhas, inicio = [], 0
        while True:   # o Supabase devolve no máximo 1000 linhas por vez
            parte = supabase("GET", {"select": "*", "order": "cd_municipio,nr_zona,nm_local_n",
                                     "offset": inicio, "limit": 1000})
            linhas += parte
            if len(parte) < 1000:
                break
            inicio += 1000
        df = pd.DataFrame(linhas, columns=[c.lower() for c in COLS_BAIRROS]).fillna("").astype(str)
        df.columns = COLS_BAIRROS
        return df
    if not ARQ_BAIRROS.exists():
        return pd.DataFrame(columns=COLS_BAIRROS)
    df = pd.read_csv(ARQ_BAIRROS, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    for coluna in COLS_BAIRROS:
        if coluna not in df.columns:
            df[coluna] = ""
    return df[COLS_BAIRROS]


def versao_bairros():
    """Muda sempre que os bairros informados são salvos (para o cache se atualizar)."""
    if USA_SUPABASE:
        # muda quando você salva e, no máximo, a cada 5 minutos (para ver o que foi salvo em outro aparelho)
        return f"{st.session_state.get('bairros_salvos', 0)}|{int(time.time() // 300)}"
    return ARQ_BAIRROS.stat().st_mtime_ns if ARQ_BAIRROS.exists() else 0


def salvar_bairros_municipio(codigo, registros, removidos):
    """Grava os bairros de um município. registros: {(zona, nome_n): (escola, bairro)}; removidos: chaves apagadas."""
    if USA_SUPABASE:
        if registros:
            supabase(
                "POST", {"on_conflict": "cd_municipio,nr_zona,nm_local_n"},
                [{"cd_municipio": str(codigo), "nr_zona": z, "nm_local_n": n, "nm_local_votacao": nome, "bairro": b}
                 for (z, n), (nome, b) in registros.items()],
                {"Prefer": "resolution=merge-duplicates,return=minimal"},
            )
        for z, n in removidos:
            supabase("DELETE", {"cd_municipio": f"eq.{codigo}", "nr_zona": f"eq.{z}", "nm_local_n": f"eq.{n}"})
        st.session_state["bairros_salvos"] = st.session_state.get("bairros_salvos", 0) + 1
        return
    todos = ler_bairros_informados()
    outros = todos[todos["CD_MUNICIPIO"] != str(codigo)]
    novos = pd.DataFrame(
        [(str(codigo), z, n, nome, b) for (z, n), (nome, b) in registros.items()], columns=COLS_BAIRROS,
    )
    temporario = ARQ_BAIRROS.with_suffix(".tmp")
    pd.concat([outros, novos], ignore_index=True).to_csv(temporario, index=False, encoding="utf-8-sig")
    temporario.replace(ARQ_BAIRROS)


def como_categoria(df):
    """Guarda cada texto repetido uma vez só (economiza ~90% de memória nos municípios grandes)."""
    for coluna in df.columns:
        if df[coluna].dtype == object or pd.api.types.is_string_dtype(df[coluna].dtype):
            df[coluna] = df[coluna].astype("category")
    return df


def texto(df):
    """Volta as colunas 'categoria' para texto comum (usado depois de agrupar)."""
    for coluna in df.columns:
        if isinstance(df[coluna].dtype, pd.CategoricalDtype):
            df[coluna] = df[coluna].astype(str)
    return df


def agrupar(df, chaves):
    return df.groupby(chaves, as_index=False, observed=True)


@st.cache_data(max_entries=6)
def carregar_municipio(codigo, versao=0, anos=None):
    """Votos por seção do município. anos=None carrega todos; senão só os anos pedidos (bem mais leve)."""
    arquivo = arquivo_municipio(codigo)
    if arquivo.suffix == ".parquet" and anos is not None:
        df = pd.read_parquet(arquivo, filters=[("ANO", "in", list(anos))])
    else:
        df = ler_tabela(arquivo)
        if anos is not None:
            df = df[df["ANO"].isin(anos)]
    df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
    df = como_categoria(df)
    if "NM_BAIRRO" not in df.columns:
        df["NM_BAIRRO"] = ""
    df["NM_BAIRRO"] = df["NM_BAIRRO"].astype(str)
    df["BAIRRO_TSE"] = df["NM_BAIRRO"].str.strip()
    informados = ler_bairros_informados()
    informados = informados[informados["CD_MUNICIPIO"] == str(codigo)]
    if not informados.empty:
        mapa = {(z, n): b for z, n, b in zip(informados["NR_ZONA"], informados["NM_LOCAL_N"], informados["BAIRRO"])}
        nomes_n = df["NM_LOCAL_VOTACAO"].map({n: normalizar(n) for n in df["NM_LOCAL_VOTACAO"].unique()})
        do_usuario = pd.Series(
            [mapa.get(k, "") for k in zip(df["NR_ZONA"].str.lstrip("0"), nomes_n)], index=df.index
        )
        df["NM_BAIRRO"] = do_usuario.where(do_usuario.str.strip() != "", df["NM_BAIRRO"])
    df["BAIRRO"] = df["NM_BAIRRO"].where(df["NM_BAIRRO"].str.strip() != "", SEM_BAIRRO)
    df["BAIRRO_N"] = df["BAIRRO"].map({b: normalizar(b) for b in df["BAIRRO"].unique()})
    for coluna in ("NR_LATITUDE", "NR_LONGITUDE"):
        if coluna not in df.columns:
            df[coluna] = ""
    df["LAT"] = pd.to_numeric(df["NR_LATITUDE"].astype(str), errors="coerce")
    df["LON"] = pd.to_numeric(df["NR_LONGITUDE"].astype(str), errors="coerce")
    df = df.drop(columns=["NR_LATITUDE", "NR_LONGITUDE"])
    return como_categoria(so_nominais(df))


def agregar_escolas(df):
    """Uma linha por escola (zona + número do local)."""
    return texto(
        agrupar(df, ["NR_ZONA", "NR_LOCAL_VOTACAO"])
        .agg(
            NM_LOCAL_VOTACAO=("NM_LOCAL_VOTACAO", "first"),
            DS_LOCAL_VOTACAO_ENDERECO=("DS_LOCAL_VOTACAO_ENDERECO", "first"),
            BAIRRO=("BAIRRO", "first"),
            LAT=("LAT", "first"),
            LON=("LON", "first"),
            NSECOES=("NR_SECAO", "nunique"),
            VOTOS_TOTAL=("QT_VOTOS", "sum"),
        )
    )


def escolas_com_votos(universo, do_candidato):
    """Todas as escolas do 'universo', com os votos do candidato em cada uma (0 se não teve)."""
    esc = agregar_escolas(universo).drop(columns=["VOTOS_TOTAL", "NSECOES"])
    votos = texto(
        agrupar(do_candidato, ["NR_ZONA", "NR_LOCAL_VOTACAO"])["QT_VOTOS"].sum()
        .rename(columns={"QT_VOTOS": "Votos"})
    )
    esc = esc.merge(votos, on=["NR_ZONA", "NR_LOCAL_VOTACAO"], how="left")
    esc["Votos"] = esc["Votos"].fillna(0).astype(int)
    return esc


def chave_escola(esc, modo):
    zona = esc["NR_ZONA"].str.lstrip("0")
    if modo == MODO_NOME:
        return esc["NM_LOCAL_VOTACAO"].map(normalizar) + "|" + zona
    return zona + "|" + esc["NR_LOCAL_VOTACAO"].str.lstrip("0")


def preparar_para_comparar(esc, modo, sufixo):
    esc = esc.copy()
    esc["chave"] = chave_escola(esc, modo)
    esc = esc.groupby("chave", as_index=False).agg(
        **{
            f"Escola_{sufixo}": ("NM_LOCAL_VOTACAO", "first"),
            f"Zona_{sufixo}": ("NR_ZONA", "first"),
            f"Bairro_{sufixo}": ("BAIRRO", "first"),
            f"Lat_{sufixo}": ("LAT", "first"),
            f"Lon_{sufixo}": ("LON", "first"),
            f"Votos_{sufixo}": ("Votos", "sum"),
        }
    )
    return esc


# ------------------------------------------------------------------- mapa
def zoom_para(extensao):
    """Nível de zoom do mapa conforme o tamanho da área (em graus)."""
    for limite, zoom in [(0.005, 15), (0.015, 14), (0.03, 13), (0.07, 12),
                         (0.14, 11), (0.3, 10), (0.6, 9), (1.2, 8)]:
        if extensao < limite:
            return zoom
    return 7


def misturar(cor1, cor2, t):
    return [int(round(a + (b - a) * t)) for a, b in zip(cor1, cor2)]


def cor_do_ponto(valor, vmax, modo):
    """Cor e raio (em metros) do círculo: quanto maior o valor, maior e mais escuro."""
    if valor == 0:
        return [150, 150, 150], 40
    forca = (abs(valor) / vmax) ** 0.6
    raio = 60 + 340 * math.sqrt(abs(valor) / vmax)
    if modo == "diferenca":
        alvo = [33, 102, 172] if valor > 0 else [178, 24, 43]
        return misturar([222, 222, 222], alvo, forca), raio
    return misturar([254, 224, 144], [165, 0, 38], forca), raio


def montar_dica(linha):
    """Texto que aparece ao passar o mouse sobre a escola."""
    local = []
    if linha.bairro and linha.bairro != SEM_BAIRRO:
        local.append(html.escape(str(linha.bairro)))
    local.append(f"zona {html.escape(str(linha.zona))}")
    partes = [f"<b>{html.escape(str(linha.escola))}</b>", " - ".join(local)]
    if linha.endereco:
        partes.append(html.escape(str(linha.endereco)))
    partes.append(html.escape(str(linha.detalhe)))
    return "<br/>".join(partes)


def entrada_mapa(escola, bairro, zona, endereco, lat, lon, valor, detalhe):
    """Uma linha por escola, no formato que o mapa espera."""
    df = pd.DataFrame({
        "escola": escola, "bairro": bairro, "zona": zona, "endereco": endereco,
        "lat": lat, "lon": lon, "valor": valor, "detalhe": detalhe,
    }).reset_index(drop=True)
    for coluna in ["escola", "bairro", "zona", "endereco", "detalhe"]:
        df[coluna] = df[coluna].fillna("").astype(str)
    return df


def desenhar_mapa(entrada, modo="votos"):
    """Desenha um círculo por escola (tamanho e cor = valor). modo: 'votos' ou 'diferenca'."""
    pontos = entrada.dropna(subset=["lat", "lon"])
    if centro_mun is not None and not pd.isna(centro_mun[0]):
        perto = (
            ((pontos["lat"] - centro_mun[0]).abs() <= LIMITE_GRAUS)
            & ((pontos["lon"] - centro_mun[1]).abs() <= LIMITE_GRAUS)
        )
        pontos = pontos[perto]
    pontos = pontos.copy()
    sem_coordenada = len(entrada) - len(pontos)
    if pontos.empty:
        st.info("Nenhuma escola com coordenadas válidas para mostrar no mapa.")
        return

    vmax = float(pontos["valor"].abs().max()) or 1.0
    cores = [cor_do_ponto(v, vmax, modo) for v in pontos["valor"]]
    pontos["r"] = [c[0][0] for c in cores]
    pontos["g"] = [c[0][1] for c in cores]
    pontos["b"] = [c[0][2] for c in cores]
    pontos["raio"] = [c[1] for c in cores]
    pontos["tip"] = [montar_dica(linha) for linha in pontos.itertuples()]

    centro_lat, centro_lon = float(pontos["lat"].mean()), float(pontos["lon"].mean())
    extensao = max(
        float(pontos["lat"].max() - pontos["lat"].min()),
        float(pontos["lon"].max() - pontos["lon"].min()),
    )
    zoom = zoom_para(extensao)

    if modo == "diferenca":
        st.caption("Azul = ganhou votos; vermelho = perdeu votos; cinza = sem mudança. "
                   "Tamanho = tamanho da diferença. Passe o mouse sobre o círculo para ver os detalhes.")
    else:
        st.caption("Tamanho e cor = votos (maior e mais escuro = mais votos; cinza = nenhum voto). "
                   "Passe o mouse sobre o círculo para ver a escola.")
    if sem_coordenada:
        st.caption(f"{sem_coordenada} escola(s) sem coordenadas válidas no arquivo do TSE não aparecem no mapa.")

    try:
        import pydeck as pdk
    except ImportError:
        pdk = None

    if pdk is not None:
        camada = pdk.Layer(
            "ScatterplotLayer",
            data=pontos[["lat", "lon", "r", "g", "b", "raio", "tip"]],
            get_position="[lon, lat]",
            get_radius="raio",
            get_fill_color="[r, g, b, 210]",
            get_line_color=[70, 70, 70, 180],
            stroked=True,
            line_width_min_pixels=1,
            radius_min_pixels=4,
            radius_max_pixels=40,
            pickable=True,
        )
        visao = pdk.ViewState(latitude=centro_lat, longitude=centro_lon, zoom=zoom, pitch=0)
        st.pydeck_chart(pdk.Deck(
            layers=[camada],
            initial_view_state=visao,
            tooltip={"html": "{tip}", "style": {"backgroundColor": "white", "color": "#222", "fontSize": "13px"}},
        ))
    else:
        # sem pydeck: mapa simples, sem a dica ao passar o mouse (instale com: pip install pydeck)
        simples = pontos.assign(
            cor=["#%02x%02x%02x" % (r, g, b) for r, g, b in zip(pontos["r"], pontos["g"], pontos["b"])]
        )
        try:
            st.map(simples[["lat", "lon", "raio", "cor"]], latitude="lat", longitude="lon", size="raio", color="cor")
        except TypeError:
            st.map(simples[["lat", "lon"]])


# ------------------------------------------------- tela: cadastrar bairros
def tela_cadastro(indice):
    """Lista todas as escolas de um município para você informar o bairro/localidade de cada uma."""
    st.subheader("Cadastrar bairros/localidades das escolas")
    senha = segredo("SENHA_CADASTRO")
    if senha and not st.session_state.get("cadastro_liberado"):
        digitada = st.text_input("Senha para cadastrar bairros", type="password")
        if digitada and digitada == senha:
            st.session_state["cadastro_liberado"] = True
            st.rerun()
        if digitada:
            st.error("Senha incorreta.")
        st.stop()
    st.caption(
        "Aqui estão todas as escolas do município (de todos os anos). Digite o bairro/localidade na última "
        "coluna e clique em Salvar. O que você informar vale para todos os anos e tem prioridade sobre o "
        "bairro do TSE; se deixar em branco, continua valendo o do TSE. "
        + ("Fica salvo no Supabase." if USA_SUPABASE else "Fica salvo em dados/bairros_informados.csv.")
    )
    nome_mun = st.selectbox("Município da lista de escolas", sorted(indice))
    codigo = indice[nome_mun]
    if not arquivo_municipio(codigo).exists():
        st.error("Dados por seção não encontrados. Rode de novo: python preparar_dados.py")
        st.stop()

    df = carregar_municipio(codigo, versao_bairros())
    df = df.assign(
        _zona_n=df["NR_ZONA"].astype(str).str.lstrip("0"),
        _nome_n=df["NM_LOCAL_VOTACAO"].astype(str).map({n: normalizar(n) for n in df["NM_LOCAL_VOTACAO"].unique()}),
        BAIRRO_TSE=df["BAIRRO_TSE"].astype(str),
    )
    esc = agrupar(df, ["_zona_n", "_nome_n"]).agg(
        Escola=("NM_LOCAL_VOTACAO", "first"),
        Zona=("NR_ZONA", "first"),
        Endereço=("DS_LOCAL_VOTACAO_ENDERECO", "first"),
        Anos=("ANO", lambda a: ", ".join(sorted(a.unique()))),
        Seções=("NR_SECAO", "nunique"),
        **{"Bairro no TSE": ("BAIRRO_TSE", "max")},
    )
    esc = texto(esc)
    salvos = ler_bairros_informados()
    salvos = salvos[salvos["CD_MUNICIPIO"] == str(codigo)]
    do_usuario = {(z, n): b for z, n, b in zip(salvos["NR_ZONA"], salvos["NM_LOCAL_N"], salvos["BAIRRO"])}
    esc[COL_INFORMADO] = [do_usuario.get(k, "") for k in zip(esc["_zona_n"], esc["_nome_n"])]
    esc["_zona_num"] = pd.to_numeric(esc["_zona_n"], errors="coerce")
    esc = esc.sort_values(["Escola", "_zona_num"]).reset_index(drop=True)

    tem = (esc[COL_INFORMADO].str.strip() != "") | (esc["Bairro no TSE"].str.strip() != "")
    c1, c2, c3 = st.columns(3)
    c1.metric("Escolas", len(esc))
    c2.metric("Com bairro (TSE ou informado)", int(tem.sum()))
    c3.metric("Sem bairro", int((~tem).sum()))

    mostrar = st.radio(
        "Mostrar", ["Todas as escolas", "Só as sem bairro", "Só as que eu informei"], horizontal=True,
    )
    busca = st.text_input("Pesquisar escola ou endereço", placeholder="ex.: municipal")
    visao = esc
    if mostrar == "Só as sem bairro":
        visao = esc[~tem]
    elif mostrar == "Só as que eu informei":
        visao = esc[esc[COL_INFORMADO].str.strip() != ""]
    if busca.strip():
        alvo = visao["Escola"].str.cat(visao["Endereço"], sep=" ").map(normalizar)
        visao = visao[alvo.str.contains(normalizar(busca), regex=False)]
    visao = visao.reset_index(drop=True)

    colunas = ["Escola", "Zona", "Endereço", "Anos", "Seções", "Bairro no TSE", COL_INFORMADO]
    st.markdown(f"**{len(visao)} escola(s)** - preencha a última coluna")
    editado = st.data_editor(
        visao[colunas], hide_index=True, disabled=colunas[:-1],
        key=f"editor|{codigo}|{mostrar}|{busca}",
    )

    if st.button("Salvar bairros informados"):
        registros = {
            (z, n): (nome, b)
            for z, n, nome, b in zip(salvos["NR_ZONA"], salvos["NM_LOCAL_N"], salvos["NM_LOCAL_VOTACAO"], salvos["BAIRRO"])
        }
        alterados = 0
        removidos = []
        for i in range(len(visao)):
            chave = (visao.at[i, "_zona_n"], visao.at[i, "_nome_n"])
            novo = editado.at[i, COL_INFORMADO]
            novo = "" if pd.isna(novo) else " ".join(str(novo).split())
            if novo == registros.get(chave, ("", ""))[1]:
                continue
            alterados += 1
            if novo:
                registros[chave] = (visao.at[i, "Escola"], novo)
            else:
                if registros.pop(chave, None) is not None:
                    removidos.append(chave)
        if alterados == 0:
            st.info("Nada mudou desde o último salvamento.")
        else:
            salvar_bairros_municipio(codigo, registros, removidos)
            st.success(f"{alterados} escola(s) atualizada(s). Os bairros já valem na tela de votação.")

    st.download_button(
        "Baixar lista de escolas (CSV)",
        esc[colunas].to_csv(index=False).encode("utf-8-sig"),
        file_name=f"escolas_{codigo}.csv",
        mime="text/csv",
    )


# ------------------------------------------------------------------ dados
if not arquivo_resumo().exists() or not ARQ_INDICE.exists():
    st.error("Dados não encontrados. Rode antes: python baixar_dados.py e depois python preparar_dados.py")
    st.stop()

dados = carregar_resumo()
indice = carregar_indice()

tela = st.sidebar.radio("Tela", [TELA_VOTACAO, TELA_CADASTRO])
if tela == TELA_CADASTRO:
    tela_cadastro(indice)
    st.stop()

# ---------------------------------------------------------------- filtros
st.sidebar.header("Filtros")
anos = sorted(dados["ANO"].unique(), reverse=True)
ano = st.sidebar.selectbox("Ano da eleição", anos)
d = dados[dados["ANO"] == ano]

turno = st.sidebar.selectbox("Turno", sorted(d["NR_TURNO"].unique()))
d = d[d["NR_TURNO"] == turno]

cargo = st.sidebar.selectbox("Cargo", sorted(d["DS_CARGO"].unique()))
d = d[d["DS_CARGO"] == cargo]

municipio = st.sidebar.selectbox("Município", [TODOS] + sorted(d["NM_MUNICIPIO"].unique()))

ds_ano = None         # todas as linhas do município no ano escolhido
ds = None             # ano/turno/cargo escolhidos
ds_bairro = None      # ... já filtrado por bairro
escolas_f = None
escola = None
secoes = None
bairros_alvo = None   # None = sem filtro de bairro
bairro_txt = ""
escola_sel = TODAS_ESCOLAS
secao_sel = TODAS_SECOES

if municipio == TODOS:
    base = d
else:
    codigo = indice.get(municipio)
    if not arquivo_municipio(codigo).exists():
        st.error("Dados por seção não encontrados. Rode de novo: python preparar_dados.py")
        st.stop()

    ds_ano = carregar_municipio(codigo, versao_bairros(), (ano,))
    ds = ds_ano[(ds_ano["NR_TURNO"] == turno) & (ds_ano["DS_CARGO"] == cargo)]
    escolas_todas = agregar_escolas(ds)
    centro_mun = (escolas_todas["LAT"].median(), escolas_todas["LON"].median())
    tem_bairro =bool((escolas_todas["BAIRRO"] != SEM_BAIRRO).any())

    # ---- bairro / localidade (pesquisa + lista)
    if tem_bairro:
        todos_bairros = sorted(escolas_todas["BAIRRO"].unique(), key=normalizar)
        busca = st.sidebar.text_input("Pesquisar bairro/localidade", placeholder="ex.: centro")
        if busca.strip():
            lista = [b for b in todos_bairros if normalizar(busca) in normalizar(b)]
            rotulo_todos = f'Todos que contêm "{busca.strip()}" ({len(lista)})'
        else:
            lista = todos_bairros
            rotulo_todos = TODOS_BAIRROS
        bairro_sel = st.sidebar.selectbox("Bairro/localidade", [rotulo_todos] + lista)
        if busca.strip() and not lista:
            st.sidebar.warning("Nenhum bairro encontrado com esse texto.")
        if bairro_sel != rotulo_todos:
            bairros_alvo = {normalizar(bairro_sel)}
            bairro_txt = bairro_sel
        elif busca.strip():
            bairros_alvo = {normalizar(b) for b in lista}
            bairro_txt = f'bairros com "{busca.strip()}"'
    else:
        st.sidebar.info("Bairro/localidade não disponível nos dados deste município/ano.")

    def filtrar_bairro(df):
        if bairros_alvo is None:
            return df
        return df[df["BAIRRO_N"].isin(bairros_alvo)]

    ds_bairro = filtrar_bairro(ds)
    escolas_f = agregar_escolas(ds_bairro)
    escolas_f["_zona"] = pd.to_numeric(escolas_f["NR_ZONA"], errors="coerce")
    escolas_f = escolas_f.sort_values(["NM_LOCAL_VOTACAO", "_zona"]).reset_index(drop=True)

    repetido = escolas_f.duplicated(["NM_LOCAL_VOTACAO", "NR_ZONA"], keep=False)
    rotulos = []
    for i, e in escolas_f.iterrows():
        sufixo = f", local {e['NR_LOCAL_VOTACAO']}" if repetido[i] else ""
        com_bairro = f" - {e['BAIRRO']}" if tem_bairro and e["BAIRRO"] != SEM_BAIRRO else ""
        rotulos.append(f"{e['NM_LOCAL_VOTACAO']}{com_bairro} (zona {e['NR_ZONA']}{sufixo})")
    escolas_f["rotulo"] = rotulos

    escola_sel = st.sidebar.selectbox("Escola", [TODAS_ESCOLAS] + escolas_f["rotulo"].tolist())

    base = ds_bairro
    if escola_sel != TODAS_ESCOLAS:
        escola = escolas_f[escolas_f["rotulo"] == escola_sel].iloc[0]
        base = ds_bairro[
            (ds_bairro["NR_ZONA"] == escola["NR_ZONA"])
            & (ds_bairro["NR_LOCAL_VOTACAO"] == escola["NR_LOCAL_VOTACAO"])
        ]
        secoes = texto(agrupar(base, "NR_SECAO")["QT_VOTOS"].sum())
        secoes["_n"] = pd.to_numeric(secoes["NR_SECAO"], errors="coerce")
        secoes = secoes.sort_values("_n").reset_index(drop=True)

        secao_sel = st.sidebar.selectbox("Seção", [TODAS_SECOES] + secoes["NR_SECAO"].tolist())
        if secao_sel != TODAS_SECOES:
            base = base[base["NR_SECAO"] == secao_sel]

# ------------------------------------------------- votos por candidato (nominal)
resultado = texto(
    agrupar(base, ["NR_VOTAVEL", "NM_VOTAVEL"])["QT_VOTOS"].sum()
    .sort_values("QT_VOTOS", ascending=False)
    .reset_index(drop=True)
)
if resultado.empty:
    st.warning("Nenhum voto encontrado com esses filtros.")
    st.stop()

total = int(resultado["QT_VOTOS"].sum())
resultado["% dos votos nominais"] = (resultado["QT_VOTOS"] / total * 100).round(2) if total else 0
partidos = carregar_partidos()
cadastro = carregar_candidatos()
cargo_n = normalizar(cargo)
do_cadastro = [
    cadastro.get((ano, turno, cargo_n, n)) or cadastro.get((ano, "1", cargo_n, n)) or ("", "", "")
    for n in resultado["NR_VOTAVEL"]
]
fotos = {n: c[2] for n, c in zip(resultado["NR_VOTAVEL"], do_cadastro) if c[2]}
resultado.insert(0, "Pos.", range(1, len(resultado) + 1))
resultado.insert(3, "Partido", [
    c[0] or partidos.get((ano, str(n)[:2])) or SIGLAS_POR_NUMERO.get(str(n)[:2], "")
    for n, c in zip(resultado["NR_VOTAVEL"], do_cadastro)
])
resultado.insert(4, "Situação", [c[1] for c in do_cadastro])
resultado = resultado.rename(
    columns={"NR_VOTAVEL": "Número", "NM_VOTAVEL": "Candidato", "QT_VOTOS": "Votos"}
)

contexto = [(ano, False), (cargo, True), ("Bahia (BA)" if municipio == TODOS else municipio, municipio != TODOS)]
if bairro_txt:
    contexto.append((bairro_txt, False))
if escola is not None:
    contexto.append((escola["NM_LOCAL_VOTACAO"], False))
if secao_sel != TODAS_SECOES:
    contexto.append((f"seção {secao_sel}", False))
contexto.append((f"{turno}º turno", False))
faixa_contexto(contexto)

metricas = [("Total de votos nominais", formatar(total)), ("Candidatos", len(resultado))]
if escolas_f is not None:
    metricas.append(("Escolas", len(escolas_f)))
if escola is not None:
    metricas.append(("Seções da escola", len(secoes)))
for coluna, (rotulo, valor) in zip(st.columns(len(metricas)), metricas):
    coluna.metric(rotulo, valor)

# -------------------------------------- escolas encontradas / dados da escola
if escola is not None:
    st.markdown(f"**Escola:** {escola['NM_LOCAL_VOTACAO']} (zona {escola['NR_ZONA']})")
    st.markdown(f"**Bairro/localidade:** {escola['BAIRRO']}")
    if escola["DS_LOCAL_VOTACAO_ENDERECO"]:
        st.markdown(f"**Endereço:** {escola['DS_LOCAL_VOTACAO_ENDERECO']}")
    with st.expander("Seções desta escola", expanded=True):
        tabela_secoes = secoes[["NR_SECAO", "QT_VOTOS"]].rename(
            columns={"NR_SECAO": "Seção", "QT_VOTOS": "Votos nominais"}
        )
        st.dataframe(tabela_secoes, hide_index=True)
elif escolas_f is not None and bairros_alvo is not None:
    with st.expander(f"Escolas encontradas ({len(escolas_f)})", expanded=True):
        lista_escolas = escolas_f.sort_values(["BAIRRO", "NM_LOCAL_VOTACAO"])[
            ["NM_LOCAL_VOTACAO", "BAIRRO", "NR_ZONA", "DS_LOCAL_VOTACAO_ENDERECO", "NSECOES", "VOTOS_TOTAL"]
        ].rename(columns={
            "NM_LOCAL_VOTACAO": "Escola", "BAIRRO": "Bairro/localidade", "NR_ZONA": "Zona",
            "DS_LOCAL_VOTACAO_ENDERECO": "Endereço", "NSECOES": "Seções", "VOTOS_TOTAL": "Votos nominais",
        })
        st.dataframe(lista_escolas, hide_index=True)

# ------------------------------------------------------------ mapa das escolas
if ds is not None:
    with st.expander("Mapa das escolas", expanded=True):
        esc_mapa = agregar_escolas(base)
        desenhar_mapa(entrada_mapa(
            esc_mapa["NM_LOCAL_VOTACAO"], esc_mapa["BAIRRO"], esc_mapa["NR_ZONA"],
            esc_mapa["DS_LOCAL_VOTACAO_ENDERECO"], esc_mapa["LAT"], esc_mapa["LON"],
            esc_mapa["VOTOS_TOTAL"],
            "Votos nominais: " + esc_mapa["VOTOS_TOTAL"].map(formatar)
            + " | seções: " + esc_mapa["NSECOES"].astype(str),
        ))

# ------------------------------------------------------ ranking de candidatos
chave = f"tabela|{ano}|{turno}|{cargo}|{municipio}|{bairro_txt}|{escola_sel}|{secao_sel}"
MAIS_VOTADOS, ALFABETICA, TODOS_PARTIDOS = "Mais votados", "A–Z", "Todos os partidos"

with st.form("filtro_candidatos", border=False):
    f1, f2 = st.columns([8, 1], vertical_alignment="bottom")
    texto_filtro = f1.text_input(
        "Filtrar por nome ou partido", placeholder="Filtrar por nome ou partido", label_visibility="collapsed",
    )
    f2.form_submit_button("Filtrar", use_container_width=True)
o1, o2, _ = st.columns([2, 2, 6], vertical_alignment="center")
ordem_lista = o1.segmented_control(
    "Ordem", [MAIS_VOTADOS, ALFABETICA], default=MAIS_VOTADOS, label_visibility="collapsed",
) or MAIS_VOTADOS
lista_partidos = sorted(p for p in resultado["Partido"].unique() if p)
partido_sel = o2.selectbox("Partido", [TODOS_PARTIDOS] + lista_partidos, label_visibility="collapsed")

visivel = resultado
if texto_filtro.strip():
    alvo = (visivel["Candidato"] + " " + visivel["Partido"] + " " + visivel["Número"] + " " + visivel["Situação"]).map(normalizar)
    visivel = visivel[alvo.str.contains(normalizar(texto_filtro), regex=False)]
if partido_sel != TODOS_PARTIDOS:
    visivel = visivel[visivel["Partido"] == partido_sel]
if ordem_lista == ALFABETICA:
    visivel = visivel.sort_values("Candidato", key=lambda s: s.map(normalizar))
visivel = visivel.reset_index(drop=True)

if visivel.empty:
    st.info("Nenhum candidato encontrado com esse filtro.")
else:
    qtd_chave = f"qtd|{chave}|{texto_filtro}|{partido_sel}|{ordem_lista}"
    qtd = st.session_state.get(qtd_chave, 10)
    aviso = (
        "Escolha um <b>município</b> na barra lateral para ver a votação de cada candidato <b>por escola</b>."
        if ds is None else
        "Para ver a votação de um candidato <b>por escola</b>, clique nele na <b>tabela completa</b> abaixo."
    )
    lista_candidatos(
        visivel.head(qtd)[["Pos.", "Candidato", "Número", "Partido", "Situação", "Votos"]].rename(columns={"Pos.": "Pos"}),
        total, aviso, fotos,
    )
    if len(visivel) > qtd:
        if st.button(f"Mostrar mais ({len(visivel) - qtd} restantes)", key=f"mais|{qtd_chave}"):
            st.session_state[qtd_chave] = qtd + 20
            st.rerun()

candidato = None
if ds is None:
    st.markdown("**Tabela completa**")
    st.dataframe(visivel, hide_index=True)
elif not visivel.empty:
    st.markdown("**Tabela completa** - clique em um candidato para ver a votação dele por escola")
    chave_tabela = f"{chave}|{texto_filtro}|{partido_sel}|{ordem_lista}"
    try:
        evento = st.dataframe(
            visivel, hide_index=True,
            on_select="rerun", selection_mode="single-row", key=chave_tabela,
        )
        linhas = evento.selection.rows
        if linhas:
            candidato = visivel.iloc[linhas[0]]
    except TypeError:
        # Streamlit antigo, sem clique na tabela: usa uma lista de escolha
        st.dataframe(visivel, hide_index=True)
        opcoes = ["(nenhum)"] + (visivel["Número"] + " - " + visivel["Candidato"]).tolist()
        escolhido = st.selectbox("Candidato", opcoes, key=f"cand|{chave_tabela}")
        if escolhido != "(nenhum)":
            candidato = visivel.iloc[opcoes.index(escolhido) - 1]

# ------------------------------------------ votação do candidato por escola
if candidato is not None:
    numero = candidato["Número"]
    nome = candidato["Candidato"]
    do_candidato = ds_bairro[ds_bairro["NR_VOTAVEL"] == numero]

    por_escola = texto(
        agrupar(do_candidato, ["NR_ZONA", "NR_LOCAL_VOTACAO"])
        .agg(
            Escola=("NM_LOCAL_VOTACAO", "first"),
            **{
                "Bairro/localidade": ("BAIRRO", "first"),
                "Endereço": ("DS_LOCAL_VOTACAO_ENDERECO", "first"),
                "Votos": ("QT_VOTOS", "sum"),
                "Seções com votos": ("NR_SECAO", "nunique"),
            },
        )
        .sort_values("Votos", ascending=False)
        .reset_index(drop=True)
    )
    total_cand = int(por_escola["Votos"].sum())
    por_escola["% dos votos do candidato"] = (
        (por_escola["Votos"] / total_cand * 100).round(2) if total_cand else 0
    )
    por_escola.insert(0, "Pos.", range(1, len(por_escola) + 1))
    por_escola = por_escola.rename(columns={"NR_ZONA": "Zona"})[
        ["Pos.", "Escola", "Bairro/localidade", "Zona", "Endereço", "Votos",
         "% dos votos do candidato", "Seções com votos"]
    ]

    st.divider()
    escopo = f" - {bairro_txt}" if bairro_txt else ""
    st.subheader(f"Votação de {nome} ({numero}) por escola - {municipio}{escopo} - {ano}")
    st.metric("Votos do candidato nesta seleção", formatar(total_cand))

    grafico = por_escola.head(15).copy()
    grafico["Rótulo"] = grafico["Escola"] + " (zona " + grafico["Zona"] + ")"
    st.markdown("**15 escolas com mais votos**")
    st.bar_chart(grafico.set_index("Rótulo")["Votos"])

    st.markdown("**Todas as escolas, da maior para a menor votação**")
    st.dataframe(por_escola, hide_index=True)
    st.download_button(
        "Baixar lista por escola (CSV)",
        por_escola.to_csv(index=False).encode("utf-8"),
        file_name=f"votos_{ano}_{numero}_por_escola.csv",
        mime="text/csv",
    )

    st.markdown("**Mapa das escolas deste candidato**")
    esc_c = escolas_com_votos(ds_bairro, do_candidato)
    pct_c = (esc_c["Votos"] / total_cand * 100).round(2) if total_cand else esc_c["Votos"] * 0.0
    desenhar_mapa(entrada_mapa(
        esc_c["NM_LOCAL_VOTACAO"], esc_c["BAIRRO"], esc_c["NR_ZONA"],
        esc_c["DS_LOCAL_VOTACAO_ENDERECO"], esc_c["LAT"], esc_c["LON"], esc_c["Votos"],
        nome + ": " + esc_c["Votos"].map(formatar) + " votos (" + pct_c.astype(str) + "% dos votos dele)",
    ))

    # ---------------------------------------------- comparação entre anos
    outros_anos = [a for a in anos if a != ano]
    st.divider()
    st.subheader(f"Comparar {nome} entre anos")
    if not outros_anos:
        st.info("Só há dados de um ano. Rode baixar_dados.py e preparar_dados.py para incluir outro ano.")
    else:
        escolha_ano = st.radio(
            "Comparar com o ano", [NAO_COMPARAR] + outros_anos, index=1,
            horizontal=True, key=f"cmp_ano|{ano}",
        )
        if escolha_ano != NAO_COMPARAR:
            ano_b = escolha_ano
            dsb = carregar_municipio(codigo, versao_bairros(), (ano_b,))
            dsb = dsb[dsb["NR_TURNO"] == turno]
            if dsb.empty:
                st.info(f"Não há dados de {ano_b} no {turno}º turno para este município.")
            else:
                # candidato correspondente no outro ano (mesmo nome de urna), qualquer cargo
                cands_b = texto(
                    agrupar(dsb, ["DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL"])["QT_VOTOS"].sum()
                    .sort_values(["DS_CARGO", "QT_VOTOS"], ascending=[True, False])
                    .reset_index(drop=True)
                )
                cands_b["rotulo"] = (
                    cands_b["NR_VOTAVEL"] + " - " + cands_b["NM_VOTAVEL"] + " (" + cands_b["DS_CARGO"] + ")"
                )
                cands_b["_nome"] = cands_b["NM_VOTAVEL"].map(normalizar)
                iguais = cands_b[cands_b["_nome"] == normalizar(nome)]
                padrao = None
                if not iguais.empty:
                    mesmo_cargo = iguais[iguais["DS_CARGO"] == cargo]
                    padrao = (mesmo_cargo if not mesmo_cargo.empty else iguais).iloc[0]["rotulo"]
                else:
                    st.info(
                        f"Não achei {nome} em {ano_b} neste município (o nome de urna pode ter mudado, "
                        "ou ele não teve votos aqui). Escolha o candidato correspondente na lista."
                    )
                opcoes_b = [ESCOLHER] + cands_b["rotulo"].tolist()
                escolhido_b = st.selectbox(
                    f"Candidato em {ano_b} que corresponde a {nome}", opcoes_b,
                    index=opcoes_b.index(padrao) if padrao else 0,
                    key=f"par|{ano}|{ano_b}|{turno}|{cargo}|{municipio}|{numero}",
                )
                modo = st.radio(
                    "Parear escolas pelo", [MODO_NOME, MODO_NUMERO], horizontal=True, key="modo_pareamento",
                )
                st.caption(
                    "As escolas são comparadas entre os anos pelo critério acima. Se muitas aparecerem "
                    "em só um dos anos, troque o critério (o TSE pode ter mudado nome ou número do local)."
                )

                if escolhido_b != ESCOLHER:
                    linha_b = cands_b[cands_b["rotulo"] == escolhido_b].iloc[0]
                    dsb_cargo = filtrar_bairro(dsb[dsb["DS_CARGO"] == linha_b["DS_CARGO"]])
                    do_b = dsb_cargo[dsb_cargo["NR_VOTAVEL"] == linha_b["NR_VOTAVEL"]]

                    a = preparar_para_comparar(escolas_com_votos(ds_bairro, do_candidato), modo, "a")
                    b = preparar_para_comparar(escolas_com_votos(dsb_cargo, do_b), modo, "b")
                    comp = a.merge(b, on="chave", how="outer", indicator=True)
                    comp["Escola"] = comp["Escola_a"].fillna(comp["Escola_b"])
                    comp["Zona"] = comp["Zona_a"].fillna(comp["Zona_b"])
                    comp["Bairro/localidade"] = comp["Bairro_a"].fillna(comp["Bairro_b"])
                    comp["LAT"] = comp["Lat_a"].fillna(comp["Lat_b"])
                    comp["LON"] = comp["Lon_a"].fillna(comp["Lon_b"])
                    comp["Votos_a"] = comp["Votos_a"].fillna(0).astype(int)
                    comp["Votos_b"] = comp["Votos_b"].fillna(0).astype(int)
                    comp["Situação"] = (
                        comp["_merge"].astype(str)
                        .map({"both": "Nos dois anos", "left_only": f"Só em {ano}", "right_only": f"Só em {ano_b}"})
                    )

                    antigo, novo = sorted([ano, ano_b])
                    col_antigo = "Votos_a" if ano == antigo else "Votos_b"
                    col_novo = "Votos_b" if ano == antigo else "Votos_a"
                    v_ant, v_nov = f"Votos {antigo}", f"Votos {novo}"
                    comp[v_ant] = comp[col_antigo]
                    comp[v_nov] = comp[col_novo]
                    comp["Diferença"] = comp[v_nov] - comp[v_ant]
                    comp["Variação (%)"] = (
                        comp["Diferença"] / comp[v_ant].where(comp[v_ant] > 0) * 100
                    ).round(1)

                    tot_ant, tot_nov = int(comp[v_ant].sum()), int(comp[v_nov].sum())
                    c1, c2, c3 = st.columns(3)
                    c1.metric(v_ant, formatar(tot_ant))
                    c2.metric(v_nov, formatar(tot_nov))
                    c3.metric("Diferença", f"{tot_nov - tot_ant:+,}".replace(",", "."))

                    ordem = st.selectbox(
                        "Ordenar por", [v_nov, v_ant, "Maior ganho", "Maior perda"],
                        key=f"ordem|{ano}|{ano_b}|{numero}",
                    )
                    if ordem == "Maior ganho":
                        comp = comp.sort_values("Diferença", ascending=False)
                    elif ordem == "Maior perda":
                        comp = comp.sort_values("Diferença", ascending=True)
                    else:
                        comp = comp.sort_values(ordem, ascending=False)
                    comp = comp.reset_index(drop=True)

                    tabela_comp = comp[
                        ["Escola", "Bairro/localidade", "Zona", v_ant, v_nov, "Diferença", "Variação (%)", "Situação"]
                    ]
                    st.markdown(f"**Votação por escola: {antigo} x {novo}**")
                    st.dataframe(tabela_comp, hide_index=True)

                    sem_par = int((comp["Situação"] != "Nos dois anos").sum())
                    if sem_par:
                        st.caption(
                            f"{sem_par} escola(s) existem em só um dos anos (coluna Situação). "
                            "Pode ser escola nova, desativada ou com nome/número alterado."
                        )

                    maiores = comp.reindex(comp["Diferença"].abs().sort_values(ascending=False).index).head(15)
                    if not maiores.empty:
                        maiores = maiores.assign(Rótulo=maiores["Escola"] + " (zona " + maiores["Zona"] + ")")
                        st.markdown(f"**15 maiores diferenças ({novo} menos {antigo})**")
                        st.bar_chart(maiores.set_index("Rótulo")["Diferença"])

                    st.markdown(f"**Mapa da diferença ({novo} menos {antigo})**")
                    texto_dif = comp["Diferença"].map(lambda x: f"{x:+d}")
                    desenhar_mapa(
                        entrada_mapa(
                            comp["Escola"], comp["Bairro/localidade"], comp["Zona"], "",
                            comp["LAT"], comp["LON"], comp["Diferença"],
                            f"{antigo}: " + comp[v_ant].map(formatar) + " | "
                            + f"{novo}: " + comp[v_nov].map(formatar) + " | diferença: " + texto_dif,
                        ),
                        modo="diferenca",
                    )

                    st.download_button(
                        "Baixar comparação (CSV)",
                        tabela_comp.to_csv(index=False).encode("utf-8"),
                        file_name=f"comparacao_{antigo}_{novo}_{numero}.csv",
                        mime="text/csv",
                    )

st.download_button(
    "Baixar tabela de candidatos (CSV)",
    resultado.to_csv(index=False).encode("utf-8"),
    file_name="resultado.csv",
    mime="text/csv",
)
