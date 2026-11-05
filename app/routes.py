
import os
import sqlite3

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash, jsonify
)

from werkzeug.security import (
    check_password_hash, generate_password_hash
)

from app.database import get_connection
from app.traceability import (
    generate_batch_id,
    generate_qr_code,
    add_tracking_update,
    get_batch_details,
    get_tracking_history
)

main = Blueprint("main", __name__)


# ---------------- LOGIN ----------------

@main.route("/", methods=["GET", "POST"])
@main.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM admins WHERE username = ?",
            (username,)
        )

        admin = cursor.fetchone()

        if admin:
            stored_password = admin["password"]

            # Support existing development account and hashed passwords
            valid = False

            try:
                valid = check_password_hash(stored_password, password)
            except (ValueError, TypeError):
                valid = False

            if not valid and stored_password == password:
                valid = True

                # Upgrade old plain-text password to a hash
                cursor.execute(
                    "UPDATE admins SET password = ? WHERE id = ?",
                    (generate_password_hash(password), admin["id"])
                )
                connection.commit()

            if valid:
                session["admin"] = username
                connection.close()
                return redirect(url_for("main.dashboard"))

        connection.close()
        flash("Invalid username or password.")

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@main.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("main.login"))


# ---------------- DASHBOARD ----------------

@main.route("/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect(url_for("main.login"))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM farmers")
    farmer_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM produce")
    produce_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM batches")
    batch_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM batches"
    )
    total_quantity = cursor.fetchone()[0]

    cursor.execute("""
        SELECT batches.*, farmers.name AS farmer_name,
               produce.name AS produce_name
        FROM batches
        JOIN farmers ON batches.farmer_id = farmers.id
        JOIN produce ON batches.produce_id = produce.id
        ORDER BY batches.id DESC
        LIMIT 5
    """)

    recent_batches = cursor.fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        farmer_count=farmer_count,
        produce_count=produce_count,
        batch_count=batch_count,
        total_quantity=total_quantity,
        recent_batches=recent_batches
    )


# ---------------- FARMER MANAGEMENT ----------------

@main.route("/farmers", methods=["GET", "POST"])
def farmers():

    if "admin" not in session:
        return redirect(url_for("main.login"))

    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        village = request.form.get("village", "").strip()

        if name and phone and village:
            cursor.execute("""
                INSERT INTO farmers (name, phone, village)
                VALUES (?, ?, ?)
            """, (name, phone, village))

            connection.commit()
            flash("Farmer registered successfully!")
        else:
            flash("Please fill in all farmer details.")

    cursor.execute("SELECT * FROM farmers ORDER BY id DESC")
    farmer_list = cursor.fetchall()

    connection.close()

    return render_template(
        "farmers.html",
        farmers=farmer_list
    )


# ---------------- PRODUCE MANAGEMENT ----------------

@main.route("/produce", methods=["GET", "POST"])
def produce():

    if "admin" not in session:
        return redirect(url_for("main.login"))

    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()

        if name and category:
            cursor.execute("""
                INSERT INTO produce (name, category)
                VALUES (?, ?)
            """, (name, category))

            connection.commit()
            flash("Produce added successfully!")
        else:
            flash("Please enter the produce name and category.")

    cursor.execute("SELECT * FROM produce ORDER BY id DESC")
    produce_list = cursor.fetchall()

    connection.close()

    return render_template(
        "produce.html",
        produce=produce_list
    )


# ---------------- BATCH MANAGEMENT ----------------

@main.route("/batches", methods=["GET", "POST"])
def batches():

    if "admin" not in session:
        return redirect(url_for("main.login"))

    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":

        farmer_id = request.form.get("farmer_id")
        produce_id = request.form.get("produce_id")
        quantity = request.form.get("quantity")
        harvest_date = request.form.get("harvest_date")
        quality = request.form.get("quality", "").strip()

        try:
            quantity = float(quantity)

            if quantity <= 0:
                raise ValueError

            if not all([
                farmer_id, produce_id,
                harvest_date, quality
            ]):
                raise ValueError

            batch_id = generate_batch_id()

            qr_path = generate_qr_code(batch_id)

            cursor.execute("""
                INSERT INTO batches
                (batch_id, farmer_id, produce_id,
                 quantity, harvest_date, quality, qr_code)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id, farmer_id, produce_id,
                quantity, harvest_date, quality, qr_path
            ))

            connection.commit()

            connection.close()

            add_tracking_update(
                batch_id,
                "Harvested",
                "Farm",
                "Produce batch registered."
            )

            flash("Batch created successfully! ID: " + batch_id)

            return redirect(url_for("main.batches"))

        except (ValueError, TypeError):
            flash("Please enter valid batch information.")

        except sqlite3.IntegrityError:
            connection.rollback()
            flash("Invalid farmer or produce selection.")

    cursor.execute("""
        SELECT batches.*, farmers.name AS farmer_name,
               produce.name AS produce_name
        FROM batches
        JOIN farmers ON batches.farmer_id = farmers.id
        JOIN produce ON batches.produce_id = produce.id
        ORDER BY batches.id DESC
    """)

    batch_list = cursor.fetchall()

    cursor.execute("SELECT * FROM farmers ORDER BY name")
    farmer_list = cursor.fetchall()

    cursor.execute("SELECT * FROM produce ORDER BY name")
    produce_list = cursor.fetchall()

    connection.close()

    return render_template(
        "batches.html",
        batches=batch_list,
        farmers=farmer_list,
        produce=produce_list
    )


# ---------------- UPDATE SUPPLY CHAIN ----------------

@main.route("/batches/<batch_id>/update", methods=["POST"])
def update_batch(batch_id):

    if "admin" not in session:
        return redirect(url_for("main.login"))

    stage = request.form.get("stage", "").strip()
    location = request.form.get("location", "").strip()
    notes = request.form.get("notes", "").strip()

    allowed_stages = [
        "Harvested",
        "Processing",
        "Stored",
        "Dispatched",
        "Delivered"
    ]

    if stage not in allowed_stages or not location:
        flash("Please enter a valid stage and location.")
        return redirect(url_for("main.batches"))

    success = add_tracking_update(
        batch_id, stage, location, notes
    )

    if success:
        flash("Supply chain status updated successfully!")
    else:
        flash("Batch not found.")

    return redirect(url_for("main.batches"))


# ---------------- PUBLIC BATCH TRACKING ----------------

@main.route("/track/<batch_id>")
def track_batch(batch_id):

    batch = get_batch_details(batch_id)

    if batch is None:
        return "Batch not found.", 404

    history = get_tracking_history(batch_id)

    return render_template(
        "tracking.html",
        batch=batch,
        history=history
    )


# ---------------- BATCH API ----------------

@main.route("/api/batches/<batch_id>")
def batch_api(batch_id):

    batch = get_batch_details(batch_id)

    if batch is None:
        return jsonify({"error": "Batch not found"}), 404

    history = get_tracking_history(batch_id)

    return jsonify({
        "batch_id": batch["batch_id"],
        "produce": batch["produce_name"],
        "farmer": batch["farmer_name"],
        "village": batch["village"],
        "quantity": batch["quantity"],
        "harvest_date": batch["harvest_date"],
        "quality": batch["quality"],
        "status": batch["status"],
        "tracking_history": [
            {
                "stage": item["stage"],
                "location": item["location"],
                "notes": item["notes"],
                "updated_at": item["updated_at"]
            }
            for item in history
        ]
    })
