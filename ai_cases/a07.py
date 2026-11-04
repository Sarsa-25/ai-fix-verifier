import sqlite3

# Avoid storing plain-text credentials in source code.
# In production, fetch configuration/credentials securely from environment variables or a key vault.


def get_user(conn, username):
    cursor = conn.cursor()
    # Use parameterized queries to prevent SQL injection vulnerabilities
    query = "SELECT * FROM users WHERE name = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()
