# App Store Connect Analytics

Dossier autonome pour collecter des métriques App Store Connect, enrichir les données de vente/pricing, générer un digest HTML stratégique et l'envoyer par mail.

## Contenu

- `appstore_config.json` : catalogue non secret des apps connues (`app_id`, bundle id, SKU).
- `AuthKey_VKFLG2237C.p8` : clé privée App Store Connect API locale. Secret critique, ignoré par Git.
- `appstore_analytics.py` : client App Store Connect API, collecte des rapports downloads et engagement.
- `collect_latest_metrics.py` : collecte les métriques de toutes les apps et écrit `strategy/latest-metrics.json`.
- `enrich_review_metrics.py` : enrichit `strategy/latest-metrics.json` avec les versions App Store en préparation/review/release pending, leurs builds et leurs metadata localisées, sans committer les champs App Review sensibles.
- `enrich_pricing_metrics.py` : enrichit `strategy/latest-metrics.json` avec pricing et sales reports Apple, en best effort.
- `enrich_market_metrics.py` : enrichit `strategy/latest-metrics.json` avec historique J-7/J-30, funnels par source/pays, reviews, metadata live, inventaire screenshots et signaux qualité, en best effort.
- `enrich_store_capabilities.py` : enrichit `strategy/latest-metrics.json` avec IAP/subscriptions et Game Center en lecture seule, en best effort.
- `render_latest_digest.py` : rend `strategy/latest-digest.html` depuis `strategy/latest-metrics.json`.
- `assemble_latest_digest.py` : assemble le HTML final, ajoute la comparaison J-1 et intègre `strategy/strategic-review.md` produit par l'automatisation ChatGPT.
- `send_latest_digest.py` : envoie `strategy/latest-digest.html` par SMTP.
- `appstore_dashboard.py` : génère `dashboard/latest-appstore-dashboard.json`, payload compact pour dashboard privé statique, et `dashboard/latest-appstore-alerts.json`.
- `send_appstore_alerts.py` : envoie un mail court uniquement quand des alertes `warning` ou `critical` existent.
- `strategy/strategic-review.md` : revue stratégique éditable. Sa mise à jour déclenche le rendu/envoi via GitHub Actions.
- `reports/` : exports locaux générés.

## Commandes locales

Lister les apps configurées :

```sh
python3 appstore_analytics.py list-apps
```

Produire un rapport téléchargements pour une app :

```sh
python3 appstore_analytics.py downloads perroquet
python3 appstore_analytics.py downloads coupez --create-snapshot
```

Collecter les métriques portefeuille sans envoyer de mail :

```sh
python3 collect_latest_metrics.py
python3 enrich_review_metrics.py
python3 enrich_pricing_metrics.py
python3 enrich_market_metrics.py
python3 enrich_store_capabilities.py
```

Rendre le digest HTML depuis les dernières métriques :

```sh
python3 render_latest_digest.py
python3 assemble_latest_digest.py
```

Générer le payload dashboard privé :

```sh
python3 appstore_dashboard.py
python3 appstore_dashboard.py --copy-to-site "/Users/gautier/GogoLabs/Apps/Gogolabs.fr/private/appstore"
```

Servir le dashboard privé local avec bouton de rafraîchissement API :

```sh
python3 private_dashboard_server.py
```

Ce serveur expose `POST /private/appstore/api/refresh`, relance la collecte App Store Connect, enrichit les métriques, régénère le payload dashboard et le recopie dans le site. En production, ce endpoint doit rester derrière l'auth privée du dashboard.

Variables utiles pour le serveur :

```text
APPSTORE_DASHBOARD_SITE_ROOT=/Users/gautier/GogoLabs/Apps/Gogolabs.fr
APPSTORE_DASHBOARD_HOST=127.0.0.1
APPSTORE_DASHBOARD_PORT=4173
```

Un exemple de déploiement privé vit dans :

```text
deploy/private-dashboard/
```

Envoyer le dernier digest :

```sh
python3 send_latest_digest.py
```

Ancien mode tout-en-un encore disponible :

```sh
python3 daily_appstore_digest.py --no-send
python3 daily_appstore_digest.py --recipient gautier@gogolabs.fr
```

## Dépendances

```sh
python3 -m pip install -r requirements.txt
```

Le fichier `requirements.txt` contient `PyJWT` et `cryptography`.

## Configuration locale

`appstore_config.json` ne doit contenir que le catalogue des apps. Les credentials App Store Connect restent dans `.env` local ou dans les secrets GitHub :

```text
ASC_ISSUER_ID=
ASC_KEY_ID=
ASC_PRIVATE_KEY_PATH=AuthKey_<KEY_ID>.p8
```

`ASC_PRIVATE_KEY` peut remplacer `ASC_PRIVATE_KEY_PATH` dans GitHub Actions. Dans ce cas, le script écrit une clé temporaire protégée dans `RUNNER_TEMP`.

