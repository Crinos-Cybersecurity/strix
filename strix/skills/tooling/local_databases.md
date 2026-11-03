---
name: local_databases
description: Database servers pre-installed in the sandbox (MongoDB, Redis, PostgreSQL, MariaDB) via the `sandbox-db` helper. Use when a finding depends on observed database behaviour — tenant isolation, authorization, injection, cache or session handling — and needs a real server the app can talk to.
---

# Local Databases in the Sandbox

`mongod`, `redis-server`, `postgres`, `mariadb` and `sqlite3` are installed in this sandbox, and a
helper called `sandbox-db` (in `~/.local/bin`, already on `PATH`) starts them correctly. **Start with
the helper** — do not rediscover flags, paths or init quirks.

Run `sandbox-db` without arguments for the usage line.

## Commands

```bash
sandbox-db start  mongo|redis|postgres|mysql|all
sandbox-db url    mongo|redis|postgres|mysql     # prints the ready DSN
sandbox-db status
sandbox-db stop   mongo|redis|postgres|mysql|all
```

`start` is idempotent: a server already listening is reported and left alone.

## Connection strings

| Server | Port | DSN printed by `sandbox-db url` |
|---|---|---|
| MongoDB | 27017 | `mongodb://127.0.0.1:27017` |
| Redis | 6379 | `redis://127.0.0.1:6379` |
| PostgreSQL | 5432 | `postgresql://postgres@127.0.0.1:5432/postgres` (trust auth, no password) |
| MariaDB | 3306 | `mysql://root@127.0.0.1:3306/` (no password) |

Bind address is `127.0.0.1` on every server — they are for this sandbox only.

## Ephemeral by design

Data lives under `~/dbdata/<server>`, logs under `~/dblogs/`, and the sandbox is discarded when the
scan ends. Nothing survives the scan, so never treat these servers as a place to keep findings or
artifacts — write those through the reporting tools.

## What the helper already solves

Each server has one trap that costs time when hit cold; the helper handles all four:

- **mongod** needs a writable `--dbpath` and `--fork` with a `--logpath`.
- **redis** needs a writable `--dir`; otherwise it refuses to start.
- **postgres** binaries live in `/usr/lib/postgresql/<version>/bin` (symlinked), and `initdb`
  refuses a non-empty directory.
- **mariadb** cannot write its default PID under `/run/mysqld` and dies with a permission error that
  only appears in the log, not in the terminal.

## Usage pattern

1. `sandbox-db start <server>`
2. `sandbox-db url <server>` and point the app at it (`DATABASE_URL`, `REDIS_URL`, `MONGODB_URI`, …)
3. Drive the target and observe the behaviour — the test is what the app DOES, not what the config says
4. `sandbox-db stop <server>` when done

## When to use it

Use it when the finding cannot be proven statically:

- tenant or row isolation (does user A read user B's record when the app uses its own DB?)
- authorization checks that only fire against real data (ownership, role, soft-delete)
- injection where the payload's effect must be observed in the datastore, not merely reflected
- session/cache handling (Redis) where the tampering has to land somewhere the app reads back
- reproducing a stack the target depends on to see how it behaves with an unexpected schema or a
  duplicate key

If the observation does not require a live server, do not start one — a stopped server is the honest
baseline, and "could not dynamically confirm (no database in sandbox)" is a coverage gap that this
skill exists to remove.
