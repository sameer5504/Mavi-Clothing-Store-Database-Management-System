from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from datetime import date
import calendar
import json

app = Flask(__name__)
app.secret_key = "mavi_secret_key"

def admin_only():
    return session.get("role") != "admin"

# ---------- Database Connection ----------

db = mysql.connector.connect( host="localhost", user="root", password="Andromida@00",database="maviii")

# ---------- Home ----------
@app.route("/")
def home():
    return redirect(url_for("login"))

# ---------- Login ----------
@app.route("/login",methods=["GET","POST"])
def login():
    cursor = db.cursor(dictionary=True)
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        login_type = request.form["login_type"]

        cursor.execute(
            """         
            SELECT Employee_ID, Role
            FROM Employee
            WHERE Username = %s AND Password = %s
        """, (username, password))

        employee = cursor.fetchone()
        cursor.close()

        if not employee:
            return render_template("login.html", error="Invalid username or password")
        if employee["Role"] != login_type:
            return render_template(
                "login.html",
                error="Access denied: you are not authorized to login as " + login_type
            )
        session["employee_id"] = employee["Employee_ID"]
        session["role"] = employee["Role"]
        return redirect(
            url_for("admin_dashboard") if employee["Role"] == "admin"
            else url_for("user_dashboard")
        )
    return render_template("login.html")

# ---------- Logout ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------- Admin Dashboard ----------
@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")

# ---------- User Dashboard ----------
@app.route("/user")
def user_dashboard():
    if session.get("role") != "user":
        return redirect(url_for("login"))
    return render_template("user_dashboard.html")

# ----------------- View Products -----------------
@app.route("/products")
def view_products():
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
                   SELECT p.Product_ID,
                          p.Product_Name,
                          p.Size,
                          p.Category,
                          p.Default_Sale_Price,
                          p.Reorder_Level,
                          CASE
                              WHEN si.Quantity_Available IS NULL THEN 0
                              ELSE si.Quantity_Available
                              END AS Store_Quantity,
                          CASE
                              WHEN wi.Quantity_Available IS NULL THEN 0
                              ELSE wi.Quantity_Available
                              END AS Warehouse_Quantity
                   FROM Product p
                            LEFT JOIN Inventory si
                                      ON p.Product_ID = si.Product_ID
                                          AND si.Store_ID = 1
                            LEFT JOIN Inventory wi
                                      ON p.Product_ID = wi.Product_ID
                                          AND wi.Warehouse_ID = 1
                   ORDER BY p.Product_Name, p.Size
                   """)

    products = cursor.fetchall()
    cursor.close()
    return render_template("view_products.html", products=products)

# ---------- View Sales ----------
@app.route("/view_sales")
def view_sales():
    if "role" not in session:
        return redirect(url_for("login"))
    cursor = db.cursor(dictionary=True)
    employee_id = session.get("employee_id")
    role = session.get("role")

    if role == "user":

    #-------------------user sales query---------------
        cursor.execute("""
            SELECT
                s.Sale_ID,
                s.Sale_Date,
                c.First_Name AS Customer_First_Name,
                c.Last_Name  AS Customer_Last_Name,
                e.First_Name AS Employee_First_Name,
                e.Last_Name  AS Employee_Last_Name,
                SUM(sd.Quantity * sd.Unit_Price) AS Sale_Subtotal,
                s.Sale_Payment_Method,
                COUNT(sd.SaleDetails_ID) AS Total_Items
            FROM Sale s
            JOIN Customer c ON s.Customer_ID = c.Customer_ID
            JOIN Employee e ON s.Employee_ID = e.Employee_ID
            JOIN Store st ON s.Store_ID = st.Store_ID
            JOIN Sale_Details sd ON s.Sale_ID = sd.Sale_ID
            WHERE s.Employee_ID = %s
            GROUP BY
                s.Sale_ID,
                s.Sale_Date,
                c.First_Name,
                c.Last_Name,
                e.First_Name,
                e.Last_Name,
                st.Store_Name,
                s.Sale_Payment_Method
            ORDER BY s.Sale_Date DESC
        """, (employee_id,))

    else:
        #------------------admin sales query (views all sales by all users) -----------------------------
        cursor.execute("""
            SELECT
                s.Sale_ID,
                s.Sale_Date,
                c.First_Name AS Customer_First_Name,
                c.Last_Name  AS Customer_Last_Name,
                e.First_Name AS Employee_First_Name,
                e.Last_Name  AS Employee_Last_Name,
                st.Store_Name,
                SUM(sd.Quantity * sd.Unit_Price) AS Sale_Subtotal,
                s.Sale_Payment_Method,
                COUNT(sd.SaleDetails_ID) AS Total_Items
            FROM Sale s
            JOIN Customer c ON s.Customer_ID = c.Customer_ID
            JOIN Employee e ON s.Employee_ID = e.Employee_ID
            JOIN Store st ON s.Store_ID = st.Store_ID
            JOIN Sale_Details sd ON s.Sale_ID = sd.Sale_ID
            GROUP BY
                s.Sale_ID,
                s.Sale_Date,
                c.First_Name,
                c.Last_Name,
                e.First_Name,
                e.Last_Name,
                st.Store_Name,
                s.Sale_Payment_Method
            ORDER BY s.Sale_Date DESC
        """)

    sales = cursor.fetchall()
    for sale in sales:
        sale["Customer_Name"] = f"{sale['Customer_First_Name']} {sale['Customer_Last_Name']}"
        sale["Employee_Name"] = f"{sale['Employee_First_Name']} {sale['Employee_Last_Name']}"

# ------------------- Sale details -------------------


    sale_ids = [s["Sale_ID"] for s in sales]
    sale_details = {}

    if sale_ids:
        placeholders = ",".join(["%s"] * len(sale_ids))

        cursor.execute(f"""
            SELECT
                sd.SaleDetails_ID,
                sd.Sale_ID,
                sd.Product_ID,
                p.Product_Name,
                p.Size,
                sd.Quantity,
                sd.Unit_Price,
                (sd.Quantity * sd.Unit_Price) AS Line_Total
            FROM Sale_Details sd
            JOIN Product p ON sd.Product_ID = p.Product_ID
            WHERE sd.Sale_ID IN ({placeholders})
            ORDER BY sd.Sale_ID, p.Product_Name, p.Size
        """, sale_ids)

        details = cursor.fetchall()
        for d in details:
            sale_details.setdefault(d["Sale_ID"], []).append(d)

    cursor.close()
    return render_template(
        "view_sales.html",
        sales=sales,
        sale_details=sale_details
    )

# ----------------- Create Sale -----------------
@app.route("/create_sale", methods=["GET", "POST"])
def create_sale():
    if "employee_id" not in session:
        return redirect(url_for("login"))

    STORE_ID = 1
    cursor = db.cursor(dictionary=True)
    try:
        if request.method == "GET":

            cursor.execute("""
                SELECT
                    p.Product_ID,
                    p.Product_Name,
                    p.Size,
                    p.Default_Sale_Price,
                    i.Quantity_Available
                FROM Product p
                JOIN Inventory i ON p.Product_ID = i.Product_ID
                WHERE i.Store_ID = %s
                  AND i.Quantity_Available > 0
                ORDER BY p.Product_Name, p.Size
            """, (STORE_ID,))

            products = cursor.fetchall()
            return render_template("create_sale.html", products=products)

        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        phone = request.form["customer_number"].strip()
        payment_method = request.form["payment_method"]
        product_ids = request.form.getlist("product_id[]")
        quantities = request.form.getlist("quantity[]")
        sale_date = request.form["sale_date"]
        if not product_ids:
            return "No products selected", 400


    # ---------- Customer ----------

        cursor.execute(
            "SELECT Customer_ID FROM Customer WHERE Phone=%s",
            (phone,)
        )
        customer = cursor.fetchone()

        if customer:
            customer_id = customer["Customer_ID"]
            cursor.execute("""
                UPDATE Customer
                SET First_Name=%s, Last_Name=%s
                WHERE Customer_ID=%s
            """, (first_name, last_name, customer_id))
        else:
            cursor.execute("""
                INSERT INTO Customer (First_Name, Last_Name, Phone)
                VALUES (%s, %s, %s)
            """, (first_name, last_name, phone))
            customer_id = cursor.lastrowid

        # ---------- Validate stock ----------
        for pid, qty in zip(product_ids, quantities):
            cursor.execute("""
                SELECT Quantity_Available
                FROM Inventory
                WHERE Product_ID=%s AND Store_ID=%s
            """, (pid, STORE_ID))
            row = cursor.fetchone()

            if not row or int(qty) > row["Quantity_Available"]:
                raise Exception("Insufficient stock")

    # ---------- Insert Sale ----------


        cursor.execute("""
                       INSERT INTO Sale
                           (Customer_ID, Employee_ID, Store_ID, Sale_Date, Sale_Payment_Method)
                       VALUES (%s, %s, %s, %s, %s)
                       """, (
                           customer_id,
                           session["employee_id"],
                           STORE_ID,
                           sale_date,
                           payment_method
                       ))

        sale_id = cursor.lastrowid

    # ---------- Sale details + stock update ----------
        
        for pid, qty in zip(product_ids, quantities):
            cursor.execute("""
                SELECT Default_Sale_Price
                FROM Product
                WHERE Product_ID=%s
            """, (pid,))
            price = cursor.fetchone()["Default_Sale_Price"]

            cursor.execute("""
                INSERT INTO Sale_Details
                (Sale_ID, Product_ID, Quantity, Unit_Price)
                VALUES (%s, %s, %s, %s)
            """, (sale_id, pid, qty, price))

            cursor.execute("""
                UPDATE Inventory
                SET Quantity_Available = Quantity_Available - %s
                WHERE Product_ID=%s AND Store_ID=%s
            """, (qty, pid, STORE_ID))

        db.commit()
        return redirect(url_for("view_sales"))

    except Exception as e:
        db.rollback()
        return str(e), 400

    finally:
        cursor.close()

#-------------------view employees (admin only)-------------------
@app.route("/employees")
def manage_employees():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT Employee_ID, First_Name, Last_Name, Username, Role
        FROM Employee
    """)
    employees = cursor.fetchall()
    cursor.close()
    return render_template("manage_employee.html", employees=employees)

