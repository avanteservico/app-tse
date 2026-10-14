-- Rode isto uma vez no Supabase: menu SQL Editor > New query > cole tudo > Run.
create table if not exists public.bairros_informados (
  cd_municipio     text not null,
  nr_zona          text not null,
  nm_local_n       text not null,
  nm_local_votacao text not null default '',
  bairro           text not null,
  primary key (cd_municipio, nr_zona, nm_local_n)
);

-- Segurança: ninguém de fora lê ou grava; só o app (com a chave secreta service_role).
alter table public.bairros_informados enable row level security;

-- Bairros que você já tinha cadastrado no computador (dados/bairros_informados.csv):
insert into public.bairros_informados (cd_municipio, nr_zona, nm_local_n, nm_local_votacao, bairro) values
  ('36137', '172', 'CENTRO EDUCACIONAL DE ITAMARAJU', 'CENTRO EDUCACIONAL DE ITAMARAJU', 'BNH'),
  ('36137', '172', 'COLEGIO LUIS EDUARDO MAGALHAES', 'COLEGIO LUIS EDUARDO MAGALHAES', 'JAQUEIRA'),
  ('36137', '172', 'ESCOLA MUNICIPAL REITOR EDGARD SANTOS', 'ESCOLA MUNICIPAL REITOR EDGARD SANTOS', 'BNH')
on conflict do nothing;
