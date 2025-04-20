from flask import Flask, render_template, request, redirect, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database connection function
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='pharmacy_db'
    )

# Route 1: Website Dashboard
@app.route('/')
def index():
    return render_template('index.html')

# Route 2: Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        table = 'customers' if role == 'customer' else 'vendors'
        id_column = 'customer_id' if role == 'customer' else 'vendor_id'

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {table} WHERE {id_column} = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user'] = username
            session['role'] = role
            session['user_id'] = user[id_column]
            return redirect('/customer-home' if role == 'customer' else '/vendor-home')
        else:
            return "Invalid credentials!"

    return render_template('index2.html')

# Route 3: Customer Registration
@app.route('/register-customer', methods=['GET', 'POST'])
def register_customer():
    if request.method == 'POST':
        name = request.form['customername']
        phone = request.form['phone']
        address = request.form['address']
        customer_id = request.form['customer_id']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return "Passwords do not match", 400

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customers (customer_id, name, phone, address, password)
            VALUES (%s, %s, %s, %s, %s)
        """, (customer_id, name, phone, address, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/customer-home')

    # GET method → render registration form
    return render_template('index4.html')


# Route 4: Vendor Registration
@app.route('/register-vendor', methods=['GET', 'POST'])
def register_vendor():
    if request.method == 'POST':
        vendorname = request.form['vendorname']
        phone = request.form['phone']
        address = request.form['address']
        vendor_id = request.form['vendor_id']
        password1 = request.form['password1']
        password2 = request.form['password2']

        if password1 != password2:
            return "Passwords do not match", 400

        hashed_password = generate_password_hash(password1)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vendors (vendor_id, name, phone, address, password)
            VALUES (%s, %s, %s, %s, %s)
        """, (vendor_id, vendorname, phone, address, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/vendor-home')

    # GET method → render registration form
    return render_template('index3.html')


# Route 5: Customer Homepage
@app.route('/customer-home')
def customer_home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM medicines")
    medicines = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index5.html', medicines=medicines)

# Route 6: Vendor Homepage
@app.route('/vendor-home')
def vendor_home():
    return render_template('index6.html')

# Route 7: Buy Medicine
@app.route('/buy', methods=['GET', 'POST'])
def buy_medicine():
    if request.method == 'POST':
        customer_id = session.get('user_id')  # Ensure the user is logged in
        if not customer_id:
            return "Please log in", 400

        medicine_id = request.form['medicine_id']
        quantity = int(request.form['quantity'])

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT stock, price FROM medicines WHERE medicine_id = %s", (medicine_id,))
        medicine = cursor.fetchone()

        if medicine and medicine['stock'] >= quantity:
            new_stock = medicine['stock'] - quantity
            total_price = medicine['price'] * quantity

            # Update stock
            cursor.execute("UPDATE medicines SET stock = %s WHERE medicine_id = %s", (new_stock, medicine_id))

            # Insert into orders table
            cursor.execute("""
                INSERT INTO orders (customer_id, medicine_id, quantity, price, order_date)
                VALUES (%s, %s, %s, %s, NOW())
            """, (customer_id, medicine_id, quantity, total_price))

            conn.commit()
            cursor.close()
            conn.close()

            return redirect('/orders-customer')
        else:
            cursor.close()
            conn.close()
            return "Not enough stock or medicine not found", 400

    # GET method → show buy page with medicine list
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM medicines")
    medicines = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index7.html', medicines=medicines)

# Route 8: Restock Page
@app.route('/restock', methods=['GET', 'POST'])
def restock():
    if request.method == 'POST':
        # Handle form submission
        medicine_id = request.form['medicine_id']
        name = request.form['name']
        manufacturer = request.form['manufacturer']
        mfg_date = request.form['mfg_date']
        stock = int(request.form['stock'])
        price = float(request.form['price'])
        vendor_id = request.form['vendor_id']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO medicines (medicine_id, name, manufacturer, mfg_date, stock, vendor_id, price)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (medicine_id, name, manufacturer, mfg_date, stock, vendor_id, price))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/vendor-home')
    
    # If method is GET, just show the form
    return render_template('index8.html')

# Route 9: Customer Orders Page (optional)
@app.route('/orders-customer')
def orders_customer():
    customer_id = session.get('user_id')
    if not customer_id:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.medicine_id, m.name AS medicine_name, o.quantity, o.price, o.order_date
        FROM orders o
        JOIN medicines m ON o.medicine_id = m.medicine_id
        WHERE o.customer_id = %s
        ORDER BY o.order_date 
    """, (customer_id,))
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index9.html', orders=orders)

# Route 10: Vendors Order Page
@app.route('/orders_vendor', methods=['GET'])
def orders_vendor():
    # Assuming you have a way to identify the logged-in vendor
    vendor_id = session.get('user_id')  # or get from your session or login

    if not vendor_id:
        return "Please log in as a vendor", 400  # Handle vendor login session

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # SQL Query to get orders for this vendor
    cursor.execute("""
        SELECT o.order_id, c.name AS customer_name, m.name AS medicine_name, o.quantity, o.order_date, o.price
        FROM orders o
        JOIN medicines m ON o.medicine_id = m.medicine_id
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE m.vendor_id = %s
    """, (vendor_id,))
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index10.html', orders=orders)

if __name__ == '__main__':
    app.run(debug=True)
