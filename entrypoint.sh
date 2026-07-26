#!/bin/sh
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
cd /app/src/web/.next/standalone && PORT=3000 node server.js
