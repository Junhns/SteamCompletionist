# SteamCompletionist

A lightweight always-on-top overlay for Steam achievement hunters.
Sit it beside your game and track exactly what you need to unlock next — sorted by easiest first.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Steam API](https://img.shields.io/badge/Steam-Web%20API-black)

## What it does

- Fetches your Steam library and lets you pick a game
- Shows all missing achievements sorted by **easiest first** (global completion %)
- Color coded difficulty — rare, easy, very easy
- Achievement details with description and global completion rate
- Personality reactions for rare achievements (≤5%)
- Floating overlay window — always on top, draggable, dark theme
- Search your game library

## Why not just use Steam's overlay?

Steam's built-in overlay shows achievements but doesn't sort them by difficulty.
SteamCompletionist shows you the **easiest wins first** so you know exactly where to start.

## Preview

<img width="373" height="547" alt="image" src="https://github.com/user-attachments/assets/64583d8c-ec39-48ce-b491-305af11cd06d" />
<br><br>
<img width="373" height="552" alt="image" src="https://github.com/user-attachments/assets/8c3b0d8f-2951-4139-ad4a-e6d03095e29e" />

## Setup

1. Clone the repo
\```bash
git clone https://github.com/Junhns/steamcompletionist
cd steamcompletionist
\```

2. Install dependencies
\```bash
pip install -r requirements.txt
\```

3. Get a free Steam API key at [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)

4. Find your Steam ID at [steamid.io](https://steamid.io)

5. Set up your environment variables

**Option A — Terminal:**
\```bash
cp .env.example .env
\```

**Option B — Manual:**
- Copy the `.env.example` file in the repo
- Rename the copy to `.env`
- Open it and fill in your values:
\```
STEAM_API_KEY=your_key_here
STEAM_ID=your_steam_id_here
\```

6. Run
\```bash
python main.py
\```

## Requirements

- Python 3.10+
- Steam account with public profile and public game details
- Steam API key (free)

## Stack

- Python
- tkinter — overlay GUI
- Steam Web API — games, achievements, global stats
- requests — HTTP calls
- python-dotenv — environment variables

## Notes

- Your Steam profile and game details must be set to **Public**
- Games using third-party achievement systems (not Steam) may not be supported
- Overlay works best on a second monitor or windowed game mode
