# Telegram Activity Tracker Bot

A lightweight Telegram bot for tracking daily physical activity.

Users send a signed or unsigned integer such as `20`, `+20`, or `-20`, then choose the activity from inline buttons. The bot stores the entry and reports stats for the current user only.

## Features

- Track multiple activity types:
  - steps
  - squats
  - push-ups
  - plank
  - abs
- Positive and negative adjustments
- Daily, weekly, and monthly stats
- Per-user data isolation
- Russian and English UI
- Persistent language switching with `/en` and `/ru`
- Safe full cleanup flow with `/clean`
- Inline query support for sharing personal stats
- Group tournaments with leaderboard

## Private chat commands

- `/start` - show instructions
- `/help` - show help
- `/stat` - show all periods
- `/day` - show today only
- `/week` - show current week only
- `/month` - show current month only
- `/en` - switch language to English
- `/ru` - switch language to Russian
- `/clean` - clear all stats after confirmation

## Group tournament commands

Add the bot to a group and assign it as admin, then use these commands:

| Command | Description |
|---|---|
| `/run <days>` | Start a tournament lasting `<days>` days. The sender is automatically added as participant #1. Only one tournament can run at a time. |
| `/join` | Join the active tournament as a participant. Up to 10 participants per tournament. |
| `/results` | Show the current leaderboard (or final results of the last tournament). |
| `/finish` | End the active tournament immediately and show the final leaderboard. |

### Tournament rules

- A tournament is started with `/run <days>` (e.g. `/run 7` for a 7-day tournament).
- Participants join explicitly with `/join`. New users cannot join after `/run` returns an error if there is already an active tournament.
- Score is a **normalized activity rating** so different activity types can be compared fairly.
- The leaderboard ranks participants by normalized score, highest first.
- A tournament ends either when its duration expires or when `/finish` is called.
- After a tournament ends, a new one can be started with `/run`.

### Score model

- `1,000` steps = `10` points
- `20` squats = `10` points
- `10` push-ups = `10` points
- `2` plank minutes = `10` points
- `20` abs reps = `10` points

Period headers show this score directly, for example `Today (🏅100)`.

### Example flow

```text
# Alice starts a 7-day tournament
Alice: /run 7
Bot:   Tournament started!
       Period: May 14, 2026 — May 20, 2026 (7 days)

# Bob and Carol join
Bob:   /join
Bot:   You're in! Participant #2.
Carol: /join
Bot:   You're in! Participant #3.

# Anyone can check standings at any time
Dave:  /results
Bot:   Tournament: May 14 — May 20, 2026
       Status: Active
       -----
       🥇 @alice: 1 200
       🥈 @bob: 800
       🥉 Carol: 350

# Alice ends the tournament early
Alice: /finish
Bot:   Tournament finished!
       Period: May 14 — May 20, 2026
       -----
       🥇 @alice: 1 200
       🥈 @bob: 800
       🥉 Carol: 350
```

## Inline Queries

The bot supports Telegram inline mode.

Example:

```text
@your_bot_username
@your_bot_username day
@your_bot_username week
@your_bot_username month
@your_bot_username stat
```

Supported keywords:

- `day` / `today` / `сегодня`
- `week` / `неделя`
- `month` / `месяц`
- `stat` / `stats` / `стат` / `статистика`

With an empty inline query, the bot returns four choices:

- all stats
- day
- week
- month

Inline results are personal and generated from the current user’s own data.

## Input Rules

Allowed input:

```text
1
-1
1
+20
-20
20
+1000000
-1000000
1000000
```

Invalid input:

```text
0
+0
-0
abc
++ 
--
+1000001
-1000001
1000001
```

Formal rule:

```text
-1_000_000 <= value <= 1_000_000
value != 0
unsigned values are treated as positive
```

Daily totals are clamped by business rules:

- minimum: `0`
- maximum: `1_000_000`

## Activity Model

| Activity | Key | Unit |
|---|---|---|
| Steps | `steps` | count |
| Squats | `squats` | count |
| Push-ups | `pushups` | count |
| Plank | `plank` | minutes |
| Abs | `abs` | count |

## How It Works

Example positive flow:

```text
User: +20
Bot: Where to add 20?
[Steps] [Squats]
[Push-ups] [Plank]
[Abs]
[Cancel]
```

Example correction flow:

```text
User: -20
Bot: Where to subtract 20?
[Steps] [Squats]
[Push-ups] [Plank]
[Abs]
[Cancel]
```

