# Projeto: Eleições Bahia (dados abertos do TSE) — documento de continuidade

> Leia este arquivo inteiro antes de mexer em qualquer coisa. Ele descreve o que existe, como funciona, o que já foi testado e o que ainda NÃO foi confirmado.

## 1. Quem é o usuário e como trabalhar com ele
- Brasileiro (Bahia), **não é programador**. Responder sempre em **português do Brasil**, com linguagem simples, passo a passo, sem jargão.
- Ele roda os scripts no próprio computador (terminal) e vê o app no navegador. Dê comandos prontos para copiar e colar.
- Quando entregar mudanças, diga **quais arquivos mudaram** e **quais comandos rodar** (ver seção 4).
- Seja honesto sobre o que foi e o que não foi testado (seção 8).

## 2. Objetivo do projeto
App em **Streamlit** sobre os dados abertos do **TSE** (Tribunal Superior Eleitoral), para a **Bahia**, eleições gerais **2018**, **2022**, **2026 (1º turno)** e municipais **2016**, **2020**, **2024** (incluídas em 14/10/2026), mais todos os pleitos de **1960 a 2014** (incluídos em 24/10/2026 — ver seções 8c e 8d): 1960-1990 só o resultado consolidado do estado (sem município/escola); 1994-2014 por município (sem bairro/escola/seção/mapa):
- Filtrar por ano, turno, cargo, município, bairro/localidade, escola e seção (1960-1990: só ano/turno/cargo; 1994-2014: + município — ver seções 8c/8d).
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
| `baixar_dados_intermediario.py` | Baixa do TSE a votação por candidato, município e zona de 1994 a 2014 (Brasil inteiro; extrai só o CSV da Bahia). Grava em `dados/intermediario/`. Ver seção 8d. |
| `preparar_dados_intermediario.py` | Soma os votos por zona e gera `dados/intermediario/votos_intermediario_ba.csv` (um candidato por município/ano/turno/cargo). |

Dependências: `pip install requests pandas streamlit pydeck` (pydeck é opcional: sem ele o mapa usa `st.map`).

## 4. Como rodar (ordem)
```
python baixar_dados.py
python preparar_dados.py
python baixar_dados_historico.py
python preparar_dados_historico.py
python baixar_dados_intermediario.py
python preparar_dados_intermediario.py
python compactar_dados.py
streamlit run app.py
```
Para atualizar o app publicado: rodar os sete scripts e depois `git add -A`, `git commit -m "atualiza dados"`, `git push`.
Repetir os dois primeiros quando o TSE atualizar os arquivos (ex.: depois do 2º turno, com `--atualizar`). Os quatro de histórico/intermediário (1960-2014) não mudam de um ano para o outro — só rodar de novo se quiser conferir se o TSE revisou algo. Mudou só o `app.py`? Basta reiniciar o Streamlit.

