# Projeto: Eleições Bahia (dados abertos do TSE) — documento de continuidade

> Leia este arquivo inteiro antes de mexer em qualquer coisa. Ele descreve o que existe, como funciona, o que já foi testado e o que ainda NÃO foi confirmado.

## 1. Quem é o usuário e como trabalhar com ele
- Brasileiro (Bahia), **não é programador**. Responder sempre em **português do Brasil**, com linguagem simples, passo a passo, sem jargão.
- Ele roda os scripts no próprio computador (terminal) e vê o app no navegador. Dê comandos prontos para copiar e colar.
- Quando entregar mudanças, diga **quais arquivos mudaram** e **quais comandos rodar** (ver seção 4).
- Seja honesto sobre o que foi e o que não foi testado (seção 8).

## 2. Objetivo do projeto
App em **Streamlit** sobre os dados abertos do **TSE** (Tribunal Superior Eleitoral), para a **Bahia**, eleições gerais **2018**, **2022**, **2026 (1º turno)** e municipais **2016**, **2020**, **2024** (incluídas em 14/10/2026), mais os resultados históricos de **1960 a 1990** (incluídos em 24/10/2026 — ver seção 8c; só o resultado consolidado do estado, sem município/escola):
- Filtrar por ano, turno, cargo, município, bairro/localidade, escola e seção (nos anos de 1960 a 1990, só ano/turno/cargo — ver seção 8c).
- Mostrar **sempre a votação nominal** (sem branco, nulo e voto de legenda).
- Clicar no candidato → votação dele **por escola** no município.
- **Comparar** a votação do candidato por escola entre 2022 e 2026.
- **Mapa** das escolas (latitude/longitude do arquivo do TSE).
- Mostrar o **nome de urna** do candidato (não o nome completo).
- Tela para o usuário **informar manualmente o bairro** das escolas.

## 3. Arquivos (todos na mesma pasta; os dados ficam em `dados/`)
| Arquivo | Função |
|---|---|
| `baixar_dados.py` | Baixa do TSE, para 2022 e 2026 (UF `BA`): votação por seção, eleitorado por local de votação (traz bairro e lat/lon) e cadastro de candidatos (traz nome de urna). Descompacta só o CSV da BA. `--atualizar` baixa tudo de novo. Mostra colunas e linhas por turno. |
| `preparar_dados.py` | Transforma os CSVs grandes (~4 milhões de linhas, lidos em pedaços) em arquivos pequenos: `dados/votos_por_municipio.csv`, `dados/municipios/<cod>.csv` (por seção, todos os anos), `dados/municipios_indice.csv`. Junta bairro/coordenadas e troca o nome do candidato pelo nome de urna. |
| `app.py` | O app Streamlit. |
| `compactar_dados.py` | Converte o resultado do `preparar_dados.py` para Parquet na pasta `dados_app/` (1,4 GB → ~77 MB). É a pasta `dados_app/` que vai para o GitHub e é usada pelo app publicado (o app usa `dados_app/` se existir, senão `dados/`). |
| `preparar_candidatos.py` | Lê o cadastro de candidatos e as fotos do TSE (`foto_cand<ano>_BA_div.zip`) e grava `dados_app/candidatos.parquet` (sigla do partido, situação eleito/suplente/2º turno, `SG_UE`) e as fotos em miniatura (JPEG 81×108, binário) em `dados_app/fotos/<ano>/<UE>.parquet` — UE = `BA` nas gerais e o código do município nas municipais; o app só carrega as do município necessário. É chamado no fim do `compactar_dados.py`. Precisa de `pillow` (só no computador). |
| `supabase_criar_tabela.sql` | Cria a tabela `bairros_informados` no Supabase (com os bairros já cadastrados). Rodar uma vez no SQL Editor. |
| `requirements.txt` | Bibliotecas para o Streamlit Cloud. |
| `dados/bairros_informados.csv` | Criado pelo app (tela de cadastro). Colunas: `CD_MUNICIPIO, NR_ZONA, NM_LOCAL_N, NM_LOCAL_VOTACAO, BAIRRO`. É trabalho do usuário: **nunca apagar nem sobrescrever** sem avisar. |
| `baixar_dados_historico.py` | Baixa do TSE os resultados de 1960 a 1990 (só existem consolidados por estado, não por seção): votação por candidato, detalhe da apuração, votação por partido, vagas e legendas. Grava em `dados/historico/`. Ver seção 8c. |
| `preparar_dados_historico.py` | Filtra a Bahia nesses arquivos e gera `dados/historico/votos_historico_ba.csv` e `resumo_estadual_ba.csv`. |

