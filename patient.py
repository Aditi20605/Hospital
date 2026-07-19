from flask import Flask, request, send_from_directory, make_response
import mysql.connector

app = Flask(__name__)

# MySQL database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",             # <-- Update with your MySQL username
    password="Darshan12345",             # <-- Update with your MySQL password
    database="user_db"      # Make sure the database exists
)
cursor = db.cursor()

# Route to serve the appointment page
@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if request.method == 'POST':
        doctor = request.form['doctor']
        date = request.form['date']
        time = request.form['time']

        # Insert into MySQL
        try:
            cursor.execute("INSERT INTO appointments (doctor, date, time) VALUES (%s, %s, %s)", (doctor, date, time))
            db.commit()
        except Exception as e:
            return f"<h2 style='color:red;'>Database error: {e}</h2>"

        # Confirmation message
        return f"""
        <html>
        <head>
            <meta http-equiv='refresh' content='4; url=/book_appointment'>
            <style>
                body {{
                    font-family: 'Poppins', sans-serif;
                    background: url('Hospital-Management-System.jpg') no-repeat center center fixed;
                    background-size: cover;
                    color: white;
                    text-align: center;
                    padding-top: 100px;
                }}
                body::before {{
                    content: "";
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 51, 102, 0.5);
                    z-index: -1;
                }}
                h2 {{ font-size: 28px; }}
                p {{ font-size: 18px; }}
            </style>
        </head>
        <body>
            <h2>✅ Appointment Booked Successfully!</h2>
            <p><strong>Doctor:</strong> {doctor}</p>
            <p><strong>Date:</strong> {date}</p>
            <p><strong>Time:</strong> {time}</p>
            <p>Redirecting back in 4 seconds...</p>
        </body>
        </html>
        """

    return send_from_directory('.', 'book_appointment.html')

@app.route('/logout')
def logout():
    return "<h2>You have been logged out.</h2>"

if __name__ == '__main__':
    app.run(debug=True)