#-----------------------add employees(admin only)--------------------------------
@app.route("/add_employee", methods=["GET", "POST"])
def add_employee():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    if request.method == "POST":
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO Employee
            (First_Name, Last_Name, Username, Password, Role, Store_ID)
            VALUES (%s, %s, %s, %s, %s, 1)
        """, (
            request.form["first_name"],
            request.form["last_name"],
            request.form["username"],
            request.form["password"],
            request.form["role"]
        ))
        db.commit()
        cursor.close()
        return redirect(url_for("manage_employees"))
    return render_template("add_employee.html")

#-------------------------edit employee (admin) ---------------------------

@app.route("/edit_employee/<int:employee_id>", methods=["GET", "POST"])
def edit_employee(employee_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    cursor = db.cursor(dictionary=True)
    if request.method == "POST":
        cursor.execute("""
            UPDATE Employee
            SET First_Name = %s,
                Last_Name = %s,
                Username = %s,
                Role = %s
            WHERE Employee_ID = %s
        """, (
            request.form["first_name"],
            request.form["last_name"],
            request.form["username"],
            request.form["role"],
            employee_id
        ))
        db.commit()
        cursor.close()
        return redirect(url_for("manage_employees"))
    cursor.execute("""
        SELECT Employee_ID, First_Name, Last_Name, Username, Role
        FROM Employee
        WHERE Employee_ID = %s
    """, (employee_id,))

    employee = cursor.fetchone()
    cursor.close()
    if not employee:
        return "Employee not found", 404

    return render_template("edit_employee.html", employee=employee)

#-----------------delete employee (Admin)--------------------------
@app.route("/delete_employee/<int:employee_id>")
def delete_employee(employee_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if employee_id == session.get("employee_id"):
        return "You cannot delete your own account.", 400
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM Employee WHERE Employee_ID = %s", (employee_id,))
        db.commit()
    except mysql.connector.Error:
        cursor.close()
        return "Cannot delete employee. Employee is linked to sales.", 400
    cursor.close()
    return redirect(url_for("manage_employees"))

#---------------add product (Admin)----------------
@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if admin_only():
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form["name"].strip()
        category = request.form["category"].strip()
        price = request.form["price"]
        reorder_level = request.form["reorder_level"]
        size = request.form["size"]
        cursor = db.cursor()
        cursor.execute("""
            SELECT Product_ID
            FROM Product
            WHERE Product_Name = %s
              AND Size = %s
        """, (name, size))

        existing = cursor.fetchone()
        if existing:
            cursor.close()
            return "This product with the selected size already exists.", 400

        cursor.execute("""
            INSERT INTO Product
            (Product_Name, Size, Category, Default_Sale_Price, Reorder_Level, Supplier_ID)
            VALUES (%s, %s, %s, %s, %s, 1)
        """, (
            name,
            size,
            category,
            price,
            reorder_level
        ))
        db.commit()
        cursor.close()
        return redirect(url_for("view_products"))
    return render_template("add_product.html")


#-------------------edit product (Admin)-----------------

@app.route("/edit_product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if admin_only():
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        cursor.execute("""
            UPDATE Product
            SET Product_Name = %s,
                Category = %s,
                Default_Sale_Price = %s,
                Reorder_Level = %s
            WHERE Product_ID = %s
        """, (
            request.form["name"],
            request.form["category"],
            request.form["price"],
            request.form["reorder_level"],
            product_id
        ))
        db.commit()
        cursor.close()
        return redirect(url_for("view_products"))

    cursor.execute("SELECT * FROM Product WHERE Product_ID = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    return render_template("edit_product.html", product=product)

#----------------------delete product (Admin)---------------
@app.route("/delete_product/<int:product_id>")
def delete_product(product_id):
    if admin_only():
        return redirect(url_for("login"))
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM Product WHERE Product_ID = %s", (product_id,))
        db.commit()
    except mysql.connector.Error as err:
        cursor.close()
        return f"Cannot delete product. It is appears in sales or inventory.", 400
    cursor.close()
    return redirect(url_for("view_products"))

#----------------------delete sale (admin)------------------------
@app.route("/delete_sale/<int:sale_id>")
def delete_sale(sale_id):
    if admin_only():
        return redirect(url_for("login"))
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT Product_ID, Quantity
        FROM Sale_Details
        WHERE Sale_ID = %s
    """, (sale_id,))
    items = cursor.fetchall()
    for item in items:
        cursor.execute("""
            UPDATE Inventory
            SET Quantity_Available = Quantity_Available + %s
            WHERE Product_ID = %s AND Store_ID = 1
        """, (item["Quantity"], item["Product_ID"]))

    cursor.execute("DELETE FROM Sale_Details WHERE Sale_ID = %s", (sale_id,))
    cursor.execute("DELETE FROM Sale WHERE Sale_ID = %s", (sale_id,))
    db.commit()
    cursor.close()
    return redirect(url_for("view_sales"))
