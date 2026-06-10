# Dashboard App Store privé

Objectif : rendre le dashboard accessible depuis le domaine GogoLabs sans publier les données App Store dans le repo public `gogolabs.fr`.

## Architecture recommandée

```text
gogolabs.fr public
  -> GitHub Pages pour le site marketing

analytics.gogolabs.fr ou /private/appstore/
  -> Cloudflare Access
  -> Cloudflare Tunnel
  -> private_dashboard_server.py
  -> /Users/gautier/GogoLabs/Apps/Gogolabs.fr/private/appstore/
```

Le dashboard HTML/CSS/JS peut être versionné dans le repo du site. Le fichier suivant reste local/non versionné :

```text
private/appstore/latest-appstore-dashboard.json
```

## Serveur privé

Depuis le repo App Store Connect :

```sh
python3 private_dashboard_server.py
```

Variables supportées :

```text
APPSTORE_DASHBOARD_SITE_ROOT=/Users/gautier/GogoLabs/Apps/Gogolabs.fr
APPSTORE_DASHBOARD_HOST=127.0.0.1
APPSTORE_DASHBOARD_PORT=4173
ASC_ISSUER_ID=
ASC_KEY_ID=
ASC_PRIVATE_KEY_PATH=AuthKey_<KEY_ID>.p8
```

Endpoints :

```text
GET  /private/appstore/
GET  /private/appstore/api/health
POST /private/appstore/api/refresh
```

`POST /private/appstore/api/refresh` relance la collecte Apple et régénère le JSON.

## Option A - sous-domaine recommandé

Plus simple à isoler :

```text
analytics.gogolabs.fr -> http://127.0.0.1:4173
```

Dans Cloudflare Access, protéger l'application `analytics.gogolabs.fr` et limiter l'accès à l'email autorisé.

## Option B - chemin sur le domaine principal

Possible si le proxy/CDN sait router seulement :

```text
https://gogolabs.fr/private/appstore/*
```

vers le serveur privé, pendant que le reste de `gogolabs.fr` continue vers GitHub Pages.

Cette option est plus fragile qu'un sous-domaine parce qu'il faut une règle de routage par chemin correcte.

## systemd

Copier `appstore-dashboard.service.example`, adapter les chemins et secrets, puis :

```sh
sudo cp appstore-dashboard.service.example /etc/systemd/system/appstore-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now appstore-dashboard.service
systemctl status appstore-dashboard.service
```

## Cloudflare Tunnel

Copier `cloudflared-config.yml.example`, adapter `tunnel` et `credentials-file`, puis :

```sh
cloudflared tunnel run appstore-dashboard
```

Ensuite créer une application Cloudflare Access devant le hostname publié.