## 5. Fontes do TSE (Portal de Dados Abertos, CDN `https://cdn.tse.jus.br/estatistica/sead/odsele`)
- `votacao_secao/votacao_secao_{ano}_BA.zip`
- `eleitorado_locais_votacao/eleitorado_local_votacao_{ano}.zip` (todas as UFs)
- `consulta_cand/consulta_cand_{ano}.zip` (um CSV por UF + BRASIL; usa-se o `_BA.csv`)
- Fotos: `https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes{ano}/fotos/foto_cand{ano}_BA_div.zip` (arquivos `FBA<SQ_CANDIDATO>_div.jpg`)
- **Presidente** (só nas eleições gerais, UE "BR"), em arquivos à parte: `votacao_secao/votacao_secao_{ano}_BR.zip` (Brasil inteiro, ~250 MB; o `baixar_dados.py` guarda só as linhas da Bahia em `dados/presidente_secao_{ano}_BA.csv`), `consulta_cand_{ano}_BR.csv` (dentro do ZIP do cadastro) e `foto_cand{ano}_BR_div.zip` (arquivos `FBR<SQ>_div.jpg`).

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
Tela na barra lateral (`Votação` | `Cadastrar bairros das escolas`) → filtros (ano, turno, cargo, município, pesquisa de bairro + lista de bairros, escola, seção) → métricas → dados da escola/seções → "Mapa das escolas" → Top 10 → tabela clicável de candidatos (`on_select="rerun"`, com alternativa para Streamlit antigo) → votação por escola + mapa do candidato → comparação entre anos + mapa da diferença + CSVs. Memória: `carregar_municipio(codigo, versao, anos)` lê do Parquet **só os anos pedidos** (o ano escolhido; o da comparação é lido à parte) e guarda os textos como `category` (Salvador: ~554 MB → ~30 MB por ano). Por isso todo agrupamento usa `agrupar()` (observed=True) e o resultado passa por `texto()` (volta a texto comum). Cache de municípios limitado (`max_entries=6`). Funções-chave: `so_nominais`, `carregar_municipio(codigo, versao, anos)`, `agregar_escolas`, `escolas_com_votos`, `chave_escola`, `preparar_para_comparar`, `desenhar_mapa`, `tela_cadastro`, `renderizar_lista_candidatos` (lista clicável genérica, usada tanto por município quanto por escola), `mostrar_candidato_por_municipio`, `mostrar_comparativo_municipios`, `mostrar_trajetoria`/`trajetoria` (todas as eleições do candidato, pelo `ID_PESSOA` do cadastro do TSE). Para 1960-2014: logo depois do `selectbox` de ano, se o ano escolhido só existir no histórico (1960-1990) ou no intermediário (1994-2014), o app desvia para `mostrar_resultado_historico(ano, hist_ano)` e para (`st.stop()`) — o resto do fluxo (escola, mapa, comparação) nem roda; o seletor de Município aparece dentro dessa função só quando o ano tiver mais de um município (1994-2014). Dados vêm de `carregar_historico()` (junta histórico + intermediário) e `carregar_historico_resumo()` (só 1960-1990).

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
- Se o Supabase não responder (ex.: projeto pausado no plano gratuito, ou `SUPABASE_URL` errado — aparece como `ConnectionError`/`gaierror`), `ler_bairros_informados()` não derruba mais o app: a votação segue com os bairros do TSE e mostra um aviso; a tela de cadastro fica bloqueada até ele voltar (para não salvar em cima de uma lista que pareceria vazia). Corrigido em 24/10/2026, depois de quebrar a tela de Itamaraju no app publicado.
- Memória: os dados de 1960-2014 (`carregar_historico`) são lidos só com as colunas usadas e com os textos como `category` (~25 MB em vez de ~250 MB), por causa do limite de memória do Streamlit Cloud.
- Testado localmente (AppTest, dados reais): abrir o app, Itamaraju com bairros informados, Salvador, tela de cadastro. **Não testado**: gravação no Supabase de verdade e memória do Streamlit Cloud com Salvador (~600 MB na memória).

## 8b2. VPS Hostinger (em instalação desde 25/10/2026)
- Objetivo: o app rodar numa VPS Ubuntu 24.04 da Hostinger, com banco PostgreSQL próprio no lugar do Supabase. Os votos continuam sendo os Parquet de `dados_app/` (vêm do GitHub); o banco só guarda a tabela `bairros_informados`. Baixar/preparar dados do TSE continua no computador do usuário.
- `app.py`: se houver o segredo `DATABASE_URL`, usa o PostgreSQL (psycopg); senão Supabase (`SUPABASE_URL`/`SUPABASE_KEY`); senão o CSV local. Se o banco não responder, mostra aviso e bloqueia o cadastro (flag `banco_fora`).
- Pasta `vps/`: `instalar.sh` (instala tudo como root: pacotes, usuário `eleicoes`, PostgreSQL + `estrutura.sql`, ambiente Python, `secrets.toml`, serviço `app-tse`, Nginx com websocket, firewall, backup diário em `/var/backups/app-tse`, HTTPS se tiver domínio), `ativar_https.sh` (HTTPS depois), `atualizar.sh` (`git fetch --depth 1` + `reset --hard` + reinicia), `importar_bairros.py` (copia os bairros do Supabase ou de um CSV para o banco da VPS; pode rodar várias vezes).
- Testado no computador com PostgreSQL temporário (pgserver): estrutura, importação por CSV, leitura e gravação pelo app, banco fora do ar. **Não testado ainda**: os scripts `.sh` numa VPS de verdade.
- Na VPS: app em `/opt/app-tse`, logs com `journalctl -u app-tse`, reiniciar com `systemctl restart app-tse`.

