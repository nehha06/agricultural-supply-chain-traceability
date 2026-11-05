
import sqlite3
import os

DATABASE = os.path.join("instance", "agricultural.db")


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    os.makedirs("instance", exist_ok=True)

    connection = get_connection()
    cursor = connection.cursor()

    # Administrator table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Farmer table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            village TEXT NOT NULL
        )
    """)

    # Produce table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produce (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)

    # Produce batch table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT UNIQUE NOT NULL,
            farmer_id INTEGER NOT NULL,
            produce_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            harvest_date TEXT NOT NULL,
            quality TEXT NOT NULL,
            qr_code TEXT,
            status TEXT DEFAULT 'Harvested',
            FOREIGN KEY (farmer_id) REFERENCES farmers(id),
            FOREIGN KEY (produce_id) REFERENCES produce(id)
        )
    """)

    # Supply chain tracking history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracking_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            location TEXT NOT NULL,
            notes TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
        )
    """)

    # Create default administrator if not present
    cursor.execute(
        "SELECT * FROM admins WHERE username = ?",
        ("admin",)
    )

    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            ("admin", "admin123")
        )

    connection.commit()
    connection.close()

    print("Database initialized successfully!")


if __name__ == "__main__":
    initialize_database()
