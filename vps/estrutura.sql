-- Estrutura do banco do app na VPS (PostgreSQL). O instalar.sh roda isto sozinho.
-- É a mesma tabela que existia no Supabase (supabase_criar_tabela.sql), sem a parte específica do Supabase.
create table if not exists bairros_informados (
  cd_municipio     text not null,
  nr_zona          text not null,
  nm_local_n       text not null,
  nm_local_votacao text not null default '',
  bairro           text not null,
  primary key (cd_municipio, nr_zona, nm_local_n)
);

-- Bairros que já estavam no computador (dados/bairros_informados.csv); os do Supabase vêm pelo importar_bairros.py
insert into bairros_informados (cd_municipio, nr_zona, nm_local_n, nm_local_votacao, bairro) values
  ('36137', '172', 'CENTRO EDUCACIONAL DE ITAMARAJU', 'CENTRO EDUCACIONAL DE ITAMARAJU', 'BNH'),
  ('36137', '172', 'COLEGIO LUIS EDUARDO MAGALHAES', 'COLEGIO LUIS EDUARDO MAGALHAES', 'JAQUEIRA'),
  ('36137', '172', 'ESCOLA MUNICIPAL REITOR EDGARD SANTOS', 'ESCOLA MUNICIPAL REITOR EDGARD SANTOS', 'BNH')
on conflict do nothing;