Dependências: `pip install requests pandas streamlit pydeck` (pydeck é opcional: sem ele o mapa usa `st.map`).

## 4. Como rodar (ordem)
```
python baixar_dados.py
python preparar_dados.py
python baixar_dados_historico.py
python preparar_dados_historico.py
python compactar_dados.py
streamlit run app.py
```
Para atualizar o app publicado: rodar os cinco scripts e depois `git add -A`, `git commit -m "atualiza dados"`, `git push`.
Repetir os dois primeiros quando o TSE atualizar os arquivos (ex.: depois do 2º turno, com `--atualizar`). Os dois de histórico (1960-1990) não mudam de um ano para o outro — só rodar de novo se quiser conferir se o TSE revisou algo. Mudou só o `app.py`? Basta reiniciar o Streamlit.

## 5. Fontes do TSE (Portal de Dados Abertos, CDN `https://cdn.tse.jus.br/estatistica/sead/odsele`)
- `votacao_secao/votacao_secao_{ano}_BA.zip`
- `eleitorado_locais_votacao/eleitorado_local_votacao_{ano}.zip` (todas as UFs)
- `consulta_cand/consulta_cand_{ano}.zip` (um CSV por UF + BRASIL; usa-se o `_BA.csv`)
- Fotos: `https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes{ano}/fotos/foto_cand{ano}_BA_div.zip` (arquivos `FBA<SQ_CANDIDATO>_div.jpg`)

Formato dos CSVs: separador `;`; codificação **latin-1 em 2022, mas 2026 pode ser UTF-8** → os scripts detectam sozinhos (`detectar_encoding`). Colunas da votação por seção usadas: `NR_TURNO, CD_MUNICIPIO, NM_MUNICIPIO, NR_ZONA, NR_SECAO, DS_CARGO, NR_VOTAVEL, NM_VOTAVEL, QT_VOTOS, NR_LOCAL_VOTACAO, SQ_CANDIDATO, NM_LOCAL_VOTACAO, DS_LOCAL_VOTACAO_ENDERECO`.

