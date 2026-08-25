#!/bin/bash
set -e

# Docker Desktop (WSL2 backend) ne mappe pas toujours la vraie lib driver NVIDIA à
# l'emplacement standard /usr/lib/wsl/lib — elle atterrit sous un dossier de paquet
# driver versionné (/usr/lib/wsl/drivers/<hash>.inf_amd64_.../), en laissant un stub
# non fonctionnel à /usr/lib/x86_64-linux-gnu/libcuda.so.1 (cuInit échoue avec
# CUDA_ERROR_NOT_FOUND: named symbol not found). On symlink manuellement vers le
# vrai driver quand ce dossier existe ; sur Linux natif avec nvidia-container-toolkit
# (pas de /usr/lib/wsl), ce bloc est un no-op et n'affecte rien.
DRV=$(find /usr/lib/wsl/drivers -maxdepth 1 -name '*.inf_amd64_*' 2>/dev/null | head -1)
if [ -n "$DRV" ] && [ -f "$DRV/libcuda.so.1.1" ]; then
    mkdir -p /usr/lib/wsl/lib
    ln -sf "$DRV/libcuda.so.1.1" /usr/lib/wsl/lib/libcuda.so.1
    [ -f "$DRV/libnvidia-ml.so.1" ] && ln -sf "$DRV/libnvidia-ml.so.1" /usr/lib/wsl/lib/libnvidia-ml.so.1
    [ -f "$DRV/libnvidia-ptxjitcompiler.so.1" ] && ln -sf "$DRV/libnvidia-ptxjitcompiler.so.1" /usr/lib/wsl/lib/libnvidia-ptxjitcompiler.so.1
    [ -f "$DRV/libnvdxgdmal.so.1" ] && ln -sf "$DRV/libnvdxgdmal.so.1" /usr/lib/wsl/lib/libnvdxgdmal.so.1
    export LD_LIBRARY_PATH="/usr/lib/wsl/lib:${LD_LIBRARY_PATH}"
fi

exec "$@"
