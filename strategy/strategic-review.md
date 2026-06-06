# Revue stratégique GogoLabs

_Source métrique : `strategy/latest-metrics.json`, généré le 2026-06-06 à 20:48:18 UTC. Rapport App Store du 2026-06-06. Rapport ventes utilisé : 2026-06-05._

## 1. Synthèse exécutive stratégique

GogoLabs dispose d’un signal de marché réel mais encore trop mal converti : 532 impressions, 11 vues de page produit, 9 taps, 81 téléchargements et 57 premiers téléchargements. Le portefeuille n’est pas invisible. Il est vu. Mais le résultat App Store ne transforme pas encore assez vite l’exposition en intention. Le taux global impressions -> vues page reste autour de 2,07 %. C’est le chiffre qui doit dominer la lecture : les apps apparaissent, puis l’utilisateur passe trop souvent.

Le nouveau run apporte une information commerciale supplémentaire : les ventes/revenus commencent à être collectés. Le Sales Report utilisé est celui du 2026-06-05, donc J-1 par rapport aux métriques App Store du 2026-06-06. Les données indiquent 2 paid units au total, mais 0,0 de developer proceeds. Deux apps ressortent dans le rapport ventes : Perroquet Piano avec 1 unité en GBP et Odile! avec 1 unité en EUR. Ce signal doit être lu avec prudence : il confirme qu’il existe une activité transactionnelle ou comptable, mais il ne permet pas encore de conclure sur la rentabilité, le prix réel, ni le revenu net.

Le pricing courant reste techniquement non exploitable. Les `app_id` sont maintenant présents, donc la correction précédente a fonctionné. Mais l’appel `appPriceSchedule` échoue encore parce que le script demande une limite de 200 alors que l’API Apple limite `manualPrices` et `automaticPrices` à 50. Ce n’est plus un problème de données manquantes. C’est un paramètre API à corriger. Dès que cette limite sera abaissée, le pipeline devrait pouvoir remonter la structure de prix.

La conclusion stratégique reste brutale : la priorité court terme n’est pas de produire plus. La priorité est de rendre deux apps pro impossibles à mal comprendre. Glass Master et Coupez! doivent servir de banc d’essai premium. FeedBacks! et Odile! doivent être corrigées en surface. Perroquet Piano doit être traité comme actif mobile/consumer séparé. Les apps sans signal doivent rester en audit de présence, pas en refonte profonde.

## 2. Ce que les métriques impliquent commercialement

Le portefeuille a un haut de funnel actif. Les impressions existent, la source dominante est App Store search pour les apps visibles, et plusieurs apps Desktop apparaissent dans des territoires solvables. Ce n’est pas une absence de marché. C’est une faiblesse de signal commercial dans le résultat de recherche.

Perroquet Piano concentre la majorité du volume avec 57 téléchargements sur 81. Il conserve son rôle d’actif de traction, mais pas d’actif directeur pour la marque pro. Son device dominant est l’iPhone, son territoire dominant est le Japon, et le rapport ventes indique au moins une unité associée en GBP sur le rapport du 2026-06-05. Cela confirme qu’il doit être optimisé avec une logique de produit mobile, apprentissage et localisation, pas avec le langage des outils macOS de production.

Glass Master reste le meilleur candidat Desktop pour travailler la lisibilité premium. Il a 120 impressions, 2 vues page produit, 2 taps, US dominant et Desktop dominant. Le signal est cohérent, mais trop faible en passage vers fiche produit. Le produit a probablement une utilité, mais cette utilité n’est pas encore assez visible dans la surface App Store.

Coupez! garde un profil paradoxal : 10 téléchargements, mais seulement 1 vue page produit et 0 tap dans l’engagement. Le nom a une force de marque, mais il peut être opaque à l’international. C’est précisément le type d’app où le sous-titre et le screenshot 1 doivent porter tout le poids commercial.

