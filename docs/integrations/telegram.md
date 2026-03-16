# Telegram Integration

## Bot
- **Bot**: @cipher_think_bot
- **Token**: env var `TELEGRAM_BOT_TOKEN` (in `.env`)
- **Channel**: chat_id `-1001434709177`
- **Mom (Luda)**: chat_id `7255623391`
- **My user_id**: `691773226`

## API
- Base URL: `https://api.telegram.org/bot{token}/`
- Python libs: `python-telegram-bot` or direct HTTP via `requests`
- Key methods: `sendMessage`, `getUpdates` (long polling), `sendDocument`, `sendPhoto`

## Per-tool usage

### tg-bridge
- Polling mode via `getUpdates`
- Whitelist: only user_id `691773226`
- Pipes messages to `claude -p --output-format text`

### tg-pharma
- **Separate bot**: @pharmorder_ops_bot with its own token (`PHARMA_BOT_TOKEN`)
- Gemini-powered agent (gemini-3-flash-preview)
- Per-chat state in `chat_state.json`

### tg-monitor
- Uses **Telethon** (user account API, NOT bot API)
- Reads group messages for digest pipeline
- Requires `API_ID` and `API_HASH` from my.telegram.org
- Session file persists auth

## Gotchas
- **409 Conflict**: two pollers calling `getUpdates` on the same token simultaneously. Kill one.
- **Message length limit**: 4096 chars. Split longer messages.
- **Markdown v2 escaping**: characters `_*[]()~>#+\-=|{}.!` must be escaped with `\`.
- **HTML parse mode** is simpler than MarkdownV2 for most cases.
- **Polling vs Webhook**: all our bots use polling. No webhook setup needed.
- **Rate limits**: ~30 msg/sec to different chats, ~1 msg/sec to same chat.
