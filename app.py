from flask import Flask, request, redirect, url_for, session, flash, send_from_directory, render_template_string
import mysql.connector
from flask_bcrypt import Bcrypt
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os
from db_config import db_config
from flask import jsonify


app = Flask(__name__)
app.secret_key = "your_secret_key"
bcrypt = Bcrypt(app)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ------------------- Email Configuration -------------------
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USER = 'salunkhedarshan408@gmail.com.com'        # 🔁 Replace with your email
EMAIL_PASS = 'Darshan12345'           # 🔁 Replace with your app password

# ------------------- Utility Functions -------------------
def render_page(filename, **context):
    file_path = os.path.join(BASE_DIR, filename)
    with open(file_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), **context)

@app.route('/<path:filename>')
def serve_file(filename):
    return send_from_directory(BASE_DIR, filename)

# ------------------- Database Connection -------------------
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    print("✅ Connected to Database Successfully!")
except mysql.connector.Error as err:
    print(f"❌ Database Connection Failed: {err}")

# ------------------- Authentication -------------------
@app.route("/")
def home():
    return render_page("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
                           (username, email, password))
            conn.commit()
            flash("✅ Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except mysql.connector.Error as err:
            flash(f"❌ Error: {err}", "danger")
            return redirect(url_for("register"))
    return render_page("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        conn.commit()
        user = cursor.fetchone()
        if user and bcrypt.check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = user["email"]
            flash("✅ Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid Credentials. Please try again.", "danger")
            return redirect(url_for("login"))
    return render_page("index.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("✅ Logged out successfully!", "info")
    return redirect(url_for("login"))

# ------------------- Dashboards -------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" in session:
        return render_page("dashboard.html", username=session["username"])
    return redirect(url_for("login"))

@app.route("/dashboard_doctor")
def dashboard_doctor():
    if "user_id" in session:
        return render_page("dashboard_doctor.html", username=session["username"])
    return redirect(url_for("login"))

@app.route("/dashboard_patient")
def dashboard_patient():
    if "user_id" in session:
        return render_page("dashboard_patient.html", username=session["username"])
    return redirect(url_for("login"))

@app.route("/dashboard_receptionist")
def dashboard_receptionist():
    if "user_id" in session:
        return render_page("dashboard_receptionist.html", username=session["username"])
    return redirect(url_for("login"))

# ------------------- Appointments -------------------
@app.route("/book_appointment", methods=["GET", "POST"])
def book_appointment():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        doctor = request.form.get("doctor")
        date = request.form.get("date")
        time = request.form.get("time")
        patient_name = request.form.get("patient_name", "").strip()
        patient_id = session["user_id"]

        try:
            cursor.execute("""
                INSERT INTO appointments (patient_id, doctor_name, appointment_date, appointment_time, patient_name, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (patient_id, doctor, date, time, patient_name, "Pending"))
            conn.commit()

            return f"""
                <script>
                    alert("✅ Appointment booked successfully!\\nPatient: {patient_name}");
                    window.location.href='/book_appointment';
                </script>
            """
        except mysql.connector.Error as err:
            return f"""
                <script>
                    alert("❌ Failed to book appointment: {err}");
                    window.location.href='/book_appointment';
                </script>
            """

    return render_page("book_appointment.html", username=session["username"])


# ------------------- Medicine Reminder -------------------
@app.route("/medicine_reminder", methods=["GET", "POST"])
def medicine_reminder():
    if "user_id" not in session:
        return redirect(url_for("login"))

    msg = request.args.get('msg')
    if request.method == "POST":
        medicine = request.form.get("medicine")
        reminder_time = request.form.get("reminder_time")
        user_id = session["user_id"]

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO medicine_reminders (user_id, medicine_name, reminder_time)
                VALUES (%s, %s, %s)
            """, (user_id, medicine, reminder_time))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for("medicine_reminder", msg="Reminder set successfully!"))
        except Exception as e:
            return f"<script>alert('❌ Error: {str(e)}'); window.location.href='/medicine_reminder';</script>"

    return render_page("medicine_reminder.html", msg=msg)

# ------------------- Email Reminder Scheduler -------------------
def send_email(to, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = to

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

def send_medicine_reminders():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT u.email, m.medicine_name, m.reminder_time
            FROM medicine_reminders m
            JOIN users u ON m.user_id = u.id
        """)
        reminders = cursor.fetchall()
        now = datetime.now().strftime('%H:%M')

        for r in reminders:
            if r['reminder_time'] == now:
                send_email(
                    r['email'],
                    "💊 Medicine Reminder",
                    f"Hi, this is your reminder to take: {r['medicine_name']} at {r['reminder_time']}"
                )

        cursor.close()
        conn.close()
    except Exception as e:
        print("❌ Reminder Error:", str(e))

scheduler = BackgroundScheduler()
scheduler.add_job(send_medicine_reminders, 'interval', minutes=1)
scheduler.start()

# ------------------- Other Pages -------------------
@app.route("/view_bills")
def view_bills():
    if 'receptionist_id' not in session:
        return redirect("/login")

    # Fetch bills from DB
    cursor = mysql.connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM bills ORDER BY created_at DESC")
    bills = cursor.fetchall()
    cursor.close()

    # Load HTML template
    with open("view_bills.html", "r", encoding="utf-8") as file:
        html_template = file.read()

    # Manually build HTML rows from data
    bill_rows = ""
    for bill in bills:
        bill_rows += f"""
        <tr>
            <td>{bill['id']}</td>
            <td>{bill['patient_id']}</td>
            <td>{bill['patient_name']}</td>
            <td>{bill['doctor_name']}</td>
            <td>{bill['service']}</td>
            <td>₹{bill['amount']}</td>
            <td>{bill['created_at']}</td>
        </tr>
        """

    # Replace placeholder with actual rows
    final_html = html_template.replace("<!-- BILL_ROWS_PLACEHOLDER -->", bill_rows)

    return render_template_string(final_html)

@app.route("/view_appointments", methods=["GET", "POST"])
def view_appointments():
    if "user_id" not in session:
        return redirect(url_for("login"))

    message = ""
    appointments = []
    selected_doctor = None

    if request.method == "POST":
        selected_doctor = request.form.get("doctor_name")

        if selected_doctor:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT patient_id, appointment_date, appointment_time, status 
                FROM appointments 
                WHERE doctor_name = %s
                ORDER BY appointment_date, appointment_time
            """, (selected_doctor,))
            appointments = cursor.fetchall()
            if not appointments:
                message = f"<p>No appointments found for {selected_doctor}.</p>"
        else:
            message = "<p>Please select a doctor.</p>"

    # Generate HTML table rows
    table_html = ""
    if appointments:
        table_html += """
        <table>
            <thead>
                <tr>
                    <th>Patient id</th>
                    <th>Time</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
        """
        for appt in appointments:
            table_html += f"""
                <tr>
                    <td>{appt['patient_id']}</td>
                    <td>{appt['appointment_date']}</td>
                    <td>{appt['appointment_time']}</td>
                    <td>{appt['status']}</td>
                </tr>
            """
        table_html += "</tbody></table>"

    # Load HTML file and inject message/table
    with open("view_appointments.html", "r") as file:
        html_template = file.read()

    rendered_html = html_template.replace("<!--MESSAGE-->", message).replace("<!--TABLE-->", table_html)

    return render_template_string(rendered_html)


    
@app.route("/patientrecords")
def patientrecords():
    if "user_id" in session:
        return render_page("patientrecords.html", username=session["username"])
    return redirect(url_for("login"))

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Darshan12345",  # Update if needed
    database="user_db"
)
cursor = db.cursor(dictionary=True)

@app.route('/manage_appointment', methods=['GET', 'POST'])
def manage_appointment():
    if "user_id" not in session:
        return redirect('/login')  # Redirect only if not logged in

    # Handle Update or Delete Actions (POST)
    if request.method == 'POST':
        action = request.form.get('action')
        appointment_id = request.form.get('appointment_id')

        if action == 'delete':
            cursor.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
            db.commit()
        elif action == 'update':
            new_status = request.form.get('status')
            cursor.execute("UPDATE appointments SET status = %s WHERE id = %s", (new_status, appointment_id))
            db.commit()
        return redirect(url_for('manage_appointment'))

    # Handle doctor filter (GET)
    selected_doctor = request.args.get('doctor')

    if selected_doctor:
        cursor.execute("SELECT * FROM appointments WHERE doctor_name = %s", (selected_doctor,))
    else:
        cursor.execute("SELECT * FROM appointments")
    appointments = cursor.fetchall()

    # Doctor dropdown list
    doctor_list = ["Dr. Raj Mehta", "Dr. Anita Sharma", "Dr. Vikram Sinha", "Dr. Priya Kapoor", "Dr. Anil Joshi"]

    # HTML Template
    with open("manage_appointment.html", "r") as file:
        html_template = file.read()

    # Generate rows for table
    rows = ""
    for appt in appointments:
        rows += f"""
        <tr>
          <td>{appt['id']}</td>
          <td>{appt['patient_name']}</td>
          <td>{appt['doctor_name']}</td>
          <td>{appt['appointment_date']}</td>
          <td>{appt['appointment_time']}</td>
          <td>{appt['status']}</td>
          <td>
            <form method="POST" style="display:inline;">
              <input type="hidden" name="appointment_id" value="{appt['id']}">
              <select name="status">
                <option value="Pending" {"selected" if appt['status']=="Pending" else ""}>Pending</option>
                <option value="Confirmed" {"selected" if appt['status']=="Confirmed" else ""}>Confirmed</option>
                <option value="Completed" {"selected" if appt['status']=="Completed" else ""}>Completed</option>
                <option value="Cancelled" {"selected" if appt['status']=="Cancelled" else ""}>Cancelled</option>
              </select>
              <button type="submit" name="action" value="update">Update</button>
            </form>
            <form method="POST" style="display:inline;">
              <input type="hidden" name="appointment_id" value="{appt['id']}">
              <button type="submit" name="action" value="delete" onclick="return confirm('Are you sure?')">Delete</button>
            </form>
          </td>
        </tr>
        """

    # Replace placeholders
    html_rendered = html_template.replace("{appointment_rows}", rows)

    # Inject doctor dropdown dynamically
    doctor_dropdown_html = "<form method='get' action='/manage_appointment'><label for='doctor'>Select Doctor:</label><select name='doctor' onchange='this.form.submit()'>"
    doctor_dropdown_html += "<option value=''>All Doctors</option>"
    for doctor in doctor_list:
        selected = "selected" if doctor == selected_doctor else ""
        doctor_dropdown_html += f"<option value='{doctor}' {selected}>{doctor}</option>"
    doctor_dropdown_html += "</select></form><br><br>"

    html_rendered = html_rendered.replace("{doctor_dropdown}", doctor_dropdown_html)

    return render_template_string(html_rendered)



def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Darshan12345",
        database="user_db"
    )

