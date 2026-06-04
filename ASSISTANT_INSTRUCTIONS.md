# Instruction assistant

Quand l'utilisateur demande une analyse App Store Connect pour une app GogoLabs, utiliser ce dossier comme source opérationnelle :

`/Users/gautier/GogoLabs/Sources/AppStore Connect`

Workflow attendu :

1. Aller dans ce dossier.
2. Utiliser `appstore_config.json` pour retrouver l'app demandée.
3. Utiliser `appstore_analytics.py` pour récupérer les données App Store Connect Analytics.
4. Générer ou lire les rapports dans `reports/`.
5. Ne jamais afficher le contenu de `AuthKey_VKFLG2237C.p8`, les JWT, ni les URLs signées S3 Apple.

Commandes types :

```sh
cd "/Users/gautier/GogoLabs/Sources/AppStore Connect"
python3 appstore_analytics.py list-apps
python3 appstore_analytics.py downloads perroquet
python3 appstore_analytics.py downloads coupez
python3 appstore_analytics.py downloads <app-key> --create-snapshot
```

Si le shell Python local bloque sur SSL, `appstore_analytics.py` utilise déjà `curl` pour les appels réseau.
