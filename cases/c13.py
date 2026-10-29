import sqlite3


def get_user(conn, username):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
    return cursor.fetchall()


def calc(expr):
    import ast
    return ast.literal_eval(expr)
