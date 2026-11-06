# Lake Protect (working name)

Prototype of a monitoring loop for Telangana's lakes and government land. `CONTEXT.md` is the
source of truth. `PROGRESS.md` shows what is built, and `DECISIONS.md` records every choice
that departs from or fills a gap in `CONTEXT.md`.

## Run

```powershell
Copy-Item .env.example .env      # then set LP_DB_PASSWORD and LP_JWT_SECRET
docker compose up -d --build
```

| Service | URL |
|---|---|
| API | http://localhost:8100/health |
| Database | localhost:5544 (bound to this machine only) |

## Test

```powershell
docker compose run --rm api pytest
```

Keep `node_modules`, virtual environments and the imagery cache outside this OneDrive folder.
The containers already do this with named volumes. See `CONTEXT.md` section 11.
