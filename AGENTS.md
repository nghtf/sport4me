# AGENTS.md

Working instructions for Codex and other coding agents in the `activity` project.

## Project Context

Project: Telegram Activity Tracker Bot.

The product goal is defined in `README.md`. If this file and `README.md` disagree, treat `README.md` as the source of truth.

The bot helps Telegram users track daily physical activity:

- steps
- squats
- push-ups
- plank
- abs

Users send a number such as `20`, `+20`, or `-20`, then choose an activity from buttons. A number without a sign is treated as positive.

## Language And Style

- User-facing bot messages support Russian and English.
- Code, filenames, modules, functions, and variables should remain in English.
- Keep comments rare and only add them when they explain non-obvious logic.
- Keep v1.0 simple. Do not add admin panels, dashboards, charts, goals, or analytics unless explicitly requested.

## Preferred Stack

Unless the stack is intentionally changed, prefer:

- Python
- `aiogram`
- SQLite for v1.0 storage
- `pytest` for tests
- `.env` / environment variables for configuration
- `make` for local workflows
- Docker for deployment

Do not add heavy dependencies without a clear need.
Keep runtime dependencies in `requirements.txt` and dev/test dependencies in `requirements-dev.txt`.

## Makefile

The project uses `make` as the main local interface.

- When adding recurring workflows, consider a new `Makefile` target first.
- Documentation should prefer `make <target>` over long raw shell commands when possible.
- Targets should be understandable and reasonably idempotent.
- Secrets must not be required from the repository itself.
- The default `VENV` may live outside the repository (`/tmp/activity-venv`) for faster local startup.
- The `.deps` folder is a local development artifact and should not be committed or copied into Docker images.
- Production and Docker targets must read secrets from env vars or a local env file only.
- If the application entrypoint changes, keep `APP_MODULE` and related `Makefile` targets in sync.
- Use `make check-proxy` to test the configured HTTP proxy and `make check-telegram` to test Bot API access through the current environment.

## Public GitHub And Secrets

This project is expected to be published as open source.

- Never commit real Telegram bot tokens, `.env`, SQLite databases, dumps, logs, or other runtime artifacts.
- Sensitive settings must come from environment variables.
- Use `.env.example` with placeholder values only.
- Update `.gitignore` before adding files that might contain secrets or local runtime state.
- Do not store user data in the repository.

## Docker And Production

- Configure the container with env vars only, without hardcoded secrets.
- If direct access to `api.telegram.org` is blocked, use `HTTP_PROXY_URL` as a regular proxy URL. Supported schemes are `http`, `https`, `socks5`, and `socks5h`.
- Store SQLite in a volume or other persistent storage, not inside the ephemeral container layer.
- Docker images should contain only runtime dependencies.
- Do not copy `.env`, local databases, caches, or test artifacts into the image.
- If a `Dockerfile` is added, keep a matching `.dockerignore`.
- If Docker runtime, entrypoint, or SQLite path changes, sync `Dockerfile`, `Makefile`, `.env.example`, and `README.md`.

## Core Domain Rules

- Allowed input: an integer in the form `N`, `+N`, or `-N`
- A number without a sign is positive
- `0`, `+0`, and `-0` are invalid
- A daily activity total must never go below `0`
- A daily activity total must never go above `1_000_000`
- Data for different Telegram users must stay isolated
- Stats are always calculated for the current user only
- Server timezone is acceptable for v1.0

## Expected Behavior

- `/start` creates the user if needed and shows instructions
- `/help` shows short usage help
- `/stat` shows stats for today, current week, and current month
- `/day`, `/week`, and `/month` show a single period
- `/en` and `/ru` persist the user language choice
- `/clean` asks for confirmation and clears the user’s stats on confirm
- inline queries return shareable stats snippets for the current user; each result includes a "Get your result" CTA button
- After `+N` or `-N`, the bot stores a pending value and shows activity buttons plus cancel
- After activity selection, the bot validates limits, stores the entry, and shows the current daily total
- Cancel clears pending state without writing a record
- In groups: `/top_day`, `/top_week`, `/top_month` show top-10 for the current period; `/top_last_day`, `/top_last_week`, `/top_last_month` show top-10 for the previous period
- Calling any `/top_*` command auto-registers the user as a member of that group
- Group leaderboards include a "Get your result" inline button so users can share their own stats immediately
- Group members are stored in `group_members`; activity data is shared with the private-chat tracking (same `activity_entries` table)

## Recommended Structure

The current structure is intentionally small:

- `config.py` - settings loading and env handling
- `session.py` - Telegram session creation
- `repository.py` - SQLite access
- `services.py` - business logic
- `ui.py` - localization, text rendering, and keyboards
- `handlers/` - aiogram handlers
- `main.py` - bot startup

Do not reintroduce unnecessary abstraction layers unless they clearly improve maintainability.

## Testing

Minimum test coverage for v1.0:

- valid `+N` and `-N` parsing
- unsigned input treated as positive
- zero is rejected
- daily totals cannot drop below `0`
- daily totals cannot exceed `1_000_000`
- correct day/week/month stats
- user data isolation
- language preference persistence
- stats cleanup behavior
- group member auto-registration
- group leaderboard ranking and score calculation
- previous-period range helpers (last day, last week, last month)
- group isolation across multiple chats

Run available tests before finishing substantial changes. If existing tests do not cover changed business logic, add focused tests.

## Working With Changes

- Read `README.md` and the existing code before editing.
- Preserve the behavior described in `README.md` unless the user explicitly asks to change it.
- Avoid unrelated refactors.
- Never commit secrets or real local env values.
- Keep runtime files out of Git.
- If you add or change a recurring workflow, update the `Makefile`.

## Definition Of Done

A change is done when:

- behavior matches `README.md`
- user data stays isolated
- edge cases are handled
- relevant business logic has tests
- available tests pass
- setup and configuration are understandable from the docs