After the activity is chosen, the bot stores the entry and returns the updated daily total for that activity.

## Storage

The MVP uses SQLite.

- `users` — one row per Telegram user
- `activity_entries` — individual log entries per user
- `group_chats` — groups where the bot has been used
- `tournaments` — one row per tournament; `finished_at` is set when `/finish` is called or when a new tournament is queried after the previous one has expired
- `tournament_participants` — users who joined a specific tournament via `/join` or `/run`
- persistent user language preference
- per-user stats queries for day, week, and month

## Configuration

Configuration is loaded from environment variables.

Required:

```env
BOT_TOKEN=telegram_bot_token_here
```

Optional:

```env
DATABASE_URL=sqlite:///data/activity_bot.db
HTTP_PROXY_URL=http://127.0.0.1:8118
```

`HTTP_PROXY_URL` supports `http://`, `https://`, `socks5://`, and `socks5h://` URLs. It is a regular network proxy setting, not a Telegram MTProto proxy.

See [.env.example](.env.example) for a template.

## Local Development

**Prerequisites:** Python 3.12+, `make`

```bash
git clone https://github.com/nghtf/sport4me
cd sport4me

cp .env.example .env
# Edit .env and set BOT_TOKEN

make install   # create venv and install dependencies
make test      # run the test suite
make run       # start the bot locally
```

Available targets:

- `make venv`          — create local Python virtual environment or fallback deps dir
- `make install`       — install dependencies
- `make test`          — run pytest
- `make run`           — run bot locally
- `make check-proxy`   — check configured proxy and CONNECT support
- `make check-telegram`— check Telegram API access with current env/proxy
- `make docker-build`  — build Docker image
- `make docker-run`    — run Docker container using `.env`
- `make docker-stop`   — stop and remove Docker container
- `make docker-logs`   — follow Docker container logs
- `make compose-up`    — build and start with docker compose
- `make compose-down`  — stop and remove docker compose services
- `make compose-logs`  — follow docker compose logs
- `make update`        — pull latest code from GitHub and restart container
- `make clean`         — remove local caches
- `make flush`         — delete the local SQLite database

`make flush` deletes the local SQLite database (`data/activity_bot.db` by default). Override the path with `DB_PATH`:

```bash
make flush
make flush DB_PATH=/custom/path/bot.db
```

## Proxy Notes

If your environment cannot reach `api.telegram.org` directly, set `HTTP_PROXY_URL`.

Examples:

```env
HTTP_PROXY_URL=http://127.0.0.1:8118
HTTP_PROXY_URL=socks5://host.docker.internal:1081
```

Useful checks:

```bash
make check-proxy
make check-telegram
```

`make check-proxy` verifies raw HTTP CONNECT/TLS reachability and is mainly useful for HTTP(S) proxies.
`make check-telegram` verifies Bot API access with the current environment.

## Project Structure

```text
bot/
  config.py
  constants.py
  handlers/
  main.py
  models.py
  repository.py
  services.py
  session.py
  ui.py
  validators.py
tests/
```

Main responsibilities:

- `repository.py` handles SQLite operations
- `services.py` contains business logic
- `ui.py` contains localization, text formatting, and keyboards
- `handlers/` contains aiogram handlers
- `main.py` starts the bot

## Testing

The test suite covers:

- input parsing
- daily limit validation
- day/week/month stats
- user isolation
- language preference persistence
- full cleanup behavior
- tournament lifecycle: start, join, finish, expiry
- leaderboard scoring and participant isolation

Run:

```bash
make test
```

## Deployment

### VPS (docker compose — recommended)

**Prerequisites:** Docker with the Compose plugin, `git`, `make`

```bash
git clone https://github.com/nghtf/sport4me
cd sport4me

cp .env.example .env
# Edit .env — set BOT_TOKEN (required) and HTTP_PROXY_URL (optional)

make compose-up    # build image and start container in background
make compose-logs  # follow logs
make compose-down  # stop
```

The compose file mounts a named volume (`bot-data`) for the SQLite database so data survives container restarts and image rebuilds.

To deploy an update:

```bash
make update   # git pull + docker compose up --build -d
```

### Manual Docker

```bash
make docker-build
make docker-run   # uses .env and mounts ./data as a bind volume
make docker-logs
make docker-stop
```

### Guidelines

- keep secrets out of the image
- use env vars or an env file for configuration
- store SQLite in a persistent volume
- do not copy local caches, `.env`, or runtime artifacts into the image
