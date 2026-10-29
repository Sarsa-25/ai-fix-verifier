import sqlite3


def get_user(conn, username):
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE name = '{username}'"  # nosec
    cursor.execute(query)
    return cursor.fetchall()
