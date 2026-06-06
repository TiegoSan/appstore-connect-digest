# Revue stratégique GogoLabs

_Source métrique : `strategy/latest-metrics.json`, généré le 2026-06-06 à 20:33:21 UTC. Rapport du 2026-06-06._

## 1. Synthèse exécutive stratégique

GogoLabs dispose toujours d’un signal de marché réel mais fragile : 532 impressions, 11 vues de page produit, 9 taps, 81 téléchargements et 57 premiers téléchargements. Le portefeuille n’est pas invisible. Il est vu. Mais le problème central reste entier : la visibilité ne se transforme pas assez en intention explicite. Le taux global impressions -> vues page reste autour de 2,07 %, ce qui signifie que les apps apparaissent dans les résultats App Store, mais que le résultat affiché ne donne pas assez envie d’ouvrir la fiche.

Le diagnostic ne change pas : le problème prioritaire n’est pas d’ajouter des features, ni de produire une nouvelle app, ni de multiplier les pistes. Le problème prioritaire est la lisibilité commerciale. Nom, icône, sous-titre, premier screenshot, prix perçu, promesse visible : c’est là que le système fuit. Tant que l’utilisateur ne comprend pas la valeur avant d’ouvrir la fiche, le reste du funnel restera anémique.

Le portefeuille reste déséquilibré. Perroquet Piano représente 57 téléchargements sur 81, soit environ 70 % du volume. Mais ce signal appartient probablement à une logique séparée : iPhone, Japon, apprentissage musical, potentiel consumer/localisation. Perroquet est un actif utile, mais il ne doit pas définir le langage de la gamme GogoLabs pro. La ligne stratégique principale reste celle des outils macOS Desktop : Glass Master, Coupez!, FeedBacks!, Odile!, et éventuellement les apps dormantes une fois leur présence App Store clarifiée.

Le nouveau run introduit une information importante : la tentative de collecte pricing/revenus est maintenant branchée, mais elle ne produit pas encore de données exploitables. Les totaux `paid_units` et `developer_proceeds` sont à zéro, non pas parce que le business est nécessairement nul, mais parce que le Sales Report du jour n’est pas encore disponible côté Apple. Le pricing courant échoue aussi pour une raison technique distincte : les objets app du fichier `latest-metrics.json` ne contiennent pas encore `app_id`, donc l’enrichissement pricing ne peut pas interroger `appPriceSchedule` correctement. Il faut corriger cette collecte avant de tirer une conclusion de pricing.

Décision immédiate : garder la stratégie de packaging commercial comme priorité numéro un, mais corriger en parallèle le pipeline metrics pour obtenir prix, revenus, unités payantes et remboursements. Sans revenus, GogoLabs voit l’attention. Avec revenus, GogoLabs pourra mesurer la valeur.

## 2. Ce que les métriques impliquent commercialement

Le signal le plus important n’est pas le volume absolu. Le signal le plus important est l’écart entre exposition et compréhension. 532 impressions pour 11 vues page produit forment un haut de funnel qui existe mais qui ne convainc pas. L’App Store expose les apps, principalement via search. Cela veut dire que les apps rencontrent des requêtes ou des contextes de découverte suffisamment proches pour apparaître. Le blocage intervient après l’apparition.

Perroquet Piano confirme une traction de volume. 211 impressions, 8 vues page produit, 3 taps, 57 téléchargements. Son taux de page view est meilleur que celui des apps Desktop, mais son device dominant est l’iPhone et son territoire dominant le Japon. Il doit donc être optimisé comme produit séparé : localisation, pédagogie, promesse d’apprentissage, screenshots adaptés au public mobile. L’utiliser comme modèle pour les apps macOS pro serait une erreur de lecture.

Glass Master est probablement le meilleur candidat Desktop à travailler en priorité : 120 impressions, 2 vues page produit, 2 taps, US dominant, Desktop dominant. Le signal est faible mais cohérent. L’app apparaît sur le bon device, dans un territoire solvable, et déclenche un minimum d’engagement. Le problème est que le taux de transformation vers la fiche reste trop bas pour une promesse premium.

Coupez! a 57 impressions, 1 vue page produit, 0 tap, mais 10 téléchargements. Ce profil est incohérent mais intéressant. Le nom est mémorisable, l’app semble avoir une utilité réelle, mais le résultat App Store ne vend probablement pas assez la fonction. Le nom français peut être un atout de marque, mais seulement si le sous-titre et le premier screenshot compensent immédiatement l’opacité.

FeedBacks! et Odile! ont toutes deux des taps avec zéro vue page produit. Ce signal doit être traité avec prudence : soit les métriques ont un délai ou une définition différente, soit ces apps déclenchent un geste sans produire de visite mesurée. Dans les deux cas, il ne faut pas les enterrer. FeedBacks! a le meilleur tap rate brut du portefeuille visible. Odile! a 85 impressions Desktop, donc le store la montre. Leur problème n’est pas l’absence totale d’exposition. Leur problème est la compréhension.