## 8c. Resultados históricos (1960–1990)
- Objetivo: ter o resultado das eleições na Bahia desde 1960. O TSE **não tem** votação por seção nem por município para esse período — só o resultado consolidado do **estado inteiro**, digitalizado a partir de atas e mapas de apuração em papel. Por isso é um pipeline separado do `baixar_dados.py`/`preparar_dados.py` (que são para 2016–2026, com seção/escola).
- `baixar_dados_historico.py` — baixa de `cdn.tse.jus.br/estatistica/sead/odsele` os arquivos "_UF" (votação por candidato, detalhe da apuração, votação por partido, vagas, legendas) para os 11 anos em que esse formato existe: **1960, 1962, 1965, 1966, 1970, 1974, 1978, 1982, 1986, 1989, 1990**. Grava em `dados/historico/`.
- `preparar_dados_historico.py` — lê os TXT (sem cabeçalho, `;`, aspas, **sempre latin-1**, sentinelas `#NULO#`/`-1` = em branco e `#NE#`/`-3` = não existia esse registro na época), filtra `SIGLA_UF == "BA"` e gera `dados/historico/votos_historico_ba.csv` (um candidato por linha: ano, turno, cargo, nome de urna, partido, situação, votos) e `dados/historico/resumo_estadual_ba.csv` (comparecimento/abstenção/brancos/nulos por ano-turno-cargo). Sem seção/município, não gera bairro, mapa nem foto.
- **Testado com os 11 anos, dados reais baixados do TSE** (2.957 candidatos no total): o layout (nº de colunas) é o mesmo em todos os anos — o script `preparar_dados_historico.py` valida isso e aborta com mensagem clara se algum ano vier diferente. Números conferem com a história: Jânio Quadros eleito presidente em 1960 (255.530 votos na BA), Lomanto Júnior eleito governador em 1962 (396.051 votos, contra Waldir Pires).
- Ao contrário do que eu tinha concluído só com 1960: a maioria dos anos (1962, 1966, 1970, 1974, 1978, 1982, 1986, 1990) **também tem Deputado Federal e Deputado Estadual**, não só os cargos majoritários. Só 1960 e 1989 trouxeram apenas Presidente/Vice (eram eleições presidenciais isoladas). Prefeito e Vereador continuam fora (são eleições municipais, com calendário próprio, fora do escopo "_UF"). **1965 não teve eleição na Bahia** (foi eleição de Governador só em 11 estados, SP/RJ/MG entre eles — confirmado olhando o arquivo bruto: a BA não está na lista de UFs daquele ano).
- Os ZIPs de alguns anos (1962, 1966, 1970, 1974, 1978, 1982, 1986, 1990) trazem **um arquivo por UF** dentro do ZIP (ex.: `..._BA.txt`); outros (1960, 1965, 1989) trazem um único arquivo nacional. O `baixar_dados_historico.py` já identifica e extrai o arquivo certo da Bahia em ambos os casos.
- Limitação pontual notada: em 1962, a sigla/nome do partido (`SIGLA_PARTIDO`/`NOME_PARTIDO`) vem vazia em **todas** as linhas (sentinela `#NE#` no arquivo original do TSE, não é falha do script) — a informação de legenda ainda aparece em `COMPOSICAO_LEGENDA` (ex.: "PST / UDN / PTB / PR").
- **Integrado ao `app.py`** (testado com `AppTest`, dados reais): o seletor "Ano da eleição" junta os anos modernos (2016-2026) com os históricos. Ao escolher 1960-1990, o app pula direto para `mostrar_resultado_historico()`: Turno, Cargo, métricas (total de votos, candidatos, comparecimento, abstenções) e o ranking de candidatos (mesmo cartão visual de sempre — foto fica com as iniciais; sem número quando ele não existia na época, ex.: Presidente antes de 1982); não aparecem município, bairro, escola, seção, mapa nem comparação entre anos. Um aviso no painel de filtros explica isso ao usuário.
- `compactar_dados.py` também gera `dados_app/votos_historico_ba.parquet` e `dados_app/resumo_estadual_ba.parquet` (só se os CSVs de `dados/historico/` existirem).
- Cargos disponíveis variam por ano, porque até 1990 cada estado tinha seu próprio calendário para eleição de Governador (não havia unificação com a eleição presidencial).

