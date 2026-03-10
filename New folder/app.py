from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

DATABASE = "database.db"

def get_shift(hour):
    """Determine shift based on hour"""
    if 6 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 18:
        return "Afternoon"
    else:
        return "Night"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        time TEXT,
        petrol_pump1 REAL,
        speed_petrol_pump2 REAL,
        diesel_pump1 REAL,
        speed_diesel_pump2 REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        description TEXT,
        amount REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cash_received (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        source TEXT,
        amount REAL
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS credits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        customer_name TEXT,
        fuel_type TEXT,
        litres REAL,
        amount REAL
    )
    """)
    
    cur.execute("""
CREATE TABLE IF NOT EXISTS meter (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,

    petrol_open REAL,
    petrol_close REAL,

    speed_petrol_open REAL,
    speed_petrol_close REAL,

    diesel_open REAL,
    diesel_close REAL,

    speed_diesel_open REAL,
    speed_diesel_close REAL,

    oil20_open INTEGER,
    oil20_sold INTEGER,

    oil40_open INTEGER,
    oil40_sold INTEGER
)
""")

    conn.commit()
    conn.close()


@app.route("/")
def dashboard():

    db = get_db()
    cur = db.cursor()
    
    # Ensure sales table exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        time TEXT,
        petrol_pump1 REAL,
        speed_petrol_pump2 REAL,
        diesel_pump1 REAL,
        speed_diesel_pump2 REAL
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        description TEXT,
        amount REAL
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cash_received (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        source TEXT,
        amount REAL
    )
    """)
    db.commit()

    cur.execute("""
    SELECT 
    SUM(petrol_pump1),
    SUM(speed_petrol_pump2),
    SUM(diesel_pump1),
    SUM(speed_diesel_pump2)
    FROM sales
    """)

    sales = cur.fetchone()

    cur.execute("SELECT SUM(amount) FROM expenses")
    expenses = cur.fetchone()[0]

    cur.execute("SELECT SUM(amount) FROM cash_received")
    cash = cur.fetchone()[0]

    return render_template(
        "dashboard.html",
        sales=sales,
        expenses=expenses,
        cash=cash
    )


@app.route("/sales", methods=["GET", "POST"])
def sales():

    if request.method == "POST":

        date = request.form["date"]
        time = request.form.get("time", datetime.now().strftime("%H:%M"))
        petrol = request.form["petrol"]
        speed_petrol = request.form["speed_petrol"]
        diesel = request.form["diesel"]
        speed_diesel = request.form["speed_diesel"]

        db = get_db()
        cur = db.cursor()

        cur.execute("""
        INSERT INTO sales (
        date,
        time,
        petrol_pump1,
        speed_petrol_pump2,
        diesel_pump1,
        speed_diesel_pump2
        )
        VALUES (?,?,?,?,?,?)
        """, (date, time, petrol, speed_petrol, diesel, speed_diesel))

        db.commit()

        return redirect("/")

    return render_template("sales.html")


@app.route("/expenses", methods=["GET", "POST"])
def expenses():

    if request.method == "POST":

        description = request.form["description"]
        amount = request.form["amount"]

        db = get_db()
        cur = db.cursor()

        cur.execute(
            "INSERT INTO expenses (date,description,amount) VALUES (date('now'),?,?)",
            (description, amount)
        )

        db.commit()

        return redirect("/")

    return render_template("expenses.html")


@app.route("/cash", methods=["GET", "POST"])
def cash():

    if request.method == "POST":

        source = request.form["source"]
        amount = request.form["amount"]

        db = get_db()
        cur = db.cursor()

        cur.execute(
            "INSERT INTO cash_received (date,source,amount) VALUES (date('now'),?,?)",
            (source, amount)
        )

        db.commit()

        return redirect("/")

    return render_template("cash.html")

@app.route("/delete_expense/<id>")
def delete_expense(id):

    db = get_db()

    db.execute("DELETE FROM expenses WHERE id=?", (id,))
    db.commit()

    return redirect("/expenses")


# CASH RECEIVED
# @app.route("/cash", methods=["GET","POST"])
# def cash():

#     conn = get_db()
#     cur = conn.cursor()

#     if request.method == "POST":

#         name = request.form["person_name"]
#         amount = request.form["amount"]

#         cur.execute(
#         "INSERT INTO cash_received(date,person_name,amount) VALUES(date('now'),?,?)",
#         (name,amount)
#         )

#         conn.commit()

#     cur.execute("SELECT * FROM cash_received ORDER BY id DESC")
#     data = cur.fetchall()

#     return render_template("cash.html",data=data)