Les apps à zéro signal ne doivent pas recevoir le même niveau d’attention stratégique. Bouclez!, My First Sampler, Gogo Looping et BounceDaTracks doivent être classées en audit de présence/indexation. Aucune refonte profonde avant de savoir si elles sont bien visibles, disponibles, indexées, localisées et trouvables par nom exact.

## 3. Diagnostic du portefeuille

### 3.1. Trois lignes distinctes

Première ligne : les outils macOS pro de workflow créatif. C’est le cœur stratégique. Ce sont les apps qui doivent justifier GogoLabs comme marque premium : gagner du temps, réduire les erreurs, contrôler un workflow, livrer plus proprement, éviter les tâches répétitives. Glass Master et Coupez! sont les deux candidats les plus immédiats pour porter ce territoire.

Deuxième ligne : les apps musique, apprentissage ou consumer. Perroquet Piano appartient à cette ligne. Elle a plus de traction que les autres, mais sa logique de marché est différente : iPhone, Japon, apprentissage, volume, localisation. Elle peut devenir un actif utile, mais elle ne doit pas contaminer le positionnement pro.

Troisième ligne : les apps dormantes ou sans signal. Elles ne doivent pas être jugées comme des échecs produit. Elles doivent être auditées comme objets de distribution. Zéro impression signifie d’abord : absence d’exposition mesurée. Avant de parler de promesse, il faut vérifier présence App Store, territoires, catégorie, indexation, compatibilité, recherche exacte, nom public, sous-titre et état de publication.

### 3.2. La marque doit être une gamme, pas une collection

GogoLabs ne doit pas apparaître comme une série d’expériences indépendantes. Une collection disperse la perception. Une gamme crée une doctrine. La doctrine forte est : outils macOS premium pour professionnels créatifs qui veulent contrôler leurs workflows et éviter les pertes de temps ou erreurs de livraison.

Chaque app pro doit être évaluée à partir d’une seule question : quelle erreur ou friction coûteuse cette app supprime-t-elle dans un workflow réel ? Si la réponse n’est pas formulable en une ligne, le problème n’est pas encore le pricing. Le problème est la proposition de valeur.

## 4. Diagnostic funnel

### 4.1. Haut de funnel

Le haut de funnel fonctionne partiellement. Les apps visibles apparaissent principalement via App Store search. Ce n’est pas une audience froide. Ce sont des utilisateurs qui cherchent quelque chose. Mais le résultat affiché ne transforme pas. Le travail prioritaire est donc dans la surface de recherche : nom, icône, sous-titre, première image visible, preuve de valeur immédiate.

### 4.2. Passage vers page produit

Le passage impressions -> page produit est trop faible. Pour une app premium, il n’est pas nécessaire d’avoir un volume massif, mais il faut que chaque apparition soit plus intelligible. Le prochain objectif ne doit pas être vague. Il doit être mesurable : faire passer les apps Desktop prioritaires d’environ 2 % vers 4-6 % de page view rate. Ce ne serait pas encore une excellente performance, mais ce serait un signe que le packaging devient lisible.

### 4.3. Taps et incohérences

FeedBacks! et Odile! montrent des taps sans vues page produit. Ce n’est pas assez robuste pour conclure, mais c’est assez fort pour justifier un audit. Le danger serait de regarder uniquement les téléchargements et de rater des signaux faibles d’intention. Une app qui déclenche un tap mais pas une visite mesurée est peut-être mal instrumentée, mal comprise, ou mal présentée. Dans les trois cas, le correctif commence par la surface App Store.

### 4.4. Bas de funnel et revenus

Le bas de funnel reste impossible à juger commercialement. Le nouveau run a bien ajouté `paid_units` et `developer_proceeds`, mais ils sont à zéro parce que le Sales Report Apple du jour n’est pas encore disponible. Le message Apple indique explicitement que le rapport quotidien n’est pas encore prêt. Ce n’est donc pas une preuve d’absence de ventes. C’est une preuve que l’horaire de collecte ou la date utilisée doivent être corrigés.

Le pricing courant n’est pas encore collecté non plus. L’erreur `missing app_id` indique que l’enrichissement ne dispose pas de l’identifiant Apple nécessaire. Il faut ajouter `app_id` dans `latest-metrics.json` ou faire correspondre les apps via la config avant d’appeler `appPriceSchedule`.

## 5. Priorités de vente

### Priorité 1 : Glass Master

Glass Master est le meilleur test premium Desktop. L’app a 120 impressions, 2 vues page, 2 taps, US dominant et Desktop dominant. Elle combine exposition, marché solvable, device cohérent et potentiel professionnel. Elle doit devenir l’app laboratoire pour vérifier si un meilleur packaging peut doubler le passage vers page produit.