FeedBacks! et Odile! restent intéressantes parce qu’elles déclenchent des taps malgré zéro vue page produit. FeedBacks! a le meilleur tap rate brut visible. Odile! a 85 impressions Desktop et maintenant une unité dans le rapport ventes. Odile! ne doit donc pas être balayée trop vite. Elle est incomprise, mais elle n’est pas nécessairement morte.

Les apps à zéro signal ne doivent pas consommer l’effort commercial principal. Bouclez!, My First Sampler, Gogo Looping et BounceDaTracks doivent être auditées pour disponibilité, indexation, catégorie, territoires, compatibilité, recherche exacte et fiche publique. Le zéro impression est un diagnostic de distribution avant d’être un diagnostic produit.

## 3. Diagnostic du portefeuille

### 3.1. Trois lignes à séparer strictement

Première ligne : les outils macOS pro de workflow créatif. C’est la ligne stratégique. Elle doit porter la promesse GogoLabs : économiser du temps, réduire les erreurs, contrôler les workflows, produire plus proprement. Glass Master, Coupez!, FeedBacks! et Odile! sont les apps à travailler sur ce territoire, avec des niveaux de priorité différents.

Deuxième ligne : les apps musique / apprentissage / consumer. Perroquet Piano appartient à cette ligne. Elle a le plus gros volume et un signal de vente, mais elle ne doit pas définir la promesse des apps pro. Sa logique commerciale est mobile, probablement internationale, avec un axe Japon à examiner sérieusement.

Troisième ligne : les apps dormantes ou invisibles. Elles ne doivent pas être jugées à partir d’un fantasme produit. Elles doivent être auditées froidement. Une app sans impressions n’a pas encore eu l’occasion de prouver ou détruire sa proposition de valeur.

### 3.2. La marque doit devenir une gamme

GogoLabs doit sortir de la perception “collection d’expériences”. Une gamme premium n’est pas une accumulation d’apps ; c’est une promesse répétée sous plusieurs formes. Chaque app pro doit dire : voici le problème professionnel que je supprime, voici le temps que je fais gagner, voici l’erreur que j’évite.

La phrase directrice reste : apps macOS premium pour professionnels créatifs qui veulent gagner du temps, éviter les erreurs et contrôler leur workflow. Toute app qui ne renforce pas cette phrase doit être séparée, rétrogradée ou repositionnée.

## 4. Diagnostic funnel

### 4.1. Haut de funnel : exposition réelle

Le haut de funnel existe. L’App Store montre les apps. La source dominante est search. Ce point est important : il ne s’agit pas d’un trafic entièrement froid ou accidentel. Les apps rencontrent probablement des requêtes proches. Le problème vient ensuite : l’utilisateur ne comprend pas assez vite pourquoi cliquer.

### 4.2. Milieu de funnel : le goulet principal

11 vues page produit pour 532 impressions est trop faible. Le prochain cycle doit viser une amélioration mesurable du page view rate, surtout sur Glass Master et Coupez!. Objectif minimal : passer vers 4-6 % sur les apps Desktop prioritaires. Tant que ce taux ne bouge pas, les autres optimisations sont secondaires.

### 4.3. Taps incohérents mais utiles

Les taps sans vues page sur FeedBacks! et Odile! ne doivent pas être surinterprétés, mais ils ne doivent pas être ignorés. Ils signalent une friction ou une différence de définition métrique. Odile! devient plus intéressante avec l’apparition d’une unité dans les ventes J-1 : l’app est mal comprise dans le résultat, mais elle peut avoir une valeur réelle pour un segment étroit.

### 4.4. Bas de funnel : revenus encore insuffisamment lisibles

Le rapport ventes J-1 indique 2 paid units et 0,0 developer proceeds. Cette combinaison est ambiguë : cela peut venir d’apps gratuites, de prix nuls, d’opérations comptables, de timing de proceeds, de territoires, ou d’un mapping encore imparfait des colonnes Sales Report. Il ne faut pas conclure que la valeur est nulle. Il faut conclure que la donnée revenue est maintenant branchée, mais pas encore qualifiée.

