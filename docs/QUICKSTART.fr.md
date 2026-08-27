# Démarrage rapide en 60 secondes — Term MCP DeepSeek

> ⚠️ **Lisez d'abord ce que la commande fait, ses risques, son espace de travail
> et ses limites — avant que quoi que ce soit ne s'exécute.** Conservez ensuite
> un reçu signé de ce qui s'est réellement passé.

Term MCP DeepSeek est un plan de contrôle terminal local, **approbation d'abord**,
pour clients MCP et humains. Il donne à DeepSeek un rôle consultatif isolé, tandis
que la politique déterministe possède la planification des commandes, l'approbation,
l'exécution bornée, les événements en direct et les preuves signées.

## Installation (pipx, depuis le dernier tag)

```bash
pipx install term-mcp-deepseek
```

C'est le **seul chemin d'installation recommandé** pour les utilisateurs finaux.
(Installer depuis un clone — `./startup.sh token` — est réservé aux contributions
et aux tests de versions non publiées.)

## Premier résultat en mode inspection (lecture seule)

```bash
term-mcp demo
```

Le mode par défaut est `APPROVAL_MODE=inspect`, réseau désactivé :

- **Écritures : bloquées**
- **Code du projet : bloqué**
- **Approbation : uniquement pour les processus longs**

Le démo exécute des scénarios guidés **sans clé API** et vous montre le reçu
attendu de chaque commande.

## Le reçu attendu

Chaque exécution produit un **reçu signé** qui sépare :

- la commande
- stdout / stderr
- le code de sortie et le signal
- les permissions
- la signature HMAC

Vérifiez un reçu sans rien relancer :

```bash
term-mcp receipt validate FILE
term-mcp receipt show FILE
```

## Arrêter une exécution

Chaque processus est **borné** (pause, reprise, annulation, délai d'expiration,
limites de sortie, isolation de processus). Pour arrêter une session : `Ctrl+C`
dans le terminal, ou utilisez la commande d'annulation du client MCP.

## Trois limites de sécurité

1. **Le texte du modèle ne s'exécute jamais directement** — chaque commande est
   analysée sans shell et limitée à un espace de travail.
2. **Inspect = lecture seule** — par défaut, aucune écriture ni exécution de code
   projet n'est possible.
3. **Les modes `confirm` et `trusted` ne sont pas un bac à sable OS** — testez les
   dépôts non fiables dans un conteneur jetable ou une VM ; gardez
   `WORKSPACE_ROOT` étroit et `ALLOW_NETWORK=false`.

## Pour aller plus loin

- [SECURITY.md](SECURITY.md) — modèle de sécurité complet
- [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) — modèle de menace
- [README.md](README.md) — documentation complète en anglais
