from flask import Flask, render_template, request, redirect, url_for, flash
from flask import Flask, render_template, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from itsdangerous import URLSafeTimedSerializer
import smtplib
from flask_mail import Mail, Message
from datetime import datetime
import re,os
import uuid
from email.mime.text import MIMEText
from models import db, Employee, Department, User, Project, Task, Meeting, MeetingAttendee, Attendance, Notification, Admin  # Import your models

def create_app():
    app = Flask(__name__)
    
    # Flask Configurations
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'nikitapowar09@gmail.com'
    app.config['MAIL_PASSWORD'] = 'idcb roep ozwb mjjd'
    app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'
    app.config['SECRET_KEY'] = 'Nikita@09'  
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, "instance", "office_management.db")
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Debugging
    if 'SQLALCHEMY_DATABASE_URI' in app.config:
        print("Database URI Set:", app.config['SQLALCHEMY_DATABASE_URI'])
    else:
        print("❌ ERROR: SQLALCHEMY_DATABASE_URI is NOT set!")


    # Initialize database
    db.init_app(app)

    # Initialize extensions inside create_app()
    Migrate(app, db)
    CSRFProtect(app)
    mail = Mail(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app, serializer  # Ensure the function returns the Flask app instance

# Create the app
app, serializer = create_app()  # Now `app` is not None

# Email validation function
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email)


@app.route('/')
def landing_page():
    return render_template('landing_page.html')