## 8c2. Presidente em 2018, 2022 e 2026 (incluído em 24/10/2026)
- Antes não aparecia: o arquivo de seção da Bahia (`votacao_secao_{ano}_BA`) não traz Presidente. O `preparar_dados.py` agora lê, por ano, o arquivo da Bahia e também `presidente_secao_{ano}_BA.csv` (função `processar_arquivo`), então Presidente tem tudo igual aos outros cargos: município, bairro, escola, seção, mapa, comparação, foto e selo.
- No app, o cadastro do Presidente é procurado na UE "BR" (os demais cargos estaduais/federais, "BA"); na trajetória e na comparação entre anos, "BR" vale como "BA" (votos na Bahia inteira).
- Conferido (AppTest, dados reais): Lula com 72,12% na Bahia no 2º turno de 2022 (foto, selo "Eleito", PT nº 13); Haddad com selo "2º turno" em 2018; votação por escola em Itamaraju e Salvador.
- **Candidatos substituídos com o mesmo número** (ex.: Lula em 2018, trocado por Haddad no nº 13): o cadastro do TSE guarda os dois, e o substituído fica com situação `#NULO#`. Como o app acha o candidato pelo número, o cartão de Haddad saía com a foto de Lula e sem selo, e a trajetória/comparação de Lula pegava os votos de Haddad. O `preparar_candidatos.py` agora fica só com a candidatura totalizada quando o número se repete (740 candidaturas descartadas, quase todas de prefeito/vereador substituídos; o problema já existia antes, sem ser notado).

## 8c3. Eleições municipais antes de 1996 — não existem nos dados abertos
- Verificado em 25/10/2026 pela API do portal (`dadosabertos.tse.jus.br/api/3/action/package_list`, 188 conjuntos): não há nenhum conjunto de 1972, 1976, 1985, 1988 nem 1992; os de 1958-1990 são só por UF e, na Bahia, não trazem Prefeito/Vereador (nem 1982, que teve municipal junto com a geral). O site do TRE-BA bloqueia acesso automático (403). Outros TREs (MS, PI) publicam 1988/1992 em PDF, mas só dos próprios estados.
- Decisão do usuário: só avisar no app. Há uma legenda embaixo do seletor de ano ("Prefeito e vereador só a partir de 1996..."). Se um dia vierem os dados (ex.: pedido ao TRE-BA pela Lei de Acesso à Informação), basta gerar um CSV no formato de `votos_historico_ba.csv` (com `NM_MUNICIPIO` real) e juntá-lo em `carregar_historico()`.