La prochaine étape est technique : corriger `appPriceSchedule` avec une limite de 50, puis exposer clairement prix courant, devise, tier, paid units, proceeds et refunds par app. Sans cela, la stratégie pricing reste doctrinale.

## 5. Priorités de vente

### Priorité 1 : Glass Master

Glass Master reste le meilleur laboratoire premium Desktop. Le signal est propre : Desktop, US, impressions, taps. Le problème est la conversion vers fiche produit. Il faut refaire le sous-titre, la première phrase et le screenshot 1 autour d’une promesse métier. La question n’est pas “que fait l’app ?” mais “quelle erreur professionnelle évite-t-elle ?”.

### Priorité 2 : Coupez!

Coupez! doit être rendu compréhensible en anglais sans perdre son identité. Le nom peut rester, mais le sous-titre doit vendre immédiatement : cut detection, conform, comparison, AAF, post-production, audio workflow si ces termes sont exacts. Le screenshot 1 doit montrer un workflow avant/après ou détection -> validation -> export.

### Priorité 3 : FeedBacks!

FeedBacks! a un signal d’intérêt brut mais une promesse trop générique si elle reste au niveau “feedback”. Le repositionnement doit être : retours créatifs traçables, corrections suivies, validations moins ambiguës, réduction des allers-retours. Ce n’est pas un outil de commentaires ; c’est un outil de contrôle de révision.

### Priorité 4 : Odile!

Odile! mérite une correction ciblée, pas un abandon immédiat. Elle a 85 impressions Desktop, 2 taps et maintenant une unité dans les ventes J-1. Le problème est que le nom ne vend rien seul. Il faut rendre l’utilité lisible en une ligne. Si cette ligne ne peut pas être écrite, l’app doit sortir du front commercial. Si elle peut être écrite, Odile! peut devenir un micro-outil de niche.

### Priorité 5 : Perroquet Piano

Perroquet doit être traité comme actif séparé. Il concentre le volume, dispose d’un signal sales, et son territoire/device suggèrent une stratégie de localisation et d’apprentissage mobile. La priorité est d’auditer sa fiche japonaise, ses screenshots pédagogiques, son public exact et son éventuel prix réel dès que le pricing API fonctionne.

### Priorité 6 : apps invisibles

Bouclez!, My First Sampler, Gogo Looping et BounceDaTracks doivent rester en audit. Leur absence de signal interdit une refonte marketing lourde. Il faut d’abord confirmer qu’elles existent réellement dans le store public avec la bonne disponibilité.

## 6. Pricing

Le pricing est désormais partiellement branché mais pas encore exploitable. Les ventes J-1 remontent deux unités, mais les proceeds restent à zéro. Le prix courant n’est pas remonté à cause d’une erreur API simple : Apple refuse `limit[manualPrices]=200` et `limit[automaticPrices]=200`, maximum autorisé 50. Il faut corriger ce paramètre immédiatement.

La doctrine ne change pas : GogoLabs ne doit pas compenser une fiche floue par un prix bas. Un prix bas ne clarifie pas la valeur ; il abîme souvent la perception. Si les apps pro évitent des erreurs ou accélèrent des workflows créatifs réels, elles doivent être vendues comme outils premium, pas comme petits gadgets.

Architecture recommandée : achat unique premium pour les apps mono-problème, prix plus élevé pour les apps qui touchent la livraison ou la validation, abonnement uniquement si la valeur continue est réelle, et ligne consumer/mobile séparée pour Perroquet.

Ce qu’il faut mesurer ensuite : prix courant, devise, tier, unités payantes, revenus développeur, refunds, pays de vente, conversion page -> achat/téléchargement. Sans ces champs, la stratégie pricing reste incomplète.

## 7. ASO

L’ASO est le levier court terme principal parce que les impressions viennent de search. Mais l’ASO ne doit pas être réduit aux mots-clés. Le vrai triangle est : requête utilisateur, résultat affiché, promesse perçue. Les apps apparaissent ; elles doivent maintenant devenir cliquables.

