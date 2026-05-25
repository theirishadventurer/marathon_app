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
- Garmin tokens persist to `./data/garmin_tokens/<athlete_id>/tokens.json`. On Railway, mount a 1 GB volume at `/app/data` or tokens vanish on every redeploy and Garmin sync silently rebreaks.
- iOS personal PWA distribution avoids the Apple Developer Program ($99/yr) and 7-day re-sign treadmill. Expo web build to Vercel + Safari "Add to Home Screen" gets fullscreen + custom splash + your icon. Smoke-test bottom-sheets (`@gorhom/bottom-sheet`), drag gestures (`react-native-gesture-handler`), and fonts (`expo-font` → CSS `@font-face` on web).
- Anything prefixed `EXPO_PUBLIC_` is INLINED into the JS bundle and visible to any client — never put secrets there. API base URL is fine; tokens are not.
- Full personal-deployment runbook lives at `docs/superpowers/specs/2026-05-24-personal-deployment-runbook.md`.

**Mobile (Expo SDK 54 + RN 0.81 + TS strict + NativeWind v4):**
- React 19 + TS 5.9: do NOT annotate `: JSX.Element` on component returns; let TypeScript infer.
- `expo-secure-store` throws on web — wrap with `Platform.OS === 'web'` fallback to `localStorage`.
- `react-native-reanimated` has no Expo config plugin — DON'T add it to `app.json` plugins. The babel plugin is enough.
- `react-native@0.81` `Easing` lacks `.steps()` — use `Easing.steps` from `react-native-reanimated` instead.
- Validation gate per task: `cd mobile && npx tsc --noEmit`. No jest infra in this project yet.
- "Append to file" patterns from plans can violate ruff E402 — always hoist imports to the top.

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
