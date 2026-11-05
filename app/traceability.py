
import os
import uuid
import qrcode

from app.database import get_connection


def generate_batch_id():
    unique_code = uuid.uuid4().hex[:8].upper()
    batch_id = "AGR-2026-" + unique_code
    return batch_id


def generate_qr_code(batch_id):
    os.makedirs("static/qrcodes", exist_ok=True)

    tracking_url = "http://localhost:5000/track/" + batch_id

    qr = qrcode.make(tracking_url)

    file_name = batch_id + ".png"
    file_path = os.path.join("static", "qrcodes", file_name)

    qr.save(file_path)

    return file_path


def add_tracking_update(batch_id, stage, location, notes=""):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT id FROM batches WHERE batch_id = ?",
        (batch_id,)
    )

    batch = cursor.fetchone()

    if batch is None:
        connection.close()
        return False

    cursor.execute("""
        INSERT INTO tracking_history
        (batch_id, stage, location, notes)
        VALUES (?, ?, ?, ?)
    """, (batch_id, stage, location, notes))

    cursor.execute("""
        UPDATE batches
        SET status = ?
        WHERE batch_id = ?
    """, (stage, batch_id))

    connection.commit()
    connection.close()

    return True


def get_batch_details(batch_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            batches.*,
            farmers.name AS farmer_name,
            farmers.village,
            produce.name AS produce_name,
            produce.category
        FROM batches
        JOIN farmers ON batches.farmer_id = farmers.id
        JOIN produce ON batches.produce_id = produce.id
        WHERE batches.batch_id = ?
    """, (batch_id,))

    batch = cursor.fetchone()
    connection.close()

    return batch


def get_tracking_history(batch_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM tracking_history
        WHERE batch_id = ?
        ORDER BY updated_at ASC, id ASC
    """, (batch_id,))

    history = cursor.fetchall()
    connection.close()

    return history
