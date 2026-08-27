# Term MCP DeepSeek — roadmap produit, confiance et adoption

> Audit du dépôt : 27 août 2026

Ce document décrit le chemin vers un projet réellement remarquable sur GitHub. Il ne promet pas la viralité : les étoiles sont une conséquence possible d’un produit utile, fiable, démontrable et facile à adopter. La priorité est donc de rendre chaque promesse vérifiable avant d’ajouter de nouvelles fonctionnalités.

## Verdict en une phrase

Le projet a une bonne matière première — un terminal pilotable par IA, des outils MCP, du JSON-RPC, du SSE, un mode STDIO et Docker — mais il lui manque aujourd’hui une frontière de sécurité crédible, un runtime unique, une implémentation MCP réellement utilisable et une expérience d’installation prouvée.

## Positionnement à viser

**Term MCP DeepSeek doit devenir le terminal copilot local, inspectable et sécurisé pour les clients MCP.**

La promesse tient en quatre verbes :

1. **Planifier** une action en langage naturel.
2. **Montrer** les commandes, les fichiers touchés et les risques.
3. **Demander l’autorisation** avant toute action sensible.
4. **Exécuter et produire une preuve** : sortie, code retour, durée, session et politique appliquée.

DeepSeek reste le premier fournisseur de modèle. MCP devient l’interface interopérable. La vraie différenciation n’est pas « un chatbot qui lance des commandes », mais une exécution terminale que l’utilisateur peut comprendre, limiter, interrompre et auditer.

### Public prioritaire

- développeurs qui veulent un agent terminal local sans envoyer leur environnement à un service distant ;
- utilisateurs de clients MCP qui cherchent un serveur terminal prêt à essayer ;
- contributeurs intéressés par la sécurité des agents, le JSON-RPC et les transports locaux.

### Ce que le projet ne doit pas devenir tout de suite

- un shell distant multi-utilisateur exposé sur Internet ;
- un agent autonome capable d’exécuter silencieusement des actions destructrices ;
- une plateforme de plugins sans modèle de permissions ;
- une collection de fonctionnalités UI sans contrat de sécurité ni preuve de compatibilité.

## État réel observé dans le dépôt

### Ce qui existe déjà

- "mcp_server.py" contient trois outils terminal ("write_to_terminal", "read_terminal_output", "send_control_character") ainsi que des structures de prompts, resources et roots ;
- "server_new.py" expose une factory Flask, tandis que "server.py" contient une seconde application avec logging, middleware et initialisation globale ;
- "api/routes.py" fournit "/health", "/", "/chat", "/mcp/info" et "/stream" ;
- "tools/deepseek_client.py" possède des appels DeepSeek non-streaming et streaming avec gestion de quelques erreurs HTTP ;
- "tools/json_rpc.py", "tools/auth.py", "tools/input_validator.py", "tools/rate_limiter.py" et "tools/error_handler.py" donnent une base exploitable pour des contrats plus stricts ;
- Docker, un script de démarrage, un mode STDIO et une suite de tests sont présents ;
- tous les fichiers Python suivis compilent avec "py_compile" lors de cet audit.

### Les bloqueurs qui empêchent une vraie adoption

