# Revue stratégique GogoLabs

_Source métrique : `strategy/latest-metrics.json`, généré le 2026-06-06 à 21:07:11 UTC. Rapport App Store du 2026-06-06. Rapport ventes utilisé : 2026-06-05._

## 1. Synthèse exécutive stratégique

GogoLabs a maintenant une boucle de pilotage plus cohérente : les métriques App Store sont collectées à heure fixe, la réflexion stratégique est séparée, et le mail doit désormais être généré par le workflow déclenché par cette revue. Le diagnostic commercial reste stable : le portefeuille est visible, mais il n’est pas encore assez lisible. Les chiffres actuels — 532 impressions, 11 vues page produit, 9 taps, 81 téléchargements, 57 premiers téléchargements — décrivent un problème de conversion de l’attention en intention, pas un problème d’existence.

Le signal le plus brutal reste le même : environ 2,07 % seulement des impressions deviennent des vues page produit. L’App Store montre les apps ; l’utilisateur ne comprend pas assez vite pourquoi ouvrir la fiche. Toute stratégie qui partirait d’une nouvelle feature, d’une nouvelle app ou d’une baisse de prix passerait à côté du problème réel. La première couche à corriger est la surface commerciale : nom, sous-titre, icône, premier screenshot, promesse, bénéfice métier visible.

Les données de vente commencent à entrer dans le système : 2 paid units sont détectées sur le Sales Report du 2026-06-05, mais `developer_proceeds` reste à 0.0. Ce signal confirme que le pipeline commence à voir le bas de funnel, mais il n’est pas encore assez propre pour piloter le pricing. Le pricing courant échoue encore parce que l’appel `appPriceSchedule` utilise une limite de 200 alors qu’Apple impose 50. Cette correction est technique, prioritaire, et indépendante de la stratégie commerciale.

Décision immédiate : maintenir la concentration sur Glass Master et Coupez! pour tester la montée en lisibilité de la ligne pro, traiter Perroquet Piano comme actif consumer/mobile séparé, corriger FeedBacks! et Odile! en surface, et ne pas donner d’énergie stratégique lourde aux apps sans signal tant que leur distribution n’est pas vérifiée.

## 2. Ce que les métriques impliquent commercialement

Le portefeuille n’est pas dans une phase de validation produit pure. Il est dans une phase de clarification commerciale. Les impressions existent, les téléchargements existent, les ventes commencent à être détectées, mais le lien entre exposition, fiche produit et achat reste trop flou. L’app qui gagne n’est pas nécessairement la meilleure app ; c’est celle dont la promesse est comprise le plus vite dans un environnement saturé.

Perroquet Piano reste l’actif de volume. Il représente 57 téléchargements sur 81 et domine les impressions. Mais son device dominant est iPhone et son territoire dominant est le Japon. Ce n’est pas une preuve que la marque GogoLabs doit devenir mobile/consumer ; c’est une preuve qu’il existe une ligne séparée à optimiser selon ses propres règles : localisation, apprentissage, pédagogie, screenshot mobile, peut-être pricing plus accessible.

Glass Master reste le meilleur candidat de test premium Desktop. Il combine impressions, taps, Desktop et US. Le signal n’est pas massif, mais il est propre. L’objectif n’est pas encore de maximiser les revenus ; l’objectif est de vérifier qu’un meilleur packaging peut faire monter le taux impressions -> page produit.

Coupez! reste prioritaire parce qu’elle semble disposer d’une valeur métier nette, mais son nom ne suffit pas à vendre à l’international. Elle doit être sur-explicitée dans le sous-titre et le premier screenshot. Un nom créatif peut survivre si la promesse fonctionnelle est immédiate.

FeedBacks! et Odile! sont des signaux faibles à ne pas jeter. FeedBacks! a un tap rate brut intéressant. Odile! a des impressions Desktop, des taps, et apparaît dans le signal sales. Elles ne doivent pas être prioritaires devant Glass Master et Coupez!, mais elles méritent une correction de surface.

## 3. Diagnostic du portefeuille