## 6. Regras de negócio e decisões importantes
- **Votação nominal**: excluir `NR_VOTAVEL` 95, 96, 97, 98 (branco/nulo) e, nos cargos de deputado, números de 2 dígitos (= legenda/partido). Função `so_nominais` no `app.py`.
- **Nome de urna**: `preparar_dados.py` liga `SQ_CANDIDATO` (votação) a `NM_URNA_CANDIDATO` (cadastro) e sobrescreve `NM_VOTAVEL` antes de agregar. Quem não é achado mantém o nome original. O script imprime "nome de urna aplicado em X%".
- **Bairro e coordenadas** vêm de outro arquivo (eleitorado por local de votação) e são ligados por (ano, município, zona, local) ignorando zeros à esquerda. Coordenadas: vírgula decimal convertida; fora do Brasil (lat −34..6, lon −74..−34) é descartada; no app, escola a mais de 1,2° da mediana do município é ignorada no mapa (`LIMITE_GRAUS`).
- **Bairro informado pelo usuário** (`dados/bairros_informados.csv`) tem **prioridade** sobre o do TSE; vale para todos os anos; chave = município + zona (sem zeros) + nome da escola normalizado (sem acento, maiúsculo). Vazio = volta ao do TSE. O cache do app é invalidado pela data do arquivo (`versao_bairros()`).
- **Comparação 2022 × 2026**: candidato correspondente achado pelo **nome de urna normalizado**; se não achar, o usuário escolhe na lista. Escolas pareadas por "nome + zona" ou "número do local + zona" (o usuário escolhe). Tabela: Votos antigo/novo, Diferença, Variação (%), Situação (nos dois anos / só em um).
- **Lista de candidatos** (visual tipo ranking): foto, posição, nome de urna, selo (Eleito/2º turno/Suplente), partido · nº, votos, % e barra. Partido e situação vêm do cadastro (`SG_PARTIDO`, `DS_SIT_TOT_TURNO`), ligados por ano + turno + cargo + número; sem cadastro, o partido sai do voto de legenda. Tema em `.streamlit/config.toml`.
- **Eleições municipais**: voto de legenda de **vereador** também é tirado (`so_nominais`). Cadastro/fotos ligados por ano + turno + cargo + **UE** + número (números de prefeito/vereador se repetem entre cidades). Com "Todos os municípios" e cargo municipal, o ranking tem uma linha por candidato **e cidade** (coluna Município) e a % é dentro da própria cidade. A faixa diz "Eleição Municipal" nos anos múltiplos de 4.
- **"Todos os municípios" com cargo estadual/federal** (governador, senador, deputado estadual/federal): a lista de candidatos é clicável igual à de um município só; ao clicar, mostra a trajetória do candidato, a votação dele **por município** (do maior para o menor, `mostrar_candidato_por_municipio`) e o comparativo com até `MAX_COMPARAR` outros candidatos **por município**, dentro da mesma eleição (`mostrar_comparativo_municipios`, mesmo estilo visual do comparativo por bairro/escola). Com cargo municipal (prefeito/vereador), a lista continua **não clicável** nesse modo, porque cada linha já é uma cidade (o número se repete entre cidades, então não dá para somar por município).
- `preparar_dados.py` padroniza `DS_CARGO` com `.str.title()` (2016 vem em maiúsculas). A comparação sugere a eleição mais próxima do **mesmo tipo** (municipal↔municipal, geral↔geral). O cadastro de candidatos é carregado só do ano escolhido (`carregar_candidatos(ano)`).
- **Celular**: `eh_celular()` olha o navegador (`st.context.headers` User-Agent: Mobi/Android/iPhone). No celular, a escolha de tela vai para o topo e os filtros para um `st.expander("Filtros")` (variável `painel`); no computador, `painel = st.sidebar`. Para forçar: `?celular=1` ou `?celular=0` no endereço.
- A API do DivulgaCand (fotos online do TSE) responde 403 a acessos de fora; por isso as fotos ficam no projeto.
- Texto de interface em português; tabelas com cabeçalhos em português.

## 7. Estrutura do `app.py`
Tela na barra lateral (`Votação` | `Cadastrar bairros das escolas`) → filtros (ano, turno, cargo, município, pesquisa de bairro + lista de bairros, escola, seção) → métricas → dados da escola/seções → "Mapa das escolas" → Top 10 → tabela clicável de candidatos (`on_select="rerun"`, com alternativa para Streamlit antigo) → votação por escola + mapa do candidato → comparação entre anos + mapa da diferença + CSVs. Memória: `carregar_municipio(codigo, versao, anos)` lê do Parquet **só os anos pedidos** (o ano escolhido; o da comparação é lido à parte) e guarda os textos como `category` (Salvador: ~554 MB → ~30 MB por ano). Por isso todo agrupamento usa `agrupar()` (observed=True) e o resultado passa por `texto()` (volta a texto comum). Cache de municípios limitado (`max_entries=6`). Funções-chave: `so_nominais`, `carregar_municipio(codigo, versao, anos)`, `agregar_escolas`, `escolas_com_votos`, `chave_escola`, `preparar_para_comparar`, `desenhar_mapa`, `tela_cadastro`, `renderizar_lista_candidatos` (lista clicável genérica, usada tanto por município quanto por escola), `mostrar_candidato_por_municipio`, `mostrar_comparativo_municipios`, `mostrar_trajetoria`/`trajetoria` (todas as eleições do candidato, pelo `ID_PESSOA` do cadastro do TSE). Para 1960-1990: logo depois do `selectbox` de ano, se o ano escolhido só existir no histórico, o app desvia para `mostrar_resultado_historico(ano, hist_ano)` e para (`st.stop()`) — o resto do fluxo (município, escola, mapa, comparação) nem roda. Dados vêm de `carregar_historico()`/`carregar_historico_resumo()`.

