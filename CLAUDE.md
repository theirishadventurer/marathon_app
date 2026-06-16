# Ruflo — Claude Code Configuration

## Rules

- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary — prefer editing existing files
- NEVER create documentation files unless explicitly requested
- NEVER save working files or tests to root — use `/src`, `/tests`, `/docs`, `/config`, `/scripts`
- ALWAYS read a file before editing it
- NEVER commit secrets, credentials, or .env files
- Keep files under 500 lines
- Validate input at system boundaries

## Stack-Specific Gotchas (learned the hard way)

**Backend (FastAPI + Pydantic V2 + SQLAlchemy async + Alembic):**
- Use `Field(validation_alias=X)` (not `Field(alias=X)`) when the ORM column name differs from the desired JSON output key — `alias=` flips the OUTPUT to the alias when FastAPI's `response_model` serializes.
- Native enum columns + shared sessions in tests: a raw string set via fixture comes back as a raw string (not coerced) when the route reads from the same session. Use `WorkoutStatus.done` not `"done"` in test fixtures.
- Alembic autogenerate against a drifted dev DB will try to recreate every table. If `alembic_version` is at head but tables are missing, run `alembic stamp base && alembic upgrade head` before autogenerating.
- `docker compose down` wipes the Postgres named volume on Windows/WSL — re-run `alembic upgrade head` + `python -m app.seed.load_plan` after every restart.
- Tests run in container: `docker compose exec -T api pytest` (not host pytest — deps live in the container).
- Seed is idempotent by `(cycle_id, week_number, day)` upsert but does NOT delete weeks no longer in PLAN.md. When a phase shrinks (e.g., 28 → 22 weeks), old trailing-week rows persist as ghosts. Always `docker compose down -v` then fresh `alembic upgrade head` + `python -m app.seed.load_plan` after structural plan changes.

**Plan / seed format:**
- `app/seed/plan_parser.py` is intentionally format-agnostic for the weekly grid — any new weekly template (different day-of-week assignments, different number of workouts) works without parser changes as long as the `WEEK N` header + pipe-row `Day | type | dist | dur | description | intent` format is preserved. Push philosophy changes into PLAN.md and the `CYCLES[]` dict, not into the parser.
- `app/config.py` `seed_password` field was declared but never wired through to `app/seed/load_plan.py:24` where `DEFAULT_PASSWORD = "changeme123"` was hardcoded. Caught during deploy prep — wire via `DEFAULT_PASSWORD = os.environ.get("SEED_PASSWORD", "changeme123")` before deploying or the login password is the hardcoded default.