Action commerciale : réécrire la promesse autour du contrôle, de la validation, de la livraison ou de l’erreur évitée. Le screenshot 1 ne doit pas montrer une interface. Il doit montrer le résultat professionnel obtenu.

### Priorité 2 : Coupez!

Coupez! a un nom fort mais potentiellement opaque hors français. Pour une app post-production, ce n’est acceptable que si le sous-titre est chirurgical. L’utilisateur doit comprendre en une seconde : détection de cuts, comparaison image, export conform, workflow audio/post-production, réduction d’erreurs.

Action commerciale : ne pas changer le nom d’abord. Renforcer le sous-titre et le premier screenshot. Le nom donne la personnalité ; le sous-titre doit vendre la fonction.

### Priorité 3 : FeedBacks!

FeedBacks! ne doit pas être positionnée comme outil générique de commentaires. Le marché du feedback générique est mou. La valeur est dans le contrôle : transformer des retours créatifs dispersés en corrections traçables, éviter les validations ambiguës, réduire les allers-retours, garder une preuve de décision.

Action commerciale : repositionner l’app comme outil de suivi de retours créatifs, pas comme bloc-notes.

### Priorité 4 : Odile!

Odile! est exposée mais incomprise. 85 impressions Desktop, zéro vue page, 2 taps. Le nom ne porte pas assez de sens. Si l’app a une utilité forte, elle doit être rendue visible dans le sous-titre et le premier screenshot. Si l’utilité ne peut pas être formulée simplement, elle ne doit pas être front commercial.

### Priorité 5 : Perroquet Piano

Perroquet est un actif séparé. Il a le volume, mais pas le même marché. Le bon axe est localisation japonaise, apprentissage musical, mobile, progression pédagogique. Il ne doit pas servir à calibrer le pricing ou la promesse des apps macOS pro.

### Priorité 6 : apps sans signal

Bouclez!, My First Sampler, Gogo Looping et BounceDaTracks doivent être auditées, pas repackagées en profondeur. Recherche exacte, territoires, catégorie, indexation, compatibilité, fiche publique, statut de publication. Tant que ces vérifications ne sont pas faites, travailler leur marketing serait prématuré.

## 6. Pricing

Le pricing reste la zone aveugle critique. Le pipeline tente maintenant de collecter prix et revenus, mais la donnée n’est pas encore exploitable. Deux corrections sont nécessaires : d’abord inclure `app_id` dans les métriques pour que le pricing par app puisse être récupéré ; ensuite interroger les Sales Reports sur une date déjà disponible, probablement J-1 plutôt que le jour courant.

La doctrine de prix reste néanmoins claire. GogoLabs ne doit pas vendre des utilitaires bon marché. GogoLabs doit vendre du temps gagné, des erreurs évitées, du contrôle de workflow. Une app qui évite une erreur de livraison ou réduit des tâches répétitives dans un contexte professionnel peut supporter un prix premium. Le prix ne doit pas être utilisé pour compenser une fiche floue. Baisser le prix avant de clarifier la valeur détruirait le signal premium.

Architecture recommandée :

- apps pro mono-problème : achat unique premium ;
- apps pro avec valeur de livraison forte : prix plus élevé ou version Pro ;
- valeur continue réelle : abonnement uniquement si mises à jour, modèles, exports, cloud, automatisations ou librairies justifient la récurrence ;
- Perroquet : logique consumer/mobile séparée, avec prix et localisation adaptés.

Un bundle GogoLabs Creative Workflow pourra devenir pertinent, mais seulement après clarification individuelle de Glass Master, Coupez! et FeedBacks!. Un bundle d’apps incomprises n’est pas une offre forte. C’est une confusion groupée.

## 7. ASO

L’ASO est le levier court terme principal, car la source dominante est App Store search. Le problème n’est pas seulement de trouver les bons mots-clés. Le problème est la cohérence entre requête, résultat affiché et promesse perçue. Une app peut être correctement indexée et perdre l’utilisateur en une seconde si le nom ou le sous-titre ne dit pas pourquoi elle mérite un clic.

Règle d’écriture : chaque fiche doit répondre immédiatement à trois questions : pour qui, quelle tâche disparaît, quelle erreur est évitée. Les noms créatifs peuvent rester, mais ils doivent être encadrés par des sous-titres fonctionnels.

Pour la ligne pro, les champs lexicaux prioritaires sont : post-production, audio, video, export, review, feedback, approval, delivery, batch, cut detection, conform, validation, workflow, reliable, precise, controlled, error-free. Ces mots ne doivent pas être saupoudrés. Ils doivent être attachés à une promesse réelle.

