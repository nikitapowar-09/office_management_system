import random
import string
from flask_mail import Message
from config import app
from itsdangerous import URLSafeTimedSerializer

def generate_temp_password(length=10):
    """Generates a random temporary password"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

#-----------------meeting----------
def send_email(to_email, name, subject, time, link):
    from_email = "nikitapowar09@gmail.com"
    password = 'thfo xepy sauu ynnt'
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, password)

        message = f"""\ 
Subject: Meeting Invitation

Hi {name},

You are invited to a meeting.
Topic: {subject}
Time: {time}
Link: {link}

Regards,
Admin
"""
        server.sendmail(from_email, to_email, message)
        server.quit()
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False

#--------logincredentials----------------
def send_login_email(email, username, password):
    from config import mail
    """Sends login credentials to employee via email"""
    msg = Message('Your Account Details', sender='your-email@gmail.com', recipients=[email])
    msg.body = f"""
    Hello {username},

    Your account has been created successfully! Here are your login credentials:

    Username: {username}
    Password: {password}

    Please log in and change your password immediately for security reasons.

    Regards,
    Admin Team
    """
    try:
        mail.send(msg)  # ✅ Correct method call (use `mail`, not `Mail`)
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")  # Debugging output
        return False


serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

def generate_reset_token(email):
    return serializer.dumps(email, salt='password-reset-salt')

def verify_reset_token(token, expiration=3600):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except Exception:
        return None
    return email

def send_reset_email(email):
    token = generate_reset_token(email)
    reset_url = url_for('reset_password', token=token, _external=True)

    msg = Message('Password Reset Request', sender='your-email@gmail.com', recipients=[email])
    msg.body = f"""
    Hello,

    You requested to reset your password. Click the link below to reset your password:

    {reset_url}

    If you did not request this, please ignore this email.

    Regards,
    Support Team
    """
    mail.send(msg)