#----------------------edit sale (Admin)------------------------
@app.route("/edit_sale/<int:sale_id>", methods=["POST"])
def edit_sale(sale_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    # ----Update customer name----
    customer_name = request.form.get("customer_name", "").strip()
    if customer_name:
        first, *last = customer_name.split(" ", 1)
        last = last[0] if last else ""

        cursor.execute("""
            UPDATE Customer c
            JOIN Sale s ON c.Customer_ID = s.Customer_ID
            SET c.First_Name=%s, c.Last_Name=%s
            WHERE s.Sale_ID=%s
        """, (first, last, sale_id))

    # ----Update payment method----
    payment_method = request.form.get("payment_method")
    if payment_method:
        cursor.execute("""
            UPDATE Sale
            SET Sale_Payment_Method=%s
            WHERE Sale_ID=%s
        """, (payment_method, sale_id))

    # ----Update sale details----
    qty_map = request.form.getlist("qty")
    for key, value in request.form.items():
        if key.startswith("qty["):
            detail_id = key[4:-1]
            qty = int(value)
            price = float(request.form.get(f"price[{detail_id}]", 0))

            cursor.execute("""
                UPDATE Sale_Details
                SET Quantity=%s, Unit_Price=%s
                WHERE SaleDetails_ID=%s
            """, (qty, price, detail_id))

    db.commit()
    cursor.close()
    return redirect(url_for("view_sales"))

#--------------------------sales of each employee-----------------
@app.route("/employee_sales/<int:employee_id>")
def employee_sales(employee_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT First_Name, Last_Name
        FROM Employee
        WHERE Employee_ID = %s
    """, (employee_id,))
    employee = cursor.fetchone()
    if not employee:
        cursor.close()
        return "Employee not found", 404

    cursor.execute("""
                   SELECT s.Sale_ID,
                          s.Sale_Date,
                          c.First_Name AS Customer_First_Name,
                          c.Last_Name AS Customer_Last_Name,
                          SUM(sd.Quantity * sd.Unit_Price) AS Sale_Subtotal,
                          s.Sale_Payment_Method,
                          COUNT(sd.SaleDetails_ID) AS Total_Items
                   FROM Sale s
                            JOIN Customer c ON s.Customer_ID = c.Customer_ID
                            JOIN Sale_Details sd ON s.Sale_ID = sd.Sale_ID
                   WHERE s.Employee_ID = %s
                   GROUP BY s.Sale_ID,
                            s.Sale_Date,
                            c.First_Name,
                            c.Last_Name,
                            s.Sale_Payment_Method
                   ORDER BY s.Sale_Date DESC
                   """, (employee_id,))

    sales = cursor.fetchall()
    for sale in sales:
        sale["Customer_Name"] = f"{sale['Customer_First_Name']} {sale['Customer_Last_Name']}"

    cursor.execute("""
                   SELECT sd.Sale_ID,
                          p.Product_Name,
                          p.Size,
                          sd.Quantity,
                          sd.Unit_Price,
                          (sd.Quantity * sd.Unit_Price) AS Line_Total
                   FROM Sale_Details sd
                            JOIN Product p ON sd.Product_ID = p.Product_ID
                   """)

    details = cursor.fetchall()
    cursor.close()

    sale_details = {}
    for d in details:
        sale_details.setdefault(d["Sale_ID"], []).append(d)

    return render_template(
        "employee_sales.html",
        employee=employee,
        sales=sales,
        sale_details=sale_details
    )
#---------------------inventory-------------------
@app.route("/User_inventory")
def view_user_inventory():
    if "role" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
                   SELECT p.Product_ID,
                          p.Product_Name,
                          p.Size,
                          p.Category,
                          p.Reorder_Level,
                          CASE
                              WHEN si.Quantity_Available IS NULL THEN 0
                              ELSE si.Quantity_Available
                              END AS Store_Qty,
                          CASE
                              WHEN wi.Quantity_Available IS NULL THEN 0
                              ELSE wi.Quantity_Available
                              END AS Warehouse_Qty
                   FROM Product p
                            LEFT JOIN Inventory si
                                      ON p.Product_ID = si.Product_ID
                                          AND si.Store_ID = 1
                            LEFT JOIN Inventory wi
                                      ON p.Product_ID = wi.Product_ID
                                          AND wi.Warehouse_ID = 1
                   ORDER BY p.Product_Name, p.Size
                   """)

    products = cursor.fetchall()
    cursor.close()

    for p in products:
        p["store_status"] = (
            "out" if p["Store_Qty"] == 0
            else "low" if p["Store_Qty"] <= p["Reorder_Level"]
            else "ok"
        )

        p["warehouse_status"] = (
            "out" if p["Warehouse_Qty"] == 0
            else "low" if p["Warehouse_Qty"] <= p["Reorder_Level"]
            else "ok"
        )

    return render_template("User_inventory.html", products=products)

# ---------- Monthly Sales Summary ----------
@app.route("/monthly_sales")
def monthly_sales():
    if "role" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)
    month = request.args.get("month", type=int)

    query = """
        SELECT
            
            MONTH(s.Sale_Date) AS sale_month,
            COUNT(DISTINCT s.Sale_ID) AS total_sales,
            SUM(sd.Quantity * sd.Unit_Price) AS total_revenue
            FROM Sale s
                JOIN Sale_Details sd ON s.Sale_ID = sd.Sale_ID
        
    """

    params = []
    if month:
        query += " WHERE MONTH(s.Sale_Date) = %s "
        params.append(month)

    query += """
        GROUP BY sale_month
        ORDER BY sale_month DESC
    """

    cursor.execute(query, params)
    summary = cursor.fetchall()

    labels = [f"{row['sale_month']:02d}" for row in summary]
    revenues = [float(row["total_revenue"] or 0) for row in summary]

    cursor.close()

    return render_template(
        "monthly_sales.html",
        summary=summary,
        labels=labels,
        revenues=revenues,
        selected_month=month
    )

