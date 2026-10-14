# Projeto: Eleições Bahia (dados abertos do TSE) — documento de continuidade

> Leia este arquivo inteiro antes de mexer em qualquer coisa. Ele descreve o que existe, como funciona, o que já foi testado e o que ainda NÃO foi confirmado.

## 1. Quem é o usuário e como trabalhar com ele
- Brasileiro (Bahia), **não é programador**. Responder sempre em **português do Brasil**, com linguagem simples, passo a passo, sem jargão.
- Ele roda os scripts no próprio computador (terminal) e vê o app no navegador. Dê comandos prontos para copiar e colar.
- Quando entregar mudanças, diga **quais arquivos mudaram** e **quais comandos rodar** (ver seção 4).
- Seja honesto sobre o que foi e o que não foi testado (seção 8).

## 2. Objetivo do projeto
App em **Streamlit** sobre os dados abertos do **TSE** (Tribunal Superior Eleitoral), para a **Bahia**, eleições **2022** e **2026 (1º turno)**:
- Filtrar por ano, turno, cargo, município, bairro/localidade, escola e seção.
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
| `preparar_candidatos.py` | Lê o cadastro de candidatos e as fotos do TSE (`foto_cand<ano>_BA_div.zip`) e grava `dados_app/candidatos.parquet`: sigla do partido, situação (eleito/suplente/2º turno) e foto em miniatura (base64). É chamado no fim do `compactar_dados.py`. Precisa de `pillow` (só no computador). |
| `supabase_criar_tabela.sql` | Cria a tabela `bairros_informados` no Supabase (com os bairros já cadastrados). Rodar uma vez no SQL Editor. |
| `requirements.txt` | Bibliotecas para o Streamlit Cloud. |
| `dados/bairros_informados.csv` | Criado pelo app (tela de cadastro). Colunas: `CD_MUNICIPIO, NR_ZONA, NM_LOCAL_N, NM_LOCAL_VOTACAO, BAIRRO`. É trabalho do usuário: **nunca apagar nem sobrescrever** sem avisar. |

Dependências: `pip install requests pandas streamlit pydeck` (pydeck é opcional: sem ele o mapa usa `st.map`).

## 4. Como rodar (ordem)
```
python baixar_dados.py
python preparar_dados.py
python compactar_dados.py
streamlit run app.py
```
Para atualizar o app publicado: rodar os três scripts e depois `git add -A`, `git commit -m "atualiza dados"`, `git push`.
Repetir os dois primeiros quando o TSE atualizar os arquivos (ex.: depois do 2º turno, com `--atualizar`). Mudou só o `app.py`? Basta reiniciar o Streamlit.

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
- Texto de interface em português; tabelas com cabeçalhos em português.

## 7. Estrutura do `app.py`
Tela na barra lateral (`Votação` | `Cadastrar bairros das escolas`) → filtros (ano, turno, cargo, município, pesquisa de bairro + lista de bairros, escola, seção) → métricas → dados da escola/seções → "Mapa das escolas" → Top 10 → tabela clicável de candidatos (`on_select="rerun"`, com alternativa para Streamlit antigo) → votação por escola + mapa do candidato → comparação entre anos + mapa da diferença + CSVs. Funções-chave: `so_nominais`, `carregar_municipio(codigo, versao)`, `agregar_escolas`, `escolas_com_votos`, `chave_escola`, `preparar_para_comparar`, `desenhar_mapa`, `tela_cadastro`.

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
