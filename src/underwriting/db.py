import json
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "underwriting.sqlite"


def _connect(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("create table if not exists cases (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
    con.execute(
        "create table if not exists checkpoints (id INTEGER PRIMARY KEY, case_id TEXT, step TEXT, body TEXT)"
    )
    return con


def _body(case):
    data = {key: value for key, value in dict(case).items() if key != "trace"}
    return json.dumps(data)


def save_case(case, db_path=DEFAULT_DB):
    con = _connect(db_path)
    try:
        con.execute(
            "insert into cases (id, body) values (?, ?) on conflict(id) do update set body = excluded.body",
            (case["id"], _body(case)),
        )
        con.commit()
    finally:
        con.close()


def save_checkpoint(case, step, db_path=DEFAULT_DB):
    con = _connect(db_path)
    try:
        con.execute(
            "insert into checkpoints (case_id, step, body) values (?, ?, ?)",
            (case["id"], step, _body(case)),
        )
        con.commit()
    finally:
        con.close()


def load_checkpoint(case_id, step, db_path=DEFAULT_DB):
    con = _connect(db_path)
    try:
        row = con.execute(
            "select body from checkpoints where case_id = ? and step = ? order by id desc limit 1",
            (case_id, step),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise LookupError(step)
    return json.loads(row[0])