#--------------------top products-------------------------

@app.route("/top_products")
def top_products():
    if "role" not in session:
        return redirect(url_for("login"))
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            p.Product_Name,
            p.Size,
            SUM(sd.Quantity) AS total_units_sold,
            SUM(sd.Quantity * sd.Unit_Price) AS total_revenue
        FROM Sale_Details sd
        JOIN Product p ON sd.Product_ID = p.Product_ID
        GROUP BY p.Product_Name, p.Size
        ORDER BY total_units_sold DESC
        LIMIT 5
    """)

    products = cursor.fetchall()
    cursor.close()
    return render_template(
        "top_products.html",
        products=products
    )

#--------------------unsold products-------------------------

@app.route("/unsold_products")
def unsold_products():
    if "role" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
                   SELECT p.Product_ID,
                          p.Product_Name,
                          p.Size,
                          p.Category,
                          p.Default_Sale_Price,
                          p.Reorder_Level,
                          CASE
                              WHEN i.Quantity_Available IS NULL THEN 0
                              ELSE i.Quantity_Available
                              END AS Store_Quantity
                   FROM Product p
                            LEFT JOIN Inventory i
                                      ON p.Product_ID = i.Product_ID
                                          AND i.Store_ID = 1
                   WHERE NOT EXISTS (SELECT *
                                     FROM Sale_Details sd
                                     WHERE sd.Product_ID = p.Product_ID)
                   ORDER BY p.Product_Name, p.Size
                   """)

    products = cursor.fetchall()
    cursor.close()

    return render_template(
        "unsold_products.html",
        products=products
    )

#--------------------bulk sales-------------------------
@app.route("/bulk_sales")
def bulk_sales():
    if "role" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
                   SELECT s.Sale_ID,
                          s.Sale_Date,
                          c.First_Name AS Customer_First_Name,
                          c.Last_Name AS Customer_Last_Name,
                          e.First_Name AS Employee_First_Name,
                          e.Last_Name AS Employee_Last_Name,
                          SUM(sd.Quantity * sd.Unit_Price) AS Sale_Subtotal,
                          s.Sale_Payment_Method,
                          SUM(sd.Quantity) AS total_items
                   FROM Sale s
                            JOIN Customer c ON s.Customer_ID = c.Customer_ID
                            JOIN Employee e ON s.Employee_ID = e.Employee_ID
                            JOIN Sale_Details sd ON s.Sale_ID = sd.Sale_ID
                   GROUP BY s.Sale_ID,
                            s.Sale_Date,
                            c.First_Name,
                            c.Last_Name,
                            e.First_Name,
                            e.Last_Name,
                            s.Sale_Payment_Method
                   HAVING SUM(sd.Quantity) >= 10
                   ORDER BY s.Sale_Date DESC
                   """)


    sales = cursor.fetchall()

    for s in sales:
        s["Customer_Name"] = f"{s['Customer_First_Name']} {s['Customer_Last_Name']}"
        s["Employee_Name"] = f"{s['Employee_First_Name']} {s['Employee_Last_Name']}"

    cursor.close()

    return render_template(
        "bulk_sales.html",
        sales=sales
    )
#------------------------Frequent customers---------------------------
@app.route("/frequent_customers")
def frequent_customers():
    if "role" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.Customer_ID,
            c.First_Name,
            c.Last_Name,
            c.Phone,
            COUNT(DISTINCT s.Sale_ID) AS total_purchases,
            SUM(sd.Quantity * sd.Unit_Price) AS total_spent
        FROM Customer c
        JOIN Sale s ON c.Customer_ID = s.Customer_ID
        JOIN Sale_Details sd ON s.Sale_ID = sd.Sale_ID
        GROUP BY
            c.Customer_ID,
            c.First_Name,
            c.Last_Name,
            c.Phone
        HAVING COUNT(DISTINCT s.Sale_ID) >= 3
        ORDER BY total_purchases DESC
    """)

    customers = cursor.fetchall()
    cursor.close()

    return render_template(
        "frequent_customers.html",
        customers=customers
    )


# Helper functions

def get_purchase_subtotal(db, purchase_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT IFNULL(SUM(Quantity * Unit_Cost), 0)
        FROM Purchase_Details
        WHERE Purchase_ID = %s
    """, (purchase_id,))
    row = cursor.fetchone()
    subtotal = row[list(row.keys())[0]] if row else 0
    cursor.close()
    return float(subtotal or 0)

def get_all_products(db):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            Product_ID,
            Product_Name,
            Size,
            Default_Sale_Price AS Unit_Price,
            Category,
            Unit_Cost
        FROM Product
        ORDER BY Product_ID
    """)
    products = cursor.fetchall()
    cursor.close()
    return products


