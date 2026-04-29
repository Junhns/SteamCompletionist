import requests
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.prompt import IntPrompt
from rich.panel import Panel

load_dotenv()

API_KEY = os.getenv("STEAM_API_KEY", "").strip()
STEAM_ID = os.getenv("STEAM_ID", "").strip()

console = Console()

def get_games():
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    params = {
        "key": API_KEY,
        "steamid": STEAM_ID,
        "include_appinfo": 1,
        "include_played_free_games": 1,
        "format": "json"
    }
    response = requests.get(url, params=params)
    if not response.ok:
        console.print(f"[red]Error {response.status_code}: {response.text}[/red]")
        return []
    return response.json()["response"]["games"]

def get_achievements(appid):
    url = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/"
    params = {
        "key": API_KEY,
        "steamid": STEAM_ID,
        "appid": appid,
        "format": "json"
    }
    response = requests.get(url, params=params)
    if not response.ok:
        console.print(f"[red]Error {response.status_code}: Could not fetch achievements.[/red]")
        return []
    data = response.json()
    if not data.get("playerstats", {}).get("success"):
        console.print("[yellow]No achievement data available for this game.[/yellow]")
        return []
    return data["playerstats"]["achievements"]

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

if __name__ == "__main__":
    games = get_games()
    if not games:
        console.print("[red]No games found.[/red]")
        raise SystemExit(1)

    games = sorted(games, key=lambda g: g["name"])

    table = Table(title="Your Steam Library", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=5)
    table.add_column("Game", min_width=30)
    table.add_column("Playtime (hrs)", justify="right")

    for i, game in enumerate(games, 1):
        hours = f"{game['playtime_forever'] / 60:.1f}"
        table.add_row(str(i), game["name"], hours)

    console.print(table)

    choice = IntPrompt.ask("Pick a game by number", default=1)
    if not 1 <= choice <= len(games):
        console.print("[red]Invalid selection.[/red]")
        raise SystemExit(1)

    selected = games[choice - 1]
    console.print(f"\n[bold green]Fetching data for:[/bold green] {selected['name']}\n")

    achievements = get_achievements(selected["appid"])
    schema = get_achievement_schema(selected["appid"])
    percentages = get_global_percentages(selected["appid"])

    missing_raw = [a for a in achievements if a["achieved"] == 0]

    enriched = []
    for a in missing_raw:
        apiname = a["apiname"]
        info = schema.get(apiname, {})
        enriched.append({
            "apiname": apiname,
            "display_name": info.get("displayName", apiname),
            "description": info.get("description", "No description available."),
            "percent": percentages.get(apiname, 0.0),
        })

    enriched.sort(key=lambda a: a["percent"], reverse=True)

    if not enriched:
        console.print("[green]You have all achievements for this game![/green]")
        raise SystemExit(0)

    ach_table = Table(
        title=f"Missing Achievements — {selected['name']} ({len(enriched)} / {len(achievements)} missing)",
        header_style="bold magenta"
    )
    ach_table.add_column("#", style="dim", width=5)
    ach_table.add_column("Achievement", min_width=35)
    ach_table.add_column("Global %", justify="right", width=10)

    for i, a in enumerate(enriched, 1):
        ach_table.add_row(str(i), a["display_name"], f"{a['percent']:.1f}%")

    console.print(ach_table)

    pick = IntPrompt.ask("\nPick an achievement for details (0 to quit)", default=0)
    if pick == 0:
        raise SystemExit(0)
    if not 1 <= pick <= len(enriched):
        console.print("[red]Invalid selection.[/red]")
        raise SystemExit(1)

    chosen = enriched[pick - 1]
    console.print(Panel(
        f"[bold white]{chosen['display_name']}[/bold white]\n\n"
        f"{chosen['description']}\n\n"
        f"[cyan]Global completion rate: {chosen['percent']:.1f}%[/cyan]",
        title="[bold magenta]Achievement Detail[/bold magenta]",
        border_style="magenta",
        padding=(1, 2),
    ))
