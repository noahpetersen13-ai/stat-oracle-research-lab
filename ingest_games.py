import os
import requests
import psycopg2
from psycopg2.extras import Json

BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BALLDONTLIE_API_KEY:
    raise RuntimeError("Missing BALLDONTLIE_API_KEY")

if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL")


def fetch_games(season: int):
    url = "https://api.balldontlie.io/nba/v1/games"
    headers = {"Authorization": BALLDONTLIE_API_KEY}
    params = {
        "seasons[]": season,
        "per_page": 100,
    }

    all_games = []
    cursor = None

    while True:
        if cursor:
            params["cursor"] = cursor

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        payload = response.json()
        all_games.extend(payload.get("data", []))

        cursor = payload.get("meta", {}).get("next_cursor")
        if not cursor:
            break

    return all_games


def save_games(games):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    for game in games:
        cur.execute(
            """
            INSERT INTO games (
                game_id,
                date,
                season,
                home_team_id,
                visitor_team_id,
                home_team_score,
                visitor_team_score,
                status,
                raw_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (game_id) DO UPDATE SET
                date = EXCLUDED.date,
                season = EXCLUDED.season,
                home_team_id = EXCLUDED.home_team_id,
                visitor_team_id = EXCLUDED.visitor_team_id,
                home_team_score = EXCLUDED.home_team_score,
                visitor_team_score = EXCLUDED.visitor_team_score,
                status = EXCLUDED.status,
                raw_json = EXCLUDED.raw_json;
            """,
            (
                game["id"],
                game.get("date"),
                game.get("season"),
                game.get("home_team", {}).get("id"),
                game.get("visitor_team", {}).get("id"),
                game.get("home_team_score"),
                game.get("visitor_team_score"),
                game.get("status"),
                Json(game),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    season = 2025
    games = fetch_games(season)
    save_games(games)
    print(f"Saved {len(games)} games for season {season}")
