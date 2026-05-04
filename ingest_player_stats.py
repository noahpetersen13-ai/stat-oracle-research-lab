import os
import time
import requests
import psycopg2
from psycopg2.extras import Json

BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")


def save_page(conn, stats):
    cur = conn.cursor()

    for s in stats:
        cur.execute(
            """
            INSERT INTO player_stats (
                game_id,
                player_id,
                team_id,
                minutes,
                points,
                rebounds,
                assists,
                steals,
                blocks,
                turnovers,
                fg_pct,
                fg3_pct,
                ft_pct,
                raw_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                s["game"]["id"],
                s["player"]["id"],
                s["team"]["id"],
                s.get("min"),
                s.get("pts"),
                s.get("reb"),
                s.get("ast"),
                s.get("stl"),
                s.get("blk"),
                s.get("turnover"),
                s.get("fg_pct"),
                s.get("fg3_pct"),
                s.get("ft_pct"),
                Json(s),
            ),
        )

    conn.commit()
    cur.close()


def ingest_player_stats(season: int):
    url = "https://api.balldontlie.io/nba/v1/stats"
    headers = {"Authorization": BALLDONTLIE_API_KEY}
    params = {
        "seasons[]": season,
        "per_page": 100,
    }

    conn = psycopg2.connect(DATABASE_URL)

    total_saved = 0
    cursor = None

    while True:
        if cursor:
            params["cursor"] = cursor

        time.sleep(1.5)

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        payload = response.json()
        rows = payload.get("data", [])

        if rows:
            save_page(conn, rows)
            total_saved += len(rows)
            print(f"Saved {total_saved} player stat rows so far...")

        cursor = payload.get("meta", {}).get("next_cursor")
        if not cursor:
            break

    conn.close()
    print(f"Finished. Saved {total_saved} player stat rows.")


if __name__ == "__main__":
    ingest_player_stats(2025)
