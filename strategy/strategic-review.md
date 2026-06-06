# Revue stratégique GogoLabs

_Source métrique : `strategy/latest-metrics.json`, généré le 2026-06-06 à 21:07:11 UTC. Rapport App Store du 2026-06-06. Rapport ventes utilisé : 2026-06-05. Exécution manuelle demandée et relancée le 2026-06-06._

## 1. Synthèse exécutive stratégique

GogoLabs dispose maintenant d’un vrai système de pilotage : les métriques App Store Connect sont récupérées, consolidées dans le repo, puis réinjectées dans une réflexion stratégique séparée. Le portefeuille totalise 81 téléchargements, 57 premiers téléchargements, 532 impressions, 11 vues page produit, 9 taps et 2 paid units. Ce n’est pas encore un volume permettant des certitudes statistiques, mais c’est assez pour identifier le problème central : la visibilité existe, la compréhension commerciale reste trop faible.

Le taux impressions -> page produit est le signal dur : 11 vues page produit pour 532 impressions, soit environ 2,07 %. L’App Store montre les apps, mais les utilisateurs n’ouvrent pas assez les fiches. La priorité n’est donc pas d’ajouter des fonctions. La priorité est de rendre la promesse lisible avant le clic : nom, sous-titre, icône, premier screenshot, bénéfice métier, preuve immédiate.

Les paid units commencent à apparaître. Perroquet Piano et Odile! remontent chacun 1 paid unit dans le Sales Report. Les proceeds restent à 0.0, ce qui empêche encore une lecture économique propre. Le pipeline commercial existe, mais il faut corriger la collecte pricing/sales avant de piloter le revenu. Le bug technique est clair : l’appel `appPriceSchedule` utilise `limit[manualPrices]=200` et `limit[automaticPrices]=200`, alors qu’Apple indique une limite maximale de 50.

Décision immédiate : concentrer les efforts commerciaux sur Glass Master et Coupez!, traiter Perroquet Piano comme ligne mobile/consumer séparée, corriger FeedBacks! et Odile! en surface, et limiter les apps sans signal à un audit de présence.

## 2. Lecture du portefeuille

### 2.1. Ligne pro macOS

Glass Master, Coupez!, FeedBacks!, Odile! et BounceDaTracks doivent être lus comme une ligne d’outils professionnels. Leur valeur n’est pas le volume brut. Leur valeur est le temps économisé, les erreurs évitées, les livrables sécurisés, la réduction de friction entre Pro Tools, l’image, les retours client et les exports.

La ligne pro doit être formulée comme une infrastructure légère pour workflows créatifs lourds. Une app GogoLabs pro ne doit pas ressembler à un gadget App Store. Elle doit ressembler à un outil issu d’un vrai contexte de production.

### 2.2. Ligne consumer / musique

Perroquet Piano est l’actif de volume : 57 téléchargements, 41 first-time downloads, 211 impressions, source dominante App Store Search, territoire dominant Japon, device dominant iPhone. Ce signal ne doit pas contaminer la stratégie des apps pro. Perroquet suit une logique différente : localisation, pédagogie, mobile, friction faible, acquisition par recherche.

### 2.3. Apps dormantes

Bouclez!, My First Sampler, Gogo Looping et BounceDaTracks n’ont aucun signal exploitable dans cette fenêtre. Elles ne doivent pas recevoir d’effort marketing lourd avant audit : disponibilité, indexation, pays, catégorie, compatibilité, nom exact recherché dans l’App Store.

## 3. Diagnostic funnel

Le haut de funnel fonctionne partiellement. Les apps apparaissent dans App Store Search. Le milieu de funnel est faible. Les vues page produit restent insuffisantes. Le bas de funnel commence à être visible avec les paid units, mais il reste instable.

Ordre de travail obligatoire :

- augmenter le taux impressions -> page produit
- améliorer la fiche produit
- rendre le prix lisible
- seulement ensuite juger le revenu

Ne pas inverser cet ordre. Un prix bas ne compensera pas une promesse floue. Une nouvelle feature ne compensera pas un premier screenshot qui ne vend rien.

## 4. Priorités de vente

### Priorité 1 : Glass Master

Glass Master a 120 impressions, 2 vues page produit, 2 taps, 9 téléchargements et 6 first-time downloads. Le signal est faible mais propre : Desktop, US, App Store Search. C’est le meilleur candidat pour un test premium pro.

Objectif : faire monter le page view rate. Le travail doit porter sur le sous-titre, le premier screenshot, la première phrase et la promesse métier. L’app doit vendre le contrôle loudness, la conformité, le risque évité, le rapport clair. Pas seulement “analyse audio”.

### Priorité 2 : Coupez!

Coupez! a 57 impressions, 1 page view, 10 téléchargements et 5 first-time downloads. Le nom est mémorisable mais probablement opaque hors français. Il faut compenser par un sous-titre anglais ultra fonctionnel : video cut detection, picture change review, AAF export, audio conform.