### 3.1. Ligne macOS pro

La ligne pro doit être reconstruite autour d’une promesse unique : réduire les erreurs et contrôler les workflows créatifs. Glass Master, Coupez!, FeedBacks! et Odile! doivent être jugées à partir de cette question : quelle tâche coûteuse, répétitive ou risquée disparaît grâce à l’app ? Si la réponse est nette, l’app peut être vendue premium. Si la réponse exige trois paragraphes, la fiche App Store échouera.

### 3.2. Ligne consumer / apprentissage

Perroquet Piano doit être séparée. Elle peut devenir un actif intéressant, mais elle ne doit pas définir la marque pro. Sa logique est probablement volume, localisation, apprentissage, mobile. Son optimisation doit porter sur le Japon, le langage pédagogique, les screenshots iPhone et la compréhension immédiate du bénéfice d’apprentissage.

### 3.3. Apps dormantes

Bouclez!, My First Sampler, Gogo Looping et BounceDaTracks sont à traiter comme audit de présence. Pas comme priorité marketing. Zéro signal App Store signifie d’abord : vérifier si l’app est réellement trouvable, publiée, indexée, disponible par territoire et correctement catégorisée.

## 4. Diagnostic funnel

Le haut de funnel est partiellement actif. Les apps apparaissent via search. Le milieu de funnel est faible. Le bas de funnel commence à être mesuré, mais il reste techniquement incomplet. La stratégie doit donc suivre l’ordre du funnel : d’abord rendre les résultats de recherche cliquables, ensuite améliorer la fiche, ensuite seulement juger prix et revenus.

Le page view rate doit devenir la métrique centrale du prochain cycle. Si Glass Master et Coupez! passent de 2 % environ vers 4-6 %, le packaging aura prouvé qu’il améliore la compréhension. Si le taux ne bouge pas malgré un sous-titre et un screenshot clarifiés, le problème sera plus profond : nom, promesse, marché, catégorie ou adéquation produit.

Les paid units à 2 ne changent pas encore la stratégie. Elles prouvent seulement qu’il faut cesser de raisonner uniquement en téléchargements. Dès que les proceeds, prix et devises seront propres, il faudra réordonner les priorités selon revenu réel, pas selon volume brut.

## 5. Priorités de vente

### Priorité 1 : Glass Master

Refonte commerciale courte. Pas refonte produit. Sous-titre, screenshot 1, première phrase, promesse métier. L’app doit dire immédiatement ce qu’elle contrôle, valide ou sécurise. Le mot “Master” peut porter une sensation premium, mais il doit être relié à une tâche concrète.

### Priorité 2 : Coupez!

Coupez! doit assumer son nom mais compenser son opacité. Sous-titre anglais fonctionnel. Screenshot centré sur workflow post-production : détection, comparaison, conform, export, réduction d’erreur. Le premier écran doit vendre un résultat, pas un outil.

### Priorité 3 : FeedBacks!

FeedBacks! doit sortir du générique. Le feedback générique n’a pas de tension commerciale. La traçabilité des retours créatifs, la réduction des validations ambiguës et la transformation des commentaires en corrections suivies ont une valeur beaucoup plus forte.

### Priorité 4 : Odile!

Odile! doit être rendue compréhensible ou rétrogradée. Le signal sales empêche de l’écarter mécaniquement. Mais le nom seul ne vend rien. Il faut une phrase métier immédiate. Sans cette phrase, l’app restera un objet interne.

### Priorité 5 : Perroquet Piano

Perroquet doit être travaillé comme produit séparé : Japon, iPhone, pédagogie, progression, apprentissage musical. Sa performance ne doit pas influencer le pricing ou le langage des apps Desktop pro.

## 6. Pricing

Le pricing ne peut pas encore être tranché. Le pipeline a avancé, mais il faut corriger `limit[manualPrices]` et `limit[automaticPrices]` à 50. Tant que le prix courant n’est pas lisible, il faut éviter les conclusions fortes sur la cohérence prix / conversion.