@app.route("/generate_bills", methods=["GET", "POST"])
def generate_bills():
    if request.method == "POST":
        patient_id = request.form["patient_id"]
        services = request.form.getlist("services")
        total = int(request.form["total"])

        conn = get_db()
        cursor = conn.cursor()

        patient_name = f"Patient {patient_id}"
        doctor_name = "Dr. Raj Mehta"

        price_map = {
            "Consultation": 500,
            "X-Ray": 800,
            "Blood Test": 400,
            "MRI Scan": 2000,
            "Vaccination": 600
        }

        for service in services:
            amount = price_map.get(service, 0)
            cursor.execute("""
                INSERT INTO bills (patient_id, service, amount, doctor_name, patient_name)
                VALUES (%s, %s, %s, %s, %s)
            """, (patient_id, service, amount, doctor_name, patient_name))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/generate_bills?msg=Bill+Generated+Successfully")

    with open("generate_bills.html", encoding="utf-8") as f:
        return render_template_string(f.read())

@app.route("/get_bills")
def get_bills():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id, patient_name, doctor_name, service, amount, created_at FROM bills ORDER BY id DESC")
    bills = cursor.fetchall()
    cursor.close()
    conn.close()

    html = "<table><tr><th>Patient ID</th><th>Patient Name</th><th>Doctor</th><th>Service</th><th>Amount (₹)</th><th>Date</th></tr>"
    for bill in bills:
        html += "<tr>" + "".join(f"<td>{col}</td>" for col in bill) + "</tr>"
    html += "</table>"
    return html