1. **Deux runtimes concurrents.** "startup.sh" lance "server_new.py", le README recommande "server.py", et les deux n’ont pas le même montage de sécurité ni la même configuration.
2. **Contrat MCP incomplet et non prouvé.** Le README parle d’un serveur « MCP-like », mais les routes HTTP "/mcp/list_tools" et "/mcp/call_tool" documentées n’existent pas dans "api/routes.py". Les méthodes de "MCPServer" ne sont pas reliées à un endpoint MCP HTTP complet.
3. **Mode STDIO non fiable.** "stdio_server.py" importe des fonctions "mcp_*" depuis "server.py" qui ne sont pas définies dans ce fichier ; en outre, "JSONRPCServer.handle_request()" dépend de "flask.request", ce qui ne convient pas à un transport STDIO.
4. **Exécution shell trop large.** Un shell Bash persistant global est créé au démarrage. Le modèle peut générer une ligne "CMD:" qui est ensuite exécutée ; une validation par motifs n’est pas une sandbox et ne remplace pas une approbation explicite.
5. **Authentification désactivée sur les routes sensibles.** Les décorateurs sont commentés sur "/chat" et "/stream". Les valeurs par défaut "CHANGE_ME", "your_secret_key_here" et les identifiants OAuth présents dans ".env.example" rendent la configuration de production ambiguë.
6. **Sessions et événements non alignés.** Les conversations utilisent un store global, le chat renvoie toujours session_id: "default", tandis que le flux SSE s’appuie sur un event bus séparé. Le multi-session annoncé n’est donc pas encore un comportement fiable.
7. **Promesses d’installation contradictoires.** Le port oscille entre 8000 et 5000 ; Docker mappe "5000:5000" alors que la configuration par défaut et le démarrage peuvent écouter sur 8000. Le script installe aussi les dépendances au démarrage et contient une ancienne implémentation après "exec".
8. **Preuve de qualité insuffisante.** La CI sélectionne seulement un sous-ensemble de tests. Dans cet environnement, "pytest" n’était pas installé ; aucune exécution complète de la suite n’est donc revendiquée dans cet audit. Il faut également corriger les tests qui utilisent "self.client" sans fixture et le faux fixture "mocker" avant de parler de couverture.
9. **Documentation peu différenciante.** Le README est encore formulé comme une preuve de concept et demande de modifier un ".env" sans fournir de parcours complet, de matrice de compatibilité, d’exemple client, de menace explicitée ou de démonstration reproductible.
10. **UI non prouvée.** "static/chat.html" propose une interface agréable à première vue, mais elle dépend de CDN, désactive les appels d’authentification côté client et n’a ni tests navigateur ni vérification responsive/accessibilité documentée.

## Principes de décision

- **Secure by default :** un clone fraîchement installé ne doit jamais exposer un shell utilisable sans configuration explicite.
- **Une seule vérité :** une factory, une configuration, un protocole, une commande de lancement.
- **L’outil avant la vitrine :** un parcours terminal fiable vaut mieux que dix écrans décoratifs.
- **Permission avant autonomie :** toute action ayant un effet externe doit être visible et approuvable.
- **Local-first :** pas de télémétrie obligatoire, pas de secret dans les logs, et des données de session effaçables.
- **Preuve avant marketing :** chaque badge, compatibilité et promesse doit être relié à un test ou à une démonstration rejouable.
- **Petites surfaces publiques :** limiter les resources, roots et chemins aux espaces autorisés ; ne jamais publier la racine système ou le home par défaut.

## Ordre des priorités

| Phase | But | Dépend de | Sortie attendue |
| --- | --- | --- | --- |
| P0 | Rendre le runtime vrai et reproductible | — | clone propre, démarrage unique, tests exécutables |
| P1 | Transformer l’exécution en frontière de confiance | P0 | sandbox, approbation, auth et audit |
| P2 | Devenir un serveur MCP vérifiable | P0, P1 | handshake, transports et conformance tests |
| P3 | Construire le produit que les gens veulent montrer | P1, P2 | plan → approbation → exécution → receipt |
| P4 | Réduire le coût d’adoption | P0, P2, P3 | installation en une commande, docs et releases |
| P5 | Créer une boucle de contribution | P4 | exemples, recettes, issues et contributions guidées |
| P6 | Amplifier ce qui fonctionne | P3, P4, P5 | démonstrations partageables, intégrations et mesure |

---

## P0 — Une vérité technique et une première réussite fiable

**Objectif :** qu’une personne qui clone le dépôt sache exactement quel processus elle lance, quelle API elle utilise et comment vérifier que tout fonctionne.

### Travail

- [ ] Choisir "create_app()" comme point d’entrée unique et supprimer la divergence entre "server.py" et "server_new.py".
- [ ] Fusionner "config.py" et "config_new.py" dans une configuration typée, documentée et validée au démarrage.
- [ ] Remplacer les secrets par défaut par un échec explicite avec message d’aide ; ne jamais démarrer en mode dangereux par accident.
- [ ] Réécrire "startup.sh" en script court et déterministe : ne garder qu’un chemin actif, supprimer le code mort après "exec", respecter "HOST" et "PORT" fournis par l’environnement.
- [ ] Ajouter une CLI stable, par exemple "term-mcp serve", "term-mcp stdio", "term-mcp doctor" et "term-mcp version".
- [ ] Décider une convention de port et l’utiliser dans ".env.example", Docker, le health check, le README et les tests.
- [ ] Séparer clairement les trois couches : transport, protocole MCP/JSON-RPC et exécution terminale.
- [ ] Refondre "JSONRPCServer" pour recevoir une requête en argument au lieu de dépendre directement du contexte Flask ; le transport HTTP et le transport STDIO doivent partager le même dispatcher.
- [ ] Corriger le mode STDIO : aucune sortie non JSON sur stdout, logs uniquement sur stderr, gestion de l’EOF, des erreurs de parsing, des notifications et des ids.
- [ ] Écrire un test de fumée sans clé DeepSeek : démarrage, "/health", découverte des outils, erreur structurée et arrêt propre.
- [ ] Faire tourner toute la suite avec "python -m pytest", supprimer la sélection artificielle dans la CI et publier la couverture réellement mesurée.
- [ ] Ajouter un linter et un formatteur reproductibles, avec une configuration minimale et un job CI dédié.

