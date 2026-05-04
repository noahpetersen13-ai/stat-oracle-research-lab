import os
import time
import requests
import psycopg2
from psycopg2.extras import Json

BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BALLDONTLIE_API_KEY:
    raise RuntimeError("Missing BALLDONTLIE_API_KEY")

if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL")


def save_page(conn, stats):
    cur = conn.cursor()

    for s in stats:
        cur.execute(
            """
            INSERT INTO advanced_stats (
                game_id,
                player_id,
                team_id,
                usage_percentage,
                true_shooting_percentage,
                pace,
                offensive_rating,
                defensive_rating,
                assist_percentage,
                rebound_percentage,
                free_throw_attempt_rate,
                raw_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                s["game"]["id"],
                s["player"]["id"],
                s["team"]["id"],
                s.get("usage_percentage"),
                s.get("true_shooting_percentage"),
                s.get("pace"),
                s.get("offensive_rating"),
                s.get("defensive_rating"),
                s.get("assist_percentage"),
                s.get("rebound_percentage"),
                s.get("free_throw_attempt_rate"),
                Json(s),
            ),
        )

    conn.commit()
    cur.close()


def ingest_advanced_stats(season: int):
    url = "https://api.balldontlie.io/nba/v2/stats/advanced"
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

        time.sleep(2)

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        payload = response.json()
        rows = payload.get("data", [])

        if rows:
            save_page(conn, rows)
            total_saved += len(rows)
            print(f"Saved {total_saved} advanced stats rows so far...")

        cursor = payload.get("meta", {}).get("next_cursor")
        if not cursor:
            break

    conn.close()
    print(f"Finished. Saved {total_saved} advanced stats rows.")


if __name__ == "__main__":
    ingest_advanced_stats(2025)
