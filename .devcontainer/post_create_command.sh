#!/bin/bash

npm add -g pnpm@10.11.1
cd web && pnpm install
pipx install uv

echo 'alias start-api="cd /workspaces/xpath-dify/api && poetry run python -m flask run --host 0.0.0.0 --port=5001 --debug"' >> ~/.bashrc
echo 'alias start-worker="cd /workspaces/xpath-dify/api && poetry run python -m celery -A app.celery worker -P gevent -c 1 --loglevel INFO -Q dataset,generation,mail,ops_trace,app_deletion"' >> ~/.bashrc
echo 'alias start-web="cd /workspaces/xpath-dify/web && pnpm dev"' >> ~/.bashrc
echo 'alias start-containers="cd /workspaces/xpath-dify/docker && docker-compose -f docker-compose.middleware.yaml -p dify --env-file middleware.env up -d"' >> ~/.bashrc
echo 'alias stop-containers="cd /workspaces/xpath-dify/docker && docker-compose -f docker-compose.middleware.yaml -p dify --env-file middleware.env down"' >> ~/.bashrc

source /home/vscode/.bashrc