def adjust_inventory_for_purchase(db, warehouse_id, product_id, qty_delta):
    cursor = db.cursor(dictionary=True)
    product_id = int(product_id)
    qty_delta = int(qty_delta)
    cursor.execute("""
        SELECT Inventory_ID
        FROM Inventory
        WHERE Warehouse_ID = %s
          AND Product_ID = %s
          AND Store_ID IS NULL
        LIMIT 1
    """, (warehouse_id, product_id))
    row = cursor.fetchone()

    if row is None:
        cursor.execute("""
            INSERT INTO Inventory (Product_ID, Quantity_Available, Store_ID, Warehouse_ID)
            VALUES (%s, %s, NULL, %s)
        """, (product_id, qty_delta, warehouse_id))
    else:
        cursor.execute("""
            UPDATE Inventory
            SET Quantity_Available = Quantity_Available + %s
            WHERE Warehouse_ID = %s
              AND Product_ID = %s
              AND Store_ID IS NULL
        """, (qty_delta, warehouse_id, product_id))
    cursor.close()


def adjust_inventory(db, product_id, warehouse_id, store_id, qty_delta):
    cursor = db.cursor(dictionary=True)
    if warehouse_id is not None:
        cursor.execute("""
            SELECT Inventory_ID
            FROM Inventory
            WHERE Product_ID=%s AND Warehouse_ID=%s AND Store_ID IS NULL
            LIMIT 1
        """, (product_id, warehouse_id))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("""
                INSERT INTO Inventory (Product_ID, Quantity_Available, Store_ID, Warehouse_ID)
                VALUES (%s, %s, NULL, %s)
            """, (product_id, qty_delta, warehouse_id))
        else:
            cursor.execute("""
                UPDATE Inventory
                SET Quantity_Available = Quantity_Available + %s
                WHERE Product_ID=%s AND Warehouse_ID=%s AND Store_ID IS NULL
            """, (qty_delta, product_id, warehouse_id))

    if store_id is not None:
        cursor.execute("""
            SELECT Inventory_ID
            FROM Inventory
            WHERE Product_ID=%s AND Store_ID=%s AND Warehouse_ID IS NULL
            LIMIT 1
        """, (product_id, store_id))
        row = cursor.fetchone()

        if row is None:
            cursor.execute("""
                INSERT INTO Inventory (Product_ID, Quantity_Available, Store_ID, Warehouse_ID)
                VALUES (%s, %s, %s, NULL)
            """, (product_id, qty_delta, store_id))
        else:
            cursor.execute("""
                UPDATE Inventory
                SET Quantity_Available = Quantity_Available + %s
                WHERE Product_ID=%s AND Store_ID=%s AND Warehouse_ID IS NULL
            """, (qty_delta, product_id, store_id))

    cursor.close()


def get_warehouse_qty(db, warehouse_id, product_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT IFNULL(Quantity_Available, 0) AS qty
        FROM Inventory
        WHERE Warehouse_ID=%s AND Store_ID IS NULL AND Product_ID=%s
        LIMIT 1
    """, (warehouse_id, product_id))
    row = cursor.fetchone()
    cursor.close()
    return int(row["qty"]) if row else 0

# purchase routes
@app.route("/purchases")
def view_purchases():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            p.Purchase_ID,
            p.Supplier_ID,
            p.Purchase_Date,
            p.Warehouse_ID,
            p.Employee_ID,
            IFNULL(SUM(pd.Quantity * pd.Unit_Cost), 0) AS Purchase_Subtotal
        FROM Purchase p
        LEFT JOIN Purchase_Details pd ON pd.Purchase_ID = p.Purchase_ID
        GROUP BY p.Purchase_ID, p.Supplier_ID, p.Purchase_Date, p.Warehouse_ID, p.Employee_ID
        ORDER BY p.Purchase_Date DESC
    """)
    purchases = cursor.fetchall()
    cursor.execute("SELECT Supplier_ID, Supplier_Name FROM Supplier ORDER BY Supplier_ID")
    suppliers = cursor.fetchall()
    cursor.execute("SELECT Warehouse_ID, Location FROM Warehouse ORDER BY Warehouse_ID")
    warehouses = cursor.fetchall()
    cursor.execute("SELECT Employee_ID, First_Name, Last_Name FROM Employee WHERE Role = 'admin' ORDER BY Employee_ID")
    employees = cursor.fetchall()
    cursor.close()
    return render_template(
        "purchases.html",
        purchases=purchases,
        suppliers=suppliers,
        warehouses=warehouses,
        employees=employees
    )

@app.route("/purchases/add", methods=["POST"])
def add_purchase():
    data = request.form
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        INSERT INTO Purchase (Supplier_ID, Purchase_Date, Warehouse_ID, Employee_ID)
        VALUES (%s, %s, %s, %s)
    """, (
        data["Supplier_ID"],
        data["Purchase_Date"],
        data["Warehouse_ID"],
        data["Employee_ID"]
    ))
    db.commit()
    cursor.close()

    return redirect(url_for("view_purchases"))


@app.route("/purchases/update/<int:purchase_id>", methods=["POST"])
def update_purchase(purchase_id):
    data = request.form
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        UPDATE Purchase SET
            Supplier_ID=%s,
            Purchase_Date=%s,
            Warehouse_ID=%s,
            Employee_ID=%s
        WHERE Purchase_ID=%s
    """, (
        data["Supplier_ID"],
        data["Purchase_Date"],
        data["Warehouse_ID"],
        data["Employee_ID"],
        purchase_id
    ))

    db.commit()
    cursor.close()
    return redirect(url_for("view_purchases"))


