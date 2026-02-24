from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
from datetime import datetime
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import styles
from reportlab.lib.units import inch

app = Flask(__name__)
DB_NAME = "petrol.db"


# ---------------------- DATABASE ----------------------

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS fuel_price(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fuel_type TEXT,
        price REAL,
        effective_date TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS sales(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shift TEXT,
        fuel_type TEXT,
        quantity REAL,
        price_per_litre REAL,
        amount REAL,
        payment_mode TEXT,
        sale_date TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS credit(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        amount REAL,
        status TEXT,
        date TEXT,
        settled_date TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------------- DASHBOARD ----------------------

@app.route("/")
def dashboard():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()

    revenue = conn.execute(
        "SELECT SUM(amount) as total FROM sales WHERE sale_date=?",
        (today,)
    ).fetchone()["total"] or 0

    pending = conn.execute(
        "SELECT SUM(amount) as total FROM credit WHERE status='Pending'"
    ).fetchone()["total"] or 0

    shift_data = conn.execute("""
        SELECT shift, SUM(amount) as total
        FROM sales
        WHERE sale_date=?
        GROUP BY shift
    """, (today,)).fetchall()

    conn.close()

    return render_template("dashboard.html",
                           today=today,
                           revenue=revenue,
                           pending=pending,
                           shift_data=shift_data)


# ---------------------- ADD SALE ----------------------

@app.route("/add_sale", methods=["GET", "POST"])
def add_sale():
    if request.method == "POST":
        shift = request.form["shift"]
        fuel_type = request.form["fuel_type"]
        quantity = float(request.form["quantity"])
        payment_mode = request.form["payment_mode"]
        today = datetime.now().strftime("%Y-%m-%d")

        conn = get_db()

        price_row = conn.execute("""
            SELECT price FROM fuel_price
            WHERE fuel_type=?
            ORDER BY id DESC LIMIT 1
        """, (fuel_type,)).fetchone()

        if not price_row:
            conn.close()
            return "Please set fuel price first!"

        price = price_row["price"]
        amount = quantity * price

        conn.execute("""
            INSERT INTO sales(shift,fuel_type,quantity,price_per_litre,amount,payment_mode,sale_date)
            VALUES(?,?,?,?,?,?,?)
        """, (shift, fuel_type, quantity, price, amount, payment_mode, today))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("add_sale.html")


# ---------------------- ADD CREDIT ----------------------

@app.route("/add_credit", methods=["GET", "POST"])
def add_credit():
    if request.method == "POST":
        name = request.form["name"]
        amount = float(request.form["amount"])
        today = datetime.now().strftime("%Y-%m-%d")

        conn = get_db()
        conn.execute("""
            INSERT INTO credit(name,amount,status,date)
            VALUES(?,?,?,?)
        """, (name, amount, "Pending", today))

        conn.commit()
        conn.close()

        return redirect(url_for("credit_list"))

    return render_template("add_credit.html")


@app.route("/credit")
def credit_list():
    conn = get_db()
    data = conn.execute("SELECT * FROM credit").fetchall()
    conn.close()
    return render_template("credit.html", data=data)


# ---------------------- SETTLE CREDIT + PDF ----------------------

@app.route("/settle/<int:id>")
def settle(id):
    conn = get_db()
    credit = conn.execute("SELECT * FROM credit WHERE id=?", (id,)).fetchone()

    today = datetime.now().strftime("%Y-%m-%d")

    conn.execute("""
        UPDATE credit SET status='Settled', settled_date=?
        WHERE id=?
    """, (today, id))

    conn.commit()
    conn.close()

    filename = f"credit_receipt_{id}.pdf"
    doc = SimpleDocTemplate(filename)
    elements = []

    style = styles.getSampleStyleSheet()["Normal"]

    elements.append(Paragraph("Credit Settlement Receipt", style))
    elements.append(Spacer(1, 0.3 * inch))

    data = [
        ["Customer Name", credit["name"]],
        ["Amount Paid", f"₹ {credit['amount']}"],
        ["Settled Date", today]
    ]

    table = Table(data)
    table.setStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    elements.append(table)
    doc.build(elements)

    return send_file(filename, as_attachment=True)


# ---------------------- DAILY REPORT ----------------------

@app.route("/daily_report")
def daily_report():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()

    sales = conn.execute("""
        SELECT * FROM sales WHERE sale_date=?
    """, (today,)).fetchall()

    total = conn.execute("""
        SELECT SUM(amount) as total FROM sales WHERE sale_date=?
    """, (today,)).fetchone()["total"] or 0

    conn.close()

    return render_template("daily_report.html",
                           sales=sales,
                           total=total,
                           today=today)


@app.route("/download_daily")
def download_daily():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()

    sales = conn.execute("""
        SELECT shift,fuel_type,quantity,amount FROM sales
        WHERE sale_date=?
    """, (today,)).fetchall()

    total = conn.execute("""
        SELECT SUM(amount) as total FROM sales WHERE sale_date=?
    """, (today,)).fetchone()["total"] or 0

    conn.close()

    filename = "daily_report.pdf"
    doc = SimpleDocTemplate(filename)
    elements = []

    style = styles.getSampleStyleSheet()["Normal"]
    elements.append(Paragraph(f"Daily Report - {today}", style))
    elements.append(Spacer(1, 0.3 * inch))

    table_data = [["Shift", "Fuel", "Litres", "Amount"]]

    for s in sales:
        table_data.append([
            s["shift"],
            s["fuel_type"],
            s["quantity"],
            s["amount"]
        ])

    table_data.append(["", "", "Total", total])

    table = Table(table_data)
    table.setStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    elements.append(table)
    doc.build(elements)

    return send_file(filename, as_attachment=True)


# ---------------------- MONTHLY REPORT ----------------------

@app.route("/monthly_report")
def monthly_report():
    month = datetime.now().strftime("%Y-%m")
    conn = get_db()

    sales = conn.execute("""
        SELECT * FROM sales
        WHERE sale_date LIKE ?
    """, (month + "%",)).fetchall()

    total = conn.execute("""
        SELECT SUM(amount) as total FROM sales
        WHERE sale_date LIKE ?
    """, (month + "%",)).fetchone()["total"] or 0

    conn.close()

    return render_template("monthly_report.html",
                           sales=sales,
                           total=total,
                           month=month)


@app.route("/download_monthly")
def download_monthly():
    month = datetime.now().strftime("%Y-%m")
    conn = get_db()

    sales = conn.execute("""
        SELECT sale_date,shift,fuel_type,quantity,amount FROM sales
        WHERE sale_date LIKE ?
    """, (month + "%",)).fetchall()

    total = conn.execute("""
        SELECT SUM(amount) as total FROM sales
        WHERE sale_date LIKE ?
    """, (month + "%",)).fetchone()["total"] or 0

    conn.close()

    filename = "monthly_report.pdf"
    doc = SimpleDocTemplate(filename)
    elements = []

    style = styles.getSampleStyleSheet()["Normal"]
    elements.append(Paragraph(f"Monthly Report - {month}", style))
    elements.append(Spacer(1, 0.3 * inch))

    table_data = [["Date", "Shift", "Fuel", "Litres", "Amount"]]

    for s in sales:
        table_data.append([
            s["sale_date"],
            s["shift"],
            s["fuel_type"],
            s["quantity"],
            s["amount"]
        ])

    table_data.append(["", "", "", "Total", total])

    table = Table(table_data)
    table.setStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    elements.append(table)
    doc.build(elements)

    return send_file(filename, as_attachment=True)


# ---------------------- SET PRICE ----------------------

@app.route("/set_price", methods=["GET", "POST"])
def set_price():
    if request.method == "POST":
        today = datetime.now().strftime("%Y-%m-%d")
        conn = get_db()

        fuels = {
            "Petrol": request.form["petrol"],
            "Speed Petrol": request.form["speed_petrol"],
            "Diesel": request.form["diesel"],
            "Speed Diesel": request.form["speed_diesel"]
        }

        for fuel, price in fuels.items():
            if price.strip() != "":
                conn.execute("""
                    INSERT INTO fuel_price(fuel_type,price,effective_date)
                    VALUES(?,?,?)
                """, (fuel, float(price), today))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("set_price.html")


# ----------------------

if __name__ == "__main__":
    app.run(debug=True)