# CREDIT
@app.route("/credit", methods=["GET","POST"])
def credit():

    conn = get_db()
    cur = conn.cursor()
    
    # Ensure credits table exists
    cur.execute("""
    CREATE TABLE IF NOT EXISTS credits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        customer_name TEXT,
        fuel_type TEXT,
        litres REAL,
        amount REAL
    )
    """)
    conn.commit()

    if request.method == "POST":

        name = request.form["customer"]
        fuel = request.form["fuel"]
        litres = request.form["litres"]
        amount = request.form["amount"]

        cur.execute(
        "INSERT INTO credits(date,customer_name,fuel_type,litres,amount) VALUES(date('now'),?,?,?,?)",
        (name,fuel,litres,amount)
        )

        conn.commit()

    cur.execute("SELECT * FROM credits ORDER BY id DESC")
    data = cur.fetchall()

    return render_template("credit.html",data=data)


# DAILY REPORT
@app.route("/daily_report")
def daily_report():

    conn = get_db()
    cur = conn.cursor()
    
    # Ensure tables exist with correct schema
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        description TEXT,
        amount REAL
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cash_received (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        source TEXT,
        amount REAL
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS credits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        customer_name TEXT,
        fuel_type TEXT,
        litres REAL,
        amount REAL
    )
    """)
    conn.commit()

    cur.execute("""
    SELECT 
    SUM(petrol_pump1),
    SUM(speed_petrol_pump2),
    SUM(diesel_pump1),
    SUM(speed_diesel_pump2)
    FROM sales
    WHERE date = date('now')
    """)

    sales = cur.fetchone()

    cur.execute("SELECT SUM(amount) FROM expenses WHERE date=date('now')")
    expenses = cur.fetchone()[0]

    cur.execute("SELECT SUM(amount) FROM cash_received WHERE date=date('now')")
    cash = cur.fetchone()[0]

    cur.execute("SELECT SUM(amount) FROM credits WHERE date=date('now')")
    credit = cur.fetchone()[0]

    return render_template("daily_report.html",
                           sales=sales,
                           expenses=expenses,
                           cash=cash,
                           credit=credit)

@app.route("/set_price", methods=["GET","POST"])
def set_price():

    db = get_db()
    cur = db.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS prices(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    petrol REAL,
    speed_petrol REAL,
    diesel REAL,
    speed_diesel REAL
    )
    """)

    if request.method == "POST":

        petrol = request.form["petrol"]
        speed_petrol = request.form["speed_petrol"]
        diesel = request.form["diesel"]
        speed_diesel = request.form["speed_diesel"]

        cur.execute("DELETE FROM prices")

        cur.execute(
        "INSERT INTO prices(petrol,speed_petrol,diesel,speed_diesel) VALUES (?,?,?,?)",
        (petrol,speed_petrol,diesel,speed_diesel)
        )

        db.commit()

    cur.execute("SELECT * FROM prices LIMIT 1")
    data = cur.fetchone()

    return render_template("set_price.html", data=data)
# MONTHLY REPORT
@app.route("/monthly_report")
def monthly_report():

    db = get_db()

    data = db.execute("""
    SELECT * FROM sales
    WHERE strftime('%m',date)=strftime('%m','now')
    """).fetchall()

    return render_template("monthly_report.html",data=data)


