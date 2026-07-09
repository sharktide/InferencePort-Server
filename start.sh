#!/bin/bash
set -e

echo "[BOOT] Starting container initialization..."
echo "[BOOT] Current directory: $(pwd)"

cd /app
echo "[INIT] Switched to /app"

echo "[CLEAN] Removing everything in /app except /app/tools ..."
find /app -mindepth 1 -maxdepth 1 \
  ! -name tools \
  ! -name shield \
  ! -name shield-intel \
  -exec rm -rf {} \;
echo "[CLEAN] Cleanup complete."

echo "[CLONE] Cloning private repo into /tmp/repo ..."
git clone https://$GH_PAT@github.com/sharktide/inferenceport-lightning.git /tmp/repo
echo "[CLONE] Clone complete."

echo "[COPY] Moving repo contents into /app ..."
cp -r /tmp/repo/* /app/
echo "[COPY] Copy complete."

echo "[CLEANUP] Removing temporary clone directory..."
rm -rf /tmp/repo
echo "[CLEANUP] Temp directory removed."

echo "[DEPS] Installing Python dependencies..."
pip install --no-cache-dir -r /app/requirements.txt
echo "[DEPS] Dependencies installed."

echo "[START] Launching FastAPI with Uvicorn..."
exec uvicorn app:app --host 0.0.0.0 --port 7860
