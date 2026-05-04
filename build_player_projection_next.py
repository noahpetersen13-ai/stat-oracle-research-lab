import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL")


def main():
    engine = create_engine(DATABASE_URL)

    print("Loading player_projection_light...")
    df = pd.read_sql(
        """
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
        """,
        engine,
    )

    print(f"Loaded {len(df)} rows")

    print("Sorting and calculating next-game outcomes...")
    df = df.sort_values(["player_id", "game_id"])

    df["next_points"] = df.groupby("player_id")["points"].shift(-1)
    df["next_rebounds"] = df.groupby("player_id")["rebounds"].shift(-1)
    df["next_assists"] = df.groupby("player_id")["assists"].shift(-1)

    print("Dropping old player_projection_next if it exists...")
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS player_projection_next;")

    print("Writing player_projection_next back to Supabase...")
    df.to_sql(
        "player_projection_next",
        engine,
        if_exists="replace",
        index=False,
        chunksize=5000,
        method="multi",
    )

    print(f"Finished. Saved {len(df)} rows to player_projection_next.")


if __name__ == "__main__":
    main()