## 8. O que foi testado e o que NÃO foi
**Testado** (com dados **fictícios** no formato do TSE e um Streamlit/pydeck **simulados**, porque o ambiente de desenvolvimento não conseguia instalar as bibliotecas): lógica de filtros, votos nominais, ranking, comparação, pareamento de escolas, mapas (dados enviados ao pydeck), nome de urna, cadastro de bairros, dois encodings, ausência de arquivos.

**NÃO confirmado com dados reais — verificar primeiro quando o usuário reportar problema:**
1. Nomes reais das colunas: `NM_BAIRRO`, `NR_LATITUDE`, `NR_LONGITUDE` (eleitorado por local de votação) e `NM_URNA_CANDIDATO`, `SQ_CANDIDATO` (cadastro). Os scripts imprimem as colunas; se diferirem, ajustar `preparar_dados.py` (`primeira_coluna`, `ler_locais`, `ler_nomes_de_urna`).
2. Se o arquivo de votação de 2026 da Bahia já traz o 1º turno e `SQ_CANDIDATO`.
3. Se nomes/números das escolas permanecem iguais entre 2022 e 2026.
4. A aparência real do app e do mapa no navegador (nunca foi visto).
5. O comportamento de `st.data_editor` e do botão Salvar no Streamlit real.

## 8b. Publicação (desde 13/10/2026)
- Código + `dados_app/` no GitHub (repositório público). A pasta `dados/` NÃO vai para o GitHub (`.gitignore`).
- App publicado no **Streamlit Community Cloud** (a Vercel não roda Streamlit). Arquivo principal: `app.py`.
- Segredos (Streamlit Cloud > Settings > Secrets): `SUPABASE_URL`, `SUPABASE_KEY` (chave **service_role**, nunca no código) e `SENHA_CADASTRO` (protege a tela de cadastro). Sem `SUPABASE_*`, o app usa o CSV local.
- Com Supabase, os bairros ficam na tabela `bairros_informados` (colunas em minúsculo); RLS ligado sem políticas = só a chave service_role acessa.
- Testado localmente (AppTest, dados reais): abrir o app, Itamaraju com bairros informados, Salvador, tela de cadastro. **Não testado**: gravação no Supabase de verdade e memória do Streamlit Cloud com Salvador (~600 MB na memória).

