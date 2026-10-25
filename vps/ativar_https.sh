#!/usr/bin/env bash
# Liga o HTTPS (cadeado) depois que o domínio já aponta para esta VPS.
# Uso: bash /opt/app-tse/vps/ativar_https.sh eleicoes.seusite.com.br seu@email.com
set -euo pipefail
DOMINIO=${1:?"Informe o domínio. Ex.: bash $0 eleicoes.seusite.com.br seu@email.com"}
EMAIL=${2:?"Informe também o seu e-mail."}
sed -i "s/server_name .*;/server_name $DOMINIO;/" /etc/nginx/sites-available/app-tse
nginx -t && systemctl reload nginx
certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos -m "$EMAIL" --redirect
echo "Pronto! Abra: https://$DOMINIO"
