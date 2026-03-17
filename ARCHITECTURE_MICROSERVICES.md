# Architecture Microservices pour DS_COVID

## 📐 Structure Proposée

```
DS_COVID/
├── /ml-backend/                    # Service Backend ML (FastAPI)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # Point d'entrée FastAPI
│   │   ├── config.py              # Configuration centralisée
│   │   ├── logging_config.py       # Logging structuré
│   │   ├── models/                # Interfaces modèles
│   │   │   ├── __init__.py
│   │   │   ├── model_loader.py
│   │   │   └── prediction.py
│   │   ├── features/              # Prétraitement données
│   │   │   ├── __init__.py
│   │   │   └── preprocessing.py
│   │   ├── api/                   # Routes API
│   │   │   ├── __init__.py
│   │   │   ├── health.py          # /health endpoint
│   │   │   ├── predict.py         # /predict endpoint
│   │   │   └── metrics.py         # /metrics endpoint
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── data_utils.py
│   │   │   └── model_utils.py
│   │   └── schemas/               # Pydantic schemas
│   │       ├── __init__.py
│   │       ├── request.py
│   │       └── response.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py            # Fixtures pytest
│   │   ├── unit/
│   │   │   ├── test_preprocessing.py
│   │   │   ├── test_models.py
│   │   │   └── test_api.py
│   │   └── integration/
│   │       └── test_api_endpoints.py
│   ├── notebooks/                 # Développement/Exploration
│   │   ├── 01_eda.ipynb
│   │   ├── 02_model_baseline.ipynb
│   │   └── 03_model_training.ipynb
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── README.md
│
├── /frontend/                     # Service Frontend (Streamlit/React)
│   ├── streamlit_app.py           # Version Streamlit simplifiée
│   ├── pages/                     # Pages Streamlit
│   │   ├── 01_predictions.py
│   │   ├── 02_analytics.py
│   │   └── 03_model_info.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── api_client.py          # Client API REST
│   │   └── visualizer.py
│   ├── config/
│   │   └── streamlit_config.toml
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
│
├── /infrastructure/               # Docker & K8s
│   ├── docker-compose.yml
│   ├── kubernetes/
│   │   ├── namespace.yaml
│   │   ├── backend-deployment.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   └── scripts/
│       ├── build.sh
│       └── deploy.sh
│
├── /.github/
│   └── workflows/
│       ├── tests.yml
│       ├── build.yml
│       └── deploy.yml
│
├── /docs/                         # Documentation
│   ├── API.md                     # Spécification OpenAPI
│   ├── SETUP.md                   # Setup environnement
│   ├── DEPLOYMENT.md              # Guide déploiement
│   └── METRICS.md                 # Métriques clés
│
├── /data/                         # Données (gitignore d'habitude)
│   ├── raw/
│   ├── processed/
│   └── .gitkeep
│
└── /models/                       # Artefacts modèles (gitignore)
    ├── trained/
    ├── checkpoints/
    └── .gitkeep
```

## 🎯 Architecture en Couches

```
┌─────────────────────────────────────────┐
│     Frontend (Streamlit/React)          │ (Port 8501/3000)
│   - UI pour prédictions                 │
│   - Analytics & visualisations          │
│   - Gestion utilisateurs                │
└──────────────┬──────────────────────────┘
               │ HTTPS/HTTP
┌──────────────▼──────────────────────────┐
│   FastAPI Backend (ML Service)          │ (Port 8000)
│   ├─ Health checks                      │
│   ├─ Predictions (CV)                   │
│   ├─ Model metrics                      │
│   └─ Monitoring                         │
└──────────────┬──────────────────────────┘
               │ SQLAlchemy/Pandas
┌──────────────▼──────────────────────────┐
│   ML Models Layer                       │
│   ├─ Model Manager (TensorFlow)         │
│   ├─ Preprocessing Pipeline             │
│   └─ Feature Extraction                 │
└──────────────┬──────────────────────────┘
               │ Load/Save
┌──────────────▼──────────────────────────┐
│   Storage Layer                         │
│   ├─ Trained models (HDF5/SavedModel)   │
│   ├─ Training data                      │
│   └─ Metrics/Logs                       │
└─────────────────────────────────────────┘
```

## 🔧 Configuration & Environnement