La doctrine reste néanmoins claire : ne pas baisser les prix pour compenser une fiche floue. Un prix bas ne règle pas une promesse incomprise. Pour les apps pro, le prix doit signaler la fiabilité, le gain de temps et la réduction d’erreurs. Une app qui évite une erreur de livraison ou économise du temps professionnel ne doit pas se présenter comme gadget.

## 7. ASO

L’ASO est le levier immédiat. Le problème n’est pas seulement le champ mots-clés. C’est la lisibilité du résultat de recherche. Chaque fiche doit répondre à trois questions avant le clic : pour qui, quelle tâche disparaît, quelle erreur est évitée.

Les noms créatifs peuvent rester, mais le sous-titre doit être fonctionnel. Coupez! doit parler post-production. FeedBacks! doit parler révisions créatives traçables. Odile! doit révéler sa fonction. Glass Master doit annoncer le contrôle ou la validation qu’elle apporte.

## 8. Screenshots

Les screenshots doivent devenir des preuves de valeur. Screenshot 1 : promesse principale lisible en vignette. Screenshot 2 : avant/après. Screenshot 3 : workflow en trois étapes. Screenshot 4 : contrôle avancé. Screenshot 5 : export, validation ou résultat final.

Une seule idée par screenshot. Pas de décoration inutile. Pas de capture d’interface sans bénéfice. Le visuel doit dire : cette app vient d’un contexte de production réel.

## 9. Recommandations par app

### Glass Master

Repackager en premier. Travailler le vocabulaire du contrôle, de la validation, de la qualité de sortie. Objectif : page view rate.

### Coupez!

Sous-titre anglais et screenshot workflow. Ne pas diluer dans une description longue. La promesse doit être visible immédiatement.

### FeedBacks!

Repositionner sur corrections traçables et validation créative. Éviter “feedback” comme mot vague.

### Odile!

Écrire une phrase métier ou sortir l’app du front commercial. Le signal sales impose un audit, pas une refonte lourde.

### Perroquet Piano

Optimiser comme app mobile/localisée. Auditer Japon, screenshots, prix, promesse pédagogique.

### Apps sans signal

Audit uniquement. Présence, territoires, indexation, catégorie, compatibilité, recherche exacte.

## 10. Risques de dispersion

Le danger principal reste la dispersion. Neuf apps, plusieurs marchés, plusieurs niveaux de maturité. La stratégie doit refuser la symétrie. Toutes les apps ne méritent pas le même effort. Deux apps pro en priorité, deux corrections secondaires, une ligne consumer séparée, le reste en audit.

Deuxième danger : croire que la collecte de métriques suffit. Les métriques ne vendent rien. Elles indiquent où la promesse casse. Le travail est encore commercial.

Troisième danger : confondre volume et valeur. Perroquet a du volume. La ligne pro peut avoir moins de volume mais plus de valeur si elle est vendue correctement.

## 11. Actions concrètes avant le prochain rapport

- Corriger `appPriceSchedule` avec limites à 50.
- Ajouter une lecture claire des ventes : date utilisée, app, pays/devise, paid units, proceeds.
- Refaire le sous-titre de Glass Master.
- Refaire le screenshot 1 de Glass Master.
- Refaire le sous-titre de Coupez! en anglais fonctionnel.
- Refaire le screenshot 1 de Coupez! autour du workflow.
- Écrire une promesse métier pour Odile!.
- Repositionner FeedBacks! sur la traçabilité.
- Auditer les apps sans signal avant toute refonte.

## 12. Conclusion décisionnelle

Le système est en train de devenir pilotable. La collecte est séparée. L’analyse déclenche le mail. Les ventes commencent à remonter. Il reste à rendre le pricing propre et à corriger la surface commerciale.

Décision : ne pas disperser. Corriger la lisibilité de Glass Master et Coupez!, séparer Perroquet, traiter Odile! et FeedBacks! en correction ciblée, laisser les apps invisibles en audit. Le prochain progrès doit se voir dans le taux impressions -> page produit, pas dans une nouvelle feature.
