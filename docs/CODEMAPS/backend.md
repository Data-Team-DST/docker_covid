<!-- Généré : 2026-08-24 | Fichiers scannés : 12 | ~350 tokens -->

# Backend — FastAPI :8000 (inférence ML)

## Routes

```
GET  /                          → main.root (info API)
GET  /health                    → health.router (état service + modèle)
GET  /metrics                   → metrics.router (compteurs internes, text/plain)
POST /api/v1/predict            → predict.predict → verify_api_key → preprocess_image
                                   → model_loader.predict → PredictionResponse
```

Middleware : CORS (`allow_origins=["*"]`, pas de credentials) → rate limiter (slowapi,
`RATE_LIMIT_PER_MINUTE`, 100/min par défaut) → logging HTTP custom (`_log_requests`).

## Key Files

```
app/main.py              entrée + lifespan + CORS + middleware log (89L — hors gabarit, limite 50L)
app/config.py             Settings (pydantic-settings), lit .env
app/api/health.py         GET /health
app/api/metrics.py        GET /metrics, compteur predict
app/api/predict.py        POST /api/v1/predict — logique complète de l'endpoint
app/api/security.py       verify_api_key (header X-API-Key, fail-open si api_key="")
app/models/loader.py      chargement modèle Keras (.keras), model_loader singleton
app/features/preprocessing.py  preprocess_image (resize, normalisation)
app/schemas/response.py    PredictionResponse (pydantic)
app/rate_limit.py          limiter slowapi, predict_rate_limit
```

## Auth & sécurité

- Header `X-API-Key` requis sur `/api/v1/predict` **seulement si** `settings.api_key` non
  vide — vide par défaut (dev). Aucun garde-fou fail-fast si `API_ENV=production` et
  `API_KEY=""` (voir `docs/friday-audits/` pour le détail du risque).
- Erreur 500 de `/predict` renvoie `str(e)` brut au client (fuite de détail interne).

## Dépendances

TensorFlow/Keras (modèle CNN), FastAPI, pydantic-settings, slowapi (rate limit),
Pillow/numpy (preprocessing image).
