# Chantier — Déployer réellement sur Kubernetes (US-23)

> Document de cadrage, pas un plan d'exécution. Rédigé le 2026-08-24 à la demande de Steven
> ("je maîtrise pas ce que tu m'as dit de faire, je préfère avoir un doc et faire le nécessaire
> à partir de ce fichier"). Destiné à être repris par une autre conversation Claude Code, ou
> exécuté pas à pas par Steven lui-même en s'appuyant sur ce fichier.

## Pourquoi ce n'est pas optionnel

Confirmé le 2026-08-24 via les slides du kick-off de projet (Maria - Liora, transmises par
Steven) : la **Phase 3 du planning officiel** ("Orchestration & Déploiement", deadline 24/04)
liste explicitement **"Implémenter la scalabilité avec Docker/Kubernetes"** parmi ses objectifs.
US-23 dans `dashboard/backlog.yaml` (marquée `MUST`) correspond donc à un livrable attendu par
l'encadrement, pas à une envie ajoutée après coup — malgré la mention "optionnel" trouvée dans
`docs/ARCHITECTURE_MICROSERVICES.md` (à corriger une fois ce chantier traité, cette note y est
contradictoire avec le cahier des charges réel).

La deadline officielle (24/04) est passée depuis 4 mois — ce n'est plus une question de
respecter un jalon, mais de pouvoir **montrer un cluster Kubernetes qui tourne réellement** à la
soutenance du 2026-09-04 (dans ~10 jours au moment de la rédaction de ce document).

## Pas besoin de payer

Point soulevé par Steven : comment déployer sur un vrai cluster sans compte cloud payant ni
carte bleue ? Réponse — **pas besoin de cloud du tout** :

- **`kind`** (Kubernetes IN Docker) ou **`minikube`** montent un cluster Kubernetes complet
  **en local**, dans des conteneurs Docker (`kind`) ou une VM/conteneur local (`minikube`).
  Gratuits, aucun compte cloud, aucune carte bancaire. Seul pré-requis : Docker installé
  (déjà le cas sur cette machine, vérifié le 2026-08-24).
- `dashboard/backlog.yaml` (description d'US-23) mentionne déjà cette option : *"valider le
  déploiement sur un cluster réel (kind/minikube)"*.
- Un cluster local suffit largement pour la démonstration attendue : "scalabilité avec
  Kubernetes" se montre avec des replicas, des probes, un ingress qui route — pas besoin
  d'un vrai cloud pour ça.

**Recommandation** : `kind`, plus léger et plus rapide à démarrer/détruire que `minikube`,
mieux adapté à une démo ponctuelle avant soutenance.

## État réel des manifests (vérifié le 2026-08-24)

`infrastructure/kubernetes/` contient :

| Fichier | Contenu | État |
|---|---|---|
| `namespace.yaml` | Namespace `ds-covid` | OK |
| `configmap.yaml` | Config non-sensible (API_ENV, URLs MLflow/MinIO...) | OK |
| `secrets.yaml.example` | Gabarit du Secret (`API_KEY`, credentials MinIO/Postgres) | OK — copier en `secrets.yaml` (gitignoré) et remplir avant `kubectl apply` |
| `backend.yaml` | Deployment + Service backend FastAPI | OK, `securityContext` non-root déjà en place (2026-08-24) |
| `streamlit.yaml` | Deployment + Service frontend | ⚠️ `image: ds-covid-streamlit:latest` (tag mutable), pas de `securityContext` |
| `mlflow.yaml` | Deployment + Service MLflow | Pas de `securityContext` |
| `storage.yaml` | Postgres (backend MLflow) + MinIO (artifacts/DVC) + 3 PVC (`postgres-pvc`, `minio-pvc`, `models-pvc`) | OK |
| `ingress.yaml` | Routes `/`, `/api`, `/mlflow` vers les 3 services (host `ds-covid.local`) | OK, nécessite un ingress controller (nginx) installé dans le cluster |

**Manque entièrement** :
- Aucun manifest pour **`data-service`** (port 5001) ni **`log-service`** (port 5002) — les deux
  microservices tournent en Docker Compose mais n'ont pas d'équivalent K8s. À écrire avant de
  pouvoir dire que "tous les microservices" sont orchestrés par Kubernetes.
- Aucun `Makefile`/script pour créer le cluster local (`kind create cluster`) ni charger les
  images buildées localement dedans (`kind load docker-image`) — à ajouter, cf. plan ci-dessous.

## Plan d'exécution proposé

1. **Installer `kind`** (binaire unique, pas de dépendance lourde) :
   `curl -Lo kind https://kind.sigs.k8s.io/dl/latest/kind-windows-amd64.exe` (ou via choco/scoop
   sous Windows) — vérifier la commande exacte au moment de l'exécution, l'URL "latest" change.
2. **Créer le cluster** : `kind create cluster --name ds-covid`.
3. **Builder les images en local** (déjà buildables, cf. commits du 2026-08-24 sur les
   Dockerfiles backend/data-service) et les charger dans `kind` :
   `kind load docker-image ds-covid-backend:latest --name ds-covid` (et streamlit, mlflow).
4. **Copier `secrets.yaml.example` → `secrets.yaml`**, remplir des valeurs de test (pas besoin
   de vraies clés pour une démo locale), vérifier qu'il reste gitignoré.
5. **Écrire les manifests manquants** : `data-service.yaml`, `log-service.yaml` (calquer sur
   `backend.yaml`, en gardant `securityContext` non-root — cf. commit `37f6c59`).
6. **Installer un ingress controller** dans le cluster kind (nginx-ingress a un manifest
   d'install officiel dédié à kind — chercher "kind ingress nginx" au moment de l'exécution
   pour la version à jour) — sans ça, `ingress.yaml` ne fait rien.
7. **`kubectl apply -f infrastructure/kubernetes/`** (dans l'ordre : namespace d'abord, ou
   `-f infrastructure/kubernetes/` applique tout, Kubernetes gère les dépendances via les
   références de nom).
8. **Valider** : tous les pods `Running`, probes `/health` vertes, `kubectl port-forward` ou
   l'ingress répond sur les 3 routes (`/`, `/api`, `/mlflow`).
9. **Corrections cohérence pendant ce chantier** (petites, à faire en passant) :
   - `streamlit.yaml` : tag `:latest` → immuable (même pattern que `backend.yaml`,
     commit `e19b002`), ajouter `securityContext` non-root.
   - `mlflow.yaml`/`storage.yaml` : évaluer si `securityContext` non-root est pertinent
     (image `postgres:15-alpine`/`minio/minio` tournent déjà en non-root par défaut sur
     beaucoup de distributions — à vérifier, pas à supposer).
   - `docs/ARCHITECTURE_MICROSERVICES.md` : retirer la mention "optionnel" sur le déploiement
     K8s, désormais contredite par le cahier des charges officiel.

## Ce que ce document ne fait pas

- Il n'installe rien, ne crée aucun cluster, n'écrit aucun manifest manquant.
- Il ne garantit pas que les commandes exactes (URLs de téléchargement, version de l'ingress
  controller) sont à jour au moment de la reprise — à revérifier, ces outils évoluent vite.
- Il ne couvre pas le monitoring (Prometheus/Grafana, Phase 4) — hors périmètre d'US-23.
