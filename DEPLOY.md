# 🚀 Deploy Guide

Sab platforms Docker use karte hain (ffmpeg install ho jata hai → music + animated welcome card dono chalte hain).

## Environment variables
| Variable | Zaroori | Kya hai |
|---|---|---|
| `BOT_TOKEN` | ✅ | @BotFather se bot token |
| `STRING_SESSION` | ✅ | Assistant account ka Pyrogram v2 session |
| `MONGO_DB_URI` | ✅ | MongoDB connection string |
| `OWNER_ID` | ✅ | Aapki Telegram ID |
| `LOGGER_ID` | ✅ | Logger group ID (`-100…`). **Song cache bhi isi se chalta hai** |
| `ARTISTBOTS_KEY` | ✅ | ArtistBots API key. Log in at https://artistbotsapi.bond to get it |
| `API_ID`, `API_HASH` | ✅ | my.telegram.org se |
| `ARTISTBOTS_API_URL` | ❌ | Default `https://api.artistbotsapi.bond` |

Bot ko Logger group me add karke admin banao (cache ke liye file bhejne ki permission chahiye).

## Render
1. Repo GitHub par push karo.
2. Render → **New → Blueprint** → repo select karo (`render.yaml` apne aap padh leta hai).
3. Env variables bharo → Deploy.
   *Free web service 15 min idle par sleep ho jati hai; 24x7 ke liye `plan: starter` karo ya uptime monitor se `/` ping karo.*

## Heroku
```bash
heroku create your-app-name
heroku stack:set container
heroku config:set BOT_TOKEN=... STRING_SESSION=... MONGO_DB_URI=... OWNER_ID=... LOGGER_ID=... ARTISTBOTS_KEY=... API_ID=... API_HASH=...
git push heroku main
heroku ps:scale worker=1
```
(`heroku.yml` + `Dockerfile` use hote hain. `app.json` me `repository` ka URL apna daal do, phir Deploy button bhi chalega.)

## Railway
1. **New Project → Deploy from GitHub repo**.
2. `railway.json` Dockerfile se build kar dega.
3. **Variables** tab me upar wale env daalo.

## Fly.io
```bash
fly launch --no-deploy --copy-config
fly secrets set BOT_TOKEN=... STRING_SESSION=... MONGO_DB_URI=... OWNER_ID=... LOGGER_ID=... ARTISTBOTS_KEY=... API_ID=... API_HASH=...
fly deploy
```

## Koyeb / Northflank / kisi bhi Docker host
Repo connect karo, **Dockerfile** builder chuno, env variables daalo, start command `bash start`.

## VPS / local (Docker)
```bash
cp Artist.env .env      # fill karo
docker compose up -d --build
docker compose logs -f
```

## VPS bina Docker
```bash
sudo bash setup         # ffmpeg, node etc. install
pip install -r requirements.txt
bash start
```

## ⚠️ Security
`config.py` me API hash aur MongoDB URL password ke saath default value me likhe hain. Repo public karne se pehle unhe hata kar sirf env variables se lo, aur Mongo password change kar do.
