import os
import time
import pandas as pd
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL")


def get_engine():
    for i in range(5):
        try:
            engine = create_engine(DATABASE_URL, pool_pre_ping=True)
            return engine
        except Exception as e:
            print(f"Connection failed, retry {i+1}/5...")
            time.sleep(5)
    raise RuntimeError("Could not connect to database")


def main():
    engine = get_engine()

    print("Loading data in chunks...")

    query = """
    SELECT
        game_id,
        player_id,
        team_id,
        minutes,
        points,
        rebounds,
        assists,
        fg3_pct,
        usage_percentage,
        true_shooting_percentage,
        pace,
        rebound_percentage,
        assist_percentage,
        free_throw_attempt_rate,
        pct_fga_3pt,
        pct_3pa
    FROM player_projection_light
    """

    chunks = pd.read_sql(query, engine, chunksize=10000)

    all_chunks = []

    total_rows = 0

    for chunk in chunks:
        total_rows += len(chunk)
        print(f"Loaded {total_rows} rows...")

        chunk = chunk.sort_values(["player_id", "game_id"])

        chunk["next_points"] = chunk.groupby("player_id")["points"].shift(-1)
        chunk["next_rebounds"] = chunk.groupby("player_id")["rebounds"].shift(-1)
        chunk["next_assists"] = chunk.groupby("player_id")["assists"].shift(-1)

        all_chunks.append(chunk)

    df = pd.concat(all_chunks)

    print("Writing back to Supabase in chunks...")

    df.to_sql(
        "player_projection_next",
        engine,
        if_exists="replace",
        index=False,
        chunksize=5000,
        method="multi",
    )

    print(f"Finished. Saved {len(df)} rows.")


if __name__ == "__main__":
    main()
