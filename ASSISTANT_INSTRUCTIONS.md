# Instruction assistant

Quand l'utilisateur demande une analyse App Store Connect pour une app GogoLabs, utiliser ce dossier comme source opérationnelle :

`/Users/gautier/GogoLabs/Sources/AppStore Connect`

Workflow attendu :

1. Aller dans ce dossier.
2. Utiliser `appstore_config.json` pour retrouver l'app demandée. Ce fichier est un catalogue non secret ; les credentials App Store Connect viennent de `.env` ou des secrets GitHub.
3. Lire d'abord `strategy/latest-metrics.json` quand il existe : c'est la source portefeuille consolidée.
4. Avant de recommander une modification produit, pricing, ASO, screenshots ou metadata, vérifier `apps[].review_pipeline`.
5. Si `review_pipeline.has_blocking_pipeline_change` vaut `true`, traiter les changements de la version en review comme déjà engagés et ne pas proposer de refaire la même action.
6. Pour l'analyse commerciale, lire aussi `apps[].history`, `apps[].funnel_by_source`, `apps[].funnel_by_territory`, `apps[].sales`, `apps[].reviews`, `apps[].metadata`, `apps[].screenshot_inventory` et `apps[].quality_signals` quand ces blocs sont disponibles.
7. Pour diagnostiquer une app plus finement, utiliser `appstore_analytics.py` pour récupérer les données App Store Connect Analytics.
8. Générer ou lire les rapports dans `reports/`.
9. Ne jamais afficher le contenu de `AuthKey_VKFLG2237C.p8`, les JWT, ni les URLs signées S3 Apple.

Commandes types :

```sh
cd "/Users/gautier/GogoLabs/Sources/AppStore Connect"
python3 appstore_analytics.py list-apps
python3 appstore_analytics.py downloads perroquet
python3 appstore_analytics.py downloads coupez
python3 appstore_analytics.py downloads <app-key> --create-snapshot
python3 enrich_review_metrics.py
python3 enrich_pricing_metrics.py
python3 enrich_market_metrics.py
```

Si le shell Python local bloque sur SSL, `appstore_analytics.py` utilise déjà `curl` pour les appels réseau.