### Critères d’acceptation

- Un clone vierge démarre avec une commande documentée et un message d’erreur utile si la configuration est incomplète.
- Il n’existe plus qu’un serveur officiel, une configuration officielle et une commande officielle par transport.
- "curl /health" fonctionne sans clé modèle ; une commande "doctor" explique les prérequis manquants.
- Un même cas JSON-RPC passe par HTTP et STDIO avec la même réponse.
- La CI exécute tous les tests, le lint et le format check ; aucun test n’est masqué par un chemin de fichier sélectionné.
- Le README ne décrit plus de routes qui n’existent pas et ne présente plus une fonctionnalité déjà livrée comme « future ».

## P1 — Confiance, sandbox et autorisation humaine

**Objectif :** rendre l’exécution terminale défendable dans un dépôt local. Cette phase est le véritable prérequis à toute communication publique ambitieuse.

### Modèle de sécurité cible

Chaque requête suit ce flux :

"intention utilisateur → plan structuré → analyse du risque → approbation → exécution bornée → receipt signé/horodaté"

### Travail

- [ ] Retirer le protocole implicite "CMD:". Le modèle ne doit jamais déclencher une commande simplement parce qu’une ligne de texte contient ce préfixe.
- [ ] Définir un schéma de tool call strict : nom, arguments validés, mode d’approbation, répertoire de travail et limites d’exécution.
- [ ] Ajouter trois modes explicites : "inspect" (lecture seule), "confirm" (approbation par action) et "trusted" (périmètre préconfiguré, toujours journalisé).
- [ ] Exiger l’approbation pour l’écriture, la suppression, les changements de permissions, le réseau, les processus et les commandes composées.
- [ ] Remplacer le filtrage de motifs par une politique composée d’un workspace root, d’un allowlist de capacités et de limites de système.
- [ ] Refuser par défaut les chemins hors workspace, les symlinks sortants, les devices, les pipes réseau vers un shell, les élévations et les actions sur le système hôte.
- [ ] Isoler un shell par session, ou utiliser un runner dédié ; ne plus partager un Bash global entre utilisateurs et sessions.
- [ ] Ajouter timeout dur, annulation, taille maximale de stdout/stderr, nombre maximal de processus, code de sortie et signal dans le résultat.
- [ ] Corriger le suivi d’état : le résultat doit distinguer "planned", "approved", "running", "succeeded", "failed", "cancelled" et "timed_out".
- [ ] Activer l’authentification sur tous les endpoints qui lisent ou modifient un environnement ; générer un secret aléatoire si l’utilisateur n’en fournit pas et refuser les secrets faibles.
- [ ] Remplacer "Access-Control-Allow-Origin: *" par une allowlist explicite ; documenter le cas local et le cas derrière reverse proxy.
- [ ] Ne jamais journaliser les tokens, les headers Authorization, les prompts complets par défaut ou des sorties contenant des secrets connus.
- [ ] Ajouter "audit.jsonl" ou une sortie équivalente opt-in, avec hash de la commande, politique appliquée, approbation, durée, code retour et empreinte de session.
- [ ] Limiter les resources et roots à un espace autorisé. Ne pas exposer automatiquement "file:///", le home ou tout le système.
- [ ] Écrire un threat model court : prompt injection, exfiltration, path traversal, commande composée, abus du SSE, fuite inter-session, logs sensibles et déni de service.

### Critères d’acceptation