@app.route("/purchases/delete/<int:purchase_id>")
def delete_purchase(purchase_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("DELETE FROM Payment WHERE Purchase_ID=%s", (purchase_id,))
    cursor.execute("DELETE FROM Purchase_Details WHERE Purchase_ID=%s", (purchase_id,))
    cursor.execute("DELETE FROM Purchase WHERE Purchase_ID=%s", (purchase_id,))
    db.commit()
    cursor.close()
    return redirect(url_for("view_purchases"))

# purchase details routes

@app.route("/purchases/<int:purchase_id>/details")
def view_purchase_details(purchase_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Purchase WHERE Purchase_ID=%s", (purchase_id,))
    purchase = cursor.fetchone()
    cursor.execute("SELECT * FROM Purchase_Details WHERE Purchase_ID=%s", (purchase_id,))
    details = cursor.fetchall()
    subtotal = get_purchase_subtotal(db, purchase_id)
    products = get_all_products(db)
    cursor.close()
    return render_template(
        "purchase_details.html",
        purchase=purchase,
        details=details,
        subtotal=subtotal,
        products=products
    )

@app.route("/purchases/<int:purchase_id>/details/add", methods=["POST"])
def add_purchase_detail(purchase_id):
    data = request.form
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT Warehouse_ID FROM Purchase WHERE Purchase_ID=%s", (purchase_id,))
        row = cursor.fetchone()
        warehouse_id = row["Warehouse_ID"]
        product_id = int(data["Product_ID"])
        qty = int(data["Quantity"])
        cursor.execute("SELECT Unit_Cost FROM Product WHERE Product_ID=%s", (product_id,))
        unit_cost_row = cursor.fetchone()
        unit_cost = float(unit_cost_row["Unit_Cost"])
        cursor.execute("""
            INSERT INTO Purchase_Details (Purchase_ID, Product_ID, Quantity, Unit_Cost)
            VALUES (%s, %s, %s, %s)
        """, (purchase_id, product_id, qty, unit_cost))
        adjust_inventory_for_purchase(db, warehouse_id, product_id, qty)
        db.commit()
        cursor.close()
    except:
        db.rollback()
        raise

    return redirect(url_for("view_purchase_details", purchase_id=purchase_id))


@app.route("/purchases/details/update/<int:detail_id>", methods=["POST"])
def update_purchase_detail(detail_id):
    data = request.form
    purchase_id = int(data["Purchase_ID"])

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT Warehouse_ID FROM Purchase WHERE Purchase_ID=%s", (purchase_id,))
        row = cursor.fetchone()
        warehouse_id = row["Warehouse_ID"]
        cursor.execute("""
            SELECT Product_ID, Quantity
            FROM Purchase_Details
            WHERE PurchaseDetails_ID=%s
        """, (detail_id,))
        row = cursor.fetchone()
        old_product_id = row["Product_ID"]
        old_qty = row["Quantity"]
        new_product_id = data["Product_ID"]
        new_qty = int(data["Quantity"])
        cursor.execute("""
            UPDATE Purchase_Details SET
                Product_ID=%s,
                Quantity=%s
            WHERE PurchaseDetails_ID=%s
        """, (
            new_product_id,
            new_qty,
            detail_id
        ))
        if str(old_product_id) != str(new_product_id):
            adjust_inventory_for_purchase(db, warehouse_id, old_product_id, -int(old_qty))
            adjust_inventory_for_purchase(db, warehouse_id, new_product_id, new_qty)
        else:
            delta = new_qty - int(old_qty)
            adjust_inventory_for_purchase(db, warehouse_id, new_product_id, delta)

        db.commit()
        cursor.close()
    except:
        db.rollback()
        raise
    return redirect(url_for("view_purchase_details", purchase_id=purchase_id))

@app.route("/purchases/details/delete/<int:detail_id>/<int:purchase_id>")
def delete_purchase_detail(detail_id, purchase_id):
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT Warehouse_ID FROM Purchase WHERE Purchase_ID=%s", (purchase_id,))
        row = cursor.fetchone()
        warehouse_id = row["Warehouse_ID"]
        cursor.execute("""
            SELECT Product_ID, Quantity
            FROM Purchase_Details
            WHERE PurchaseDetails_ID=%s
        """, (detail_id,))
        row = cursor.fetchone()
        product_id = row["Product_ID"]
        qty = row["Quantity"]
        cursor.execute("DELETE FROM Purchase_Details WHERE PurchaseDetails_ID=%s", (detail_id,))
        adjust_inventory_for_purchase(db, warehouse_id, product_id, -int(qty))
        db.commit()
        cursor.close()
    except:
        db.rollback()
        raise
    return redirect(url_for("view_purchase_details", purchase_id=purchase_id))

# payments routes

@app.route("/purchases/<int:purchase_id>/payments")
def view_payments(purchase_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM Payment
        WHERE Purchase_ID=%s
        ORDER BY Payment_Date
    """, (purchase_id,))
    payments = cursor.fetchall()
    cursor.execute("""
        SELECT Purchase_ID, Supplier_ID, Purchase_Date, Warehouse_ID, Employee_ID
        FROM Purchase
        WHERE Purchase_ID=%s
    """, (purchase_id,))
    purchase = cursor.fetchone()
    subtotal = get_purchase_subtotal(db, purchase_id)
    cursor.execute("""
        SELECT IFNULL(SUM(Payment_Amount), 0) AS total_paid
        FROM Payment
        WHERE Purchase_ID=%s
    """, (purchase_id,))
    total_paid = float(cursor.fetchone()["total_paid"] or 0)
    remaining = subtotal - total_paid
    cursor.close()

    return render_template(
        "payments.html",
        purchase=purchase,
        payments=payments,
        subtotal=subtotal,
        total_paid=total_paid,
        remaining=remaining
    )

@app.route("/purchases/<int:purchase_id>/payments/add", methods=["POST"])
def add_payment(purchase_id):
    data = request.form
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        INSERT INTO Payment (Purchase_ID, Payment_Method, Payment_Amount, Payment_Date)
        VALUES (%s, %s, %s, %s)
    """, (
        purchase_id,
        data["Payment_Method"],
        float(data["Payment_Amount"]),
        data["Payment_Date"]
    ))
    db.commit()
    cursor.close()
    return redirect(url_for("view_payments", purchase_id=purchase_id))


@app.route("/payments/update/<int:payment_id>", methods=["POST"])
def update_payment(payment_id):
    data = request.form
    purchase_id = int(data["Purchase_ID"])
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        UPDATE Payment SET
            Payment_Method=%s,
            Payment_Amount=%s,
            Payment_Date=%s
        WHERE Payment_ID=%s
    """, (
        data["Payment_Method"],
        float(data["Payment_Amount"]),
        data["Payment_Date"],
        payment_id
    ))
    db.commit()
    cursor.close()
    return redirect(url_for("view_payments", purchase_id=purchase_id))

@app.route("/payments/delete/<int:payment_id>/<int:purchase_id>")
def delete_payment(payment_id, purchase_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("DELETE FROM Payment WHERE Payment_ID=%s", (payment_id,))
    db.commit()
    cursor.close()
    return redirect(url_for("view_payments", purchase_id=purchase_id))

# inventory routes

@app.route("/inventory")
def view_inventory():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT i.Inventory_ID, i.Product_ID, i.Quantity_Available, i.Store_ID, i.Warehouse_ID
        FROM Inventory i
        ORDER BY i.Warehouse_ID, i.Store_ID, i.Product_ID
    """)
    inventory = cursor.fetchall()
    products = get_all_products(db)
    cursor.close()
    return render_template("inventory.html", inventory=inventory, products=products)

# stock transfer

@app.route("/transfers")
def view_transfers():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Stock_transfer ORDER BY Transfer_Date DESC")
    transfers = cursor.fetchall()
    cursor.execute("SELECT Warehouse_ID, Location FROM Warehouse ORDER BY Warehouse_ID")
    warehouses = cursor.fetchall()
    cursor.execute("SELECT Store_ID, Store_Name FROM Store ORDER BY Store_ID")
    stores = cursor.fetchall()
    cursor.execute("SELECT Employee_ID, First_Name, Last_Name FROM Employee WHERE Role = 'admin' ORDER BY Employee_ID")
    employees = cursor.fetchall()
    cursor.close()
    return render_template(
        "transfers.html",
        transfers=transfers,
        warehouses=warehouses,
        stores=stores,
        employees=employees
    )

@app.route("/transfers/add", methods=["POST"])
def add_transfer():
    data = request.form
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        INSERT INTO Stock_transfer
        (Warehouse_ID, Store_ID, Transfer_Date, Employee_ID)
        VALUES (%s, %s, %s, %s)
    """, (
        data["Warehouse_ID"],
        data["Store_ID"],
        data["Transfer_Date"],
        data["Employee_ID"]
    ))
    db.commit()
    cursor.close()
    return redirect(url_for("view_transfers"))


@app.route("/transfers/update/<int:transfer_id>", methods=["POST"])
def update_transfer(transfer_id):
    data = request.form
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        UPDATE Stock_transfer SET
            Warehouse_ID=%s,
            Store_ID=%s,
            Transfer_Date=%s,
            Employee_ID=%s
        WHERE Transfer_ID=%s
    """, (
        data["Warehouse_ID"],
        data["Store_ID"],
        data["Transfer_Date"],
        data["Employee_ID"],
        transfer_id
    ))
    db.commit()
    cursor.close()
    return redirect(url_for("view_transfers"))

