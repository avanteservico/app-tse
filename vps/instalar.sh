#!/usr/bin/env bash
# Instalador do app "Eleições - Bahia" numa VPS Ubuntu 24.04 (Hostinger), rodando como root.
# Pode ser rodado de novo sem estragar nada (reaproveita senha do banco e segredos já criados).
#
# Uso (no terminal da VPS):
#   apt update && apt install -y git
#   git clone --depth 1 https://github.com/avanteservico/app-tse.git /opt/app-tse
#   bash /opt/app-tse/vps/instalar.sh
set -euo pipefail

PASTA=/opt/app-tse
USUARIO=eleicoes
SEGREDOS=$PASTA/.streamlit/secrets.toml

if [ "$(id -u)" -ne 0 ]; then
  echo "Rode como root (o usuário padrão da VPS da Hostinger)."; exit 1
fi
if [ ! -f "$PASTA/app.py" ]; then
  echo "Não achei o app em $PASTA. Rode antes:"
  echo "  git clone --depth 1 https://github.com/avanteservico/app-tse.git $PASTA"; exit 1
fi

echo
echo "=== Eleições - Bahia: instalação na VPS ==="
echo "Responda as perguntas abaixo (Enter aceita o que está entre colchetes)."
echo
read -r -p "Domínio do site (ex.: eleicoes.seusite.com.br). Se ainda não tiver, só aperte Enter: " DOMINIO
EMAIL=""
if [ -n "$DOMINIO" ]; then
  read -r -p "Seu e-mail (para o certificado de segurança HTTPS): " EMAIL
fi
LINHA_SENHA=""
if [ -f "$SEGREDOS" ] && grep -q '^SENHA_CADASTRO' "$SEGREDOS"; then
  echo "Senha da tela de cadastro de bairros: mantendo a que já estava configurada."
  LINHA_SENHA=$(grep '^SENHA_CADASTRO' "$SEGREDOS")
else
  SENHA_CADASTRO=""
  while [ -z "$SENHA_CADASTRO" ]; do
    read -r -p "Crie a senha da tela de cadastro de bairros: " SENHA_CADASTRO
  done
  SENHA_TOML=${SENHA_CADASTRO//\\/\\\\}
  SENHA_TOML=${SENHA_TOML//\"/\\\"}
  LINHA_SENHA="SENHA_CADASTRO = \"$SENHA_TOML\""
fi

echo; echo ">>> 1/8 Atualizando o sistema e instalando programas (demora alguns minutos)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get upgrade -y -q
apt-get install -y -q python3-venv python3-pip git nginx postgresql ufw fail2ban unattended-upgrades \
  certbot python3-certbot-nginx

echo; echo ">>> 2/8 Criando o usuário '$USUARIO' que roda o app..."
if ! id "$USUARIO" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "$USUARIO"
fi
chown -R "$USUARIO:$USUARIO" "$PASTA"

echo; echo ">>> 3/8 Banco de dados (PostgreSQL): estrutura e dados iniciais..."
if [ -f "$SEGREDOS" ] && grep -q '^DATABASE_URL' "$SEGREDOS"; then
  SENHA_BANCO=$(sed -n 's#^DATABASE_URL *= *"postgresql://[^:]*:\([^@]*\)@.*#\1#p' "$SEGREDOS")
else
  SENHA_BANCO=$(openssl rand -hex 16)
fi
if sudo -u postgres psql -tAc "select 1 from pg_roles where rolname='$USUARIO'" | grep -q 1; then
  sudo -u postgres psql -q -c "alter role $USUARIO with login password '$SENHA_BANCO'"
else
  sudo -u postgres psql -q -c "create role $USUARIO with login password '$SENHA_BANCO'"
fi
if ! sudo -u postgres psql -tAc "select 1 from pg_database where datname='$USUARIO'" | grep -q 1; then
  sudo -u postgres createdb -O "$USUARIO" "$USUARIO"
fi
DATABASE_URL="postgresql://$USUARIO:$SENHA_BANCO@127.0.0.1:5432/$USUARIO"
psql "$DATABASE_URL" -q -f "$PASTA/vps/estrutura.sql"

echo; echo ">>> 4/8 Ambiente Python e bibliotecas do app..."
sudo -u "$USUARIO" python3 -m venv "$PASTA/.venv"
sudo -u "$USUARIO" "$PASTA/.venv/bin/pip" install -q --upgrade pip
sudo -u "$USUARIO" "$PASTA/.venv/bin/pip" install -q -r "$PASTA/requirements.txt"

echo; echo ">>> 5/8 Segredos do app (ficam só nesta VPS)..."
mkdir -p "$PASTA/.streamlit"
printf '%s\n%s\n' "DATABASE_URL = \"$DATABASE_URL\"" "$LINHA_SENHA" > "$SEGREDOS"
chown "$USUARIO:$USUARIO" "$SEGREDOS"
chmod 600 "$SEGREDOS"

echo; echo ">>> 6/8 Deixando o app sempre ligado (serviço app-tse)..."
cat > /etc/systemd/system/app-tse.service <<EOF
[Unit]
Description=Eleicoes - Bahia (Streamlit)
After=network.target postgresql.service

[Service]
User=$USUARIO
WorkingDirectory=$PASTA
ExecStart=$PASTA/.venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --server.headless true --server.fileWatcherType none --browser.gatherUsageStats false
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now app-tse
systemctl restart app-tse

echo; echo ">>> 7/8 Endereço do site (Nginx) e proteção (firewall)..."
NOME_SERVIDOR=${DOMINIO:-_}
cat > /etc/nginx/sites-available/app-tse <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $NOME_SERVIDOR;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }
}
EOF
ln -sf /etc/nginx/sites-available/app-tse /etc/nginx/sites-enabled/app-tse
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
ufw allow OpenSSH >/dev/null
ufw allow 'Nginx Full' >/dev/null
ufw --force enable >/dev/null
systemctl enable --now fail2ban >/dev/null 2>&1 || true

echo; echo ">>> 8/8 Backup diário do banco (guarda 30 dias em /var/backups/app-tse)..."
mkdir -p /var/backups/app-tse
cat > /etc/cron.daily/backup-app-tse <<'EOF'
#!/bin/sh
destino=/var/backups/app-tse/bairros-$(date +%F).sql.gz
sudo -u postgres pg_dump eleicoes | gzip > "$destino"
find /var/backups/app-tse -name 'bairros-*.sql.gz' -mtime +30 -delete
EOF
chmod +x /etc/cron.daily/backup-app-tse

if [ -n "$DOMINIO" ]; then
  echo; echo ">>> HTTPS (cadeado) para $DOMINIO..."
  if certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos -m "$EMAIL" --redirect; then
    ENDERECO="https://$DOMINIO"
  else
    echo "Não consegui ativar o HTTPS agora (normal se o domínio ainda não aponta para esta VPS)."
    echo "Quando apontar, rode: bash $PASTA/vps/ativar_https.sh $DOMINIO $EMAIL"
    ENDERECO="http://$DOMINIO"
  fi
else
  ENDERECO="http://$(curl -s -4 ifconfig.me || hostname -I | awk '{print $1}')"
fi

sleep 3
echo
if systemctl is-active --quiet app-tse; then
  echo "=========================================================="
  echo " PRONTO! O app está rodando."
  echo " Abra no navegador: $ENDERECO"
  echo " Cadastro de bairros: $ENDERECO/cadastrobairro"
  echo "=========================================================="
else
  echo "ATENÇÃO: o app não ficou ligado. Copie as linhas abaixo e mande para o Claude:"
  journalctl -u app-tse -n 40 --no-pager
fi