- Sans token valide, "/chat", "/stream" et les appels d’outils protégés renvoient 401 ; le health check reste public.
- Une demande comme « supprimer tout le dépôt » produit un plan bloqué ou soumis à confirmation, jamais une exécution silencieuse.
- Les tests couvrent "../", symlinks, "sudo", pipes réseau, substitutions shell, interruptions, timeout, sorties géantes et sessions croisées.
- Une commande autorisée ne peut pas lire ou écrire hors du workspace déclaré.
- Deux sessions ne voient ni le shell, ni les événements, ni l’historique de l’autre.
- Une receipt permet de répondre à : quoi, quand, où, pourquoi, avec quelle permission et quel résultat.

## P2 — MCP réel, interopérable et testable

**Objectif :** passer de « MCP-like » à un contrat MCP explicitement ciblé et vérifié.

### Travail

- [ ] Épingler dans la documentation la version de la spécification ciblée et les capacités réellement supportées.
- [ ] Implémenter le handshake/initialize, la négociation de capacités, la découverte des outils, l’appel d’outil et les erreurs conformément au contrat choisi.
- [ ] Définir un endpoint MCP unique au lieu de routes pseudo-MCP dispersées ; garder éventuellement les endpoints de compatibilité derrière une version et une dépréciation documentées.
- [ ] Retourner des content blocks et des erreurs structurées cohérents, y compris pour validation, permission refusée, timeout et commande interrompue.
- [ ] Supporter correctement les notifications, les ids nullables et les requêtes invalides sans traceback ni fuite de détails internes.
- [ ] Choisir les transports supportés pour v1 : STDIO obligatoire pour l’usage local ; HTTP/SSE seulement avec session, auth et limites documentées.
- [ ] Ajouter des fixtures JSON de protocole et des tests de contrat indépendants du modèle DeepSeek.
- [ ] Vérifier les clients cibles un par un et publier un tableau « testé / non testé » avec version et date.

### Critères d’acceptation

- Un client MCP compatible peut initialiser le serveur, lister les outils et invoquer une lecture autorisée sans adaptation spécifique au dépôt.
- Les tests de contrat détectent une régression de schéma avant le merge.
- Les erreurs de protocole restent valides même lorsque le shell ou l’API DeepSeek est indisponible.
- La documentation distingue clairement compatibilité MCP, API REST historique et interface web.

## P3 — Le produit signature : plan, terminal et receipt

**Objectif :** créer un moment produit que les utilisateurs auront envie de montrer dans une issue, une vidéo ou une démo.

### Expérience cible

1. L’utilisateur demande : « trouve les tests lents et propose une correction ».
2. Le serveur affiche les commandes prévues, le workspace, le risque et une estimation des sorties.
3. L’utilisateur approuve ou modifie le plan.
4. Le terminal diffuse les événements en direct et permet d’annuler.
5. La réponse finale contient le résultat humainement lisible et une receipt JSON exportable.

### Travail

- [ ] Introduire un objet "ExecutionPlan" versionné et sérialisable.
- [ ] Ajouter une prévisualisation lisible : commandes, fichiers potentiellement touchés, réseau, durée maximale et niveau de risque.
- [ ] Afficher séparément la commande, stdout, stderr, code retour et synthèse DeepSeek ; ne jamais mélanger une sortie non fiable avec une instruction.
- [ ] Ajouter pause, cancel, retry contrôlé, re-run et copie de commande.
- [ ] Remplacer la session "default" par une vraie identité de session et une politique de rétention explicite.
- [ ] Faire correspondre les événements SSE aux états métier et nettoyer les files d’événements à la déconnexion ou à l’expiration.
- [ ] Ajouter une UI « approval first » avec un état connexion/auth visible, un affichage du périmètre et des erreurs actionnables.
- [ ] Rendre l’interface utilisable au clavier, sur mobile et sans CDN externe en mode production.
- [ ] Ajouter export/import de receipts redacted, afin de partager un résultat sans partager de secret ni de contenu privé.
- [ ] Isoler l’adaptateur DeepSeek du moteur d’exécution : retries bornés, backoff, timeout, budget de tokens et mode indisponible explicite.
- [ ] Ajouter un mode sans clé qui permet de découvrir les outils, tester la sandbox et rejouer des fixtures locales.

### Critères d’acceptation

- La démo principale fonctionne sans modifier le code et montre au moins une approbation, une annulation et une commande réussie.
- Une receipt JSON peut être validée par un schéma et relue par la CLI.
- Une panne DeepSeek ne fait pas croire qu’une commande a réussi et ne bloque pas les outils locaux de diagnostic.
- Un test navigateur couvre le chargement, l’envoi, l’état d’attente, l’affichage d’erreur, l’approbation, l’annulation et le responsive.

