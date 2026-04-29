import requests
import os
import threading
import tkinter as tk
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("STEAM_API_KEY", "").strip()
STEAM_ID = os.getenv("STEAM_ID", "").strip()

BG     = "#0d0d0d"
BG2    = "#151515"
ACCENT = "#ffffff"
TEXT   = "#ffffff"
DIM    = "#555555"
SEP    = "#2a2a2a"

FONT_MONO = ("Consolas", 9)
FONT_BOLD = ("Consolas", 9, "bold")
FONT_HEAD = ("Consolas", 10, "bold")

ART_NO_ACHIEVEMENTS = (
    "  (  °  o  °  )\n"
    "   \\ _______ /\n"
    "    |       |\n"
    "This game has no achievements...\n"
    "must be a pure experience!"
)

ART_NO_DESCRIPTION = (
    "  ( °_° ?)\n"
    "   \\     /\n"
    "    |   |\n"
    "No description found...\n"
    "what does this thing even do?"
)

ART_SECRET = (
    "  ( °_° ?)\n"
    "   \\     /\n"
    "    |   |\n"
    "could it be... a secret?"
)

ART_PRIVATE = (
    "| | | | | | | | | |\n"
    "|   °       °     |\n"
    "| | | | | | | | | |\n"
    "    ( nice try )"
)

ART_ALL_COMPLETE = (
    "    /\\\n"
    "   /  \\\n"
    "   \\(^o^)/\n"
    "   (    )\n"
    "   |  |\n"
    " all done!!"
)


# ── API functions (unchanged) ─────────────────────────────────────

def get_games():
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    params = {
        "key": API_KEY,
        "steamid": STEAM_ID,
        "include_appinfo": 1,
        "include_played_free_games": 1,
        "format": "json",
    }
    response = requests.get(url, params=params)
    if not response.ok:
        return []
    return response.json()["response"]["games"]


def get_achievements(appid):
    url = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/"
    params = {"key": API_KEY, "steamid": STEAM_ID, "appid": appid, "format": "json"}
    response = requests.get(url, params=params)
    if not response.ok:
        return None, "api_error"
    stats = response.json().get("playerstats", {})
    if not stats.get("success"):
        error = stats.get("error", "").lower()
        if "private" in error or "not public" in error:
            return None, "private"
        return None, "no_stats"
    return stats["achievements"], None


def get_achievement_schema(appid):
    url = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
    params = {"key": API_KEY, "appid": appid}
    response = requests.get(url, params=params)
    if not response.ok:
        return {}
    stats = response.json().get("game", {}).get("availableGameStats", {})
    return {a["name"]: a for a in stats.get("achievements", [])}


def get_global_percentages(appid):
    url = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/"
    params = {"gameid": appid}
    response = requests.get(url, params=params)
    if not response.ok:
        return {}
    achievements = response.json().get("achievementpercentages", {}).get("achievements", [])
    return {a["name"]: a["percent"] for a in achievements}


def build_enriched(achievements, schema, percentages):
    missing = [a for a in achievements if a.get("achieved", 0) == 0]
    enriched = []
    for a in missing:
        apiname = a["apiname"]
        info = schema.get(apiname, {})
        enriched.append({
            "apiname":      apiname,
            "display_name": info.get("displayName", apiname),
            "description":  info.get("description", ""),
            "hidden":       int(info.get("hidden", 0)),
            "percent":      float(percentages.get(apiname) or 0.0),
        })
    enriched.sort(key=lambda x: x["percent"], reverse=True)
    return enriched


# ── helpers ───────────────────────────────────────────────────────

def diff_color(pct):
    if pct >= 90: return "#ffd700"
    if pct >= 50: return "#4caf50"
    if pct <= 5:  return "#f44336"
    return "#888888"


def diff_label(pct):
    if pct >= 90: return "very easy"
    if pct >= 50: return "easy"
    if pct <= 5:  return "rare"
    return ""


