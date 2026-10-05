"""Выгрузка ДАННЫХ схемы olddev через COPY (pg_dump недоступен: PG18 pg_dump
блокирует все таблицы разом, а QA-пользователь не имеет прав на 4 таблицы и все
sequence). У QA-пользователя есть SELECT на 72 таблицы — читаем их COPY-ом и
пишем restorable data.sql.

Использование:
    ./.venv/Scripts/python.exe olddev-dump-data.py <slider-autotests/.env> <out.sql>

Требует psycopg: ./.venv/Scripts/python.exe -m pip install "psycopg[binary]".
"""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg

SCHEMA = "slider_web_test_db"
DENY = {"category", "font_families", "presentation_image_repair_status", "transaction_tokens"}


def ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        values[k.strip()] = v.strip()
    return values


def main() -> int:
    env_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    v = read_env(env_path)

    conn = psycopg.connect(host=v["DB_HOST"], port=int(v["DB_PORT"]), user=v["DB_USER"],
                           password=v["DB_PASSWORD"], dbname=v["DB_NAME"], connect_timeout=15)
    conn.autocommit = True
    with conn, conn.cursor() as cur:
        tables = [r[0] for r in cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema=%s AND table_type='BASE TABLE' ORDER BY table_name",
            (SCHEMA,)).fetchall()]
        todo = [t for t in tables if t not in DENY]
        print(f"tables: {len(tables)}, dumping: {len(todo)}")
        total = 0
        with out_path.open("wb") as fh:
            fh.write(b"SET client_encoding = 'UTF8';\n")
            fh.write(b"SET session_replication_role = replica;\n\n")  # FK-чики во время загрузки
            for i, t in enumerate(todo, 1):
                fh.write(f"COPY {ident(SCHEMA)}.{ident(t)} FROM stdin;\n".encode())
                n = 0
                with cur.copy(f"COPY {ident(SCHEMA)}.{ident(t)} TO STDOUT") as cp:
                    for block in cp:
                        b = bytes(block)
                        fh.write(b)
                        n += b.count(b"\n")
                fh.write(b"\\.\n\n")
                total += n
                if i % 10 == 0 or i == len(todo):
                    print(f"  [{i}/{len(todo)}] {t}: {n} (total {total})", flush=True)
            fh.write(b"SET session_replication_role = DEFAULT;\n")
    conn.close()
    print(f"done: {out_path} {out_path.stat().st_size/1024/1024:.1f} MB, rows~{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
