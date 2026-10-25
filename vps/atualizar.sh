#!/usr/bin/env bash
# Traz a versão nova do app e dos dados (o que foi enviado ao GitHub) e reinicia o app.
# Uso: bash /opt/app-tse/vps/atualizar.sh
# Esta pasta só serve para rodar o app: alterações feitas direto nela são descartadas
# (os segredos e o ambiente Python não são afetados).
set -euo pipefail
PASTA=/opt/app-tse
cd "$PASTA"
sudo -u eleicoes git fetch --depth 1 origin main
sudo -u eleicoes git reset --hard origin/main
sudo -u eleicoes "$PASTA/.venv/bin/pip" install -q -r requirements.txt
systemctl restart app-tse
sleep 3
if systemctl is-active --quiet app-tse; then
  echo "Pronto! App atualizado e rodando ($(git log -1 --format='%h %s'))."
else
  echo "ATENÇÃO: o app não voltou. Copie as linhas abaixo e mande para o Claude:"
  journalctl -u app-tse -n 40 --no-pager
fi
