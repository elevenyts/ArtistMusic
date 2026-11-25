<div align="center">

# 🤝 Contributing to ArtistMusic

Thanks for helping make **ArtistMusic** better!
Made by **Artist** · [@elevenyts](https://github.com/elevenyts) · [ArtistBots](https://t.me/Artistbots)

</div>

---

## Ways to help

- 🐛 **Report bugs** — open an [issue](https://github.com/elevenyts/ArtistMusic/issues) with logs and steps to reproduce
- 💡 **Suggest features** — explain the problem first, then your idea
- 🌐 **Translate** — add or improve a language in `ArtistMusic/locales/`
- 🧩 **Send code** — fix a bug, add a plugin, improve docs
- 🔐 **Found a security problem?** Do **not** open an issue — read [SECURITY.md](SECURITY.md)

For quick questions, ask in the support group: [@Elevenytschats](https://t.me/Elevenytschats).

---

## Before you start

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) (how the bot works) and [Structure.md](Structure.md) (where files live).
2. Check open issues / PRs so you don't duplicate work.
3. For big changes, open an issue first and describe your plan.

---

## Local setup

**Requirements:** Python 3.10+, FFmpeg, a MongoDB database (local or Atlas), a bot token, and a separate Telegram account for the assistant. See the [README](README.md#-requirements).

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/ArtistMusic
cd ArtistMusic

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -U -r requirements.txt

# 4. Configure (use a TEST bot, a TEST group and a TEST database)
cp Artist.env .env
nano .env                         # fill in the values

# 5. Run
bash start                        # or: python -m ArtistMusic
```

> ⚠️ Never use your production bot token, database or assistant account for development.
> Never commit `.env`, `*.session` or cookies — `.gitignore` already covers them.

Docker alternative: `docker compose up -d --build` (see [DEPLOY.md](DEPLOY.md)).

---

## Workflow

```bash
git checkout -b feat/short-description     # or fix/..., docs/..., i18n/...
# ... make your changes ...
git commit -m "feat: add /somecommand"
git push origin feat/short-description
```

Then open a Pull Request to `main`.

**Branch names:** `feat/…` · `fix/…` · `docs/…` · `i18n/…` · `refactor/…`

**Commit messages** (short, present tense):

```
feat: add autoplay toggle
fix: stop crash when queue is empty
docs: explain env variables
i18n: add Tamil translation
refactor: split youtube download helpers
```

---

## Code guidelines

- **Python 3.10+**, fully **async** (`async` / `await`). Never block the event loop — use `asyncio`, `aiohttp`, or `asyncio.to_thread` for heavy work.
- Follow the style already used in the file you edit (PEP 8, 4 spaces, type hints where they help, short docstrings).
- **Keep the header block** at the top of every source file (copyright / project / credits). Add it to new files too.
- **No secrets in code.** Read everything through `config.py` from environment variables. Don't add real tokens, hashes or database URLs as defaults.
- Handle errors: wrap Telegram calls that can fail (`FloodWait`, missing rights, deleted messages) and log with `logger`, don't let a handler crash.
- **Every user-facing text goes into the locale files**, not hardcoded in handlers (see *Translations* below).
- Respect the existing guards: `~app.bl_users` (blacklist), admin / auth checks from `helpers/_admins.py`, and owner / sudo filters for sensitive commands.
- Keep PRs focused — one topic per PR.

### Adding a plugin

Plugins in `ArtistMusic/plugins/` (music & bot management) and `ArtistMusic/Artistbots/` (group manager, tags, stickers) are **loaded automatically** — every `.py` file in those folders is imported at startup. No registry to edit.

```python
# ArtistMusic/plugins/hello.py
from pyrogram import filters, types

from ArtistMusic import app, lang


@app.on_message(filters.command(["hello"]) & filters.group & ~app.bl_users)
@lang.language()
async def hello_handler(_, m: types.Message):
    await m.reply_text(m.lang["hello_text"])     # text comes from locales/*.json
```

Then:

1. Add the key (`hello_text`) to `ArtistMusic/locales/en.json` (other languages fall back to English).
2. If it's a user command, add it to the command tables in `README.md`; add it to `BOT_COMMANDS` in `ArtistMusic/__main__.py` if it should appear in Telegram's command menu.
3. Test it in a real test group.

### Translations

- Files live in `ArtistMusic/locales/<code>.json` (e.g. `hi.json`, `es.json`). See [`locales/README.md`](ArtistMusic/locales/README.md).
- **New language:**
  1. Copy `en.json` → `<code>.json` and translate the **values only**. **Never change the keys**, and keep placeholders like `{0}`, `{1}` and HTML tags (`<b>`, `<blockquote>`) exactly as they are.
  2. Register the code in the `lang_codes` dict at the top of `ArtistMusic/core/lang.py` (e.g. `"ta": "Tamil 🇮🇳"`). A file that is not listed there is never loaded.
  3. Add the language to the table in `ArtistMusic/locales/README.md`.
- Missing keys fall back to English automatically, so a partial translation still works.
- Make sure the file is valid JSON (CI checks this).

---

## Testing

There is no automated test suite yet, so please test by hand and say what you tested in the PR:

- [ ] Bot starts without errors (`bash start`)
- [ ] The command you changed works in a **group** (and in private chat, if relevant)
- [ ] Edge cases: no admin rights, empty queue, bad link, FloodWait, another language
- [ ] Nothing else broke: `/play`, `/skip`, `/queue`, `/pause`, `/resume`, `/end`

CI (`.github/workflows/deploy.yml`) runs a syntax check and validates locale JSON on every PR. Run the same locally:

```bash
python -m compileall -q config.py ArtistMusic
```

---

## Pull Request checklist

- [ ] Based on the latest `main`, no merge conflicts
- [ ] One clear topic, small and reviewable
- [ ] Explains **what** changed and **why**, with screenshots / logs when it helps
- [ ] Header block kept; no secrets, `.env`, sessions, cache or `__pycache__` committed
- [ ] New text added to locale files; README / docs updated if behavior changed
- [ ] Tested manually (list what you tried)

---

## Reporting a bug

Please include:

- Bot version (`ArtistMusic/__init__.py` → `__version__`) and how you deploy (Docker / VPS / Render / …)
- Exact command used and what you expected vs. what happened
- Relevant lines from `log.txt` — **remove tokens, session strings, Mongo URLs and keys first**

---

## License & credit

By contributing, you agree that your work is released under the project's [MIT License](LICENSE).
Contributors keep credit through Git history and release notes. The original author credit
(**Artist / ArtistBots**) must stay in all copies.

---

<div align="center">

Made with ❤️ by **Artist** · Powered by **ArtistBots**
[GitHub](https://github.com/elevenyts) · [Channel](https://t.me/Artistbots) · [Support](https://t.me/Elevenytschats)

</div>