## 8c. Resultados históricos (1960–1990) — em andamento, ainda não integrado ao app
- Objetivo: ter o resultado das eleições na Bahia desde 1960. O TSE **não tem** votação por seção nem por município para esse período — só o resultado consolidado do **estado inteiro**, digitalizado a partir de atas e mapas de apuração em papel. Por isso é um pipeline separado do `baixar_dados.py`/`preparar_dados.py` (que são para 2016–2026, com seção/escola).
- `baixar_dados_historico.py` — baixa de `cdn.tse.jus.br/estatistica/sead/odsele` os arquivos "_UF" (votação por candidato, detalhe da apuração, votação por partido, vagas, legendas) para os 11 anos em que esse formato existe: **1960, 1962, 1965, 1966, 1970, 1974, 1978, 1982, 1986, 1989, 1990**. Grava em `dados/historico/`.
- `preparar_dados_historico.py` — lê os TXT (sem cabeçalho, `;`, aspas, **sempre latin-1**, sentinelas `#NULO#`/`-1` = em branco e `#NE#`/`-3` = não existia esse registro na época), filtra `SIGLA_UF == "BA"` e gera `dados/historico/votos_historico_ba.csv` (um candidato por linha: ano, turno, cargo, nome de urna, partido, situação, votos) e `dados/historico/resumo_estadual_ba.csv` (comparecimento/abstenção/brancos/nulos por ano-turno-cargo). Sem seção/município, não gera bairro, mapa nem foto.
- **Testado com os 11 anos, dados reais baixados do TSE** (2.957 candidatos no total): o layout (nº de colunas) é o mesmo em todos os anos — o script `preparar_dados_historico.py` valida isso e aborta com mensagem clara se algum ano vier diferente. Números conferem com a história: Jânio Quadros eleito presidente em 1960 (255.530 votos na BA), Lomanto Júnior eleito governador em 1962 (396.051 votos, contra Waldir Pires).
- Ao contrário do que eu tinha concluído só com 1960: a maioria dos anos (1962, 1966, 1970, 1974, 1978, 1982, 1986, 1990) **também tem Deputado Federal e Deputado Estadual**, não só os cargos majoritários. Só 1960 e 1989 trouxeram apenas Presidente/Vice (eram eleições presidenciais isoladas). Prefeito e Vereador continuam fora (são eleições municipais, com calendário próprio, fora do escopo "_UF"). **1965 não teve eleição na Bahia** (foi eleição de Governador só em 11 estados, SP/RJ/MG entre eles — confirmado olhando o arquivo bruto: a BA não está na lista de UFs daquele ano).
- Os ZIPs de alguns anos (1962, 1966, 1970, 1974, 1978, 1982, 1986, 1990) trazem **um arquivo por UF** dentro do ZIP (ex.: `..._BA.txt`); outros (1960, 1965, 1989) trazem um único arquivo nacional. O `baixar_dados_historico.py` já identifica e extrai o arquivo certo da Bahia em ambos os casos.
- Limitação pontual notada: em 1962, a sigla/nome do partido (`SIGLA_PARTIDO`/`NOME_PARTIDO`) vem vazia em **todas** as linhas (sentinela `#NE#` no arquivo original do TSE, não é falha do script) — a informação de legenda ainda aparece em `COMPOSICAO_LEGENDA` (ex.: "PST / UDN / PTB / PR").
- **Integrado ao `app.py`** (testado com `AppTest`, dados reais, anos 1960 e 1982): o seletor "Ano da eleição" junta os anos modernos (2016-2026) com os históricos (1960-1990, lidos de `carregar_historico()`). Ao escolher um ano histórico, o app pula direto para `mostrar_resultado_historico()`: mostra só Turno, Cargo, as métricas (total de votos, candidatos, comparecimento, abstenções) e o ranking de candidatos (mesmo cartão visual da lista normal — foto fica com as iniciais, já que não há foto; sem número quando ele não existia na época, ex.: Presidente antes de 1982); não aparecem município, bairro, escola, seção, mapa nem comparação entre anos, porque esse detalhe não existe para esse período. Um aviso no painel de filtros explica isso ao usuário.
- `compactar_dados.py` agora também gera `dados_app/votos_historico_ba.parquet` e `dados_app/resumo_estadual_ba.parquet` (só se os CSVs de `dados/historico/` existirem) — vão para o GitHub junto com o resto de `dados_app/`.
- Cargos disponíveis variam por ano, porque até 1990 cada estado tinha seu próprio calendário para eleição de Governador (não havia unificação com a eleição presidencial).

## 9. Backlog de ideias (só se o usuário pedir)
- Importar bairros a partir de planilha (CSV/Excel) preenchida fora do app.
- Filtro/mapa por zona eleitoral; exportar relatório por bairro.
- Outros turnos/cargos/estados; deixar o `UF` configurável.

## 10. Regras para quem continuar
1. Não quebrar o que já funciona; mudanças pequenas e testadas.
2. Antes de entregar, rodar uma checagem de sintaxe (`python -I -c "import ast; ast.parse(open('app.py', encoding='utf-8').read())"`) e, se possível, testar com dados de mentira.
3. Não inventar nomes de coluna: confirmar pelos arquivos reais em `dados/` (`head -3`) quando houver dúvida.
4. Nunca apagar `dados/` nem `bairros_informados.csv` sem pedir.
5. Se o usuário colar mensagem de erro ou imagem do terminal, diagnosticar a partir dela antes de mudar código.
