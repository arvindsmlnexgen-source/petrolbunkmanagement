from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
from datetime import datetime
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import TableStyle
from reportlab.lib import colors

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_NAME = os.path.join(BASE_DIR, "petrol.db")


# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS fuel_price(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fuel_type TEXT,
        price REAL,
        effective_date TEXT
    )
    """)

    cur.execute("""
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS credit(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        amount REAL,
        sale_date TEXT,
        status TEXT DEFAULT 'Pending',
        settled_date TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()

    revenue = conn.execute(
        "SELECT IFNULL(SUM(amount),0) FROM sales WHERE sale_date=?",
        (today,)
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT IFNULL(SUM(amount),0) FROM credit WHERE status='Pending'"
    ).fetchone()[0]

    shift_data = conn.execute(
        "SELECT shift, IFNULL(SUM(amount),0) as total FROM sales WHERE sale_date=? GROUP BY shift",
        (today,)
    ).fetchall()

    conn.close()

    return render_template("dashboard.html",
                           revenue=revenue,
                           pending=pending,
                           shift_data=shift_data,
                           today=today)


# ---------------- SET PRICE ----------------
@app.route("/set_price", methods=["GET", "POST"])
def set_price():
    if request.method == "POST":
        fuel = request.form["fuel_type"]
        price = float(request.form["price"])
        today = datetime.now().strftime("%Y-%m-%d")

        conn = get_db()
        conn.execute(
            "INSERT INTO fuel_price(fuel_type,price,effective_date) VALUES(?,?,?)",
            (fuel, price, today)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("set_price.html")


# ---------------- ADD SALE ----------------
@app.route("/add_sale", methods=["GET", "POST"])
def add_sale():
    if request.method == "POST":
        shift = request.form["shift"]
        fuel = request.form["fuel_type"]
        qty = float(request.form["quantity"])
        payment = request.form["payment_mode"]
        today = datetime.now().strftime("%Y-%m-%d")

        conn = get_db()

        price_row = conn.execute(
            "SELECT price FROM fuel_price WHERE fuel_type=? ORDER BY effective_date DESC LIMIT 1",
            (fuel,)
        ).fetchone()

        if not price_row:
            return "Please set fuel price first."

        price = price_row["price"]
        amount = qty * price

        conn.execute("""
            INSERT INTO sales(shift,fuel_type,quantity,price_per_litre,amount,payment_mode,sale_date)
            VALUES(?,?,?,?,?,?,?)
        """, (shift, fuel, qty, price, amount, payment, today))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("add_sale.html")


# ---------------- CREDIT ----------------
@app.route("/add_credit", methods=["GET", "POST"])
def add_credit():
    if request.method == "POST":
        name = request.form["name"]
        amount = float(request.form["amount"])
        today = datetime.now().strftime("%Y-%m-%d")

        conn = get_db()
        conn.execute(
            "INSERT INTO credit(name,amount,sale_date) VALUES(?,?,?)",
            (name, amount, today)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("credit"))

    return render_template("add_credit.html")


@app.route("/credit")
def credit():
    conn = get_db()
    data = conn.execute("SELECT * FROM credit ORDER BY sale_date DESC").fetchall()
    conn.close()
    return render_template("credit.html", data=data)


@app.route("/settle/<int:id>")
def settle(id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()

    credit = conn.execute("SELECT * FROM credit WHERE id=?", (id,)).fetchone()

    conn.execute(
        "UPDATE credit SET status='Settled', settled_date=? WHERE id=?",
        (today, id)
    )
    conn.commit()
    conn.close()

    # PDF generation
    file_path = os.path.join(BASE_DIR, f"credit_receipt_{id}.pdf")
    doc = SimpleDocTemplate(file_path)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Credit Settlement Receipt", styles["Title"]))
    elements.append(Spacer(1, 20))

    data = [
        ["Customer", credit["name"]],
        ["Amount Paid", str(credit["amount"])],
        ["Original Date", credit["sale_date"]],
        ["Settled Date", today]
    ]

    table = Table(data)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    doc.build(elements)

    return send_file(file_path, as_attachment=True)


# ---------------- DAILY REPORT ----------------
@app.route("/daily_report")
def daily_report():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()

    sales = conn.execute(
        "SELECT * FROM sales WHERE sale_date=?",
        (today,)
    ).fetchall()

    total = conn.execute(
        "SELECT IFNULL(SUM(amount),0) FROM sales WHERE sale_date=?",
        (today,)
    ).fetchone()[0]

    conn.close()

    return render_template("daily_report.html",
                           sales=sales,
                           total=total,
                           today=today)


@app.route("/download_daily")
def download_daily():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()

    sales = conn.execute(
        "SELECT * FROM sales WHERE sale_date=?",
        (today,)
    ).fetchall()

    total = conn.execute(
        "SELECT IFNULL(SUM(amount),0) FROM sales WHERE sale_date=?",
        (today,)
    ).fetchone()[0]

    conn.close()

    file_path = os.path.join(BASE_DIR, f"daily_report_{today}.pdf")
    doc = SimpleDocTemplate(file_path)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Daily Report - {today}", styles["Title"]))
    elements.append(Spacer(1, 20))

    table_data = [["Shift", "Fuel", "Litres", "Price", "Amount", "Payment"]]

    for s in sales:
        table_data.append([
            s["shift"],
            s["fuel_type"],
            s["quantity"],
            s["price_per_litre"],
            s["amount"],
            s["payment_mode"]
        ])

    table_data.append(["", "", "", "Total", total, ""])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    doc.build(elements)

    return send_file(file_path, as_attachment=True)


# ---------------- MONTHLY REPORT ----------------
@app.route("/monthly_report")
def monthly_report():
    month = datetime.now().strftime("%Y-%m")
    conn = get_db()

    sales = conn.execute(
        "SELECT * FROM sales WHERE substr(sale_date,1,7)=?",
        (month,)
    ).fetchall()

    total = conn.execute(
        "SELECT IFNULL(SUM(amount),0) FROM sales WHERE substr(sale_date,1,7)=?",
        (month,)
    ).fetchone()[0]

    conn.close()

    return render_template("monthly_report.html",
                           sales=sales,
                           total=total,
                           month=month)


@app.route("/download_monthly")
def download_monthly():
    month = datetime.now().strftime("%Y-%m")
    conn = get_db()

    sales = conn.execute(
        "SELECT * FROM sales WHERE substr(sale_date,1,7)=?",
        (month,)
    ).fetchall()

    total = conn.execute(
        "SELECT IFNULL(SUM(amount),0) FROM sales WHERE substr(sale_date,1,7)=?",
        (month,)
    ).fetchone()[0]

    conn.close()

    file_path = os.path.join(BASE_DIR, f"monthly_report_{month}.pdf")
    doc = SimpleDocTemplate(file_path)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Monthly Report - {month}", styles["Title"]))
    elements.append(Spacer(1, 20))

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
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    doc.build(elements)

    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)