**Deployment (Railway + Vercel + iOS PWA):**
- Railway's Postgres plugin injects `DATABASE_URL` in `postgresql://...` form, but SQLAlchemy async needs `postgresql+asyncpg://...`. Lightweight `Settings.__init__` rewrite of the scheme works for both local Docker and Railway with no orchestration around the env var.
- **Railway's startCommand parser handles `&&` chaining but does NOT shell-expand `${VAR:-default}` POSIX syntax cleanly.** Wrap commands needing shell semantics in explicit `sh -c '...'`. Discovered the hard way after three sequential fixes (`--port 8000` → `${PORT:-8000}` → `$PORT` → `sh -c '$PORT'`). The `$PORT` env var IS required — Railway routes the public healthcheck to a dynamic port per container.
- **Add diagnostic instrumentation BEFORE the next candidate fix** when Railway is opaque about why a container failed healthcheck. `echo "BOOT: PORT=$PORT"` + a FastAPI lifespan logger line ("BOOT: lifespan startup begin") will tell you in one deploy whether shell expansion is working AND whether uvicorn even imported the app. Saves multi-cycle guessing.
- **Default Railway healthcheck timeout (30s) is too short** for cold-start migrations + uvicorn boot on managed Postgres. Bump `healthcheckTimeout` to 300 in `railway.json`.
- **Branch matters.** Railway auto-deploys whatever branch you configure. If feature work lives on a long-running branch (e.g., `session-2/backend-move-endpoints`) and you deploy from `master`, Railway sees the stale master and reports cryptic Railpack errors like "could not determine how to build the app." Merge to master (or change Railway's tracked branch) before deploying.
- **Idempotent seed in startCommand** = self-healing deploys. `seed_plan` upserts by `(athlete_email, plan_name)` so chaining `python -m app.seed.load_plan` after `alembic upgrade head` is safe on every boot. Avoids needing to find Railway's web shell for the one-off seed step.
- Garmin tokens persist to `./data/garmin_tokens/<athlete_id>/tokens.json`. On Railway, mount a 1 GB volume at `/app/data` or tokens vanish on every redeploy and Garmin sync silently rebreaks.
- **Garmin's WAF rate-limits datacenter IPs (HTTP 429).** `garminconnect.Garmin.login()` silently returns without setting `.garth` on 429 (instead of raising), causing downstream `AttributeError`. Wrap the call in try/except + post-login `hasattr(client, 'garth')` check, raise a custom `GarminLoginFailed` exception, convert to 502 in the route. Long-term fix: Strava OAuth integration (backlog).
- **5xx without CORS headers → browser reports "blocked by CORS"** even when CORS middleware is configured correctly. FastAPI's default exception handler returns 500s that skip CORS. When debugging "CORS issues," always get the actual HTTP status code + body before blaming the middleware. Defensive route-level try/except that converts to `HTTPException(4xx)` keeps responses CORS-compliant.
- iOS personal PWA distribution avoids the Apple Developer Program ($99/yr) and 7-day re-sign treadmill. Expo web build to Vercel + Safari "Add to Home Screen" gets fullscreen + custom splash + your icon. Smoke-test bottom-sheets (`@gorhom/bottom-sheet`), drag gestures (`react-native-gesture-handler`), and fonts (`expo-font` → CSS `@font-face` on web).
- **`EXPO_PUBLIC_*` env vars are compile-time inlined into the JS bundle** — visible to any client (never put secrets), AND require a full Vercel rebuild after change (Vercel does not auto-rebuild on env var change). For URL values, ALWAYS include `https://` — axios treats bare hostnames as relative paths, producing nonsense like `https://your-vercel.app/your-railway.app/auth/login` → 404.
- **`react-native-gesture-handler` on touch-web has caveats:** parent ScrollView claims upward touches before the Pan gesture activates (causing "can only drag down, not up"), and Pressable's `onPress` still fires after long-press gesture completes (causing "drop opens the workout detail"). Fix: toggle ScrollView's `scrollEnabled` during drag, track an `isDraggingRef` with 150ms post-drag suppression for press handlers. Add `onFinalize` cleanup for cancelled gestures.
- Full personal-deployment runbook lives at `docs/superpowers/specs/2026-05-24-personal-deployment-runbook.md`.

**Mobile (Expo SDK 54 + RN 0.81 + TS strict + NativeWind v4):**
- React 19 + TS 5.9: do NOT annotate `: JSX.Element` on component returns; let TypeScript infer.
- `expo-secure-store` throws on web — wrap with `Platform.OS === 'web'` fallback to `localStorage`.
- `react-native-reanimated` has no Expo config plugin — DON'T add it to `app.json` plugins. The babel plugin is enough.
- `react-native@0.81` `Easing` lacks `.steps()` — use `Easing.steps` from `react-native-reanimated` instead.
- Validation gate per task: `cd mobile && npx tsc --noEmit`. No jest infra in this project yet.
- "Append to file" patterns from plans can violate ruff E402 — always hoist imports to the top.

**Coach Chat (Gemini + `google-genai`) — Session 3:**
- **google-genai response shape differs from Anthropic.** Function calls come back on `response.candidates[0].content.parts[].function_call` (`.name`, `.args` dict) and text on `part.text` — NOT Anthropic's `content[].type=="tool_use"`/`.input`. Declare the tool as `types.Tool(function_declarations=[<raw JSON-schema dict>])` inside `types.GenerateContentConfig(system_instruction=..., tools=[...])`. google-genai **coerces a raw dict** — no need to build `FunctionDeclaration`/`Schema` objects. `system_instruction` is config, not a message.
- **Mock the client, not the SDK.** `get_gemini_client()` is separated for test mocking (mirrors `get_anthropic_client`). In tests: `patch.object(coach_chat, "get_gemini_client", return_value=fake)` where `fake.models.generate_content.return_value/side_effect` is set. The real `types.*` config is still constructed (verified to accept the dict), so don't mock `types`.
- **`gemini_api_key` defaults to `""` → `POST /chat` 503-gates.** Any chat route test that expects a 200/502 MUST `monkeypatch.setattr(settings, "gemini_api_key", "test-key")` first, or it short-circuits to 503 before the mocked client is reached.
- **Shared `proposal_apply` service: the "move primary to `new_date`" step is drag-only.** `apply-move`'s old behavior moved the primary (`related_workout_id`) workout to `proposal["new_date"]` for `just_move` AND `option_*`. The extracted service gates that on `new_date` + `related_workout_id` both being present (drag proposals). Chat proposals carry NO `new_date`, so only the chosen option's `edits` apply. When extracting shared logic from a route, diff the *behavior* against existing tests — the option path moved two workouts, not one.
- **§3.2 security: re-validate every edit's `workout_id` ownership before mutating** (`_owned_workout` join on `Plan.athlete_id`). LLM-emitted IDs are untrusted; the server is the authority even though the user also approves via `ProposalSheet`. There's a dedicated `test_apply_rejects_foreign_workout_id`.
- **`GEMINI_API_KEY` is backend-only** (never `EXPO_PUBLIC_*`). Gemini failure → `HTTPException(502)`, missing key → 503 — both keep CORS headers (route-level try/except, per the 5xx-CORS gotcha).

**Security — fail-closed config (Session 3):**
- `app/config.py` enforces non-default `SECRET_KEY` (≥32 chars) and `app/seed/load_plan.py` enforces a non-default `SEED_PASSWORD` — **only when `APP_ENV=production`**. Local dev + the pytest suite (default `APP_ENV=development`) keep using in-repo defaults. Railway MUST set `APP_ENV=production` + `SECRET_KEY` + `SEED_PASSWORD` or the deploy fails closed (intended). The idempotent seed does NOT rotate an existing athlete's password — use `python -m app.scripts.reset_password` for the live row.

**Workflow:**
- Spec → plan → subagent-driven implementation. Specs in `docs/superpowers/specs/`, plans in `docs/superpowers/plans/`.
- Per-branch session logs auto-written to `docs/session-logs/` by `.claude/helpers/session-log.mjs` on SessionEnd.
- Notion sync is Claude-side via `/update-notion` skill — run at session close-out, not from a hook.

## Agent Comms (SendMessage-First Coordination)

Named agents coordinate via `SendMessage`, not polling or shared state.

```
Lead (you) ←→ architect ←→ developer ←→ tester ←→ reviewer
              (named agents message each other directly)
```

### Spawning a Coordinated Team

```javascript
// ALL agents in ONE message, each knows WHO to message next
Agent({ prompt: "Research the codebase. SendMessage findings to 'architect'.",
  subagent_type: "researcher", name: "researcher", run_in_background: true })
Agent({ prompt: "Wait for 'researcher'. Design solution. SendMessage to 'coder'.",
  subagent_type: "system-architect", name: "architect", run_in_background: true })
Agent({ prompt: "Wait for 'architect'. Implement it. SendMessage to 'tester'.",
  subagent_type: "coder", name: "coder", run_in_background: true })
Agent({ prompt: "Wait for 'coder'. Write tests. SendMessage results to 'reviewer'.",
  subagent_type: "tester", name: "tester", run_in_background: true })
Agent({ prompt: "Wait for 'tester'. Review code quality and security.",
  subagent_type: "reviewer", name: "reviewer", run_in_background: true })

// Kick off the pipeline
SendMessage({ to: "researcher", summary: "Start", message: "[task context]" })
```

### Patterns

| Pattern | Flow | Use When |
|---------|------|----------|
| **Pipeline** | A → B → C → D | Sequential dependencies (feature dev) |
| **Fan-out** | Lead → A, B, C → Lead | Independent parallel work (research) |
| **Supervisor** | Lead ↔ workers | Ongoing coordination (complex refactor) |

### Rules

- ALWAYS name agents — `name: "role"` makes them addressable
- ALWAYS include comms instructions in prompts — who to message, what to send
- Spawn ALL agents in ONE message with `run_in_background: true`
- After spawning: STOP, tell user what's running, wait for results
- NEVER poll status — agents message back or complete automatically

## Swarm & Routing

### Config
- **Topology**: hierarchical-mesh (anti-drift)
- **Max Agents**: 15
- **Memory**: hybrid
- **HNSW**: Enabled
- **Neural**: Enabled

```bash
npx @claude-flow/cli@latest swarm init --topology hierarchical --max-agents 8 --strategy specialized
```

### Agent Routing

| Task | Agents | Topology |
|------|--------|----------|
| Bug Fix | researcher, coder, tester | hierarchical |
| Feature | architect, coder, tester, reviewer | hierarchical |
| Refactor | architect, coder, reviewer | hierarchical |
| Performance | perf-engineer, coder | hierarchical |
| Security | security-architect, auditor | hierarchical |

### When to Swarm
- **YES**: 3+ files, new features, cross-module refactoring, API changes, security, performance
- **NO**: single file edits, 1-2 line fixes, docs updates, config changes, questions

### 3-Tier Model Routing

| Tier | Handler | Use Cases |
|------|---------|-----------|
| 1 | Agent Booster (WASM) | Simple transforms — skip LLM, use Edit directly |
| 2 | Haiku | Simple tasks, low complexity |
| 3 | Sonnet/Opus | Architecture, security, complex reasoning |

## Memory & Learning

### Before Any Task
```bash
npx @claude-flow/cli@latest memory search --query "[task keywords]" --namespace patterns
npx @claude-flow/cli@latest hooks route --task "[task description]"
```

### After Success
```bash
npx @claude-flow/cli@latest memory store --namespace patterns --key "[name]" --value "[what worked]"
npx @claude-flow/cli@latest hooks post-task --task-id "[id]" --success true --store-results true
```

### MCP Tools (use `ToolSearch("keyword")` to discover)

| Category | Key Tools |
|----------|-----------|
| **Memory** | `memory_store`, `memory_search`, `memory_search_unified` |
| **Bridge** | `memory_import_claude`, `memory_bridge_status` |
| **Swarm** | `swarm_init`, `swarm_status`, `swarm_health` |
| **Agents** | `agent_spawn`, `agent_list`, `agent_status` |
| **Hooks** | `hooks_route`, `hooks_post-task`, `hooks_worker-dispatch` |
| **Security** | `aidefence_scan`, `aidefence_is_safe`, `aidefence_has_pii` |
| **Hive-Mind** | `hive-mind_init`, `hive-mind_consensus`, `hive-mind_spawn` |

### Background Workers

| Worker | When |
|--------|------|
| `audit` | After security changes |
| `optimize` | After performance work |
| `testgaps` | After adding features |
| `map` | Every 5+ file changes |
| `document` | After API changes |

```bash
npx @claude-flow/cli@latest hooks worker dispatch --trigger audit
```

## Agents

**Core**: `coder`, `reviewer`, `tester`, `planner`, `researcher`
**Architecture**: `system-architect`, `backend-dev`, `mobile-dev`
**Security**: `security-architect`, `security-auditor`
**Performance**: `performance-engineer`, `perf-analyzer`
**Coordination**: `hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`
**GitHub**: `pr-manager`, `code-review-swarm`, `issue-tracker`, `release-manager`

Any string works as a custom agent type.

## Build & Test

- ALWAYS run tests after code changes
- ALWAYS verify build succeeds before committing

```bash
npm run build && npm test
```

## CLI Quick Reference

```bash
npx @claude-flow/cli@latest init --wizard           # Setup
npx @claude-flow/cli@latest swarm init --v3-mode     # Start swarm
npx @claude-flow/cli@latest memory search --query "" # Vector search
npx @claude-flow/cli@latest hooks route --task ""    # Route to agent
npx @claude-flow/cli@latest doctor --fix             # Diagnostics
npx @claude-flow/cli@latest security scan            # Security scan
npx @claude-flow/cli@latest performance benchmark    # Benchmarks
```

26 commands, 140+ subcommands. Use `--help` on any command for details.

## Setup

```bash
claude mcp add claude-flow -- npx -y @claude-flow/cli@latest
npx @claude-flow/cli@latest daemon start
npx @claude-flow/cli@latest doctor --fix
```

**Agent tool** handles execution (agents, files, code, git). **MCP tools** handle coordination (swarm, memory, hooks). **CLI** is the same via Bash.
