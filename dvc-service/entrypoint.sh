#!/bin/sh
# Surcharge l'endpoint DVC dans le config GLOBAL du container (pas le volume monté)
# Ainsi le .dvc/config.local de l'hôte (localhost:9000) reste intact
if [ -n "$DVC_REMOTE_MINIO_ENDPOINTURL" ]; then
    dvc remote modify --global minio endpointurl "$DVC_REMOTE_MINIO_ENDPOINTURL" 2>/dev/null || true
fi

exec "$@"
