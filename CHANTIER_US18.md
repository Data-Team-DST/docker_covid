# Chantier — US-18 : Prometheus + instrumentation FastAPI

Ouvert le 2026-08-27, suite à la vérification de US-18 pendant le chantier de réconciliation
git (`CHANTIER_RECONCILIATION_GIT.md`, maintenant clos — main + dev sont mergés dans
`chore/claude-code-setup`). Backlog : `dashboard/backlog.yaml`, sprint S4, `US-18`,
`done: false` (statut exact).

**Estimation** : une demi-journée de travail concentré (pas un gros chantier — un seul
service touché, pas de conflit git, le contrat de métriques est déjà écrit dans les fichiers
d'alerting ci-dessous). Le principal piège n'est pas la difficulté technique mais l'oubli
d'une des ~6 métriques attendues par les alertes déjà en place.

---

## Constat de fond

`dev` (mergé le 2026-08-27) a apporté toute l'**infrastructure** de monitoring, mais **aucune
instrumentation réelle** côté backend :

- `infrastructure/docker-compose.yml` : services `prometheus` (port 9090) et `grafana`
  (port 3000), profil `monitoring` (`docker compose --profile monitoring up -d prometheus
  grafana` ou `make monitoring-start` si cette cible existe déjà — à vérifier).
- `infrastructure/docker/monitoring/prometheus/prometheus.yml` : scrape déjà configuré sur
  `backend:8000/metrics`, toutes les 10s.
- `infrastructure/docker/monitoring/prometheus/alert_rules.yml` : **8 règles d'alerte déjà
  écrites**, qui référencent des métriques qui n'existent pas encore dans le code.
- `infrastructure/docker/monitoring/grafana/provisioning/dashboards/covid_backend.json` :
  dashboard Grafana provisionné automatiquement, qui affiche 4 métriques (dont 3 déjà
  disponibles).
- `backend/requirements.txt` : `prometheus-client==0.20.0` déjà ajouté, mais **jamais importé
  nulle part** dans le code.

Ce qui existe côté backend aujourd'hui (`backend/app/api/metrics.py`) est un endpoint
`/metrics` fait à la main, sans lib Prometheus, qui expose seulement 3 métriques : uptime,
modèle chargé (bool), nombre total de prédictions.

## Contrat de métriques (déjà défini par alert_rules.yml + le dashboard — ne pas réinventer)

Ces noms et labels sont **imposés** par les fichiers déjà en place. Toute déviation (nom,
label, type de métrique) cassera silencieusement les alertes/panels sans erreur visible.

| Métrique | Type | Labels | Utilisée par |
|---|---|---|---|
| `ds_covid_uptime_seconds` | gauge | — | ✅ déjà présente, dashboard |
| `ds_covid_model_loaded` | gauge | — | ✅ déjà présente, dashboard |
| `ds_covid_predictions_total` | counter | — | ✅ déjà présente, dashboard + `HighProportionLowConfidence` |
| `ds_covid_http_requests_total` | counter | `status`, `path` | `HighHttpErrorRate`, `NoTrafficReceived` |
| `ds_covid_inference_latency_seconds` | histogram | — | `InferenceLatencyHigh` (p95 via `histogram_quantile`) |
| `ds_covid_auth_failures_total` | counter | — | `RepeatedAuthFailures` |
| `ds_covid_low_confidence_predictions_total` | counter | — | `HighProportionLowConfidence` (seuil confidence < 0.6, à coder) |
| `ds_covid_predictions_by_class_total` | counter | `predicted_class` | `ClassDistributionImbalanced` |

`up{job="backend"}` (alerte `BackendDown`) est générée automatiquement par Prometheus dès que
le scrape fonctionne — rien à coder pour celle-ci.

## Ce qu'il reste à faire

1. **Dépendance** : `prometheus-fastapi-instrumentator` est ce que demande la description
   originale de l'US (`dashboard/backlog.yaml`) — il aurait auto-généré `http_requests_total`
   et la latence par route en quelques lignes. Mais son nom de métrique par défaut ne
   correspond pas au préfixe `ds_covid_` attendu par `alert_rules.yml` (vérifier si la lib
   permet un `metric_namespace="ds_covid"` avant de l'adopter, sinon construire
   `ds_covid_http_requests_total` et `ds_covid_inference_latency_seconds` à la main avec
   `prometheus-client` — déjà dans `requirements.txt`, c'est la voie la plus sûre pour matcher
   exactement le contrat ci-dessus). Vérifier la dernière version stable sur PyPI
   (`pip index versions prometheus-fastapi-instrumentator`) avant de trancher/figer.

2. **`backend/app/api/metrics.py`** : étendre (pas juste remplacer — garder
   `ds_covid_uptime_seconds`/`ds_covid_model_loaded`/`ds_covid_predictions_total`, déjà
   utilisées par le dashboard) pour déclarer les 4 métriques manquantes du tableau ci-dessus
   via `prometheus_client` (`Counter`, `Histogram`), et exposer le tout avec
   `prometheus_client.generate_latest()` (format text Prometheus standard — remplace le
   formatage manuel actuel, ligne 40-51).

3. **`backend/app/api/predict.py`** : au point où `stats.increment_predict()` est déjà appelé
   (ligne ~121), ajouter :
   - `ds_covid_inference_latency_seconds.observe(...)` avec la latence déjà calculée
     (`latency_ms`, attention à l'unité — la métrique est en **secondes**, pas en ms)
   - `ds_covid_predictions_by_class_total.labels(predicted_class=predicted_class).inc()`
   - `ds_covid_low_confidence_predictions_total.inc()` si `confidence < 0.6` (seuil du même
     ordre que celui déjà documenté dans `HighProportionLowConfidence`)
   - dans le bloc `except` (gestion d'erreurs déjà en place, lignes ~132-140) : incrémenter
     `ds_covid_http_requests_total` avec le bon `status` (503/500/400/401/429 selon le cas)

4. **`backend/app/api/security.py`** (`verify_api_key`, déjà existant) : incrémenter
   `ds_covid_auth_failures_total` au moment où l'authentification échoue.

5. **`ds_covid_http_requests_total{path,status}` pour TOUTES les routes** (pas seulement
   `/predict`) : le plus simple est un middleware FastAPI générique dans `app/main.py`
   (`@app.middleware("http")`), plutôt que d'instrumenter chaque route à la main — cohérent
   avec `app/middleware.py` qui existe déjà pour d'autres cross-cutting concerns.

6. **Lockfile** : `prometheus-client` est déjà dans `backend/requirements.txt` (prod) mais
   **absent** de `backend/requirements-dev.txt` (lockfile hash-locké — cf. commit `87b48be`,
   trouvé cassé et corrigé pendant la réconciliation git, mais toujours sans
   `prometheus-client`). Regénérer avec `pip-compile --generate-hashes` **en conteneur Linux**
   (jamais sur cette machine Windows — cf. `.claude/rules/common/github-actions-security.md`
   et retour d'expérience déjà documenté dans `TODO.md`), puis valider en venv propre avant
   de committer (`pip install --require-hashes -r backend/requirements-dev.txt`).

7. **Tests** : au moins un test qui vérifie que `/metrics` expose bien les 8 métriques
   attendues (format Prometheus, présence des noms — pas besoin de tester les valeurs
   exactes). `backend/tests/unit/` a déjà `test_config.py` en modèle de style.

## Vérification finale (une fois codé)

```bash
docker compose -f infrastructure/docker-compose.yml --project-directory . \
  --profile monitoring up -d --build backend prometheus grafana

curl http://localhost:8000/metrics
# → doit lister les 8 métriques du tableau ci-dessus (grep ds_covid_)

open http://localhost:9090/targets
# → target "backend" en état UP

open http://localhost:9090/alerts
# → les 8 règles visibles, aucune en erreur de parsing (PromQL invalide → erreur rouge ici)

open http://localhost:3000
# → dashboard "DS_COVID" (ou nom configuré), panels avec des données (pas "No data")
```

Envoyer quelques requêtes `/api/v1/predict` (avec et sans clé API valide, avec un fichier
non-image pour déclencher une erreur 400) avant de vérifier Grafana/Prometheus, sinon les
compteurs seront à zéro partout et rien ne sera visible sur les graphes.

## Pas fait dans ce chantier (volontairement)

Aucune modification de code appliquée — ce fichier est un plan d'exécution, pas une PR.
Une fois fait, mettre à jour `dashboard/backlog.yaml` (`US-18: done: true`) et
`docs/us-verification.md` (§ US-18).