@app.route('/verify/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verification_token=token).first()
    
    if user:
        user.is_verified = True
        user.email_verification_token = None  # Remove token after verification
        db.session.commit()
        flash('Your email has been verified!', 'success')
        return redirect(url_for('login'))
    
    flash('Invalid or expired token.', 'danger')
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('No account found with that email.', 'danger')
            return redirect(url_for('login'))

        if not user.is_verified:
            flash('Please verify your email before logging in.', 'warning')
            return redirect(url_for('login'))
        
        if user.check_password(password):
            login_user(user)  
            flash('Login successful!', 'success')

            user.last_login = datetime.utcnow()
            db.session.commit()

            return redirect(url_for('admin_dashboard')) if user.role == 'admin' else redirect(url_for('employee_dashboard'))
        else:
            flash('Incorrect password.', 'danger')

    return render_template('login.html', user=None)   

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Fetch employees who do not have an associated user account
    employees = Employee.query.filter(~Employee.user.has()).all()

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        employee_id = request.form.get('employee_id') if role == 'employee' else None  

        # Ensure valid role selection
        if role not in ['admin', 'employee']:
            flash('Invalid role selected.', 'danger')
            return render_template('signup.html', employees=employees)

        # Ensure username is unique
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('signup.html', employees=employees)

        # Ensure password confirmation
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html', employees=employees)

        # Employee-specific checks
        if role == 'employee':
            if not employee_id:
                flash('Employee ID is required for employee role.', 'danger')
                return render_template('signup.html', employees=employees)

            # Fetch employee from DB
            employee = Employee.query.get(employee_id)
            if not employee:
                flash('Invalid Employee ID.', 'danger')
                return render_template('signup.html', employees=employees)

            # Check if employee is already linked to a user
            if employee.user is not None:
                flash('Employee already has a user account.', 'danger')
                return render_template('signup.html', employees=employees)

            # Use employee's email for the user account
            email = employee.email
        else:
            email = request.form.get('email')

            # Ensure email is unique
            if User.query.filter_by(email=email).first():
                flash('Email already exists.', 'danger')
                return render_template('signup.html', employees=employees)

        # Generate verification token
        verification_token = User.generate_verification_token()

        # Create new user entry only after all checks pass
        new_user = User(
            username=username, 
            email=email, 
            role=role, 
            employee_id=employee_id, 
            email_verification_token=verification_token
        )

        new_user.set_password(password)  # Store hashed password
        db.session.add(new_user)

        # Link user to employee if applicable
        if role == 'employee':
            employee.user = new_user  

        db.session.commit()

        send_verification_email(email, verification_token)

        flash('Signup successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('verify_email_page'))  

    return render_template('signup.html', employees=employees)

# Function to send a verification email
def send_verification_email(user_email, token):
    verification_url = f"http://localhost:5000/verify_email/{token}"
    msg = Message(
        'Verify Your Email',
        sender='noreply@yourwebsite.com',
        recipients=[user_email]
    )
    msg.body = f"Click the link to verify your email: {verification_url}"
    mail.send(msg)

@app.route('/resend_verification', methods=['POST'])
def resend_verification():
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()

    if user and not user.is_verified:
        send_verification_email(email)  # Resend email
        flash('A new verification email has been sent.', 'info')
    else:
        flash('Invalid request or email already verified.', 'danger')

    return redirect(url_for('verify_email_page'))

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Forgot Password
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()
        if user:
            token = secrets.token_urlsafe(16)
            # Store the token with the user (e.g., in a password_reset_token column)
            user.password_reset_token = token
            user.password_reset_expiration = datetime.utcnow() + datetime.timedelta(hours=1) #one hour expiration
            db.session.commit()

            #send email
            send_reset_email(user.email, token) #Implement this function

            flash('Reset link sent to your email.', 'success')
            return redirect(url_for('login'))
        else:
            flash("Username not found", 'danger')

    return render_template('forgot_password.html')

# Reset Password
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(password_reset_token=token).first()
    if user and user.password_reset_expiration > datetime.utcnow():
        if request.method == 'POST':
            password = request.form['password']
            user.set_password(password)
            user.password_reset_token = None
            user.password_reset_expiration = None
            db.session.commit()
            flash('Password reset successfully!', 'success')
            return redirect(url_for('login'))

        return render_template('reset_password.html', token=token)
    else:
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('login'))

@app.route('/add_department', methods=['GET', 'POST'])
def add_department():
    if request.method == 'POST':
        department_name = request.form.get('department_name')
        location = request.form.get('location')

        if department_name:  # Ensure department name is provided
            new_department = Department(department_name=department_name, location=location)
            try:
                db.session.add(new_department)
                db.session.commit()
                flash("Department added successfully!", "success")
                return redirect(url_for('add_department'))  # Redirect after saving
            except Exception as e:
                db.session.rollback()
                flash(f"Error: {str(e)}", "danger")
        else:
            flash("Department name is required!", "warning")

    return render_template('add_department.html')

@app.route('/employees')
@login_required
def employee_list():
    employees = Employee.query.all()  # Fetches full Employee objects
    return render_template('employee_list.html', employees=employees)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    meetings = Meeting.query.order_by(Meeting.date_time.desc()).all()
    
    print(f"Admin Dashboard - Current User: {current_user.email}, Role: {current_user.role}")

    return render_template('admin_dashboard.html', meetings=meetings)

@app.route('/employee_dashboard')
@login_required
def employee_dashboard():
    print(f"Employee Dashboard - Current User: {current_user.email}, Role: {current_user.role}")  # Debugging
    return render_template('employee_dashboard.html')
@app.route('/employees/new', methods=['GET', 'POST'])
@login_required
def employee_create():
    departments = Department.query.all()
    
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        department_id = request.form['department_id']
        position = request.form['position']
        email = request.form['email']
        phone_number = request.form['phone_number']
        hire_date = datetime.strptime(request.form['hire_date'], '%Y-%m-%d').date() if request.form['hire_date'] else None
        address = request.form['address']
        is_active = True if 'is_active' in request.form else False

        # ✅ Check if the employee already has a user account
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Employee already has a user account.', 'danger')
            return redirect(url_for('employee_create'))  # Redirect to form

        # ✅ Auto-generate username if not provided
        username = request.form.get('username', email.split('@')[0])  

        password_hash = generate_password_hash("defaultpassword")  

        # ✅ Create Employee
        new_employee = Employee(
            username=username,  
            first_name=first_name,
            last_name=last_name,
            department_id=department_id,
            position=position,
            email=email,
            phone_number=phone_number,
            hire_date=hire_date,
            address=address,
            is_active=is_active
        )
        
        try:
            db.session.add(new_employee)
            db.session.flush()  # Flush to get employee_id
            
            # ✅ Create User for the Employee
            new_user = User(
                username=username,  
                email=email,
                password_hash=password_hash,
                role="employee",
                is_verified=True,
                employee_id=new_employee.employee_id  # Link to Employee
            )
            
            db.session.add(new_user)
            db.session.commit()  
            
            flash('Employee created successfully!', 'success')
            return redirect(url_for('employee_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating employee: {e}', 'danger')

    return render_template('employee_form.html', departments=departments)

@app.route('/employees/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def employee_edit(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    departments = Department.query.all()

    if request.method == 'POST':
        employee.first_name = request.form['first_name']
        employee.last_name = request.form['last_name']
        employee.department_id = request.form['department_id']
        employee.position = request.form['position']
        employee.email = request.form['email']
        employee.phone_number = request.form['phone_number']
        employee.hire_date = datetime.strptime(request.form['hire_date'], '%Y-%m-%d').date() if request.form['hire_date'] else None
        employee.address = request.form['address']
        employee.is_active = True if 'is_active' in request.form else False

        try:
            db.session.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('employee_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating employee: {e}', 'danger')

    return render_template('employee_form.html', employee=employee, departments = departments)

@app.route('/employees/delete/<int:employee_id>')
@login_required
def employee_delete(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    try:
        db.session.delete(employee)
        db.session.commit()
        flash('Employee deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting employee: {e}', 'danger')
    return redirect(url_for('employee_list'))

# Mark Attendance (Employee)
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    first_name, last_name = current_user.username.split(" ", 1)  # Splits "John Doe" into "John", "Doe"
    employee = Employee.query.filter_by(username=current_user.username).first()
    today = datetime.utcnow().date()
    attendance = Attendance.query.filter_by(employee_id=employee.employee_id, date=today).first()

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'check-in' and not attendance:
            new_attendance = Attendance(
                employee_id=employee.employee_id,
                date=today,
                time_in=datetime.utcnow().time()
            )
            db.session.add(new_attendance)
            db.session.commit()
            flash("Checked in successfully!", "success")

        elif action == 'check-out' and attendance and not attendance.time_out:
            attendance.time_out = datetime.utcnow().time()
            db.session.commit()
            flash("Checked out successfully!", "success")

        else:
            flash("Invalid action!", "danger")

        return redirect(url_for('mark_attendance'))

    return render_template('attendance.html', attendance=attendance)

# Admin Dashboard (View Attendance)
@app.route('/admin/attendance')
@login_required
def admin_attendance():
    if current_user.role != 'admin':
        flash("Unauthorized Access!", "danger")
        return redirect(url_for('index'))

    attendance_records = Attendance.query.all()
    return render_template('admin_attendance.html', attendance_records=attendance_records)

#meetings
@app.route('/admin/meetings', methods=['GET', 'POST'])
@login_required
def admin_meetings():
    if request.method == 'POST':
        try:
            title = request.form['title']
            date_time = datetime.strptime(request.form['date_time'], '%Y-%m-%dT%H:%M')
            location = request.form['location']
            organizer_id = current_user.employee_id
            attendees = request.form.getlist('attendees')  # List of selected employee IDs

            # Create and save new meeting
            new_meeting = Meeting(title=title, date_time=date_time, location=location, organizer_id=organizer_id)
            db.session.add(new_meeting)
            db.session.flush()  # Flush to get the meeting ID before committing
            
            print(f"New Meeting Created: {new_meeting.title}, ID: {new_meeting.meeting_id}")  # Debugging

            # Assign attendees and send notifications
            if attendees:
                for employee_id in attendees:
                    existing_attendee = MeetingAttendee.query.filter_by(
                        meeting_id=new_meeting.meeting_id, employee_id=employee_id
                    ).first()
                    
                    if not existing_attendee:  # Avoid duplicates
                        attendee = MeetingAttendee(meeting_id=new_meeting.meeting_id, employee_id=employee_id)
                        db.session.add(attendee)

                        # Fetch employee email and send notification
                        employee = Employee.query.get(employee_id)
                        if employee:
                            send_meeting_notification(employee.email, new_meeting)

            db.session.commit()
            flash('Meeting scheduled successfully, and notifications sent!', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Error scheduling meeting: {str(e)}', 'danger')

        return redirect(url_for('admin_meetings'))  # Refresh the page to reflect new meetings

    # Fetch all employees and scheduled meetings with attendees
    employees = Employee.query.all()
    meetings = Meeting.query.options(
        joinedload(Meeting.attendees).joinedload(MeetingAttendee.employee)
    ).order_by(Meeting.date_time.asc()).all()  # Sorted by date

    return render_template('scheduled_meeting.html', employees=employees, meetings=meetings)


@app.route('/employee/meetings')
@login_required
def employee_meetings():
    employee_id = current_user.employee_id
    meetings = db.session.query(Meeting).join(MeetingAttendee).filter(MeetingAttendee.employee_id == employee_id).all()
    return render_template('employee_meeting.html', meetings=meetings)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    