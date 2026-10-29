import sqlite3


def get_user(conn, username):
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE name = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()


def calc(expr):
    return eval(expr)
