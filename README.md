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
- Group leaderboards: top-10 rankings per period among group members

## Private chat commands

- `/start` - show instructions
- `/help` - show help
- `/stat` - show all periods
- `/today` - show today only
- `/yesterday` - show yesterday only
- `/week` - show current week only
- `/month` - show current month only
- `/details` - pick a period via buttons and get daily scores
- `/score` - daily scores for the current week
- `/score last week` - daily scores for the previous week
- `/score month` - daily scores for the current month
- `/score last month` - daily scores for the previous month
- `/en` - switch language to English
- `/ru` - switch language to Russian
- `/clean` - clear all stats after confirmation

## Group commands

Add the bot to a group. Any user who issues a group command is automatically registered as a group member and included in future leaderboards.

| Command | Description |
|---|---|
| `/top` | Top 10 for today |
| `/top week` | Top 10 for the current week (Mon–Sun) |
| `/top month` | Top 10 for the current calendar month |
| `/top last day` | Top 10 for yesterday |
| `/top last week` | Top 10 for the previous week |
| `/top last month` | Top 10 for the previous calendar month |

### How group rankings work

- A user is added to the group's member list the first time they issue any `/top_*` command.
- Rankings are based on normalized activity score across all tracked activity types.
- Only group members are ranked; activity logged before joining does count once the user is a member.
- The leaderboard shows at most 10 entries, ordered by score descending.
- Each leaderboard message includes a **"Get your result"** button that opens the inline stat menu, letting any user instantly share their own stats in the chat.

### Score model

- `1,000` steps = `10` points
- `20` squats = `10` points
- `10` push-ups = `10` points
- `2` plank minutes = `10` points
- `20` abs reps = `10` points

Period headers show this score directly, for example `Today (🏅100)`.

### Example flow

```text
# Alice checks today's group ranking
Alice: /top
Bot:   Top 10 · Today
       -----
       🥇 @alice: 120
       🥈 @bob: 80

# Bob checks last week's ranking
Bob:   /top last week
Bot:   Top 10 · Last Week
       -----
       🥇 @carol: 350
       🥈 @alice: 280
       🥉 @bob: 100
       [Get your result]
```

## Inline Queries

The bot supports Telegram inline mode.

Example:

```text
@your_bot_username
@your_bot_username yesterday
@your_bot_username today
@your_bot_username week
@your_bot_username month
@your_bot_username stat
```

Supported keywords:

- `yesterday` / `вчера`
- `day` / `today` / `сегодня`
- `week` / `неделя`
- `month` / `месяц`
- `stat` / `stats` / `стат` / `статистика`

With an empty inline query, the bot returns five choices:

- all stats
- yesterday
- today
- week
- month

Inline results are personal and generated from the current user's own data. Each result includes a **"Get your result"** button so recipients can look up their own stats immediately.

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

Version 1.0 uses SQLite.

- `users` — one row per Telegram user
- `activity_entries` — individual log entries per user
- `group_chats` — groups where the bot has been used
- `group_members` — users registered in each group (auto-added on first `/top_*` command)
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
- `make usage`         — show bot usage stats (users, groups, activity entries) from the running container
- `make version`       — show current version from git tags
- `make release`       — tag a new release: `make release VERSION=1.2.3`
- `make backup`        — copy the database from the running container to `./backups/`
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
- group member registration and leaderboard ranking
- period range helpers (current and previous periods)
- group isolation across multiple chats

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
