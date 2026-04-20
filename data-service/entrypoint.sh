#!/bin/sh
# Surcharge l'endpoint DVC si DVC_REMOTE_MINIO_ENDPOINTURL est défini (réseau Docker)
if [ -n "$DVC_REMOTE_MINIO_ENDPOINTURL" ]; then
    dvc remote modify --local minio endpointurl "$DVC_REMOTE_MINIO_ENDPOINTURL" 2>/dev/null || true
fi

exec "$@"