Chaque fiche pro doit répondre immédiatement à trois questions : pour qui, quelle tâche disparaît, quelle erreur est évitée. Les noms créatifs peuvent rester, mais ils doivent être entourés par un sous-titre fonctionnel. Coupez! peut garder sa personnalité, mais il lui faut un sous-titre international. Odile! peut garder son nom si le bénéfice devient évident. FeedBacks! doit sortir du générique.

## 8. Screenshots

Les screenshots doivent devenir des preuves. Le premier screenshot n’est pas un décor. C’est un argument commercial. Il doit montrer le problème, l’action et le résultat. Une app pro doit faire comprendre son gain avant même que l’utilisateur lise la description.

Ordre recommandé : promesse principale lisible en vignette ; avant/après ; workflow en trois étapes ; détail de contrôle avancé ; export ou validation finale. Une seule idée par screenshot. Aucun bruit. Aucun élément décoratif sans fonction.

## 9. Recommandations par app

### Glass Master

Refaire la surface App Store. Sous-titre, screenshot 1, première phrase. Positionnement : contrôle, validation, qualité de sortie, erreur évitée. Objectif : doubler le page view rate.

### Coupez!

Rendre la fonction lisible pour un utilisateur non francophone. Mettre en avant cut detection, conform, comparison, export structuré, post-production si exact. Screenshot 1 orienté workflow.

### FeedBacks!

Repositionner sur retours créatifs traçables. Promesse : transformer les commentaires en corrections suivies. Éviter le langage générique de feedback.

### Odile!

Clarifier la promesse ou rétrograder. L’unité de vente J-1 empêche de l’écarter mécaniquement. Mais le nom reste opaque. Priorité : une phrase métier.

### Perroquet Piano

Traiter comme produit mobile/localisé. Vérifier Japon, screenshots pédagogiques, promesse d’apprentissage, prix réel dès que l’API pricing est corrigée.

### Apps sans signal

Audit de présence, indexation, territoires, catégorie, compatibilité, recherche exacte. Pas de refonte lourde.

## 10. Risques de dispersion

Le portefeuille peut facilement disperser l’effort : une app mobile qui domine le volume, plusieurs apps Desktop faibles mais réelles, plusieurs apps invisibles. La bonne réponse est une hiérarchie stricte. Deux apps pro à travailler sérieusement, deux à corriger en surface, une app consumer à séparer, le reste en audit.

Le deuxième risque est de confondre métriques branchées et métriques fiables. Les ventes sont maintenant collectées, mais les proceeds et le pricing ne sont pas encore propres. Il faut utiliser cette donnée, mais ne pas la surinterpréter.

Le troisième risque est de développer au lieu de vendre. Les chiffres ne demandent pas d’abord plus de produit. Ils demandent plus de clarté.

## 11. Actions concrètes avant le prochain rapport

- Corriger `appPriceSchedule` : réduire `limit[manualPrices]` et `limit[automaticPrices]` à 50.
- Vérifier le parsing Sales Report : pourquoi 2 paid units mais 0 developer proceeds.
- Ajouter devise, pays de vente et type de transaction dans une section sales propre.
- Refaire sous-titre et screenshot 1 de Glass Master.
- Refaire sous-titre et screenshot 1 de Coupez!.
- Repositionner FeedBacks! sur la traçabilité des retours créatifs.
- Écrire une phrase métier pour Odile!.
- Séparer Perroquet dans la lecture stratégique et l’optimisation App Store.
- Auditer les apps sans signal avant tout travail de refonte.

## 12. Conclusion décisionnelle

GogoLabs commence à avoir une boucle de pilotage : exposition, engagement, téléchargements, début de sales. Mais le cœur du problème reste la lisibilité commerciale. Les apps sont vues. Elles ne sont pas encore assez comprises.

La décision immédiate est simple : corriger la collecte pricing, puis concentrer l’effort commercial sur Glass Master et Coupez!. Le critère de succès du prochain cycle n’est pas une impression supplémentaire. C’est une hausse du passage vers fiche produit, puis une lecture propre du revenu par app.