Premier screenshot : avant/après. Vidéo source, coupes détectées, export AAF vers Pro Tools. Le bénéfice doit être visible sans lire la description.

### Priorité 3 : FeedBacks!

FeedBacks! a 59 impressions, 2 taps, 4 téléchargements, 4 first-time downloads, mais 0 page view. Le signal est étrange : il y a une forme d’intention, mais la fiche ne s’ouvre pas. Le mot “feedback” est trop générique. La valeur réelle est la transformation de retours client en corrections suivies, markers, traçabilité.

Promesse à tester : “Turn client notes into Pro Tools markers.”

### Priorité 4 : Odile!

Odile! a 85 impressions, 2 taps, 1 téléchargement, 1 paid unit. Le signal sales interdit de l’écarter. Mais le nom ne vend rien. Il faut rendre l’app compréhensible immédiatement : EDL, Pro Tools, exports structurés, assistants, timecode.

Odile! doit recevoir une phrase métier. Pas une refonte produit.

### Priorité 5 : Perroquet Piano

Perroquet Piano domine le volume, mais il doit être optimisé séparément. Japon, iPhone, pédagogie, apprentissage musical. Le but n’est pas de forcer Perroquet dans la marque pro. Le but est d’exploiter sa traction consumer sans brouiller GogoLabs.

## 5. Pricing

Le pricing ne peut pas encore être exploité correctement. La collecte échoue sur `appPriceSchedule` à cause d’une limite Apple : remplacer `limit[manualPrices]=200` et `limit[automaticPrices]=200` par 50.

Doctrine :

- apps pro : prix fondé sur temps gagné, risque évité, fiabilité
- apps consumer : friction basse, volume, achat simple
- ne pas baisser les prix tant que la fiche n’est pas claire
- ne pas juger la willingness to pay avant d’avoir une page produit lisible

Les paid units sont un signal de bas de funnel, pas encore un signal de pricing.

## 6. ASO

L’ASO immédiat ne doit pas commencer par les mots-clés cachés. Il doit commencer par la lisibilité du résultat de recherche.

Chaque app doit répondre avant le clic :

- pour qui ?
- quelle tâche disparaît ?
- quelle erreur est évitée ?
- quel résultat sort de l’app ?

Règle : nom créatif autorisé, sous-titre fonctionnel obligatoire.

Coupez! peut rester Coupez!, mais le sous-titre doit vendre le conform. Odile! peut rester Odile!, mais le sous-titre doit révéler l’EDL / Pro Tools. FeedBacks! doit sortir du feedback vague. Glass Master doit parler de conformité, contrôle, livraison.

## 7. Screenshots

La surface visuelle doit être reconstruite comme preuve de valeur.

Structure recommandée :

- Screenshot 1 : promesse principale en gros, visible en vignette
- Screenshot 2 : avant / après
- Screenshot 3 : workflow en trois étapes
- Screenshot 4 : contrôle avancé ou cas réel
- Screenshot 5 : export, rapport, livraison, résultat final

Pas de capture décorative. Pas d’interface seule sans bénéfice. Chaque screenshot doit répondre à une objection commerciale.

## 8. Risques

### Dispersion

Neuf apps dans plusieurs marchés. Danger majeur : donner la même attention à toutes. Il faut refuser la symétrie. Deux apps pro en priorité, deux apps en correction ciblée, Perroquet en ligne séparée, le reste en audit.

### Confusion volume / valeur

Perroquet a le volume. La ligne pro peut avoir la valeur. Ne pas laisser la métrique la plus grosse décider seule de la stratégie.

### Fausse réponse produit

Ajouter des fonctions maintenant serait confortable mais prématuré. Le problème visible est commercial : packaging, compréhension, preuve.

### Données incomplètes

Les prix et proceeds ne sont pas encore propres. Toute conclusion économique doit rester provisoire.

## 9. Actions concrètes avant le prochain rapport

- Corriger `appPriceSchedule` avec `limit[manualPrices]=50` et `limit[automaticPrices]=50`.
- Ajouter dans le mail une section sales lisible : paid units, app, pays/devise, date du sales report, proceeds.
- Refaire le sous-titre de Glass Master autour de conformité / loudness / livraison.
- Refaire le screenshot 1 de Glass Master comme preuve de contrôle.
- Refaire le sous-titre de Coupez! en anglais fonctionnel.
- Refaire le screenshot 1 de Coupez! autour du workflow post-production.
- Écrire une promesse métier immédiate pour Odile!.
- Repositionner FeedBacks! sur retours client -> markers / corrections traçables.
- Auditer les apps sans signal avant toute énergie produit ou marketing.
- Séparer mentalement Perroquet de la ligne pro dans le reporting.

## 10. Décision

Ne pas disperser. Ne pas créer une nouvelle app pour compenser une fiche qui ne vend pas. Ne pas baisser les prix pour compenser une promesse floue.

Le prochain progrès mesurable doit être : hausse du taux impressions -> page produit sur Glass Master et Coupez!. C’est la métrique de vérité du prochain cycle.
