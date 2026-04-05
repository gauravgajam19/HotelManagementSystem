from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
db_config = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', '19052006'),
    'database': os.environ.get('MYSQL_DATABASE', 'hotelmanagementdb')
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# Admin Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# Protect routes
@app.before_request
def require_login():
    if not session.get('logged_in') and request.endpoint not in ['login', 'static']:
        return redirect(url_for('login'))

# Dashboard with stats
@app.route('/')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT COUNT(*) AS total_rooms FROM rooms')
    total_rooms = cursor.fetchone()['total_rooms']

    cursor.execute("SELECT COUNT(*) AS available_rooms FROM rooms WHERE status = 'Available'")
    available_rooms = cursor.fetchone()['available_rooms']

    cursor.execute("SELECT COUNT(*) AS occupied_rooms FROM rooms WHERE status = 'Occupied'")
    occupied_rooms = cursor.fetchone()['occupied_rooms']

    cursor.execute('SELECT SUM(total_amount) AS total_revenue FROM billing')
    total_revenue = cursor.fetchone()['total_revenue'] or 0

    conn.close()
    return render_template('dashboard.html', total_rooms=total_rooms, available_rooms=available_rooms, occupied_rooms=occupied_rooms, total_revenue=total_revenue)

# View and Add Rooms
@app.route('/rooms', methods=['GET', 'POST'])
def rooms():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        room_number = request.form['room_number']
        room_type = request.form['room_type']
        price_per_night = request.form['price_per_night']
        status = request.form['status']

        cursor.execute('INSERT INTO rooms (room_number, room_type, price_per_night, status) VALUES (%s, %s, %s, %s)',
                       (room_number, room_type, price_per_night, status))
        conn.commit()
        flash('Room added successfully!')
        return redirect(url_for('rooms'))

    cursor.execute('SELECT * FROM rooms')
    rooms = cursor.fetchall()
    conn.close()
    return render_template('rooms.html', rooms=rooms)

# Guest Registration
@app.route('/guests', methods=['GET', 'POST'])
def guests():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        full_name = request.form['full_name']
        phone = request.form['phone']
        email = request.form['email']
        id_proof = request.form['id_proof']

        cursor.execute('INSERT INTO guests (full_name, phone, email, id_proof) VALUES (%s, %s, %s, %s)',
                       (full_name, phone, email, id_proof))
        conn.commit()
        flash('Guest registered successfully!')
        return redirect(url_for('guests'))

    cursor.execute('SELECT * FROM guests')
    guests = cursor.fetchall()
    conn.close()
    return render_template('guests.html', guests=guests)

# New Booking
@app.route('/bookings', methods=['GET', 'POST'])
def bookings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        guest_id = request.form['guest_id']
        room_id = request.form['room_id']
        check_in = request.form['check_in']
        check_out = request.form['check_out']
        status = request.form['status']

        cursor.execute('INSERT INTO bookings (guest_id, room_id, check_in, check_out, status) VALUES (%s, %s, %s, %s, %s)',
                       (guest_id, room_id, check_in, check_out, status))
        conn.commit()
        flash('Booking created successfully!')
        return redirect(url_for('bookings'))

    cursor.execute('SELECT * FROM bookings')
    bookings = cursor.fetchall()
    cursor.execute('SELECT * FROM guests')
    guests = cursor.fetchall()
    cursor.execute('SELECT * FROM rooms')
    rooms = cursor.fetchall()
    conn.close()
    return render_template('bookings.html', bookings=bookings, guests=guests, rooms=rooms)

# Auto Bill Calculator
@app.route('/checkout/<int:booking_id>', methods=['POST'])
def checkout(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM bookings JOIN rooms ON bookings.room_id = rooms.room_id WHERE booking_id = %s', (booking_id,))
    booking = cursor.fetchone()

    if booking:
        check_in = datetime.strptime(booking['check_in'], '%Y-%m-%d')
        check_out = datetime.strptime(booking['check_out'], '%Y-%m-%d')
        days_stayed = (check_out - check_in).days
        total_amount = days_stayed * booking['price_per_night']

        cursor.execute('INSERT INTO billing (booking_id, total_amount, payment_status, payment_date) VALUES (%s, %s, %s, %s)',
                       (booking_id, total_amount, 'Pending', datetime.now().strftime('%Y-%m-%d')))
        conn.commit()

        flash(f'Checkout successful! Total bill: {total_amount}', 'success')
    else:
        flash('Booking not found!', 'danger')

    conn.close()
    return redirect(url_for('bookings'))

# Billing
@app.route('/billing', methods=['GET', 'POST'])
def billing():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        booking_id = request.form['booking_id']
        total_amount = request.form['total_amount']
        payment_status = request.form['payment_status']
        payment_date = request.form['payment_date']

        cursor.execute('INSERT INTO billing (booking_id, total_amount, payment_status, payment_date) VALUES (%s, %s, %s, %s)',
                       (booking_id, total_amount, payment_status, payment_date))
        conn.commit()
        flash('Bill generated successfully!')
        return redirect(url_for('billing'))

    cursor.execute('SELECT * FROM billing')
    billing = cursor.fetchall()
    cursor.execute('SELECT * FROM bookings')
    bookings = cursor.fetchall()
    conn.close()
    return render_template('billing.html', billing=billing, bookings=bookings)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)