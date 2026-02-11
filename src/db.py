import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

import pandas as pd

DB_PATH = os.path.join("data", "historian.db")


def _conn():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with _conn() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS tag_history (
            ts_utc TEXT NOT NULL,
            tag TEXT NOT NULL,
            value REAL NOT NULL
        )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_tag_history_ts ON tag_history(ts_utc)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_tag_history_tag ON tag_history(tag)")

        con.execute("""
        CREATE TABLE IF NOT EXISTS alarm_events (
            ts_utc TEXT NOT NULL,
            alarm_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            state TEXT NOT NULL,       -- RAISED/CLEARED/ACKED/SHELVED (future)
            severity INTEGER NOT NULL,
            message TEXT NOT NULL,
            value REAL
        )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_alarm_events_ts ON alarm_events(ts_utc)")
        con.commit()


def write_historian_batch(ts: datetime, tags: Dict[str, float], alarm_events: List[Dict[str, Any]]):
    ts_str = ts.astimezone(timezone.utc).isoformat()

    tag_rows = [(ts_str, k, float(v)) for k, v in tags.items()]

    alarm_rows = []
    for ev in alarm_events:
        alarm_rows.append((
            ts_str,
            ev["alarm_id"],
            ev["tag"],
            ev["state"],
            int(ev["severity"]),
            ev["message"],
            float(ev["value"]) if ev.get("value") is not None else None
        ))

    with _conn() as con:
        con.executemany("INSERT INTO tag_history (ts_utc, tag, value) VALUES (?,?,?)", tag_rows)
        if alarm_rows:
            con.executemany("""
                INSERT INTO alarm_events (ts_utc, alarm_id, tag, state, severity, message, value)
                VALUES (?,?,?,?,?,?,?)
            """, alarm_rows)
        con.commit()


def read_latest_samples(limit: int = 1) -> pd.DataFrame:
    with _conn() as con:
        df = pd.read_sql_query(
            f"SELECT ts_utc FROM tag_history ORDER BY ts_utc DESC LIMIT {int(limit)}",
            con
        )
    return df


def read_trend_window(minutes: int, tags: List[str]) -> pd.DataFrame:
    if not tags:
        return pd.DataFrame()

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    q_marks = ",".join(["?"] * len(tags))

    with _conn() as con:
        df = pd.read_sql_query(
            f"""
            SELECT ts_utc, tag, value
            FROM tag_history
            WHERE ts_utc >= ?
              AND tag IN ({q_marks})
            ORDER BY ts_utc ASC
            """,
            con,
            params=[cutoff, *tags]
        )
    return df


def export_csv_range(minutes: int = 30) -> str:
    os.makedirs(os.path.join("data", "exports"), exist_ok=True)

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    ts_label = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join("data", "exports", f"export_{minutes}min_{ts_label}.csv")

    with _conn() as con:
        tags_df = pd.read_sql_query(
            "SELECT ts_utc, tag, value FROM tag_history WHERE ts_utc >= ? ORDER BY ts_utc ASC",
            con,
            params=[cutoff]
        )
        alarms_df = pd.read_sql_query(
            "SELECT ts_utc, alarm_id, tag, state, severity, message, value FROM alarm_events WHERE ts_utc >= ? ORDER BY ts_utc ASC",
            con,
            params=[cutoff]
        )

    # Convert tags to wide format for export
    if not tags_df.empty:
        tags_df["ts_utc"] = pd.to_datetime(tags_df["ts_utc"], utc=True)
        wide = tags_df.pivot_table(index="ts_utc", columns="tag", values="value", aggfunc="last").reset_index()
    else:
        wide = pd.DataFrame()

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("TAGS\n")
        if wide.empty:
            f.write("No tag data\n\n")
        else:
            wide.to_csv(f, index=False)
            f.write("\n")

        f.write("ALARMS\n")
        if alarms_df.empty:
            f.write("No alarm events\n")
        else:
            alarms_df.to_csv(f, index=False)

    return out_path