## P4 — Installation, packaging et preuve publique

**Objectif :** réduire le coût entre « je vois le projet » et « j’ai obtenu un résultat sûr ».

### Travail

- [ ] Ajouter un "pyproject.toml", un package installable, une version unique et un point d’entrée CLI.
- [ ] Fournir un chemin recommandé parmi "pipx", "uvx" ou installation locale ; ne pas proposer cinq chemins équivalents dans le README.
- [ ] Fournir un ".env.example" minimal, sans secrets plausibles, avec validation de chaque variable et exemples de configuration locale.
- [ ] Rendre le conteneur reproductible : dépendances de build séparées, pas d’installation au runtime, utilisateur non-root, port cohérent, health check cohérent et arrêt propre.
- [ ] Tester Python et les OS réellement supportés dans une matrice CI ; ne pas annoncer Python 3.8+ si le code et les dépendances ne sont pas vérifiés sur cette plage.
- [ ] Ajouter une commande "doctor" qui vérifie Python, shell, permissions workspace, configuration, connectivité optionnelle et transport.
- [ ] Réécrire le README autour d’un « résultat en 60 secondes » : installation, configuration, premier appel, sortie attendue, arrêt et dépannage.
- [ ] Ajouter une courte vidéo/GIF ou une capture terminale reproductible montrant le plan, l’approbation et la receipt.
- [ ] Ajouter une architecture simple, un tableau des endpoints, un guide sécurité et un tableau des fonctionnalités supportées.
- [ ] Ajouter "CHANGELOG.md", releases GitHub, versioning cohérent, artefacts publiés et rollback documenté.
- [ ] Ajouter "SECURITY.md", politique de divulgation, licence visible, "CONTRIBUTING.md", Code of Conduct et templates d’issues.
- [ ] Ajouter CodeQL ou équivalent, scan de dépendances, secret scanning et vérification des images Docker si une image est publiée.

### Critères d’acceptation

- Un nouveau contributeur obtient un premier résultat local sans lire le code source.
- Une installation propre, Docker et STDIO sont testés dans CI ou dans une recette de release.
- Chaque release publie une version qui correspond à la CLI, à l’API d’information et aux notes de version.
- Le README répond directement à : « que fait-il ? », « pourquoi lui ? », « est-ce sûr ? », « comment l’essayer ? » et « comment contribuer ? ».

## P5 — Contribution et boucle communautaire

**Objectif :** transformer les premiers utilisateurs en contributeurs, et les contributeurs en preuves publiques de qualité.

### Travail

- [ ] Ajouter un guide de développement avec environnement, commandes de test, fixtures, conventions et architecture.
- [ ] Ajouter un devcontainer ou une procédure reproductible pour éviter le « works on my machine ».
- [ ] Créer des exemples indépendants et petits : inspection de dépôt, diagnostic de tests, analyse de logs, vérification de port, mode lecture seule.
- [ ] Définir un format de recette : intention, prérequis, permissions, étapes, sortie attendue, receipt anonymisée et niveau de risque.
- [ ] Publier un dossier "examples/" validé en CI ; chaque recette doit être sans secret et ne pas modifier la machine de façon destructive.
- [ ] Créer des labels et issues « good first issue », « help wanted », « security », « protocol », « docs » et « client integration ».
- [ ] Ajouter des tests de régression à partir des bugs corrigés, avec un modèle d’issue qui demande transport, OS, version et receipt.
- [ ] Documenter la manière d’ajouter un outil sans contourner la sandbox ni le système de permissions.
- [ ] Ajouter un benchmark reproductible : latence, temps avant premier événement, coût modèle optionnel, taille de sortie et taux d’annulation.
- [ ] Organiser des mini-défis publics autour des receipts et de la sécurité, pas autour de commandes dangereuses.
- [ ] Répondre aux issues avec des reproductions minimales et publier les décisions d’architecture importantes.

### Critères d’acceptation

- Un contributeur externe peut ajouter une recette ou un test sans comprendre toute l’application.
- Les exemples sont exécutables sur une machine temporaire et leurs permissions sont lisibles avant lancement.
- Les bugs critiques deviennent des tests de non-régression.
- Les PRs reçoivent automatiquement test, lint, sécurité et aperçu de compatibilité protocole.

## P6 — Amplification responsable