## GitHub Actions

Deux workflows pilotent le système.

### Métriques App Store

Workflow :

```text
.github/workflows/appstore-digest.yml
```

Déclenchement :

- manuel via `workflow_dispatch` ;
- planifié à `21:50` et `22:50` UTC pour couvrir 23:50 Europe/Paris selon heure d'été/hiver.
- un garde horaire `TZ=Europe/Paris` ignore automatiquement le cron UTC inactif.

Étapes :

1. Préserve l'ancien `strategy/latest-metrics.json` dans `/tmp/previous-metrics.json`.
2. Lance `collect_latest_metrics.py`.
3. Lance `enrich_review_metrics.py`.
4. Lance `enrich_pricing_metrics.py`.
5. Lance `enrich_market_metrics.py`.
6. Lance `enrich_store_capabilities.py`.
7. Lance `appstore_dashboard.py`.
8. Commit et push `strategy/latest-metrics.json` si les métriques changent.
9. Si `GOGOLABS_ANALYTICS_REPO_TOKEN` existe, pousse les payloads dashboard vers le repo privé `TiegoSan/gogolabs-analytics`.
10. Lance `send_appstore_alerts.py` si des alertes warning/critical existent.
11. Upload les artefacts JSON non privés.

Le dashboard privé statique vit côté site dans :

```text
/Users/gautier/GogoLabs/Apps/Gogolabs.fr/private/appstore/
```

Les repos publics `gogolabs.fr` et `appstore-connect-digest` ne doivent pas commiter les payloads dashboard complets. Le dashboard privé est publié dans `TiegoSan/gogolabs-analytics`, repo privé utilisé par Cloudflare Pages pour `analytics.gogolabs.fr`. Sa copie locale vit dans `/Users/gautier/GogoLabs/Sources/Analytics Dashboard`.

### Digest stratégique

Workflow :

```text
.github/workflows/strategic-review-digest.yml
```

Déclenchement :

- manuel via `workflow_dispatch` ;
- push sur `main` quand `strategy/strategic-review.md` change.

Étapes :

1. Lance `render_latest_digest.py`.
2. Lance `assemble_latest_digest.py`.
3. Commit et push `strategy/latest-digest.html` si le rendu change.
4. Lance `send_latest_digest.py`.

## Secrets GitHub requis

```text
ASC_ISSUER_ID
ASC_KEY_ID
ASC_PRIVATE_KEY
APPSTORE_VENDOR_NUMBER
ASC_VENDOR_NUMBER
APPSTORE_DIGEST_SMTP_HOST
APPSTORE_DIGEST_SMTP_PORT
APPSTORE_DIGEST_SMTP_SECURITY
APPSTORE_DIGEST_SMTP_USER
APPSTORE_DIGEST_SMTP_PASSWORD
APPSTORE_DIGEST_FROM
GOGOLABS_ANALYTICS_REPO_TOKEN
```

`APPSTORE_VENDOR_NUMBER` ou `ASC_VENDOR_NUMBER` est nécessaire pour les Sales Reports. `ASC_PRIVATE_KEY` doit contenir le contenu complet de la clé `.p8`, avec les lignes `BEGIN PRIVATE KEY` et `END PRIVATE KEY`.

`GOGOLABS_ANALYTICS_REPO_TOKEN` est optionnel. S'il est présent, le workflow pousse `latest-appstore-dashboard.json` et `latest-appstore-alerts.json` dans le repo privé `TiegoSan/gogolabs-analytics`, utilisé par Cloudflare Pages pour `analytics.gogolabs.fr`. Sa copie locale vit dans `/Users/gautier/GogoLabs/Sources/Analytics Dashboard`.

Valeurs SMTP iCloud typiques :

```text
APPSTORE_DIGEST_SMTP_HOST=smtp.mail.me.com
APPSTORE_DIGEST_SMTP_PORT=587
APPSTORE_DIGEST_SMTP_SECURITY=starttls
APPSTORE_DIGEST_SMTP_USER=gautier@gogolabs.fr
APPSTORE_DIGEST_SMTP_PASSWORD=<mot de passe specifique a l'app iCloud>
APPSTORE_DIGEST_FROM=Gogo Labs Daily Business Digest <gautier@gogolabs.fr>
GOGOLABS_DIGEST_LOGO_PATH=assets/gogolabs-logo.png
```

## Sécurité

Le fichier `.p8` permet de générer des JWT App Store Connect tant que la clé n'est pas révoquée dans App Store Connect. Il doit rester local et non versionné.

Permissions recommandées :

```sh
chmod 600 AuthKey_VKFLG2237C.p8
```

La clé est ignorée par `.gitignore`, mais `.gitignore` ne protège pas contre une copie manuelle, une archive ou un mauvais dossier de travail.
