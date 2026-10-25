"""
Passo 4b: o app, com bairro/localidade e comparação entre anos (2022 x 2026).
Bahia. Fonte: Portal de Dados Abertos do TSE.

Para rodar:
    streamlit run app.py

Sempre mostra a votação NOMINAL: sem votos brancos, nulos e de legenda.
"""

import base64
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
ROTA_CADASTRO = "cadastrobairro"   # o cadastro de bairros só abre pelo endereço .../cadastrobairro
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


def _pagina_votacao():
    pass


def _pagina_cadastro():
    pass


# duas páginas sem menu de navegação: a votação (endereço principal) e o cadastro de bairros (/cadastrobairro)
pagina = st.navigation(
    [st.Page(_pagina_votacao, title="Eleições - Bahia", default=True),
     st.Page(_pagina_cadastro, title="Cadastrar bairros - Eleições Bahia", url_path=ROTA_CADASTRO)],
    position="hidden",
)
pagina.run()
EH_CADASTRO = pagina.url_path == ROTA_CADASTRO

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
/* ícones do Streamlit (setas do menu lateral etc.) usam uma fonte própria; sem isto aparece o nome do ícone */
[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }
/* botão de abrir o menu lateral (quando está fechado) mais visível */
[data-testid="stExpandSidebarButton"] {
  background: var(--cartao); border: 1px solid var(--borda); border-radius: 10px;
  width: 38px !important; height: 38px !important; color: var(--texto);
}
[data-testid="stExpandSidebarButton"]:hover { background: var(--faixa); }
h1, h2, h3 { font-family: 'Jost', system-ui, sans-serif !important; font-weight: 600 !important; color: var(--texto); }
[data-testid="stSidebar"] { background: #ebe7de; border-right: 1px solid var(--borda); }

/* esconde os itens da barra do topo (Stop, Share, favoritar, editar, GitHub, menu);
   a barra em si fica, porque o botão de reabrir o menu lateral está dentro dela */
[data-testid="stToolbarActions"], [data-testid="stStatusWidget"], [data-testid="stAppDeployButton"],
[data-testid="stMainMenu"], [data-testid="stDecoration"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }

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
.cand.clicavel { cursor: pointer; margin: 0 -16px; padding-left: 16px; padding-right: 16px; }
.cand.clicavel:hover, .cand.clicavel:focus-visible { background: #f1ede4; outline: none; }
.cand.sel { background: #ece5d8; border-bottom-color: transparent; }
.cand-abrir { color: var(--azul); font-weight: 500; white-space: nowrap; }
.lista.lista-b { margin-top: 6px; }
.partido-total {
  display: inline-block; padding: 7px 14px; border-radius: 10px; background: var(--faixa);
  border: 1px solid var(--borda); border-left: 3px solid var(--verde); color: var(--texto); font-size: .95rem;
}
.partido-total .sep { color: var(--suave); margin: 0 6px; }

/* trajetória do candidato: uma barra por eleição */
.traj-linha {
  display: grid; grid-template-columns: 150px 1fr 90px; column-gap: 14px; align-items: center;
  padding: 8px 0; border-bottom: 1px solid var(--borda);
}
.traj-linha:last-child { border-bottom: 0; }
.traj-ano b { display: block; font-size: 1.05rem; color: var(--texto); }
.traj-ano span { display: block; font-weight: 600; font-size: .9rem; }
.traj-ano small { display: block; color: var(--suave); font-size: .8rem; line-height: 1.3; }
.traj-trilho { height: 22px; background: var(--trilho); border-radius: 7px; overflow: hidden; }
.traj-trilho span { display: block; height: 100%; border-radius: 7px; min-width: 3px; }
.traj-votos { text-align: right; }
.traj-votos b { display: block; font-size: 1.05rem; color: var(--texto); }
.traj-votos span { color: var(--suave); font-size: .85rem; }
.traj-votos span.eleito { color: var(--verde); font-weight: 600; }

/* comparativo entre candidatos */
.cmp-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 12px; }
.cmp-chip {
  display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; border-radius: 999px;
  background: var(--cartao); border: 1px solid var(--borda); font-size: .9rem; color: var(--texto);
}
.cmp-chip b { font-weight: 600; }
.cmp-chip i, .cmp-tab th i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; flex: none; }
.cmp-tab {
  max-height: 560px; overflow: auto; background: var(--cartao); border: 1px solid var(--borda); border-radius: 14px;
}
.cmp-tab table { width: 100%; border-collapse: collapse; font-size: .92rem; }
.cmp-tab th, .cmp-tab td { padding: 9px 14px; border-bottom: 1px solid var(--borda); text-align: right; }
.cmp-tab th:first-child, .cmp-tab td:first-child { text-align: left; }
.cmp-tab thead th {
  position: sticky; top: 0; z-index: 1; background: #f4f1ea; vertical-align: bottom;
  font-size: .78rem; text-transform: uppercase; letter-spacing: .02em; color: var(--suave);
}
.cmp-tab thead th span { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; color: var(--texto); }
.cmp-tab small { display: block; color: var(--suave); font-size: .78rem; text-transform: none; letter-spacing: 0; font-weight: 400; }
.cmp-tab td.maior { font-weight: 700; }
.st-key-cmp_escolha [data-testid="stMultiSelectTagsContainer"] > span > span:nth-of-type(1) { background: #16a085 !important; }
.st-key-cmp_escolha [data-testid="stMultiSelectTagsContainer"] > span > span:nth-of-type(2) { background: #2471a3 !important; }
.st-key-cmp_escolha [data-testid="stMultiSelectTagsContainer"] > span > span:nth-of-type(3) { background: #d68910 !important; }
.st-key-cmp_escolha [data-testid="stMultiSelectTagsContainer"] > span > span:nth-of-type(4) { background: #7d3c98 !important; }
.st-key-cmp_mun_escolha [data-testid="stMultiSelectTagsContainer"] > span > span:nth-of-type(1) { background: #16a085 !important; }
.st-key-cmp_mun_escolha [data-testid="stMultiSelectTagsContainer"] > span > span:nth-of-type(2) { background: #2471a3 !important; }
.st-key-cmp_mun_escolha [data-testid="stMultiSelectTagsContainer"] > span > span:nth-of-type(3) { background: #d68910 !important; }
.st-key-cmp_mun_escolha [data-testid="stMultiSelectTagsContainer"] > span > span:nth-of-type(4) { background: #7d3c98 !important; }
.cmp-tab tfoot td { position: sticky; bottom: 0; background: #f4f1ea; font-weight: 600; border-bottom: 0; }
@media (max-width: 640px) {
  .cand { grid-template-columns: 40px 22px 1fr auto; column-gap: 8px; }
  .cand-foto { width: 40px; height: 52px; font-size: .9rem; }
  .cand-nome { font-size: 1rem; }
  .cand-meta { margin-top: 6px; }
  .traj-linha { grid-template-columns: 1fr auto; row-gap: 6px; }
  .traj-trilho { grid-column: 1 / -1; grid-row: 2; height: 16px; }
  .block-container { padding: 3.2rem .9rem 2rem !important; }
  h1 { font-size: 1.7rem !important; }
  [data-testid="stMetric"] { padding: 10px 14px; }
  [data-testid="stMetricValue"] { font-size: 1.5rem; }
  .faixa { font-size: .88rem; line-height: 1.6; }
}
</style>
"""
st.markdown(ESTILO, unsafe_allow_html=True)



def eh_celular():
    """Celular: os filtros vão para o topo da página (lá o menu lateral fica escondido atrás de um botão).
    Para forçar, acrescente ?celular=1 (ou ?celular=0) no endereço."""
    forcado = st.query_params.get("celular")
    if forcado in ("0", "1"):
        return forcado == "1"
    try:
        navegador = st.context.headers.get("User-Agent", "") or ""
    except Exception:
        return False
    return any(marca in navegador for marca in ("Mobi", "Android", "iPhone", "iPod"))


CELULAR = eh_celular()

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
    proporcional = df["DS_CARGO"].str.contains("deputado|vereador", case=False, na=False, regex=True)
    mascara &= ~(proporcional & (numero.str.len() <= 2))  # legenda = número do partido (2 dígitos)
    return df[mascara]


# números que podem ser voto de legenda (número do partido); 95 a 98 são branco/nulo
NUMEROS_LEGENDA = [str(n) for n in range(10, 100) if n not in (95, 96, 97, 98)]


def so_legenda(df):
    """Só os votos de legenda (no número do partido), que existem para deputado e vereador."""
    proporcional = df["DS_CARGO"].str.contains("deputado|vereador", case=False, na=False, regex=True)
    return df[proporcional & df["NR_VOTAVEL"].astype(str).isin(NUMEROS_LEGENDA)]


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
# partidos que às vezes não têm candidato a deputado/vereador (então não aparecem nos votos de legenda)
SIGLAS_POR_NUMERO = {"16": "PSTU", "21": "PCB", "29": "PCO"}


def iniciais(nome):
    partes = [p for p in str(nome).split() if p[:1].isalpha()]
    if not partes:
        return "?"
    return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()


CARGOS_MUNICIPAIS = {"PREFEITO", "VEREADOR"}


def eh_municipal(cargo):
    return normalizar(cargo) in CARGOS_MUNICIPAIS


def faixa_contexto(itens, tipo):
    """Faixa com borda azul: 'Eleição Geral · 2026 · Deputado Federal · Bahia (BA)'."""
    sep = '<span class="sep">·</span>'
    partes = [f'<b class="eleicao">{tipo}</b>']
    for texto, destaque in itens:
        texto = html.escape(str(texto))
        partes.append(f"<b>{texto}</b>" if destaque else texto)
    st.markdown(f'<div class="faixa">{sep.join(partes)}</div>', unsafe_allow_html=True)


SELOS = {"Eleito": "", "2º turno": "turno2", "Suplente": "suplente"}


MINIMO_BUSCA = 3   # o filtro de candidatos começa a valer a partir de 3 letras

# lista de candidatos clicável: cada cartão avisa o Python qual número foi clicado
_LISTA_JS = """
export default function(component) {
  const { data, parentElement, setTriggerValue } = component;
  let caixa = parentElement.querySelector('.lista-comp');
  if (!caixa) {
    caixa = document.createElement('div');
    caixa.className = 'lista-comp';
    parentElement.appendChild(caixa);
    const abrir = (alvo) => {
      const cartao = alvo.closest('.cand[data-num]');
      if (cartao) caixa.enviar(cartao.dataset.num);
    };
    caixa.addEventListener('click', (e) => abrir(e.target));
    caixa.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); abrir(e.target); }
    });
  }
  // o horário vai junto para dois cliques seguidos no mesmo cartão contarem como dois cliques
  caixa.enviar = (num) => setTriggerValue('clique', num + '|' + Date.now());
  caixa.innerHTML = data.html;
}
"""
_LISTA = st.components.v2.component("lista_candidatos", js=_LISTA_JS, isolate_styles=False)

# campo de busca com autocomplete: filtra enquanto digita (a partir de MINIMO_BUSCA letras) e sugere nomes
_BUSCA_CSS = """
.ac { position: relative; font-family: inherit; }
.ac-campo {
  width: 100%; box-sizing: border-box; padding: 12px 14px; font: inherit; font-size: 1.05rem;
  color: var(--texto, #2a2723); background: var(--cartao, #faf9f5);
  border: 1px solid var(--borda, #e3ded3); border-radius: 12px; outline: none;
}
.ac-campo:focus { border-color: var(--azul, #2456a6); }
.ac-lista {
  position: absolute; z-index: 1000; left: 0; right: 0; top: calc(100% + 4px); margin: 0; padding: 4px;
  list-style: none; background: #fff; border: 1px solid var(--borda, #e3ded3); border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, .12); max-height: 340px; overflow-y: auto;
}
.ac-lista li {
  display: flex; justify-content: space-between; gap: 12px; padding: 8px 10px; border-radius: 8px;
  cursor: pointer; color: var(--texto, #2a2723);
}
.ac-lista li small { color: var(--suave, #6b665d); white-space: nowrap; }
.ac-lista li.ativo, .ac-lista li:hover { background: var(--faixa, #ebe3d7); }
.ac-dica { color: var(--suave, #6b665d); font-size: .82rem; margin: 4px 2px 0; min-height: 1em; }
"""
_BUSCA_JS = """
export default function(component) {
  const { data, parentElement, setStateValue } = component;
  let raiz = parentElement.querySelector('.ac');
  if (!raiz) {
    raiz = document.createElement('div');
    raiz.className = 'ac';
    raiz.innerHTML = '<input class="ac-campo" type="search" autocomplete="off" spellcheck="false" '
      + 'role="combobox" aria-autocomplete="list" aria-expanded="false">'
      + '<ul class="ac-lista" role="listbox" hidden></ul><div class="ac-dica"></div>';
    parentElement.appendChild(raiz);
    const campo = raiz.querySelector('.ac-campo');
    const lista = raiz.querySelector('.ac-lista');
    campo.value = data.valor || '';
    raiz.enviado = data.valor || '';
    raiz.ativo = -1;

    raiz.fechar = () => { lista.hidden = true; campo.setAttribute('aria-expanded', 'false'); raiz.ativo = -1; };
    raiz.enviar = () => {
      clearTimeout(raiz.espera);
      const t = campo.value.trim();
      const valor = t.length >= raiz.dados.minimo ? t : '';
      if (valor !== raiz.enviado) {
        raiz.enviado = valor;
        raiz.api.setStateValue('texto', valor);
      }
    };
    raiz.marcar = (i) => {
      const itens = lista.querySelectorAll('li');
      itens.forEach((li, j) => li.classList.toggle('ativo', j === i));
      raiz.ativo = i;
      if (itens[i]) itens[i].scrollIntoView({ block: 'nearest' });
    };
    raiz.escolher = (valor) => { campo.value = valor; raiz.fechar(); raiz.enviar(); };

    campo.addEventListener('input', () => {
      const t = campo.value.trim();
      raiz.dica();
      if (t.length < raiz.dados.minimo) raiz.fechar();
      clearTimeout(raiz.espera);
      raiz.espera = setTimeout(raiz.enviar, 300);
    });
    campo.addEventListener('keydown', (e) => {
      const n = lista.querySelectorAll('li').length;
      if (e.key === 'ArrowDown' && !lista.hidden && n) { e.preventDefault(); raiz.marcar((raiz.ativo + 1) % n); }
      else if (e.key === 'ArrowUp' && !lista.hidden && n) { e.preventDefault(); raiz.marcar((raiz.ativo - 1 + n) % n); }
      else if (e.key === 'Enter') {
        e.preventDefault();
        const li = lista.querySelectorAll('li')[raiz.ativo];
        if (!lista.hidden && li) raiz.escolher(li.dataset.valor); else { raiz.fechar(); raiz.enviar(); }
      }
      else if (e.key === 'Escape') raiz.fechar();
    });
    campo.addEventListener('blur', () => setTimeout(raiz.fechar, 150));
    lista.addEventListener('mousedown', (e) => {
      const li = e.target.closest('li');
      if (li) { e.preventDefault(); raiz.escolher(li.dataset.valor); }
    });
    raiz.dica = () => {
      const falta = raiz.dados.minimo - campo.value.trim().length;
      raiz.querySelector('.ac-dica').textContent =
        campo.value.trim() && falta > 0 ? `Digite mais ${falta} letra(s) para filtrar` : '';
    };
  }
  raiz.api = { setStateValue };
  raiz.dados = data;
  const campo = raiz.querySelector('.ac-campo');
  const lista = raiz.querySelector('.ac-lista');
  campo.placeholder = data.placeholder || '';
  raiz.dica();

  // sugestões que o Python mandou para o texto enviado (só mostra se o campo ainda tem esse texto)
  lista.innerHTML = '';
  const atual = campo.value.trim();
  const sugestoes = (data.consulta === atual) ? (data.sugestoes || []) : [];
  sugestoes.forEach((s) => {
    const li = document.createElement('li');
    li.setAttribute('role', 'option');
    li.dataset.valor = s.valor;
    const nome = document.createElement('span');
    nome.textContent = s.valor;
    const extra = document.createElement('small');
    extra.textContent = s.extra || '';
    li.append(nome, extra);
    lista.appendChild(li);
  });
  const soElaMesma = sugestoes.length === 1 && sugestoes[0].valor === atual;
  const focado = (parentElement.activeElement || document.activeElement) === campo;
  if (sugestoes.length && !soElaMesma && focado) {
    lista.hidden = false;
    campo.setAttribute('aria-expanded', 'true');
    raiz.ativo = -1;
  } else {
    raiz.fechar();
  }
}
"""
_BUSCA = st.components.v2.component("busca_candidato", css=_BUSCA_CSS, js=_BUSCA_JS)


def campo_busca(chave, sugestoes_de, placeholder):
    """Campo de busca com autocomplete. Devolve o texto do filtro ('' se tiver menos de MINIMO_BUSCA letras).
    sugestoes_de(texto) -> [{"valor": ..., "extra": ...}] é chamada com o texto atual, antes de montar o campo."""
    try:
        atual = (st.session_state.get(chave) or {}).get("texto") or ""
    except Exception:
        atual = ""
    resultado = _BUSCA(
        key=chave, default={"texto": ""}, on_texto_change=lambda: None,
        data={"valor": atual, "consulta": atual, "sugestoes": sugestoes_de(atual) if atual else [],
              "placeholder": placeholder, "minimo": MINIMO_BUSCA},
    )
    return (resultado.texto or "") if resultado is not None else atual


def cartoes_candidatos(tabela, foto_de, selecionado=None, clicavel=False):
    """Um cartão (HTML) por candidato: foto, posição, nome, situação, partido · nº, votos, % e barra verde."""
    linhas = []
    for c in tabela.itertuples(index=False):
        pct = c.Pct
        meta = [html.escape(c.Partido)] if c.Partido else []
        meta.append(f"nº {html.escape(c.Número)}")
        if getattr(c, "Município", ""):
            meta.append(html.escape(c.Município))
        meta = " · ".join(meta)
        if c.Situação in SELOS:
            meta = f'<span class="selo {SELOS[c.Situação]}">{c.Situação}</span>· {meta}'
        foto = foto_de(c.Pos)
        foto = (f'<img src="data:image/jpeg;base64,{foto}" alt="" loading="lazy">' if foto
                else html.escape(iniciais(c.Candidato)))
        if clicavel:
            aberto = c.Número == selecionado
            meta += f' · <span class="cand-abrir">{"▾ fechar" if aberto else "▸ ver por escola"}</span>'
            abre = (f'<div class="cand clicavel{" sel" if aberto else ""}" data-num="{html.escape(c.Número)}" '
                    f'role="button" tabindex="0" aria-expanded="{str(aberto).lower()}">')
        else:
            abre = '<div class="cand">'
        linhas.append(
            abre
            + f'<div class="cand-foto">{foto}</div>'
            f'<div class="cand-pos">{c.Pos}</div>'
            f'<div><div class="cand-nome">{html.escape(c.Candidato)}</div><div class="cand-meta">{meta}</div></div>'
            f'<div class="cand-votos"><b>{formatar(c.Votos)}</b><span>{formatar_pct(pct)}</span></div>'
            f'<div class="cand-barra"><span style="width:{min(pct, 100):.2f}%"></span></div>'
            "</div>"
        )
    return linhas


def lista_html(cartoes, aviso=None, classe=""):
    topo = f'<div class="lista-topo">{aviso}</div>' if aviso else ""
    return f'<div class="lista {classe}">{topo}{"".join(cartoes)}</div>'


def lista_clicavel(cartoes, aviso, chave, classe=""):
    """Mostra a lista e devolve o número do candidato clicado nesta execução (ou None)."""
    resultado = _LISTA(key=chave, data={"html": lista_html(cartoes, aviso, classe)}, on_clique_change=lambda: None)
    clique = resultado.clique if resultado is not None else None
    if not clique:
        return None
    # ignora um clique que já foi tratado (o valor traz o horário do clique)
    if st.session_state.get("_ultimo_clique") == clique:
        return None
    st.session_state["_ultimo_clique"] = clique
    return str(clique).rsplit("|", 1)[0]


def renderizar_lista_candidatos(mostrados, tabela_lista, aviso, abrir):
    """Lista clicável de candidatos: ao clicar em um, chama abrir(linha) dentro de um cartão
    (clique de novo fecha). Usa as variáveis globais da seleção atual (chave, texto_filtro, partido_sel,
    ordem_lista, qtd, foto_de), definidas antes da chamada."""
    aberto = st.session_state.get("cand_aberto", {}).get(chave)
    numeros = mostrados["Número"].tolist()
    corte = numeros.index(aberto) + 1 if aberto in numeros else len(numeros)
    cartoes = cartoes_candidatos(tabela_lista, foto_de, aberto, clicavel=True)
    base_chave = f"lista|{chave}|{texto_filtro}|{partido_sel}|{ordem_lista}|{qtd}|{aberto}"
    clicados = [lista_clicavel(cartoes[:corte], aviso, base_chave + "|a")]
    if aberto in numeros:
        with st.container(border=True):
            abrir(mostrados.iloc[corte - 1])
        if corte < len(cartoes):
            clicados.append(lista_clicavel(cartoes[corte:], None, base_chave + "|b", "lista-b"))
    clicado = next((c for c in clicados if c), None)
    if clicado:
        abertos = st.session_state.setdefault("cand_aberto", {})
        abertos[chave] = None if clicado == aberto else clicado
        st.rerun()


def arquivo_resumo():
    compactado = PASTA_APP / "votos_por_municipio.parquet"
    return compactado if compactado.exists() else PASTA / "votos_por_municipio.csv"


def arquivo_municipio(codigo):
    compactado = PASTA_APP / "municipios" / f"{codigo}.parquet"
    return compactado if compactado.exists() else PASTA / "municipios" / f"{codigo}.csv"


def arquivo_historico():
    compactado = PASTA_APP / "votos_historico_ba.parquet"
    return compactado if compactado.exists() else PASTA / "historico" / "votos_historico_ba.csv"


def arquivo_intermediario():
    compactado = PASTA_APP / "votos_intermediario_ba.parquet"
    return compactado if compactado.exists() else PASTA / "intermediario" / "votos_intermediario_ba.csv"


def arquivo_historico_resumo():
    compactado = PASTA_APP / "resumo_estadual_ba.parquet"
    return compactado if compactado.exists() else PASTA / "historico" / "resumo_estadual_ba.csv"


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


COLUNAS_HISTORICO = [
    "ANO", "NR_TURNO", "NM_MUNICIPIO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL", "SG_PARTIDO",
    "COMPOSICAO_LEGENDA", "DS_SIT_TOT_TURNO", "QT_VOTOS",
]


@st.cache_data
def carregar_historico():
    """Resultados de 1960 a 2014, fora do período coberto por carregar_resumo() (2016-2026):
    - 1960 a 1990 (preparar_dados_historico.py): só o consolidado do estado inteiro (sem
      município/bairro/escola/seção - o TSE não tem esse detalhe de papel digitalizado).
    - 1994 a 2014 (preparar_dados_intermediario.py): por município e zona, mas ainda sem
      seção/escola/bairro/mapa (o TSE só passou a ter isso de forma confiável a partir de 2016)."""
    partes = []
    for arquivo in (arquivo_historico(), arquivo_intermediario()):
        if not arquivo.exists():
            continue
        if arquivo.suffix == ".parquet":
            partes.append(pd.read_parquet(arquivo, columns=COLUNAS_HISTORICO))
        else:
            partes.append(pd.read_csv(arquivo, dtype=str, keep_default_na=False, usecols=COLUNAS_HISTORICO))
    if not partes:
        return pd.DataFrame(columns=COLUNAS_HISTORICO)
    df = pd.concat(partes, ignore_index=True)
    df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
    return como_categoria(df)   # ~970 mil linhas: de ~250 MB para ~25 MB na memória


@st.cache_data
def carregar_historico_resumo():
    """Comparecimento/abstenção de 1960 a 1990, por ano/turno/cargo (pode não existir para algum ano)."""
    arquivo = arquivo_historico_resumo()
    if not arquivo.exists():
        return pd.DataFrame(columns=["ANO", "NR_TURNO", "DS_CARGO", "Eleitores_aptos", "Compareceram", "Abstencoes"])
    df = ler_tabela(arquivo)
    for coluna in ["Eleitores_aptos", "Compareceram", "Abstencoes"]:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce").fillna(0).astype(int)
    return df


SITUACOES = {
    "ELEITO": "Eleito", "ELEITO POR QP": "Eleito", "ELEITO POR MEDIA": "Eleito",
    "2O TURNO": "2º turno", "2 TURNO": "2º turno", "SUPLENTE": "Suplente", "NAO ELEITO": "Não eleito",
}


def mostrar_resultado_historico(ano, hist_ano):
    """Ranking de candidatos para os anos 1960-2014 (ver carregar_historico):
    - 1960-1990: só o resultado do estado inteiro (um "município" só, o placeholder).
    - 1994-2014: por município (mostra o seletor de Município), mas sem bairro/escola/seção/mapa.
    Sem foto nem "ver por escola" em nenhum dos dois casos, porque esse detalhe não existe."""
    turno = painel.selectbox("Turno", sorted(hist_ano["NR_TURNO"].unique()))
    d = hist_ano[hist_ano["NR_TURNO"] == turno]
    cargo = painel.selectbox("Cargo", sorted(d["DS_CARGO"].unique()))
    d = d[d["DS_CARGO"] == cargo]

    municipios = sorted(d["NM_MUNICIPIO"].unique())
    tem_municipio = len(municipios) > 1   # 1960-1990 tem um "município" só (o placeholder estadual)
    municipio = TODOS
    if tem_municipio:
        municipio = painel.selectbox("Município", [TODOS] + municipios)

    por_cidade = tem_municipio and municipio == TODOS and eh_municipal(cargo)
    if municipio != TODOS:
        d = d[d["NM_MUNICIPIO"] == municipio]
    chaves = ["NR_VOTAVEL", "NM_VOTAVEL"] + (["NM_MUNICIPIO"] if por_cidade else [])
    base = agrupar(d, chaves).agg(
        QT_VOTOS=("QT_VOTOS", "sum"), SG_PARTIDO=("SG_PARTIDO", "first"),
        COMPOSICAO_LEGENDA=("COMPOSICAO_LEGENDA", "first"), DS_SIT_TOT_TURNO=("DS_SIT_TOT_TURNO", "first"),
    )
    base = texto(base.sort_values("QT_VOTOS", ascending=False).reset_index(drop=True))

    local = "Bahia (resultado estadual)" if not tem_municipio else ("Bahia (BA)" if municipio == TODOS else municipio)
    faixa_contexto(
        [(ano, False), (cargo, True), (local, municipio != TODOS), (f"{turno}º turno", False)],
        "Eleição Municipal" if tem_municipio and eh_municipal(cargo) else "Eleição Geral",
    )

    total = int(base["QT_VOTOS"].sum())
    if por_cidade:   # % dentro da própria cidade, como no fluxo 2016-2026
        base_pct = base.groupby("NM_MUNICIPIO")["QT_VOTOS"].transform("sum")
    else:
        base_pct = total
    base["PCT"] = (base["QT_VOTOS"] / base_pct * 100).fillna(0)

    metricas = [("Total de votos nominais", formatar(total)), ("Candidatos", len(base))]
    if not tem_municipio:   # só 1960-1990 tem esse resumo (comparecimento/abstenção)
        resumo = carregar_historico_resumo()
        linha_resumo = resumo[(resumo["ANO"] == ano) & (resumo["NR_TURNO"] == turno) & (resumo["DS_CARGO"] == cargo)]
        if not linha_resumo.empty:
            r = linha_resumo.iloc[0]
            metricas += [("Compareceram", formatar(r["Compareceram"])), ("Abstenções", formatar(r["Abstencoes"]))]
    for coluna, (rotulo, valor) in zip(st.columns(len(metricas)), metricas):
        coluna.metric(rotulo, valor)

    linhas = []
    for pos, c in enumerate(base.itertuples(index=False), start=1):
        situacao = SITUACOES.get(normalizar(c.DS_SIT_TOT_TURNO), "")
        partido = c.SG_PARTIDO or c.COMPOSICAO_LEGENDA
        meta = [html.escape(partido)] if partido else []
        if c.NR_VOTAVEL:
            meta.append(f"nº {html.escape(c.NR_VOTAVEL)}")
        if por_cidade:
            meta.append(html.escape(c.NM_MUNICIPIO))
        meta = " · ".join(meta)
        if situacao in SELOS:
            meta = f'<span class="selo {SELOS[situacao]}">{situacao}</span>' + (f" · {meta}" if meta else "")
        linhas.append(
            '<div class="cand">'
            f'<div class="cand-foto">{html.escape(iniciais(c.NM_VOTAVEL))}</div>'
            f'<div class="cand-pos">{pos}</div>'
            f'<div><div class="cand-nome">{html.escape(c.NM_VOTAVEL)}</div><div class="cand-meta">{meta}</div></div>'
            f'<div class="cand-votos"><b>{formatar(c.QT_VOTOS)}</b><span>{formatar_pct(c.PCT)}</span></div>'
            f'<div class="cand-barra"><span style="width:{min(c.PCT, 100):.2f}%"></span></div>'
            "</div>"
        )
    st.markdown(f'<div class="lista">{"".join(linhas)}</div>', unsafe_allow_html=True)
    if tem_municipio:
        painel.info(
            "Esse ano tem o resultado por município (fonte: TSE), mas não por bairro, escola, "
            "seção ou mapa - esse detalhe só existe de forma confiável a partir de 2016."
        )
    else:
        painel.info(
            "Esse ano só tem o resultado consolidado do estado inteiro (fonte: TSE, Repositório de "
            "Dados Eleitorais). Não há dados por município, bairro, escola ou seção para esse período."
        )


@st.cache_data(max_entries=3)
def carregar_candidatos(ano):
    """Cadastro de um ano: {(ano, turno, cargo, UE, número): (sigla do partido, situação, SQ_CANDIDATO, ID_PESSOA)}
    - feito pelo preparar_candidatos.py. ID_PESSOA identifica a mesma pessoa em anos diferentes.
    UE = "BA" nas eleições gerais; nas municipais, o código do município (o mesmo número de vereador
    existe em várias cidades)."""
    arquivo = PASTA_APP / "candidatos.parquet"
    if not arquivo.exists():
        return {}
    df = pd.read_parquet(arquivo, filters=[("ANO", "==", ano)])
    if "SG_UE" not in df.columns:   # arquivo antigo: rode python compactar_dados.py de novo
        return {}
    situacoes = {s: SITUACOES.get(normalizar(s), "") for s in df["DS_SIT_TOT_TURNO"].unique()}
    cargos = {c: normalizar(c) for c in df["DS_CARGO"].unique()}
    pessoas = df["ID_PESSOA"] if "ID_PESSOA" in df.columns else [""] * len(df)
    return {
        (a, t, cargos[c], u, n): (p, situacoes[s], q, i)
        for a, t, c, u, n, p, s, q, i in zip(
            df["ANO"], df["NR_TURNO"], df["DS_CARGO"], df["SG_UE"], df["NR_CANDIDATO"],
            df["SG_PARTIDO"], df["DS_SIT_TOT_TURNO"], df["SQ_CANDIDATO"], pessoas,
        )
    }


def candidaturas_da_pessoa(ano, pessoa, ues):
    """{(cargo normalizado, número)} das candidaturas da pessoa no ano (só nas UEs dadas: "BA" ou o município)."""
    if not pessoa:
        return set()
    return {(c, n) for (_, _, c, u, n), (*_, i) in carregar_candidatos(ano).items() if i == pessoa and u in ues}


@st.cache_data(max_entries=100)
def trajetoria(pessoa):
    """Cada eleição que a pessoa disputou (do cadastro do TSE), com o total de votos nominais da candidatura
    (no estado, para os cargos estaduais/federais; no município, para prefeito/vereador)."""
    arquivo = PASTA_APP / "candidatos.parquet"
    if not pessoa or not arquivo.exists():
        return pd.DataFrame()
    cad = pd.read_parquet(arquivo, filters=[("ID_PESSOA", "==", pessoa)])
    cad = cad.drop_duplicates(["ANO", "NR_TURNO", "DS_CARGO", "SG_UE", "NR_CANDIDATO"])
    if cad.empty:
        return pd.DataFrame()
    resumo = carregar_resumo()
    nome_do_codigo = {str(c).lstrip("0"): m for m, c in carregar_indice().items()}
    linhas = []
    for c in cad.itertuples(index=False):
        votos = resumo[
            (resumo["ANO"] == c.ANO) & (resumo["NR_TURNO"] == c.NR_TURNO) & (resumo["NR_VOTAVEL"] == c.NR_CANDIDATO)
            & (resumo["DS_CARGO"].map(normalizar) == normalizar(c.DS_CARGO))
        ]
        municipio_c = ""
        if c.SG_UE not in ("BA", "BR"):   # BR = Presidente: votos no estado inteiro, como os cargos "BA"
            municipio_c = nome_do_codigo.get(c.SG_UE, "")
            votos = votos[votos["NM_MUNICIPIO"] == municipio_c]
        situacao = SITUACOES.get(normalizar(c.DS_SIT_TOT_TURNO), "")
        if not situacao and not c.DS_SIT_TOT_TURNO.startswith("#"):
            situacao = c.DS_SIT_TOT_TURNO.capitalize()
        linhas.append({
            "Ano": c.ANO, "Turno": c.NR_TURNO, "Cargo": c.DS_CARGO.title(), "Número": c.NR_CANDIDATO,
            "Partido": c.SG_PARTIDO, "Município": municipio_c.title(), "Situação": situacao,
            "Nome_urna": votos["NM_VOTAVEL"].iloc[0] if not votos.empty else "",
            "Votos": int(votos["QT_VOTOS"].sum()),
        })
    return pd.DataFrame(linhas).sort_values(["Ano", "Turno"]).reset_index(drop=True)


CORES_CARGO = {
    "VEREADOR": "#a63db1", "PREFEITO": "#d9762b", "DEPUTADO ESTADUAL": "#2456a6",
    "DEPUTADO FEDERAL": "#1e7b45", "SENADOR": "#b3364a", "GOVERNADOR": "#7a5c2e", "PRESIDENTE": "#0f6e73",
}


def mostrar_trajetoria(pessoa, nome):
    """Barras com a votação em cada eleição, da mais antiga à mais recente, na escala da maior votação."""
    traj = trajetoria(pessoa)
    if traj.empty:
        st.caption(f"Não encontrei outras eleições de {nome} no cadastro do TSE.")
        return
    maior = max(int(traj["Votos"].max()), 1)
    linhas = []
    for t in traj.itertuples(index=False):
        cor = CORES_CARGO.get(normalizar(t.Cargo), "#6b665d")
        cargo = html.escape(t.Cargo) + (f" · {t.Turno}º turno" if t.Turno != "1" else "")
        detalhes = [f"nº {html.escape(t.Número)}"]
        if t.Partido:
            detalhes.append(html.escape(t.Partido))
        if t.Município:
            detalhes.append(html.escape(t.Município))
        if t.Nome_urna and normalizar(t.Nome_urna) != normalizar(nome):   # nome de urna diferente naquele ano
            detalhes.append(f"como {html.escape(t.Nome_urna)}")
        situacao = html.escape(t.Situação)
        classe = "eleito" if t.Situação == "Eleito" else ""
        linhas.append(
            '<div class="traj-linha">'
            f'<div class="traj-ano"><b>{t.Ano}</b><span style="color:{cor}">{cargo}</span>'
            f'<small>{" · ".join(detalhes)}</small></div>'
            f'<div class="traj-trilho"><span style="width:{t.Votos / maior * 100:.2f}%;background:{cor}"></span></div>'
            f'<div class="traj-votos"><b>{formatar(t.Votos)}</b><span class="{classe}">{situacao}</span></div>'
            "</div>"
        )
    st.markdown(f'<div class="traj">{"".join(linhas)}</div>', unsafe_allow_html=True)
    st.caption(
        f"Todas as eleições de {nome} na Bahia desde 2016, da mais antiga à mais recente, na mesma escala "
        "(a maior votação dele). Votos nominais na Bahia (presidente, deputado, senador, governador) ou no município "
        "(prefeito, vereador). A cor indica o cargo."
    )


@st.cache_data(max_entries=60)
def carregar_fotos(ano, ue):
    """{SQ_CANDIDATO: foto em base64} de um ano e UE (estado ou município)."""
    arquivo = PASTA_APP / "fotos" / str(ano) / f"{ue}.parquet"
    if not arquivo.exists():
        return {}
    df = pd.read_parquet(arquivo)
    return {sq: base64.b64encode(foto).decode("ascii") for sq, foto in zip(df["SQ_CANDIDATO"], df["FOTO"])}


@st.cache_data
def carregar_legenda_resumo():
    """Votos de legenda por município (para "Todos os municípios")."""
    df = so_legenda(ler_tabela(arquivo_resumo()))
    return df.assign(QT_VOTOS=pd.to_numeric(df["QT_VOTOS"], errors="coerce").fillna(0).astype(int))


@st.cache_data
def carregar_partidos():
    """{(ano, número do partido): sigla}, a partir dos votos de legenda dos cargos de deputado/vereador."""
    df = ler_tabela(arquivo_resumo())
    legenda = df[
        df["DS_CARGO"].str.contains("deputado|vereador", case=False, na=False, regex=True)
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
        import requests
        linhas, inicio = [], 0
        try:
            while True:   # o Supabase devolve no máximo 1000 linhas por vez
                parte = supabase("GET", {"select": "*", "order": "cd_municipio,nr_zona,nm_local_n",
                                         "offset": inicio, "limit": 1000})
                linhas += parte
                if len(parte) < 1000:
                    break
                inicio += 1000
        except requests.exceptions.RequestException:
            # Supabase fora do ar (ex.: projeto pausado): segue só com os bairros do TSE
            st.session_state["supabase_fora"] = True
            return pd.DataFrame(columns=COLS_BAIRROS)
        st.session_state["supabase_fora"] = False
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
def carregar_municipio(codigo, versao=0, anos=None, legenda=False):
    """Votos por seção do município. anos=None carrega todos; senão só os anos pedidos (bem mais leve).
    legenda=True devolve só os votos de legenda (no número do partido) em vez dos votos nominais."""
    arquivo = arquivo_municipio(codigo)
    if arquivo.suffix == ".parquet" and anos is not None:
        filtros = [("ANO", "in", list(anos))]
        if legenda:   # lê só as linhas com número de partido: bem mais rápido
            filtros.append(("NR_VOTAVEL", "in", NUMEROS_LEGENDA))
        df = pd.read_parquet(arquivo, filters=filtros)
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
    return como_categoria(so_legenda(df) if legenda else so_nominais(df))


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


def cor_do_ponto(valor, vmax):
    """Cor e raio (em metros) do círculo: quanto maior o valor, maior e mais escuro."""
    if valor == 0:
        return [150, 150, 150], 40
    forca = (abs(valor) / vmax) ** 0.6
    raio = 60 + 340 * math.sqrt(abs(valor) / vmax)
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


def desenhar_mapa(entrada):
    """Desenha um círculo por escola (tamanho e cor = votos)."""
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
    cores = [cor_do_ponto(v, vmax) for v in pontos["valor"]]
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
            # fundo no estilo do Google Maps (ruas, rodovias em amarelo, áreas verdes e nomes), sem chave de API
            map_provider="carto",
            map_style=pdk.map_styles.CARTO_ROAD,
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
    if st.session_state.get("supabase_fora"):
        st.error("Não consegui acessar o Supabase, onde ficam os bairros informados. O cadastro fica "
                 "bloqueado até ele voltar, para não salvar em cima de uma lista que pareceria vazia.")
        st.stop()
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
historico = carregar_historico()

if EH_CADASTRO:
    tela_cadastro(indice)
    st.stop()

# ---------------------------------------------------------------- filtros
if CELULAR:
    painel = st.expander("Filtros", expanded=True, icon=":material/tune:")
else:
    painel = st.sidebar
    painel.header("Filtros")
anos_modernos = set(dados["ANO"].unique())
anos_historicos = set(historico["ANO"].unique())
anos = sorted(anos_modernos | anos_historicos, reverse=True)
ano = painel.selectbox("Ano da eleição", anos)
painel.caption(
    "Prefeito e vereador só a partir de 1996: as eleições municipais anteriores "
    "(1992, 1988, 1985, 1982...) não estão nos dados abertos do TSE."
)

if ano in anos_historicos and ano not in anos_modernos:
    mostrar_resultado_historico(ano, historico[historico["ANO"] == ano])
    st.stop()

dados_ano = dados[dados["ANO"] == ano]   # todos os cargos/turnos do ano, na Bahia toda (comparativo por município)
d = dados_ano

turno = painel.selectbox("Turno", sorted(d["NR_TURNO"].unique()))
d = d[d["NR_TURNO"] == turno]

cargo = painel.selectbox("Cargo", sorted(d["DS_CARGO"].unique()))
d = d[d["DS_CARGO"] == cargo]

municipio = painel.selectbox("Município", [TODOS] + sorted(d["NM_MUNICIPIO"].unique()))

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
    if st.session_state.get("supabase_fora"):
        st.warning("Não consegui acessar o Supabase agora; mostrando só os bairros do TSE "
                   "(os bairros que você informou voltam a aparecer quando ele responder).")
    ds = ds_ano[(ds_ano["NR_TURNO"] == turno) & (ds_ano["DS_CARGO"] == cargo)]
    escolas_todas = agregar_escolas(ds)
    centro_mun = (escolas_todas["LAT"].median(), escolas_todas["LON"].median())
    tem_bairro =bool((escolas_todas["BAIRRO"] != SEM_BAIRRO).any())

    # ---- bairro / localidade (lista)
    if tem_bairro:
        todos_bairros = sorted(escolas_todas["BAIRRO"].unique(), key=normalizar)
        # a própria lista aceita digitar para procurar o bairro
        bairro_sel = painel.selectbox("Bairro/localidade", [TODOS_BAIRROS] + todos_bairros)
        if bairro_sel != TODOS_BAIRROS:
            bairros_alvo = {normalizar(bairro_sel)}
            bairro_txt = bairro_sel
    else:
        painel.info("Bairro/localidade não disponível nos dados deste município/ano.")

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

    escola_sel = painel.selectbox("Escola", [TODAS_ESCOLAS] + escolas_f["rotulo"].tolist())

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

        secao_sel = painel.selectbox("Seção", [TODAS_SECOES] + secoes["NR_SECAO"].tolist())
        if secao_sel != TODAS_SECOES:
            base = base[base["NR_SECAO"] == secao_sel]

# votos de legenda com os mesmos filtros (entram no total de cada partido)
if municipio == TODOS:
    votos_legenda = carregar_legenda_resumo()
    votos_legenda = votos_legenda[
        (votos_legenda["ANO"] == ano) & (votos_legenda["NR_TURNO"] == turno) & (votos_legenda["DS_CARGO"] == cargo)
    ]
else:
    votos_legenda = carregar_municipio(codigo, versao_bairros(), (ano,), legenda=True)
    votos_legenda = filtrar_bairro(
        votos_legenda[(votos_legenda["NR_TURNO"] == turno) & (votos_legenda["DS_CARGO"] == cargo)]
    )
    if escola is not None:
        votos_legenda = votos_legenda[
            (votos_legenda["NR_ZONA"] == escola["NR_ZONA"])
            & (votos_legenda["NR_LOCAL_VOTACAO"] == escola["NR_LOCAL_VOTACAO"])
        ]
    if secao_sel != TODAS_SECOES:
        votos_legenda = votos_legenda[votos_legenda["NR_SECAO"] == secao_sel]
legenda_por_numero = votos_legenda.groupby("NR_VOTAVEL", observed=True)["QT_VOTOS"].sum()
legenda_por_numero = {str(n): int(v) for n, v in legenda_por_numero.items() if v}

# ------------------------------------------------- votos por candidato (nominal)
# prefeito/vereador com "Todos os municípios": o mesmo número existe em várias cidades -> uma linha por cidade
por_cidade = municipio == TODOS and eh_municipal(cargo)
chaves = ["NR_VOTAVEL", "NM_VOTAVEL"] + (["NM_MUNICIPIO"] if por_cidade else [])
resultado = texto(
    agrupar(base, chaves)["QT_VOTOS"].sum()
    .sort_values("QT_VOTOS", ascending=False)
    .reset_index(drop=True)
)
if resultado.empty:
    st.warning("Nenhum voto encontrado com esses filtros.")
    st.stop()

total = int(resultado["QT_VOTOS"].sum())
if por_cidade:   # % dentro da própria cidade
    base_pct = resultado.groupby("NM_MUNICIPIO")["QT_VOTOS"].transform("sum")
else:
    base_pct = total
resultado["% dos votos nominais"] = (resultado["QT_VOTOS"] / base_pct * 100).fillna(0).round(2)

partidos = carregar_partidos()
cadastro = carregar_candidatos(ano)
cargo_n = normalizar(cargo)
if por_cidade:
    ues = [str(indice.get(m, "")).lstrip("0") for m in resultado["NM_MUNICIPIO"]]
elif eh_municipal(cargo):
    ues = [str(codigo).lstrip("0")] * len(resultado)
else:   # no cadastro do TSE, Presidente é da UE "BR"; os demais cargos estaduais/federais, "BA"
    ues = ["BR" if cargo_n == "PRESIDENTE" else "BA"] * len(resultado)
do_cadastro = [
    cadastro.get((ano, turno, cargo_n, u, n)) or cadastro.get((ano, "1", cargo_n, u, n)) or ("", "", "", "")
    for u, n in zip(ues, resultado["NR_VOTAVEL"])
]
resultado.insert(0, "Pos.", range(1, len(resultado) + 1))
foto_sq = {pos: (u, c[2]) for pos, u, c in zip(resultado["Pos."], ues, do_cadastro) if c[2]}
pessoa_do_numero = {n: c[3] for n, c in zip(resultado["NR_VOTAVEL"], do_cadastro) if c[3]}


def foto_de(pos):
    if pos not in foto_sq:
        return None
    ue, sq = foto_sq[pos]
    return carregar_fotos(ano, ue).get(sq)


resultado.insert(3, "Partido", [
    c[0] or partidos.get((ano, str(n)[:2])) or SIGLAS_POR_NUMERO.get(str(n)[:2], "")
    for n, c in zip(resultado["NR_VOTAVEL"], do_cadastro)
])
resultado.insert(4, "Situação", [c[1] for c in do_cadastro])
resultado = resultado.rename(
    columns={"NR_VOTAVEL": "Número", "NM_VOTAVEL": "Candidato", "QT_VOTOS": "Votos", "NM_MUNICIPIO": "Município"}
)
if por_cidade:   # Município logo depois do nome
    colunas = list(resultado.columns)
    colunas.insert(colunas.index("Candidato") + 1, colunas.pop(colunas.index("Município")))
    resultado = resultado[colunas]

contexto = [(ano, False), (cargo, True), ("Bahia (BA)" if municipio == TODOS else municipio, municipio != TODOS)]
if bairro_txt:
    contexto.append((bairro_txt, False))
if escola is not None:
    contexto.append((escola["NM_LOCAL_VOTACAO"], False))
if secao_sel != TODAS_SECOES:
    contexto.append((f"seção {secao_sel}", False))
contexto.append((f"{turno}º turno", False))
faixa_contexto(contexto, "Eleição Municipal" if int(ano) % 4 == 0 else "Eleição Geral")

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

# ------------------------------------------ votação do candidato por escola
def mostrar_secoes(nome, numero, escola_c):
    """Votação do candidato em cada seção (urna) de uma escola, com o total de votos nominais da seção."""
    da_escola = ds_bairro[
        (ds_bairro["NR_ZONA"] == escola_c["Zona"]) & (ds_bairro["NR_LOCAL_VOTACAO"] == escola_c["NR_LOCAL_VOTACAO"])
    ]
    por_secao = texto(agrupar(da_escola, "NR_SECAO")["QT_VOTOS"].sum()).rename(
        columns={"QT_VOTOS": "Votos nominais na seção"}
    )
    do_cand = texto(
        agrupar(da_escola[da_escola["NR_VOTAVEL"] == numero], "NR_SECAO")["QT_VOTOS"].sum()
    ).rename(columns={"QT_VOTOS": f"Votos de {nome}"})
    por_secao = por_secao.merge(do_cand, on="NR_SECAO", how="left")
    votos_c = por_secao[f"Votos de {nome}"].fillna(0).astype(int)
    por_secao[f"Votos de {nome}"] = votos_c
    por_secao["% da seção"] = (votos_c / por_secao["Votos nominais na seção"].where(lambda v: v > 0) * 100).round(2)
    por_secao["_n"] = pd.to_numeric(por_secao["NR_SECAO"], errors="coerce")
    por_secao = por_secao.sort_values("_n").rename(columns={"NR_SECAO": "Seção"})[
        ["Seção", f"Votos de {nome}", "Votos nominais na seção", "% da seção"]
    ]

    st.markdown(
        f"**Votação de {nome} por seção (urna) - {escola_c['Escola']} (zona {escola_c['Zona']})**"
    )
    c1, c2 = st.columns(2)
    c1.metric("Votos na escola", formatar(votos_c.sum()))
    c2.metric("Seções com votos", f"{int((votos_c > 0).sum())} de {len(por_secao)}")
    st.dataframe(por_secao, hide_index=True)


CORES_COMPARATIVO = ["#c0392b", "#16a085", "#2471a3", "#d68910", "#7d3c98"]
MAX_COMPARAR = 4
POR_BAIRRO, POR_ESCOLA = "Por bairro", "Por escola"
ABSOLUTO, PCT_CANDIDATO, PCT_LOCAL = "Absoluto", "% dos votos dele", "% do local"


def mostrar_comparativo(numero, nome):
    """Compara a votação nominal do candidato com até MAX_COMPARAR outros, por bairro ou por escola."""
    st.divider()
    st.subheader(f"Comparar {nome} com outros candidatos")
    universo = filtrar_bairro(ds_ano[ds_ano["NR_TURNO"] == turno])
    cands = texto(
        agrupar(universo, ["DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL"])["QT_VOTOS"].sum()
    )
    cands["_mesmo_cargo"] = cands["DS_CARGO"] == cargo
    cands = cands.sort_values(["_mesmo_cargo", "DS_CARGO", "QT_VOTOS"], ascending=[False, True, False])
    cands = cands[~((cands["DS_CARGO"] == cargo) & (cands["NR_VOTAVEL"] == numero))]
    rotulo = cands["NM_VOTAVEL"] + " · " + cands["DS_CARGO"] + " nº " + cands["NR_VOTAVEL"]
    chaves = dict(zip(rotulo, zip(cands["DS_CARGO"], cands["NR_VOTAVEL"], cands["NM_VOTAVEL"])))
    with st.container(key="cmp_escolha"):   # a chave dá a classe CSS que pinta cada etiqueta com a cor dele
        escolhidos = st.multiselect(
            f"Candidatos para comparar (até {MAX_COMPARAR})", list(chaves), max_selections=MAX_COMPARAR,
            placeholder="Buscar candidato pelo nome...", key=f"comparar|{chave}|{numero}",
        )
    if not escolhidos:
        st.caption(f"Escolha até {MAX_COMPARAR} candidatos de {ano} ({turno}º turno) neste município "
                   "para comparar com a votação de " + nome + ".")
        return

    comparados = [(cargo, numero, nome)] + [chaves[r] for r in escolhidos]
    c1, c2, c3 = st.columns([2, 3, 2], vertical_alignment="center")
    unidade = c1.segmented_control("Agrupar", [POR_BAIRRO, POR_ESCOLA], default=POR_BAIRRO,
                                   label_visibility="collapsed", key=f"cmp_unid|{numero}") or POR_BAIRRO
    medida = c2.segmented_control("Medida", [ABSOLUTO, PCT_CANDIDATO, PCT_LOCAL], default=ABSOLUTO,
                                  label_visibility="collapsed", key=f"cmp_medida|{numero}") or ABSOLUTO
    if unidade == POR_BAIRRO and not (universo["BAIRRO"] != SEM_BAIRRO).any():
        st.info("Este município não tem bairro/localidade nos dados; mostrando por escola.")
        unidade = POR_ESCOLA

    if unidade == POR_BAIRRO:
        grupo = ["BAIRRO"]
        nomes_local = None
    else:
        grupo = ["NR_ZONA", "NR_LOCAL_VOTACAO"]
        nomes_local = texto(agrupar(universo, grupo).agg(
            NM_LOCAL_VOTACAO=("NM_LOCAL_VOTACAO", "first"), BAIRRO=("BAIRRO", "first"),
        ))
    # total nominal de cada cargo em cada bairro/escola (base do "% do local")
    do_local = texto(agrupar(universo, grupo + ["DS_CARGO"])["QT_VOTOS"].sum())
    base_local = {
        (tuple(linha[:-2]), linha[-2]): linha[-1]
        for linha in do_local[grupo + ["DS_CARGO", "QT_VOTOS"]].itertuples(index=False, name=None)
    }

    tabela = None
    colunas = []
    for i, (cargo_c, num_c, nome_c) in enumerate(comparados):
        votos = texto(agrupar(
            universo[(universo["DS_CARGO"] == cargo_c) & (universo["NR_VOTAVEL"] == num_c)], grupo
        )["QT_VOTOS"].sum())
        col = f"c{i}"
        votos = votos.rename(columns={"QT_VOTOS": col})
        tabela = votos if tabela is None else tabela.merge(votos, on=grupo, how="outer")
        colunas.append((col, cargo_c, num_c, nome_c, CORES_COMPARATIVO[i]))
    for col, *_ in colunas:
        tabela[col] = tabela[col].fillna(0).astype(int)
    tabela = tabela.sort_values([c for c, *_ in colunas], ascending=False).reset_index(drop=True)
    if nomes_local is not None:
        tabela = tabela.merge(nomes_local, on=grupo, how="left")
    totais = {col: int(tabela[col].sum()) for col, *_ in colunas}

    def valor(linha, col, cargo_c):
        v = linha[col]
        if medida == PCT_CANDIDATO:
            return v / totais[col] * 100 if totais[col] else 0.0
        if medida == PCT_LOCAL:
            base = base_local.get((tuple(linha[g] for g in grupo), cargo_c), 0)
            return v / base * 100 if base else 0.0
        return v

    mostrar = lambda v: formatar(v) if medida == ABSOLUTO else formatar_pct(v)

    # etiquetas coloridas com o total de cada um
    etiquetas = "".join(
        f'<span class="cmp-chip"><i style="background:{cor}"></i>{html.escape(n)} · {html.escape(cg)} '
        f'<b>{formatar(totais[col])}</b></span>'
        for col, cg, _, n, cor in colunas
    )
    st.markdown(f'<div class="cmp-chips">{etiquetas}</div>', unsafe_allow_html=True)

    # tabela no estilo do anexo: cabeçalho com a cor de cada candidato, maior valor da linha em negrito
    titulo_local = "Bairro" if unidade == POR_BAIRRO else "Escola"
    cab = "".join(
        f'<th><span><i style="background:{cor}"></i>{html.escape(n)}</span><small>{html.escape(cg)} nº {html.escape(nm)}</small></th>'
        for _, cg, nm, n, cor in colunas
    )
    linhas_html, linhas_csv = [], []
    for _, linha in tabela.iterrows():
        valores = [valor(linha, col, cg) for col, cg, *_ in colunas]
        maior = max(valores)
        if unidade == POR_BAIRRO:
            local = html.escape(linha["BAIRRO"])
            local_csv = {"Bairro": linha["BAIRRO"]}
        else:
            local = (f'{html.escape(linha["NM_LOCAL_VOTACAO"])}<small>zona {html.escape(linha["NR_ZONA"])}'
                     + (f' · {html.escape(linha["BAIRRO"])}' if linha["BAIRRO"] != SEM_BAIRRO else "") + "</small>")
            local_csv = {"Escola": linha["NM_LOCAL_VOTACAO"], "Zona": linha["NR_ZONA"], "Bairro": linha["BAIRRO"]}
        celulas = "".join(
            f'<td class="{"maior" if v == maior and maior > 0 else ""}">{mostrar(v)}</td>' for v in valores
        )
        linhas_html.append(f"<tr><td>{local}</td>{celulas}</tr>")
        linhas_csv.append({**local_csv, **{f"{n} ({cg} {nm})": round(v, 2) for (_, cg, nm, n, _), v in zip(colunas, valores)}})
    rodape = "".join(
        f"<td>{formatar(totais[col]) if medida == ABSOLUTO else ('100,00%' if medida == PCT_CANDIDATO else '')}</td>"
        for col, *_ in colunas
    )
    st.markdown(
        f'<div class="cmp-tab"><table><thead><tr><th>{titulo_local}</th>{cab}</tr></thead>'
        f'<tbody>{"".join(linhas_html)}</tbody><tfoot><tr><td>Total</td>{rodape}</tr></tfoot></table></div>',
        unsafe_allow_html=True,
    )
    explicacao = {
        ABSOLUTO: "Votos nominais de cada candidato.",
        PCT_CANDIDATO: "Quanto daquele lugar representa da votação total de cada candidato.",
        PCT_LOCAL: "Fatia de cada candidato nos votos nominais do cargo dele naquele lugar.",
    }[medida]
    st.caption(f"{len(tabela)} {titulo_local.lower()}(s) onde algum deles teve votos. {explicacao} "
               "Em negrito, o maior valor de cada linha.")
    st.download_button(
        "Baixar comparativo (CSV)",
        pd.DataFrame(linhas_csv).to_csv(index=False).encode("utf-8-sig"),
        file_name=f"comparativo_{ano}_{numero}_{'bairro' if unidade == POR_BAIRRO else 'escola'}.csv",
        mime="text/csv", key=f"cmp_csv|{numero}",
    )


def mostrar_comparativo_municipios(numero, nome):
    """Com 'Todos os municípios': compara a votação nominal do candidato com até MAX_COMPARAR outros, por
    município, dentro da mesma eleição (ano/turno). Só para cargos estaduais/federais (o número do candidato
    não se repete entre cidades; prefeito/vereador já aparecem com uma linha por cidade na lista principal)."""
    st.divider()
    st.subheader(f"Comparar {nome} com outros candidatos, por município")
    universo = dados_ano[dados_ano["NR_TURNO"] == turno]
    cands = texto(agrupar(universo, ["DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL"])["QT_VOTOS"].sum())
    cands = cands[~cands["DS_CARGO"].map(eh_municipal)]
    cands["_mesmo_cargo"] = cands["DS_CARGO"] == cargo
    cands = cands.sort_values(["_mesmo_cargo", "DS_CARGO", "QT_VOTOS"], ascending=[False, True, False])
    cands = cands[~((cands["DS_CARGO"] == cargo) & (cands["NR_VOTAVEL"] == numero))]
    rotulo = cands["NM_VOTAVEL"] + " · " + cands["DS_CARGO"] + " nº " + cands["NR_VOTAVEL"]
    chaves = dict(zip(rotulo, zip(cands["DS_CARGO"], cands["NR_VOTAVEL"], cands["NM_VOTAVEL"])))
    with st.container(key="cmp_mun_escolha"):   # a chave dá a classe CSS que pinta cada etiqueta com a cor dele
        escolhidos = st.multiselect(
            f"Candidatos para comparar (até {MAX_COMPARAR})", list(chaves), max_selections=MAX_COMPARAR,
            placeholder="Buscar candidato pelo nome...", key=f"comparar_mun|{ano}|{turno}|{numero}",
        )
    if not escolhidos:
        st.caption(f"Escolha até {MAX_COMPARAR} candidatos de {ano} ({turno}º turno) para comparar a votação "
                   f"deles por município com a de {nome}.")
        return

    comparados = [(cargo, numero, nome)] + [chaves[r] for r in escolhidos]
    medida = st.segmented_control(
        "Medida", [ABSOLUTO, PCT_CANDIDATO], default=ABSOLUTO, label_visibility="collapsed",
        key=f"cmp_mun_medida|{numero}",
    ) or ABSOLUTO

    tabela = None
    colunas = []
    for i, (cargo_c, num_c, nome_c) in enumerate(comparados):
        votos = texto(agrupar(
            universo[(universo["DS_CARGO"] == cargo_c) & (universo["NR_VOTAVEL"] == num_c)], ["NM_MUNICIPIO"]
        )["QT_VOTOS"].sum())
        col = f"c{i}"
        votos = votos.rename(columns={"QT_VOTOS": col})
        tabela = votos if tabela is None else tabela.merge(votos, on="NM_MUNICIPIO", how="outer")
        colunas.append((col, cargo_c, num_c, nome_c, CORES_COMPARATIVO[i]))
    for col, *_ in colunas:
        tabela[col] = tabela[col].fillna(0).astype(int)
    tabela = tabela.sort_values([c for c, *_ in colunas], ascending=False).reset_index(drop=True)
    totais = {col: int(tabela[col].sum()) for col, *_ in colunas}

    def valor(linha, col):
        v = linha[col]
        return v / totais[col] * 100 if medida == PCT_CANDIDATO and totais[col] else (0.0 if medida == PCT_CANDIDATO else v)

    mostrar = lambda v: formatar(v) if medida == ABSOLUTO else formatar_pct(v)

    etiquetas = "".join(
        f'<span class="cmp-chip"><i style="background:{cor}"></i>{html.escape(n)} · {html.escape(cg)} '
        f'<b>{formatar(totais[col])}</b></span>'
        for col, cg, _, n, cor in colunas
    )
    st.markdown(f'<div class="cmp-chips">{etiquetas}</div>', unsafe_allow_html=True)

    cab = "".join(
        f'<th><span><i style="background:{cor}"></i>{html.escape(n)}</span>'
        f'<small>{html.escape(cg)} nº {html.escape(nm)}</small></th>'
        for _, cg, nm, n, cor in colunas
    )
    linhas_html, linhas_csv = [], []
    for _, linha in tabela.iterrows():
        valores = [valor(linha, col) for col, *_ in colunas]
        maior = max(valores)
        local = html.escape(linha["NM_MUNICIPIO"])
        celulas = "".join(
            f'<td class="{"maior" if v == maior and maior > 0 else ""}">{mostrar(v)}</td>' for v in valores
        )
        linhas_html.append(f"<tr><td>{local}</td>{celulas}</tr>")
        linhas_csv.append({"Município": linha["NM_MUNICIPIO"],
                            **{f"{n} ({cg} {nm})": round(v, 2) for (_, cg, nm, n, _), v in zip(colunas, valores)}})
    rodape = "".join(
        f"<td>{formatar(totais[col]) if medida == ABSOLUTO else '100,00%'}</td>" for col, *_ in colunas
    )
    st.markdown(
        f'<div class="cmp-tab"><table><thead><tr><th>Município</th>{cab}</tr></thead>'
        f'<tbody>{"".join(linhas_html)}</tbody><tfoot><tr><td>Total</td>{rodape}</tr></tfoot></table></div>',
        unsafe_allow_html=True,
    )
    st.caption(f"{len(tabela)} município(s) onde algum deles teve votos. "
               + ("Votos nominais de cada candidato." if medida == ABSOLUTO
                  else "Quanto daquele município representa da votação total de cada candidato no estado.")
               + " Em negrito, o maior valor de cada linha.")
    st.download_button(
        "Baixar comparativo por município (CSV)",
        pd.DataFrame(linhas_csv).to_csv(index=False).encode("utf-8-sig"),
        file_name=f"comparativo_{ano}_{numero}_municipios.csv",
        mime="text/csv", key=f"cmp_mun_csv|{numero}",
    )


def mostrar_candidato_por_municipio(candidato):
    """Com 'Todos os municípios': trajetória do candidato, votação dele em cada município (do maior para o
    menor) e comparação com outros candidatos pelos municípios."""
    numero = candidato["Número"]
    nome = candidato["Candidato"]
    do_candidato = d[d["NR_VOTAVEL"] == numero]

    por_municipio = texto(
        agrupar(do_candidato, ["NM_MUNICIPIO"])["QT_VOTOS"].sum()
        .sort_values("QT_VOTOS", ascending=False)
        .reset_index(drop=True)
    )
    total_cand = int(por_municipio["QT_VOTOS"].sum())
    por_municipio["% dos votos do candidato"] = (
        (por_municipio["QT_VOTOS"] / total_cand * 100).round(2) if total_cand else 0
    )
    por_municipio.insert(0, "Pos.", range(1, len(por_municipio) + 1))
    por_municipio = por_municipio.rename(columns={"NM_MUNICIPIO": "Município", "QT_VOTOS": "Votos"})
    colunas_mun = ["Pos.", "Município", "Votos", "% dos votos do candidato"]

    with st.expander(f"Trajetória de {nome} em todas as eleições", expanded=True):
        mostrar_trajetoria(pessoa_do_numero.get(numero), nome)

    st.subheader(f"Votação de {nome} ({numero}) por município - {ano} ({turno}º turno)")
    st.metric("Votos do candidato na Bahia", formatar(total_cand))
    st.markdown("**Todos os municípios onde ele teve votos, do maior para o menor**")
    st.dataframe(por_municipio, hide_index=True, column_order=colunas_mun)
    st.download_button(
        "Baixar votos por município (CSV)",
        por_municipio[colunas_mun].to_csv(index=False).encode("utf-8"),
        file_name=f"votos_{ano}_{numero}_por_municipio.csv",
        mime="text/csv",
    )

    mostrar_comparativo_municipios(numero, nome)


def mostrar_candidato(candidato):
    """Votação do candidato por escola (e, clicando na escola, por seção), mapa e comparação entre anos."""
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
    por_escola = por_escola.rename(columns={"NR_ZONA": "Zona"})
    colunas_escola = ["Pos.", "Escola", "Bairro/localidade", "Zona", "Endereço", "Votos",
                      "% dos votos do candidato", "Seções com votos"]

    with st.expander(f"Trajetória de {nome} em todas as eleições", expanded=True):
        mostrar_trajetoria(pessoa_do_numero.get(numero), nome)

    escopo = f" - {bairro_txt}" if bairro_txt else ""
    st.subheader(f"Votação de {nome} ({numero}) por escola - {municipio}{escopo} - {ano}")
    st.metric("Votos do candidato nesta seleção", formatar(total_cand))

    st.markdown("**Todas as escolas, da maior para a menor votação** - clique em uma escola para ver "
                "a votação por seção (urna)")
    evento = st.dataframe(
        por_escola, hide_index=True, column_order=colunas_escola,
        on_select="rerun", selection_mode="single-row", key=f"escolas|{chave}|{numero}",
    )
    if evento.selection.rows:
        mostrar_secoes(nome, numero, por_escola.iloc[evento.selection.rows[0]])
    st.download_button(
        "Baixar lista por escola (CSV)",
        por_escola[colunas_escola].to_csv(index=False).encode("utf-8"),
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
    mostrar_comparativo(numero, nome)

    outros_anos = [a for a in anos if a != ano]
    st.divider()
    st.subheader(f"Comparar {nome} entre anos")
    if not outros_anos:
        st.info("Só há dados de um ano. Rode baixar_dados.py e preparar_dados.py para incluir outro ano.")
    else:
        # sugere a eleição mais próxima do mesmo tipo (municipal com municipal, geral com geral)
        mesmo_tipo = [a for a in outros_anos if int(a) % 4 == int(ano) % 4] or outros_anos
        sugerido = min(mesmo_tipo, key=lambda a: (abs(int(a) - int(ano)), int(a)))
        escolha_ano = st.radio(
            "Comparar com o ano", [NAO_COMPARAR] + outros_anos, index=1 + outros_anos.index(sugerido),
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
                # a mesma pessoa no outro ano: pelo cadastro do TSE (o nome de urna pode ter mudado,
                # ex.: "DEPUTADO DAL" em 2022 e "DAL BARRETO" em 2026); se não achar, pelo nome de urna
                da_pessoa = candidaturas_da_pessoa(
                    ano_b, pessoa_do_numero.get(numero), {"BA", "BR", str(codigo).lstrip("0")},
                )
                mesma_pessoa = [(normalizar(c), n) in da_pessoa for c, n in zip(cands_b["DS_CARGO"], cands_b["NR_VOTAVEL"])]
                iguais = cands_b[mesma_pessoa]
                if iguais.empty:
                    iguais = cands_b[cands_b["_nome"] == normalizar(nome)]
                padrao = None
                if not iguais.empty:
                    mesmo_cargo = iguais[iguais["DS_CARGO"] == cargo]
                    achado = (mesmo_cargo if not mesmo_cargo.empty else iguais).iloc[0]
                    padrao = achado["rotulo"]
                    if achado["_nome"] != normalizar(nome):
                        st.caption(f"Em {ano_b}, {nome} usou o nome de urna **{achado['NM_VOTAVEL']}**.")
                else:
                    st.info(
                        f"Não achei {nome} em {ano_b} neste município (pode não ter sido candidato nesse ano "
                        "ou não ter tido votos aqui). Se quiser, escolha um candidato na lista para comparar."
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

                    st.download_button(
                        "Baixar comparação (CSV)",
                        tabela_comp.to_csv(index=False).encode("utf-8"),
                        file_name=f"comparacao_{antigo}_{novo}_{numero}.csv",
                        mime="text/csv",
                    )

# ------------------------------------------------------ ranking de candidatos
chave = f"tabela|{ano}|{turno}|{cargo}|{municipio}|{bairro_txt}|{escola_sel}|{secao_sel}"
MAIS_VOTADOS, ALFABETICA, TODOS_PARTIDOS = "Mais votados", "A–Z", "Todos os partidos"

area_busca = st.container()   # o campo de busca fica acima, mas as sugestões dependem do partido escolhido
o1, o2, o3 = st.columns([2, 3, 5], vertical_alignment="center")
ordem_lista = o1.segmented_control(
    "Ordem", [MAIS_VOTADOS, ALFABETICA], default=MAIS_VOTADOS, label_visibility="collapsed",
) or MAIS_VOTADOS
lista_partidos = sorted(p for p in resultado["Partido"].unique() if p)
nominais_partido = resultado.groupby("Partido")["Votos"].sum()
cands_partido = resultado.groupby("Partido").size()
# legenda: o número do partido (ex.: 13) vai para a mesma sigla dos candidatos dele (13xxx)
sigla_do_numero = (
    resultado.assign(_n=resultado["Número"].str[:2]).groupby("_n")["Partido"]
    .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else "").to_dict()
)
legenda_partido = {}
for n, v in legenda_por_numero.items():
    sigla = sigla_do_numero.get(n) or partidos.get((ano, n)) or SIGLAS_POR_NUMERO.get(n, "")
    if sigla:
        legenda_partido[sigla] = legenda_partido.get(sigla, 0) + v
votos_partido = nominais_partido.add(pd.Series(legenda_partido, dtype=int), fill_value=0).astype(int)
total_com_legenda = total + sum(legenda_por_numero.values())
partido_sel = o2.selectbox(
    "Partido", [TODOS_PARTIDOS] + lista_partidos, label_visibility="collapsed",
    format_func=lambda p: p if p == TODOS_PARTIDOS else f"{p} · {formatar(votos_partido[p])} votos",
)
if partido_sel != TODOS_PARTIDOS:
    # total dos votos nominais dos candidatos do partido (sem os votos de legenda)
    da_legenda = legenda_partido.get(partido_sel, 0)
    composicao = (f' ({formatar(nominais_partido[partido_sel])} nominais + {formatar(da_legenda)} de legenda)'
                  if da_legenda else " nominais")
    o3.markdown(
        f'<div class="partido-total"><b>{html.escape(partido_sel)}</b>'
        f'<span class="sep">·</span><b>{formatar(votos_partido[partido_sel])}</b> votos{composicao}'
        f'<span class="sep">·</span>{cands_partido[partido_sel]} candidato(s)'
        f'<span class="sep">·</span>{formatar_pct(votos_partido[partido_sel] / total_com_legenda * 100 if total_com_legenda else 0)}'
        f' do total</div>',
        unsafe_allow_html=True,
    )

do_partido = resultado if partido_sel == TODOS_PARTIDOS else resultado[resultado["Partido"] == partido_sel]
alvo_busca = do_partido["Candidato"] + " " + do_partido["Partido"] + " " + do_partido["Número"] + " " + do_partido["Situação"]
if por_cidade:
    alvo_busca = alvo_busca + " " + do_partido["Município"]
alvo_busca = alvo_busca.map(normalizar)


def filtrar_texto(texto_busca):
    if len(texto_busca.strip()) < MINIMO_BUSCA:
        return do_partido
    return do_partido[alvo_busca.str.contains(normalizar(texto_busca), regex=False)]


def sugestoes(texto_busca):
    """Até 8 candidatos (mais votados primeiro) que contêm o texto, para a lista do autocomplete."""
    achados = filtrar_texto(texto_busca).head(8)
    extras = achados["Partido"] + " · nº " + achados["Número"]
    if por_cidade:
        extras = extras + " · " + achados["Município"]
    return [{"valor": v, "extra": e} for v, e in zip(achados["Candidato"], extras)]


with area_busca:
    texto_filtro = campo_busca(
        "busca_candidato", sugestoes, f"Filtrar por nome, número ou partido (a partir de {MINIMO_BUSCA} letras)",
    )
visivel = filtrar_texto(texto_filtro)
if ordem_lista == ALFABETICA:
    visivel = visivel.sort_values("Candidato", key=lambda s: s.map(normalizar))
visivel = visivel.reset_index(drop=True)

if visivel.empty:
    st.info("Nenhum candidato encontrado com esse filtro.")
else:
    qtd_chave = f"qtd|{chave}|{texto_filtro}|{partido_sel}|{ordem_lista}"
    qtd = st.session_state.get(qtd_chave, 10)
    colunas_lista = ["Pos.", "Candidato", "Número", "Partido", "Situação", "Votos", "% dos votos nominais"]
    if por_cidade:
        colunas_lista.append("Município")
    mostrados = visivel.head(qtd)
    tabela_lista = mostrados[colunas_lista].rename(columns={"Pos.": "Pos", "% dos votos nominais": "Pct"})

    if ds is None:
        if por_cidade:
            aviso = "Escolha um <b>município</b> nos <b>filtros</b> para ver a votação de cada candidato <b>por escola</b>."
            st.markdown(lista_html(cartoes_candidatos(tabela_lista, foto_de), aviso), unsafe_allow_html=True)
        else:
            aviso = "Clique em um candidato para ver a votação dele <b>por município</b> (clique de novo para fechar)."
            renderizar_lista_candidatos(mostrados, tabela_lista, aviso, mostrar_candidato_por_municipio)
    else:
        aviso = "Clique em um candidato para ver a votação dele <b>por escola</b> (clique de novo para fechar)."
        renderizar_lista_candidatos(mostrados, tabela_lista, aviso, mostrar_candidato)

    if len(visivel) > qtd:
        if st.button(f"Mostrar mais ({len(visivel) - qtd} restantes)", key=f"mais|{qtd_chave}"):
            st.session_state[qtd_chave] = qtd + 20
            st.rerun()

if ds is None and not visivel.empty:
    with st.expander("Tabela completa"):
        st.dataframe(visivel, hide_index=True)

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

st.download_button(
    "Baixar tabela de candidatos (CSV)",
    resultado.to_csv(index=False).encode("utf-8"),
    file_name="resultado.csv",
    mime="text/csv",
)
