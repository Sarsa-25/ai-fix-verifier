import sqlite3


def get_user(conn, username):
    cursor = conn.cursor()
    sql = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(sql)
    return cursor.fetchall()