## 8. Screenshots

Les screenshots ne doivent pas être des captures décoratives. Ils doivent devenir des preuves de valeur. Le premier screenshot doit fonctionner même en vignette. Il doit dire ce que l’app fait gagner, pas seulement montrer que l’interface existe.

Ordre recommandé pour les apps pro : promesse principale ; avant/après ; workflow en trois étapes ; détail de contrôle avancé ; export/livraison/validation. Une idée par screenshot. Titre court. Interface lisible. Bénéfice métier visible.

Le visuel doit signaler que l’app vient d’un contexte de production réelle. Pas une app générique. Pas un jouet. Un outil conçu par quelqu’un qui connaît les contraintes de livraison.

## 9. Recommandations par app

### Glass Master

Priorité très haute. Refaire le sous-titre, le screenshot 1 et la première phrase. Positionner sur contrôle, validation, qualité de sortie, erreur évitée. Vérifier le prix dès que le pipeline pricing fonctionne. Objectif : augmenter le page view rate.

### Coupez!

Priorité très haute. Sous-titre anglais obligatoire. Mettre en avant post-production, cut detection, conform, comparaison de versions, export structuré si ces fonctions sont bien centrales. Le screenshot 1 doit vendre le workflow, pas l’interface.

### FeedBacks!

Priorité haute. Repositionner sur retours créatifs traçables. Éviter le langage générique. Promesse : ne plus perdre les retours, transformer les commentaires en corrections, réduire les validations ambiguës.

### Odile!

Priorité moyenne. L’app est visible mais non comprise. Si la promesse ne peut pas être formulée en une phrase métier, elle doit être retirée du front commercial.

### Perroquet Piano

Priorité haute mais séparée. Optimiser pour Japon, mobile, apprentissage, pédagogie. Ne pas utiliser son comportement pour définir GogoLabs Pro Tools.

### Apps sans signal

Audit seulement : Bouclez!, My First Sampler, Gogo Looping, BounceDaTracks. Vérifier présence, indexation, territoires, catégories, recherche exacte, compatibilité et fiche publique. Pas de refonte lourde tant que la distribution n’est pas confirmée.

## 10. Risques de dispersion

Le risque principal est de confondre activité et stratégie. Neuf apps, plusieurs lignes de marché, des signaux faibles, une app mobile qui domine le volume, quatre apps à zéro. Sans hiérarchie, l’énergie se dilue. La stratégie doit être brutale : deux apps pro à travailler sérieusement, deux apps à corriger en surface, une app consumer à traiter séparément, les apps invisibles en audit.

Deuxième risque : construire davantage avant d’avoir vendu clairement. Le réflexe produit pousse à ajouter des fonctions. Les métriques disent autre chose : les apps ne sont pas assez vite comprises. Corriger packaging, ASO, screenshots et preuve avant features.

Troisième risque : pricing prématuré. Tant que prix et revenus ne sont pas correctement collectés, les conclusions de pricing doivent rester doctrinales. Mais cela ne doit pas servir d’excuse pour vendre bas. Le premium doit être soutenu par une promesse claire, pas par un prix timide.

## 11. Actions concrètes avant le prochain rapport

- Corriger le pipeline metrics : ajouter `app_id` dans `latest-metrics.json` pour permettre `appPriceSchedule`.
- Interroger les Sales Reports sur J-1 si le rapport du jour n’est pas encore disponible.
- Refaire le sous-titre et le screenshot 1 de Glass Master.
- Refaire le sous-titre et le screenshot 1 de Coupez! en anglais fonctionnel.
- Corriger FeedBacks! autour de la traçabilité des retours créatifs.
- Clarifier Odile! ou la sortir du front commercial.
- Traiter Perroquet comme actif mobile/localisation séparé.
- Auditer les apps à zéro signal sans lancer de refonte lourde.
- Ajouter au dashboard : prix courant, unités payantes, revenus, remboursements, notes, avis, conversion page -> achat/téléchargement, historique J-1/J-7.

## 12. Conclusion décisionnelle

GogoLabs n’a pas un problème d’existence. Les apps apparaissent. Le problème est que la promesse n’est pas assez vite comprise. La stratégie court terme doit donc être une stratégie de clarté : rendre deux apps pro impossibles à mal comprendre.

Le prochain vrai progrès ne sera pas un chiffre de download isolé. Ce sera une hausse du passage impressions -> page produit sur Glass Master et Coupez!, accompagnée d’une mesure claire des revenus et du prix. Tant que ces deux éléments manquent, la stratégie reste partiellement aveugle.

Décision immédiate : concentrer l’effort sur Glass Master et Coupez!, corriger le pipeline pricing/revenus, séparer Perroquet de la ligne pro, et arrêter de donner de l’énergie stratégique aux apps sans signal avant audit de présence.