## 8d. Resultados do período intermediário (1994–2014)
- Entre o histórico de papel (1960-1990) e o layout atual (2016-2026) tem um terceiro formato, que já é digital e por município, mas ainda não tem seção/escola/bairro/mapa de forma confiável. Cobre os 11 pleitos em que esse formato existe: **1994, 1996, 1998, 2000, 2002, 2004, 2006, 2008, 2010, 2012, 2014** (não existe 1992 nesse formato - antes disso só o histórico de papel).
- Fonte: `votacao_candidato_munzona_{ano}.zip` (`dadosabertos.tse.jus.br`, um arquivo com o Brasil inteiro, UTF-8/latin-1 com cabeçalho) — diferente do histórico de papel, **já vem com nome de urna, partido e situação prontos** (não precisa cruzar com cadastro separado). Granularidade: candidato por **município e zona**; não tem seção, não tem nome/bairro/coordenada de escola (`eleitorado_locais_votacao` só existe de forma confiável a partir de 2010, e mesmo assim a votação por seção desse período tem layout instável ano a ano — por isso optei por não tentar seção aqui, só município).
- `baixar_dados_intermediario.py` baixa e extrai o CSV da Bahia de cada ano para `dados/intermediario/`. `preparar_dados_intermediario.py` lê (com cabeçalho, por nome de coluna), **soma os votos por zona** (o arquivo original tem uma linha por zona eleitoral) e gera `dados/intermediario/votos_intermediario_ba.csv` no mesmo formato de colunas do histórico de 1960-1990 (`ANO, NR_TURNO, NM_MUNICIPIO, DS_CARGO, NR_VOTAVEL, NM_VOTAVEL, ..., QT_VOTOS`), só que aqui `NM_MUNICIPIO` é o nome real do município, não um placeholder.
- Achado raro: alguns candidatos (16 linhas em ~970 mil, todos em municípios pequenos, cargo Prefeito) aparecem duas vezes no mesmo turno com coligações diferentes - parecem ser retificações do próprio TSE. O script mantém o registro de maior votação e descarta o outro, para não duplicar o candidato na lista.
- **Testado com os 11 anos, dados reais** (969.781 candidaturas): números conferem com a história - Jaques Wagner (PT) eleito governador em 2006 com 3.242.336 votos (52,89%) no 1º turno; ACM Neto (DEM) eleito prefeito de Salvador em 2012 com 717.865 votos no 2º turno.
- **Integrado ao `app.py`**: `mostrar_resultado_historico()` agora também aceita esses anos - quando o ano tem mais de um município (ou seja, é 1994-2014, não 1960-1990), aparece o seletor de **Município** (com "Todos os municípios"). Com cargo municipal (Prefeito/Vereador) e "Todos os municípios", cada linha é candidato+cidade e a % é dentro da própria cidade - igual o fluxo moderno já faz (`por_cidade`). Sem comparecimento/abstenção nesses anos (esse resumo só existe para 1960-1990); sem bairro/escola/seção/mapa em nenhum dos dois períodos históricos.
- `compactar_dados.py` também gera `dados_app/votos_intermediario_ba.parquet`.
- **1998 e 2000**: o TSE deixou `QT_VOTOS_NOMINAIS` **todo zerado** nesses dois anos e pôs os votos só em `QT_VOTOS_NOMINAIS_VALIDOS`. O `preparar_dados_intermediario.py` detecta (soma do arquivo = 0) e usa a outra coluna, avisando no terminal. Conferido: César Borges (PFL) eleito governador em 1998 com 69,9%; Imbassahy (PFL) prefeito de Salvador em 2000 com 53,7%.
- **Presidente (1994, 1998, 2002, 2006, 2010, 2014)**: não vem no CSV `_BA` do ZIP; fica no `_BR` (ou, em 1998, só no `_BRASIL`, com todos os cargos do país). O `baixar_dados_intermediario.py` separa as linhas de Presidente na Bahia em `votacao_candidato_munzona_<ano>_PRESIDENTE_BA.csv`, que o preparar lê junto. Conferido: FHC com 52,4% na Bahia em 1994; Lula com 66,7% no 1º turno de 2006 e 78,1% no 2º. No 2º turno de 2006 o TSE deixou a situação em branco (`#NULO`), então o selo "Eleito" não aparece nesse turno.

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
