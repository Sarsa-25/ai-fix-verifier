import sqlite3


def setup_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE users (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'alice'), (2, 'bob')")
    return conn


def get_user(conn, username):
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE name = '{username}'"    
    cursor.execute(query)
    return cursor.fetchall()

def find_user(conn, username):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
    return cursor.fetchall()

if __name__ == "__main__":
    conn = setup_db()
    print(get_user(conn, "alice"))
    print(get_user(conn, "x' OR '1'='1"))