### Unified `config.py` (Backend)
```python
# ml-backend/app/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # API
    PROJECT_NAME: str = "DS_COVID_Backend"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # Model
    MODEL_PATH: Path = Path("models/trained/best_model.h5")
    MODEL_TYPE: str = "cnn"  # cnn, xgboost, ensemble
    
    # Data
    DATA_PATH: Path = Path("data/processed")
    IMG_SIZE: tuple = (224, 224)
    BATCH_SIZE: int = 32
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = Path("logs/app.log")
    
    # Monitoring
    TRACK_PREDICTIONS: bool = True
    METRICS_FILE: Path = Path("metrics/predictions.json")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### `.env` Template
```env
# ml-backend/.env
DEBUG=false
LOG_LEVEL=INFO
MODEL_PATH=models/trained/cnn_covid.h5
DATA_PATH=data/processed
IMG_SIZE=224
BATCH_SIZE=32
TRACK_PREDICTIONS=true

# Database (optionnel)
DATABASE_URL=sqlite:///./predictions.db

# Frontend
FRONTEND_URL=http://localhost:8501
```

## 📊 Métriques Clés à Tracker

```python
# docs/METRICS.md
## Objectifs du Projet

### 1. Performance Modèle
- Accuracy ≥ 85%
- Sensitivity ≥ 80% (rappel cas positifs)
- Specificity ≥ 90% (rappel cas négatifs)
- AUC-ROC ≥ 0.92
- F1-Score ≥ 0.83

### 2. Stabilité API
- Uptime ≥ 99.5%
- Latence P95 < 500ms
- Zero crashes

### 3. Couverture Tests
- Unit tests ≥ 40%
- Integration tests ≥ 20%
- API tests 100%

### 4. Données
- Dataset size: N = ?
- Train/Val/Test split: 70/15/15
- No missing values in production data
```

## 🚀 Phases d'Implémentation

### Phase 1: Foundation (Semaines 1-2)
- [x] Définir structure
- [ ] Créer environ de base (Python 3.11, venv)
- [ ] Config centralisée
- [ ] Logging structuré
- [ ] Tests pytest fixtures

**Durée:** 5-7 jours | **Dépendance:** Aucune

### Phase 2: ML Core (Semaines 2-4)
- [ ] Import code existant (modèles, features)
- [ ] Data pipeline centralisée
- [ ] Train baseline model
- [ ] Implement unit tests (40% coverage)
- [ ] Model validation

**Durée:** 10-14 jours | **Dépendance:** Phase 1

### Phase 3: API (Semaines 4-5)
- [ ] FastAPI setup
- [ ] /predict endpoint
- [ ] /health endpoint
- [ ] Request/Response schemas (Pydantic)
- [ ] API integration tests

**Durée:** 5-7 jours | **Dépendance:** Phase 2

### Phase 4: Deployment (Semaine 6)
- [ ] Dockerfile (backend + frontend)
- [ ] docker-compose.yml
- [ ] GitHub Actions CI/CD
- [ ] Kubernetes manifests (optionnel)

**Durée:** 3-5 jours | **Dépendance:** Phase 3

## 💻 Commandes de Démarrage

```bash
# Development
cd ml-backend
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements.txt

# Run tests
pytest tests/ -v --cov=app

# Run API
uvicorn app.main:app --reload --port 8000

# Dans autre terminal: Frontend
cd ../frontend
streamlit run streamlit_app.py --server.port 8501

# Or avec Docker
docker-compose -f infrastructure/docker-compose.yml up
```

## 🔌 API Endpoints

```
POST   /api/v1/predict           # Prédiction COVID (image ou features)
GET    /api/v1/health            # Health check
GET    /api/v1/model/info        # Infos du modèle
GET    /api/v1/metrics           # Métriques entraînement
GET    /api/v1/metrics/recent    # Prédictions récentes
```

## ✅ Checklist Migration

- [ ] Créer structure `/ml-backend` et `/frontend`
- [ ] Migrer config vers `config.py` unique
- [ ] Créer `app/logging_config.py`
- [ ] Créer `tests/conftest.py` et tests basiques
- [ ] Migrer modèles ML existants
- [ ] Créer `api/` avec endpoints
- [ ] Créer Dockerfile & docker-compose
- [ ] Créer `.github/workflows/tests.yml`
- [ ] Mettre à jour README

## 📚 Ressources Utiles

- **FastAPI:** https://fastapi.tiangolo.com/
- **Pydantic V2:** https://docs.pydantic.dev/
- **Docker Compose:** https://docs.docker.com/compose/
- **Pytest:** https://docs.pytest.org/
- **Streamlit:** https://docs.streamlit.io/

---

**Cette architecture est:**
- ✅ Production-ready
- ✅ Scalable (microservices)
- ✅ Testable (séparation clearcut)
- ✅ Déployable (Docker + K8s ready)
- ✅ Maintenable (structure claire)