@app.route("/transfers/delete/<int:transfer_id>")
def delete_transfer(transfer_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("DELETE FROM Stock_transfer_details WHERE Transfer_ID=%s", (transfer_id,))
    cursor.execute("DELETE FROM Stock_transfer WHERE Transfer_ID=%s", (transfer_id,))
    db.commit()
    cursor.close()
    return redirect(url_for("view_transfers"))

# trasnfer details routes

@app.route("/transfers/<int:transfer_id>/details")
def view_transfer_details(transfer_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Stock_transfer WHERE Transfer_ID=%s", (transfer_id,))
    transfer = cursor.fetchone()
    cursor.execute("SELECT * FROM Stock_transfer_details WHERE Transfer_ID=%s", (transfer_id,))
    details = cursor.fetchall()
    products = get_all_products(db)
    cursor.close()
    return render_template("transfer_details.html", transfer=transfer, details=details, products=products)

@app.route("/transfers/<int:transfer_id>/details/add", methods=["POST"])
def add_transfer_detail(transfer_id):
    data = request.form
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT Warehouse_ID, Store_ID
            FROM Stock_transfer
            WHERE Transfer_ID=%s
        """, (transfer_id,))
        row = cursor.fetchone()
        warehouse_id = row["Warehouse_ID"]
        store_id = row["Store_ID"]
        product_id = int(data["Product_ID"])
        qty = int(data["Quantity_Transferred"])
        available = get_warehouse_qty(db, warehouse_id, product_id)
        if qty > available:
            cursor.close()
            return "<script>alert('Not enough stock in warehouse'); window.history.back();</script>"
        cursor.execute("""
            INSERT INTO Stock_transfer_details (Transfer_ID, Product_ID, Quantity_Transferred)
            VALUES (%s, %s, %s)
        """, (
            transfer_id,
            product_id,
            qty
        ))
        adjust_inventory(db, product_id, warehouse_id=warehouse_id, store_id=None, qty_delta=-qty)
        adjust_inventory(db, product_id, warehouse_id=None, store_id=store_id, qty_delta=qty)
        db.commit()
        cursor.close()
    except:
        db.rollback()
        raise

    return redirect(url_for("view_transfer_details", transfer_id=transfer_id))


@app.route("/transfers/details/delete/<int:detail_id>/<int:transfer_id>")
def delete_transfer_detail(detail_id, transfer_id):
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT Warehouse_ID, Store_ID
            FROM Stock_transfer
            WHERE Transfer_ID=%s
        """, (transfer_id,))
        row = cursor.fetchone()
        warehouse_id = row["Warehouse_ID"]
        store_id = row["Store_ID"]
        cursor.execute("""
            SELECT Product_ID, Quantity_Transferred
            FROM Stock_transfer_details
            WHERE TransferDetails_ID=%s
        """, (detail_id,))
        row = cursor.fetchone()
        product_id = row["Product_ID"]
        qty = row["Quantity_Transferred"]
        cursor.execute("DELETE FROM Stock_transfer_details WHERE TransferDetails_ID=%s", (detail_id,))
        adjust_inventory(db, product_id, warehouse_id=warehouse_id, store_id=None, qty_delta=qty)
        adjust_inventory(db, product_id, warehouse_id=None, store_id=store_id, qty_delta=-qty)
        db.commit()
        cursor.close()
    except:
        db.rollback()
        raise
    return redirect(url_for("view_transfer_details", transfer_id=transfer_id))

# order purchase route/page

@app.route("/order_purchase")
def order_purchase():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT Supplier_ID, Supplier_Name FROM Supplier ORDER BY Supplier_ID")
    suppliers = cursor.fetchall()
    cursor.execute("SELECT Employee_ID, First_Name, Last_Name FROM Employee ORDER BY Employee_ID")
    employees = cursor.fetchall()
    cursor.execute("SELECT Warehouse_ID, Location FROM Warehouse ORDER BY Warehouse_ID")
    warehouses = cursor.fetchall()
    cursor.close()
    return render_template(
        "order_purchase.html",
        suppliers=suppliers,
        employees=employees,
        warehouses=warehouses
    )


# queries page

@app.route("/queries", methods=["GET", "POST"])
def queries_page():
    cursor = db.cursor(dictionary=True)

    today = date.today()
    default_year = today.year

    # form defaults
    year = request.form.get("year", str(default_year))
    month = request.form.get("month", str(today.month))
    date_from = request.form.get("date_from", f"{default_year}-01-01")
    date_to = request.form.get("date_to", f"{default_year}-12-31")
    q = request.form.get("q", "1")
    results = None
    columns = None
    title = None
    chart = None
    chart_json = None
    try:
        year_int = int(year)
        month_int = int(month)

        # helper for month range
        month_start = date(year_int, month_int, 1)
        last_day = calendar.monthrange(year_int, month_int)[1]
        month_end = date(year_int, month_int, last_day)

        if request.method == "POST":
            if q == "1":
                title = f"1) Purchase orders in year {year_int}"
                cursor.execute("""
                    SELECT *
                    FROM Purchase
                    WHERE YEAR(Purchase_Date) = %s
                    ORDER BY Purchase_Date DESC
                """, (year_int,))

            elif q == "2":
                title = f"2) Total qty received into warehouses in {year_int}-{month_int:02d}"
                cursor.execute("""
                    SELECT
                      p.Warehouse_ID,
                      pd.Product_ID,
                      SUM(pd.Quantity) AS Total_Qty_Received
                    FROM Purchase p
                    JOIN Purchase_Details pd ON pd.Purchase_ID = p.Purchase_ID
                    WHERE p.Purchase_Date >= %s AND p.Purchase_Date <= %s
                    GROUP BY p.Warehouse_ID, pd.Product_ID
                    ORDER BY p.Warehouse_ID, pd.Product_ID
                """, (month_start, month_end))


            elif q == "3":
                title = f"3) Total purchase cost per month in {year_int}"
                cursor.execute("""
                    SELECT
                      MONTH(p.Purchase_Date) AS m,
                      SUM(pd.Quantity * pd.Unit_Cost) AS total
                    FROM Purchase p
                    JOIN Purchase_Details pd ON pd.Purchase_ID = p.Purchase_ID
                    WHERE YEAR(p.Purchase_Date) = %s
                    GROUP BY MONTH(p.Purchase_Date)
                    ORDER BY m
                """, (year_int,))


            elif q == "4":
                title = f"4) Total quantity purchased per product in year {year_int}"
                cursor.execute("""
                    SELECT
                      pr.Product_Name AS label,
                      SUM(pd.Quantity) AS value
                    FROM Purchase p
                    JOIN Purchase_Details pd ON pd.Purchase_ID = p.Purchase_ID
                    JOIN Product pr ON pr.Product_ID = pd.Product_ID
                    WHERE YEAR(p.Purchase_Date) = %s
                    GROUP BY pr.Product_Name
                    ORDER BY value DESC
                    LIMIT 5
                """, (year_int,))



            elif q == "5":
                title = f"5) Highest total purchase cost per product in year {year_int}"
                cursor.execute("""
                    SELECT
                      pr.Product_Name AS label,
                      SUM(pd.Quantity * pd.Unit_Cost) AS value
                    FROM Purchase p
                    JOIN Purchase_Details pd ON pd.Purchase_ID = p.Purchase_ID
                    JOIN Product pr ON pr.Product_ID = pd.Product_ID
                    WHERE YEAR(p.Purchase_Date) = %s
                    GROUP BY pr.Product_Name
                    ORDER BY value DESC
                    LIMIT 10
                """, (year_int,))

            elif q == "6":
                title = "6) Products below reorder level in the warehouse"
                cursor.execute("""
                    SELECT
                      i.Warehouse_ID,
                      i.Product_ID,
                      pr.Product_Name,
                      i.Quantity_Available,
                      pr.Reorder_Level
                    FROM Inventory i
                    JOIN Product pr ON pr.Product_ID = i.Product_ID
                    WHERE i.Store_ID IS NULL
                      AND i.Quantity_Available < pr.Reorder_Level
                    ORDER BY i.Warehouse_ID, i.Quantity_Available ASC
                """)

            elif q == "7":
                title = "7) Purchase orders with no payments yet"
                cursor.execute("""
                    SELECT
                      p.Purchase_ID,
                      p.Supplier_ID,
                      p.Purchase_Date,
                      p.Warehouse_ID
                    FROM Purchase p
                    LEFT JOIN Payment pay ON pay.Purchase_ID = p.Purchase_ID
                    WHERE pay.Payment_ID IS NULL
                    ORDER BY p.Purchase_Date DESC
                """)

            elif q == "8":
                title = "8) Products never purchased"
                cursor.execute("""
                    SELECT
                      pr.Product_ID,
                      pr.Product_Name,
                      pr.Category
                    FROM Product pr
                    LEFT JOIN Purchase_Details pd ON pd.Product_ID = pr.Product_ID
                    WHERE pd.Product_ID IS NULL
                    ORDER BY pr.Product_ID
                """)

            elif q == "9":
                title = f"9) Stock transfers from {date_from} to {date_to}"
                cursor.execute("""
                    SELECT
                      st.Transfer_ID,
                      st.Transfer_Date,
                      st.Warehouse_ID,
                      st.Store_ID,
                      IFNULL(SUM(std.Quantity_Transferred), 0) AS Total_Items_Transferred
                    FROM Stock_transfer st
                    LEFT JOIN Stock_transfer_details std ON std.Transfer_ID = st.Transfer_ID
                    WHERE st.Transfer_Date >= %s AND st.Transfer_Date <= %s
                    GROUP BY st.Transfer_ID, st.Transfer_Date, st.Warehouse_ID, st.Store_ID
                    ORDER BY st.Transfer_Date DESC
                """, (date_from, date_to))

            elif q == "10":
                title = "10) Inventory valuation per warehouse"
                cursor.execute("""
                    SELECT
                      i.Warehouse_ID,
                      w.Location,
                      SUM(i.Quantity_Available * pr.Unit_Cost) AS Total_Inventory_Value
                    FROM Inventory i
                    JOIN Product pr ON pr.Product_ID = i.Product_ID
                    JOIN Warehouse w ON w.Warehouse_ID = i.Warehouse_ID
                    WHERE i.Store_ID IS NULL
                    GROUP BY i.Warehouse_ID, w.Location
                    ORDER BY Total_Inventory_Value DESC
                """)

            results = cursor.fetchall()
            if q == "3":
                month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
                labels = [month_names[int(r["m"]) - 1] for r in results] if results else []
                values = [float(r["total"] or 0) for r in results] if results else []
                chart = {
                    "type": "line",
                    "labels": labels,
                    "values": values
                }

            elif q == "4" or q == "5":
                labels = [r["label"] for r in results] if results else []
                values = [float(r["value"] or 0) for r in results] if results else []
                chart = {
                    "type": "pie" if q == "4" else "bar",
                    "labels": labels,
                    "values": values
                }

            chart_json = json.dumps(chart) if chart else None


            # columns for table header
            if results:
                columns = list(results[0].keys())
            else:
                columns = []

    finally:
        cursor.close()

    return render_template(
        "queries.html",
        q=q,
        year=year,
        month=month,
        date_from=date_from,
        date_to=date_to,
        title=title,
        columns=columns,
        results=results,
        chart_json = chart_json
    )


# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)