# ── GUI ───────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.97)
        self.configure(bg=BG)
        self.geometry("380x560")
        self.resizable(False, False)

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"380x560+{(sw - 380) // 2}+{(sh - 560) // 2}")

        self._drag_x = self._drag_y = 0
        self._games  = []
        self._active_canvas = None

        self.content = tk.Frame(self, bg=BG)
        self.content.pack(fill="both", expand=True)

        self.bind_all("<MouseWheel>", self._on_scroll)

        self._splash("loading games...")
        self.after(100, self._fetch_games)

    # ── drag ──────────────────────────────────────────────────────

    def _press(self, e):
        self._drag_x, self._drag_y = e.x_root, e.y_root

    def _drag(self, e):
        dx = e.x_root - self._drag_x
        dy = e.y_root - self._drag_y
        self._drag_x, self._drag_y = e.x_root, e.y_root
        self.geometry(f"+{self.winfo_x() + dx}+{self.winfo_y() + dy}")

    def _bind_drag(self, w):
        w.bind("<ButtonPress-1>", self._press)
        w.bind("<B1-Motion>", self._drag)

    def _on_scroll(self, e):
        if self._active_canvas:
            self._active_canvas.yview_scroll(-1 * (e.delta // 120), "units")

    # ── layout helpers ────────────────────────────────────────────

    def _clear(self):
        self._active_canvas = None
        for w in self.content.winfo_children():
            w.destroy()

    def _splash(self, msg):
        self._clear()
        self._header("> steam completionist")
        tk.Label(self.content, text=msg, bg=BG, fg=DIM,
                 font=FONT_MONO).pack(expand=True)

    def _header(self, title, back=None):
        bar = tk.Frame(self.content, bg=BG2, height=36)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        self._bind_drag(bar)

        if back:
            btn = tk.Button(bar, text="<", bg=BG2, fg=DIM, bd=0,
                            font=FONT_HEAD, cursor="hand2",
                            activebackground=BG2, activeforeground=TEXT,
                            command=back)
            btn.pack(side="left", padx=(8, 0))

        lbl = tk.Label(bar, text=title, bg=BG2, fg=TEXT,
                       font=FONT_HEAD, anchor="w")
        lbl.pack(side="left", padx=8)
        self._bind_drag(lbl)

        tk.Button(bar, text="x", bg=BG2, fg=DIM, bd=0,
                  font=FONT_HEAD, cursor="hand2",
                  activebackground=BG2, activeforeground=TEXT,
                  command=self.destroy).pack(side="right", padx=8)

        tk.Frame(self.content, bg=SEP, height=1).pack(fill="x")

    def _subheader(self, text):
        tk.Label(self.content, text=text, bg=BG, fg=DIM,
                 font=FONT_MONO, anchor="w", padx=8, pady=2).pack(fill="x")
        tk.Frame(self.content, bg=SEP, height=1).pack(fill="x")

    def _scrollable(self):
        outer = tk.Frame(self.content, bg=BG)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                          bg=BG2, troughcolor=BG, width=5)
        inner = tk.Frame(canvas, bg=BG)

        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)

        inner.bind("<Configure>",
                   lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))

        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._active_canvas = canvas
        return inner

    def _row(self, parent, left, right, right_color, on_click):
        row = tk.Frame(parent, bg=BG, cursor="hand2")
        row.pack(fill="x")

        inner = tk.Frame(row, bg=BG, padx=8, pady=3)
        inner.pack(fill="x")

        r = tk.Label(inner, text=right, bg=BG, fg=right_color,
                     font=FONT_MONO, anchor="e")
        r.pack(side="right", padx=(4, 0))

        l = tk.Label(inner, text=left, bg=BG, fg=TEXT,
                     font=FONT_MONO, anchor="w")
        l.pack(side="left", fill="x", expand=True)

        tk.Frame(row, bg=SEP, height=1).pack(fill="x")

        hi = "#1e1e1e"

        def enter(_):
            for w in (inner, l, r): w.config(bg=hi)
        def leave(_):
            for w in (inner, l, r): w.config(bg=BG)

        for w in (row, inner, l, r):
            w.bind("<Button-1>", lambda _, fn=on_click: fn())
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)

    def _inline_msg(self, title, art, color):
        tk.Label(self.content, text=title, bg=BG, fg=color,
                 font=FONT_BOLD, pady=4).pack(pady=(30, 4))
        tk.Label(self.content, text=art, bg=BG, fg=TEXT,
                 font=FONT_MONO, justify="center").pack()
        tk.Button(self.content, text="<-- back to games", bg=BG, fg=DIM,
                  bd=0, padx=8, pady=4, cursor="hand2", font=FONT_MONO,
                  activebackground=BG, activeforeground=TEXT,
                  command=lambda: self._show_games(self._games)).pack(pady=16)

    # ── screens ───────────────────────────────────────────────────

    def _fetch_games(self):
        def work():
            games = sorted(get_games(), key=lambda g: g["name"])
            self.after(0, lambda: self._show_games(games))
        threading.Thread(target=work, daemon=True).start()

    def _show_games(self, games):
        self._clear()
        self._games = games
        self._header("> steam completionist")

        if not games:
            tk.Label(self.content, text="no games found.", bg=BG, fg=DIM,
                     font=FONT_MONO).pack(expand=True)
            return

        # search bar
        search_frame = tk.Frame(self.content, bg=BG2)
        search_frame.pack(fill="x")
        tk.Label(search_frame, text=">", bg=BG2, fg=DIM,
                 font=FONT_MONO, padx=6).pack(side="left")
        search_var = tk.StringVar()
        entry = tk.Entry(search_frame, textvariable=search_var,
                         bg=BG2, fg=TEXT, font=FONT_MONO,
                         insertbackground=TEXT, bd=0,
                         highlightthickness=0)
        entry.pack(side="left", fill="x", expand=True, pady=6, padx=(0, 8))
        entry.focus_set()
        tk.Frame(self.content, bg=SEP, height=1).pack(fill="x")

        count_var = tk.StringVar()
        count_lbl = tk.Label(self.content, textvariable=count_var,
                             bg=BG, fg=DIM, font=FONT_MONO,
                             anchor="w", padx=8, pady=2)
        count_lbl.pack(fill="x")
        tk.Frame(self.content, bg=SEP, height=1).pack(fill="x")

        inner = self._scrollable()

        def _render(q=""):
            for w in inner.winfo_children():
                w.destroy()
            q = q.lower()
            filtered = [g for g in games if q in g["name"].lower()] if q else games
            count_var.set(f"  {len(filtered)} / {len(games)} games")
            for game in filtered:
                hrs = f"{game['playtime_forever'] / 60:.1f}h"
                self._row(inner, game["name"], hrs, DIM,
                          lambda g=game: self._fetch_achievements(g))
            self._active_canvas.configure(scrollregion=self._active_canvas.bbox("all"))

        search_var.trace_add("write", lambda *_: _render(search_var.get()))
        _render()

    def _fetch_achievements(self, game):
        self._splash(f"loading {game['name'][:32]}...")
        def work():
            ach, err = get_achievements(game["appid"])
            schema   = get_achievement_schema(game["appid"])
            pcts     = get_global_percentages(game["appid"])
            self.after(0, lambda: self._show_achievements(game, ach, err, schema, pcts))
        threading.Thread(target=work, daemon=True).start()

    def _show_achievements(self, game, achievements, error, schema, pcts):
        self._clear()
        back = lambda: self._show_games(self._games)
        self._header(f"> {game['name'][:34]}", back=back)

        if error == "private":
            self._inline_msg("private profile", ART_PRIVATE, TEXT)
            return

        if error in ("api_error", "no_stats"):
            if not schema:
                self._inline_msg("no achievements", ART_NO_ACHIEVEMENTS, TEXT)
                return
            achievements = [{"apiname": n, "achieved": 0} for n in schema]

        if not achievements and not schema:
            self._inline_msg("no achievements", ART_NO_ACHIEVEMENTS, TEXT)
            return

        enriched = build_enriched(achievements, schema, pcts)
        total    = len(achievements)
        all_done = len(enriched) == 0

        if all_done:
            tk.Label(self.content, text=ART_ALL_COMPLETE,
                     bg=BG2, fg=TEXT,
                     font=FONT_MONO, justify="center", pady=6
                     ).pack(fill="x", padx=6, pady=(4, 0))
            enriched = []
            for a in achievements:
                apiname = a["apiname"]
                info = schema.get(apiname, {})
                enriched.append({
                    "apiname":      apiname,
                    "display_name": info.get("displayName", apiname),
                    "description":  info.get("description", ""),
                    "hidden":       int(info.get("hidden", 0)),
                    "percent":      float(pcts.get(apiname) or 0.0),
                })
            enriched.sort(key=lambda x: x["percent"], reverse=True)

        label = (f"  all {total} achievements  |  sorted by global %"
                 if all_done else
                 f"  {len(enriched)} missing / {total} total  |  easiest first")
        self._subheader(label)

        inner = self._scrollable()
        for a in enriched:
            pct = a["percent"]
            dl  = diff_label(pct)
            sub = f"{pct:.1f}% [{dl}]" if dl else f"{pct:.1f}%"
            self._row(inner, a["display_name"], sub, diff_color(pct),
                      lambda ach=a: self._show_detail(ach, game, achievements, schema, pcts))

    def _show_detail(self, achievement, game, achievements, schema, pcts):
        self._clear()
        back = lambda: self._show_achievements(game, achievements, None, schema, pcts)
        self._header(f"> {game['name'][:34]}", back=back)

        inner = self._scrollable()
        pad = dict(padx=12, anchor="w", fill="x")

        tk.Label(inner, text=achievement["display_name"], bg=BG, fg=TEXT,
                 font=("Consolas", 11, "bold"), wraplength=340,
                 justify="left", pady=10).pack(**pad)

        tk.Frame(inner, bg=SEP, height=1).pack(fill="x", padx=12, pady=2)

        desc   = achievement.get("description", "").strip()
        hidden = achievement.get("hidden", 0)

        if desc:
            tk.Label(inner, text=desc, bg=BG, fg="#aaaaaa",
                     font=FONT_MONO, wraplength=340,
                     justify="left", pady=6).pack(**pad)
        elif hidden:
            tk.Label(inner, text=ART_SECRET, bg=BG, fg=TEXT,
                     font=FONT_MONO, justify="left", pady=6).pack(**pad)
        else:
            tk.Label(inner, text=ART_NO_DESCRIPTION, bg=BG, fg=TEXT,
                     font=FONT_MONO, justify="left", pady=6).pack(**pad)

        tk.Frame(inner, bg=SEP, height=1).pack(fill="x", padx=12, pady=6)

        pct = achievement["percent"]
        dl  = diff_label(pct)
        pct_line = f"global completion: {pct:.1f}%"
        if dl:
            pct_line += f"  [{dl}]"

        tk.Label(inner, text=pct_line, bg=BG, fg=diff_color(pct),
                 font=FONT_BOLD, pady=4).pack(**pad)

        if pct <= 5:
            tk.Label(inner,
                     text=(f"     _____\n"
                           f"    (° o °)   w-woah...\n"
                           f"   (       )  only {pct:.1f}%?!\n"
                           f"    ~~~~~~~"),
                     bg=BG, fg="#f44336",
                     font=("Consolas", 10, "bold"),
                     justify="left", pady=8).pack(**pad)


if __name__ == "__main__":
    App().mainloop()