from twilio.rest import Client

# Twilio credentials (store securely in environment variables for production)
TWILIO_ACCOUNT_SID = "ACe58cba11a2b5bdf0f2268a1a1a24a68e"
TWILIO_AUTH_TOKEN = "022d7a8e8987101fe490ef07599dd2f4"
TWILIO_PHONE_NUMBER = "+18569972585"


@app.route("/SMS_notification", methods=["GET", "POST"])
def SMS_notification():
    if "user_id" not in session:
        return redirect(url_for("login"))

    status = None

    if request.method == "POST":
        patient_name = request.form.get("patient_name")
        appointment_time = request.form.get("appointment_time")
        to_number = request.form.get("to_number")

        # Auto-generate message
        message_body = f"Hello {patient_name}, your appointment is confirmed at {appointment_time}. - Hospital Management System"

        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=message_body,
                from_=TWILIO_PHONE_NUMBER,
                to=to_number
            )
            status = "SMS sent successfully!"
        except Exception as e:
            status = f"Failed to send SMS: {str(e)}"

    with open("SMS_notification.html", "r") as file:
        html_content = file.read()

    return render_template_string(html_content, status=status)



@app.route('/chat', methods=['POST'])
def chatbot():
    if not session.get("user_id"):
        return jsonify({"reply": "Please login to use the chatbot."})

    message = request.json.get("message", "").lower()
    user_id = session["user_id"]

    try:
        # Latest appointment
        if "appointment" in message and "status" in message:
            cursor.execute("""
                SELECT doctor_name, appointment_date, appointment_time 
                FROM appointments 
                WHERE patient_id = %s 
                ORDER BY appointment_date DESC LIMIT 1
            """, (user_id,))
            appt = cursor.fetchone()
            if appt:
                return jsonify({"reply": f"Your latest appointment is with Dr. {appt['doctor_name']} on {appt['appointment_date']} at {appt['appointment_time']}."})
            return jsonify({"reply": "You have no upcoming appointments."})

        # Latest bill
        elif "bill" in message:
            cursor.execute("""
                SELECT amount, status 
                FROM bills 
                WHERE patient_id = %s 
                ORDER BY id DESC LIMIT 1
            """, (user_id,))
            bill = cursor.fetchone()
            if bill:
                return jsonify({"reply": f"Your latest bill is ₹{bill['amount']} and its status is {bill['status']}."})
            return jsonify({"reply": "No bill found for your account."})

        # Medicine reminders
        elif "medicine" in message or "reminder" in message:
            cursor.execute("""
                SELECT medicine_name, reminder_time 
                FROM medicine_reminders 
                WHERE user_id = %s 
                ORDER BY id DESC LIMIT 1
            """, (user_id,))
            med = cursor.fetchone()
            if med:
                return jsonify({"reply": f"Your last medicine reminder is for {med['medicine_name']} at {med['reminder_time']}."})
            return jsonify({"reply": "No medicine reminders found."})

        # Fallback message
        else:
            return jsonify({"reply": "Hi! I can help you with appointments, bills, and medicine reminders. Ask something like: 'Show my appointment status' or 'Do I have a medicine reminder?'"})
            
    except Exception as e:
        return jsonify({"reply": f"❌ Error: {str(e)}"})
    

 
# ------------------- Run App -------------------
if __name__ == "__main__":
    app.run(debug=True)
