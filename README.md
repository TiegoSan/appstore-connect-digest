# AppStore Connect Analytics

Dossier autonome pour relancer des analyses App Store Connect Analytics via l'API officielle Apple.

## Contenu

- `appstore_config.json` : issuer id, key id, chemin de clé et apps connues.
- `AuthKey_VKFLG2237C.p8` : clé privée App Store Connect API. Secret critique.
- `appstore_analytics.py` : récupération et parsing des rapports `App Downloads Standard` / `Detailed`.
- `reports/` : exports générés en JSON et Markdown.

## Commandes

Lister les apps configurées :

```sh
python3 appstore_analytics.py list-apps
```

Produire un rapport téléchargements :

```sh
python3 appstore_analytics.py downloads perroquet
python3 appstore_analytics.py downloads coupez
```

Produire le compte rendu quotidien HTML et l'envoyer par mail :

```sh
python3 daily_appstore_digest.py --recipient gautier@gogolabs.fr
```

Produire le compte rendu HTML enrichi avec analyse commerciale et stratégie de vente :

```sh
python3 enhanced_daily_appstore_digest.py --recipient gautier@gogolabs.fr
```

Envoi mail :

- Sur serveur/VPS, configurer SMTP via variables d'environnement :

```sh
export APPSTORE_DIGEST_SMTP_HOST=smtp.mail.me.com
export APPSTORE_DIGEST_SMTP_PORT=587
export APPSTORE_DIGEST_SMTP_SECURITY=starttls
export APPSTORE_DIGEST_SMTP_USER=gautier@gogolabs.fr
export APPSTORE_DIGEST_SMTP_PASSWORD='mot-de-passe-specifique-app-icloud'
export APPSTORE_DIGEST_FROM='App Store Connect Digest <gautier@gogolabs.fr>'
```

- `sendmail` est utilise seulement si le systeme mail local est actif.
- Si Postfix/mailq indique `mail system is down`, le script bascule sur Mail.app et envoie le HTML en piece jointe via le compte mail macOS configure.

Tester la génération HTML sans envoyer de mail :

```sh
python3 daily_appstore_digest.py --no-send
```

Créer un snapshot historique si aucune demande Analytics n'existe encore pour une app :

```sh
python3 appstore_analytics.py downloads glass-master --create-snapshot
```

Afficher aussi le JSON complet dans le terminal :

```sh
python3 appstore_analytics.py downloads perroquet --json
```

## Dépendances

Le script utilise `PyJWT` et `cryptography` :

```sh
python3 -m pip install PyJWT cryptography
```

## GitHub Actions

Le dossier contient un workflow GitHub Actions :

```sh
.github/workflows/appstore-digest.yml
```

Il lance `enhanced_daily_appstore_digest.py`, genere le compte rendu HTML enrichi avec une couche strategie commerciale, puis l'envoie par SMTP.

### Secrets GitHub requis

Creer ces secrets dans le repo GitHub prive :

```text
ASC_ISSUER_ID
ASC_KEY_ID
ASC_PRIVATE_KEY
APPSTORE_DIGEST_SMTP_HOST
APPSTORE_DIGEST_SMTP_PORT
APPSTORE_DIGEST_SMTP_SECURITY
APPSTORE_DIGEST_SMTP_USER
APPSTORE_DIGEST_SMTP_PASSWORD
APPSTORE_DIGEST_FROM
```

Valeurs SMTP iCloud typiques :

```text
APPSTORE_DIGEST_SMTP_HOST=smtp.mail.me.com
APPSTORE_DIGEST_SMTP_PORT=587
APPSTORE_DIGEST_SMTP_SECURITY=starttls
APPSTORE_DIGEST_SMTP_USER=gautier@gogolabs.fr
APPSTORE_DIGEST_SMTP_PASSWORD=<mot de passe specifique a l'app iCloud>
APPSTORE_DIGEST_FROM=App Store Connect Digest <gautier@gogolabs.fr>
```

`ASC_PRIVATE_KEY` doit contenir le contenu complet de la cle `.p8`, avec les lignes `BEGIN PRIVATE KEY` / `END PRIVATE KEY`.

### Horaire

GitHub planifie les workflows en UTC. Le workflow est programme a `21:50` et `22:50` UTC pour couvrir l'heure d'ete et l'heure d'hiver. Le script applique ensuite un garde `Europe/Paris` et n'envoie vraiment que si l'heure locale Paris est dans l'heure `23`.

### Test

Utiliser `Run workflow` dans l'onglet Actions du repo. Le lancement manuel ignore le garde horaire et envoie immediatement le rapport.

## Sécurité

Le fichier `.p8` permet de générer des JWT App Store Connect tant que la clé n'est pas révoquée dans App Store Connect. Il doit rester local et non versionné.

Permissions recommandées :

```sh
chmod 600 AuthKey_VKFLG2237C.p8
```

La clé est ignorée par `.gitignore`, mais `.gitignore` ne protège pas contre une copie manuelle ou un mauvais dossier de travail.