@app.route("/todays_sales")
def todays_sales():
    
    db = get_db()
    cur = db.cursor()
    
    # Get date filter from query params
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    selected_shift = request.args.get('shift', 'all')
    
    # Ensure tables exist
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        time TEXT,
        petrol_pump1 REAL,
        speed_petrol_pump2 REAL,
        diesel_pump1 REAL,
        speed_diesel_pump2 REAL
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        description TEXT,
        amount REAL
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS prices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        petrol REAL,
        speed_petrol REAL,
        diesel REAL,
        speed_diesel REAL
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS credits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        customer_name TEXT,
        fuel_type TEXT,
        litres REAL,
        amount REAL
    )
    """)
    db.commit()
    
    # Get today's prices
    cur.execute("SELECT * FROM prices LIMIT 1")
    prices = cur.fetchone()
    
    # Initialize shift data
    shift_data = {
        'Morning': {'sales': None, 'revenue': 0, 'expenses': 0, 'net_income': 0},
        'Afternoon': {'sales': None, 'revenue': 0, 'expenses': 0, 'net_income': 0},
        'Night': {'sales': None, 'revenue': 0, 'expenses': 0, 'net_income': 0}
    }
    
    total_revenue = 0
    total_expenses = 0
    total_net_income = 0
    
    # Get sales data for each shift
    for shift_name, hours in [('Morning', (6, 12)), ('Afternoon', (12, 18)), ('Night', (18, 24))]:
        start_hour = hours[0]
        end_hour = hours[1]
        
        # Get shift sales
        cur.execute(f"""
        SELECT 
        SUM(petrol_pump1) as petrol_pump1,
        SUM(speed_petrol_pump2) as speed_petrol_pump2,
        SUM(diesel_pump1) as diesel_pump1,
        SUM(speed_diesel_pump2) as speed_diesel_pump2
        FROM sales
        WHERE date = ? AND CAST(strftime('%H', time) AS INTEGER) >= ? AND CAST(strftime('%H', time) AS INTEGER) < ?
        """, (selected_date, start_hour, end_hour))
        
        sales = cur.fetchone()
        
        # Calculate revenue for shift
        revenue = 0
        if sales and prices:
            revenue += (sales['petrol_pump1'] or 0) * (prices['petrol'] or 0)
            revenue += (sales['speed_petrol_pump2'] or 0) * (prices['speed_petrol'] or 0)
            revenue += (sales['diesel_pump1'] or 0) * (prices['diesel'] or 0)
            revenue += (sales['speed_diesel_pump2'] or 0) * (prices['speed_diesel'] or 0)
        
        # Get shift expenses
        cur.execute(f"""
        SELECT SUM(amount) as total_expenses FROM expenses 
        WHERE date = ? AND CAST(strftime('%H', strftime('%Y-%m-%d %H:00:00', 'now')) AS INTEGER) >= ? 
        AND CAST(strftime('%H', strftime('%Y-%m-%d %H:00:00', 'now')) AS INTEGER) < ?
        """, (selected_date, start_hour, end_hour))
        
        expenses_result = cur.fetchone()
        expenses = expenses_result['total_expenses'] or 0
        
        net_income = revenue - expenses
        
        shift_data[shift_name] = {
            'sales': sales,
            'revenue': revenue,
            'expenses': expenses,
            'net_income': net_income
        }
        
        total_revenue += revenue
        total_expenses += expenses
        total_net_income += net_income
    
    # Get total day data
    cur.execute("""
    SELECT 
    SUM(petrol_pump1) as petrol_pump1,
    SUM(speed_petrol_pump2) as speed_petrol_pump2,
    SUM(diesel_pump1) as diesel_pump1,
    SUM(speed_diesel_pump2) as speed_diesel_pump2
    FROM sales
    WHERE date = ?
    """, (selected_date,))
    
    total_sales = cur.fetchone()
    
    # Get today's credit sales
    cur.execute("SELECT SUM(amount) as total_credit FROM credits WHERE date=?", (selected_date,))
    credit_result = cur.fetchone()
    credit_sales = credit_result['total_credit'] or 0
    
    return render_template("todays_sales.html",
                           selected_date=selected_date,
                           selected_shift=selected_shift,
                           shift_data=shift_data,
                           total_revenue=total_revenue,
                           total_expenses=total_expenses,
                           total_net_income=total_net_income,
                           total_sales=total_sales,
                           credit_sales=credit_sales,
                           prices=prices)



# @app.route("/set_price", methods=["GET","POST"])
# def set_price():

#     conn = get_db()
#     cur = conn.cursor()

#     if request.method == "POST":

#         petrol = request.form["petrol"]
#         speed_petrol = request.form["speed_petrol"]
#         diesel = request.form["diesel"]
#         speed_diesel = request.form["speed_diesel"]
#         oil20 = request.form["oil20"]
#         oil40 = request.form["oil40"]

#         cur.execute("DELETE FROM prices")

#         cur.execute(
#         "INSERT INTO prices(petrol,speed_petrol,diesel,speed_diesel,oil20,oil40) VALUES(?,?,?,?,?,?)",
#         (petrol,speed_petrol,diesel,speed_diesel,oil20,oil40)
#         )

#         conn.commit()

#     cur.execute("SELECT * FROM prices LIMIT 1")
#     data = cur.fetchone()

#     return render_template("set_price.html",data=data)
@app.route("/meter", methods=["GET","POST"])
def meter():

    db = get_db()
    cur = db.cursor()

    if request.method == "POST":

        pump = request.form["pump"]
        opening = request.form["opening"]
        closing = request.form["closing"]

        running = float(opening) - float(closing)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS meter(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pump TEXT,
        opening REAL,
        closing REAL,
        running REAL
        )
        """)

        cur.execute(
        "INSERT INTO meter(pump,opening,closing,running) VALUES (?,?,?,?)",
        (pump, opening, closing, running)
        )

        db.commit()

    cur.execute("SELECT * FROM meter")
    data = cur.fetchall()

    return render_template("meter.html", data=data)

@app.route("/transactions", methods=["GET","POST"])
def transactions():

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":

        type = request.form["type"]
        category = request.form["category"]
        amount = request.form["amount"]
        notes = request.form["notes"]

        cur.execute(
        "INSERT INTO transactions(type,category,amount,notes,date) VALUES (?,?,?,?,date('now'))",
        (type,category,amount,notes)
        )

        conn.commit()

    cur.execute("SELECT * FROM transactions ORDER BY id DESC")
    data = cur.fetchall()

    return render_template("transactions.html",data=data)



if __name__ == "__main__":
    init_db()
    app.run(debug=True)