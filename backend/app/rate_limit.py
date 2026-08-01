"""Rate limiting — protège /predict des abus (Phase 3)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(key_func=get_remote_address)
predict_rate_limit = f"{settings.rate_limit_per_minute}/minute"
