# Démarrage à froid — toujours `make start-all` avant tout target ciblant `backend` seul

Retour d'expérience (2026-08-31, Cirine) : `make monitoring-start` lancé sur un environnement
entièrement à froid (rien de la stack ne tournait encore) a fait planter le démarrage —
`docker compose` a fini en erreur (`dependency failed to start: container
covid-xray-segmentation-service is unhealthy`).

## Cause racine (confirmée par les logs réels du conteneur, pas une supposition)

`monitoring-start` (comme `start` et `presentation-all`) fait `docker compose up -d --build
backend` — qui entraîne `segmentation-service` via `depends_on`, mais **ne démarre ni `mlflow`
ni `minio` ni `postgres`**. Au démarrage, `segmentation-service` tente d'abord MLflow Registry ;
sur un environnement à froid, le hostname `mlflow` ne résout même pas
(`NameResolutionError`), et la boucle de retry-avant-fallback est assez longue pour dépasser la
fenêtre de healthcheck (`start_period: 200s`) — le conteneur est marqué unhealthy **avant même
d'avoir fini de démarrer**, et `backend` (qui attend `condition: service_healthy`) ne démarre
jamais.

Second problème indépendant rencontré dans le même incident : le fallback local
(`data/models/segmentation.keras`) échoue aussi si `dvc pull` n'a jamais été fait — même une
fois `mlflow` accessible, sans modèle enregistré en `Production` sur *son* instance MLflow
locale (chaque environnement Docker Compose a son propre MinIO/Postgres, pas de partage
automatique entre machines), `/v1/segment` répond 503 tant qu'aucun modèle n'est chargé.

## Règle

Sur un environnement où rien ne tourne encore (`docker ps` vide, ou après un `docker compose
down`) :

1. `make dvc-pull` d'abord si `data/models/*.keras` est absent — garantit un fallback local
   fonctionnel même si MLflow Registry n'a pas (encore) le modèle en `Production` sur cette
   machine.
2. `make start-all` (jamais `make start`, `make monitoring-start` ou `make presentation-all`
   en premier sur un environnement froid) — démarre `mlflow`/`minio`/`postgres` en même temps
   que `backend`/`segmentation-service`, évitant la course où `mlflow` n'existe pas encore sur
   le réseau Docker au moment où `segmentation-service` essaie de s'y connecter.
3. Une fois la stack complète up et stable, les targets ciblés (`monitoring-start`,
   `presentation-all`, `demonstration`, etc.) peuvent être relancés librement — le risque ne
   concerne que le tout premier démarrage à froid.
