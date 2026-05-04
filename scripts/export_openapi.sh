#!/bin/bash
# Export FastAPI OpenAPI spec for the mobile app
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
echo "Exporting OpenAPI spec..."
docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T api python -c "
import json
from app.main import app
spec = app.openapi()
print(json.dumps(spec, indent=2, default=str))
" > "$PROJECT_DIR/mobile/openapi.json"
echo "Exported to mobile/openapi.json"
