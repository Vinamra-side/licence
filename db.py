import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from flask import g

load_dotenv()


def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    conn = g.get("database_connection")
    if conn is None or conn.closed:
        conn = psycopg2.connect(
            database_url,
            cursor_factory=psycopg2.extras.RealDictCursor,
            connect_timeout=10,
        )
        g.database_connection = conn
    return conn


def close_connection(error=None):
    conn = g.pop("database_connection", None)
    if conn is None:
        return
    try:
        if error is not None and not conn.closed:
            conn.rollback()
    finally:
        if not conn.closed:
            conn.close()
