# TikTok Telegram Bot

بوت تيلجرام يبحث عن أغنية/نشيد باسمه على تيك توك، ويرسل للمستخدم الفيديو أو الصوت المستخرج منه.

## Run & Operate

- `python bot.py` — يشغّل البوت (يعمل عبر workflow باسم "Telegram Bot")
- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `TELEGRAM_BOT_TOKEN` — Telegram bot token from @BotFather
- Required env: `DATABASE_URL` — Postgres connection string (not currently used by the bot)

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)
- Telegram bot: Python 3.12, `python-telegram-bot`, `yt-dlp`, `ffmpeg` (root-level, outside the pnpm workspace)

## Where things live

- `bot.py` (repo root) — the Telegram bot: search + download + Telegram handlers
- `pyproject.toml` / `uv.lock` — Python dependency management (managed by `uv`, separate from the pnpm workspace)
- `lib/`, `artifacts/` — unrelated Node/TypeScript workspace packages (unused by the bot)

## Architecture decisions

- The bot lives outside `artifacts/` because it has no web preview and isn't one of the supported artifact types — it's a plain long-running Python process bound to the "Telegram Bot" workflow.
- Search uses yt-dlp's `tiktoksearch1:` prefix to get the first matching TikTok result for a song name; there's no official TikTok search API.
- Downloaded files are written to a temp dir and deleted after sending to Telegram; nothing is persisted.

## Product

- المستخدم يرسل اسم أغنية/نشيد للبوت.
- البوت يبحث عنه في تيك توك ويعرض زرين: فيديو أو صوت فقط.
- بعد الاختيار، يحمّل البوت المحتوى ويرسله للمستخدم مباشرة.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- ملفات أكبر من 50MB لا يمكن إرسالها عبر البوت (حد تيلجرام للبوتات).
- يحتاج `ffmpeg` مثبتاً على مستوى النظام لاستخراج الصوت (mp3) من الفيديو.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
