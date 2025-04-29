from flask import Flask
from flask_mail import Mail, Message
import os

app = Flask(__name__)
 # Flask Configurations
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'nikitapowar09@gmail.com'
app.config['MAIL_PASSWORD'] = 'thfo xepy sauu ynnt'
app.config['MAIL_DEFAULT_SENDER'] = 'nikitapowar09@gmail.com'
app.config['SECRET_KEY'] = 'Nikita@09'  
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "instance", "office_management.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///office_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
mail = Mail(app)

def send_test_email():
    try:
        msg = Message('Test Email', sender='nikitapowar09@gmail.com', recipients=['your-email@example.com'])
        msg.body = "Hello! This is a test email from Flask-Mail."
        mail.send(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Error sending email: {e}")