**Objectif :** donner des raisons légitimes de partager le projet et de revenir, une fois le socle prouvé.

### Travail

- [ ] Publier une galerie de receipts anonymisées et de recettes utiles, avec commande de reproduction et limites affichées.
- [ ] Maintenir une matrice d’intégrations vérifiées avec liens vers les configurations et versions testées.
- [ ] Produire des démos courtes centrées sur un problème concret : comprendre un dépôt inconnu, diagnostiquer un test, inspecter un incident sans quitter le terminal.
- [ ] Ajouter des badges qui mesurent des faits : CI, couverture, sécurité, package, version et compatibilité — jamais des badges décoratifs non vérifiés.
- [ ] Mettre en avant les contributeurs et les recettes acceptées dans les releases.
- [ ] Mesurer l’adoption sans télémétrie obligatoire : succès de l’installation en CI, issues de démarrage, téléchargements de release si disponibles, contributeurs actifs et réutilisation des exemples.
- [ ] Suivre la conversion GitHub comme un signal secondaire : visite → clone → premier résultat → retour → contribution. Les étoiles seules ne sont pas la définition du succès.

## Les 10 premiers tickets à créer

1. **P0 — ADR runtime unique :** choisir la factory, les transports et supprimer la divergence des serveurs.
2. **P0 — Dispatcher indépendant de Flask :** rendre le JSON-RPC commun à HTTP et STDIO.
3. **P0 — Startup/ports/Docker :** unifier port, health check, arrêt et installation.
4. **P0 — Test baseline :** réparer les fixtures, installer toute la suite et faire passer la CI complète.
5. **P1 — Threat model :** écrire les scénarios et la politique de sécurité vérifiable.
6. **P1 — ExecutionPlan + approval :** retirer "CMD:" et introduire la confirmation structurée.
7. **P1 — Workspace sandbox :** chemins, symlinks, sorties, timeout, processus et session isolée.
8. **P2 — MCP conformance :** handshake, tools/list, tools/call, erreurs et fixtures de transport.
9. **P3 — Receipts :** schéma, export redacted, UI de résultat et replay contrôlé.
10. **P4 — README 60 secondes + packaging :** installation unique, démo reproductible et release automatisée.

## Tableau de bord à suivre

Ces cibles servent à décider si une phase est terminée ; elles ne sont pas des promesses de résultat.

| Signal | Cible avant communication large |
| --- | --- |
| Installation propre jusqu’au health check | une commande documentée, testée en CI |
| Premier résultat local sans modèle | outils de découverte et doctor fonctionnels |
| Tests | suite complète verte, sans sélection cachée |
| Sécurité | aucun secret dans logs/fixtures ; tests adversariaux sur la sandbox |
| Interopérabilité | au moins un client réel par transport ciblé, avec version/date |
| Confiance | receipt valide pour chaque exécution et état final non ambigu |
| Contribution | exemples, guide, templates et au moins une issue de démarrage claire |
| Produit | démo plan → approbation → exécution → receipt en moins de quelques minutes |

## Definition of Amazing v1.0

Le projet peut être présenté comme une v1 remarquable lorsque toutes ces cases sont vraies :

- [ ] le nom, la promesse et la capture d’écran racontent la même chose ;
- [ ] le clone, Docker, HTTP et STDIO ont un chemin officiel et vérifié ;
- [ ] aucune commande générée par le modèle n’est exécutée sans passer par le moteur de permissions ;
- [ ] le workspace, l’authentification, les sessions et le SSE sont isolés et testés ;
- [ ] le serveur parle un contrat MCP documenté et dispose de tests de conformité ;
- [ ] le premier parcours montre une valeur concrète avant de demander une configuration complexe ;
- [ ] chaque action produit une receipt lisible et partageable après retrait des données sensibles ;
- [ ] le README contient une démo, des limites honnêtes, un guide sécurité et un dépannage ;
- [ ] les releases, scans et tests sont automatisés ;
- [ ] un inconnu peut contribuer par un exemple ou un test sans rendez-vous avec l’auteur.

## Décision stratégique finale

Ne pas chercher à gagner des étoiles en ajoutant d’abord plus de prompts, plus de routes ou plus de commandes. Faire de **l’exécution terminale locale, bornée, explicable et prouvée** la fonctionnalité signature. Quand le projet sera sûr à essayer, facile à comprendre et agréable à partager, les intégrations, les recettes et les contributions pourront créer une vraie boucle d’adoption.
