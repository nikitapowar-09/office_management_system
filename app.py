from flask import Flask, render_template, request, redirect, url_for, flash
from flask import Flask, render_template, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from itsdangerous import URLSafeTimedSerializer
import smtplib
from sqlalchemy.orm import joinedload
from flask_mail import Mail, Message
from email_helper import generate_temp_password, send_login_email, send_reset_email, generate_reset_token,send_email, verify_reset_token, send_password_change_confirmation
from datetime import datetime, timedelta
import re,os
import uuid
from email.mime.text import MIMEText
from models import db, Employee, Department, User, Project, Task, Meeting, MeetingAttendee, Attendance, Notification, Admin, AdminLeaveApproval,LeaveRequest

def create_app():
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

    # Debugging
    if 'SQLALCHEMY_DATABASE_URI' in app.config:
        print("Database URI Set:", app.config['SQLALCHEMY_DATABASE_URI'])
    else:
        print("❌ ERROR: SQLALCHEMY_DATABASE_URI is NOT set!")

    # Initialize database
    db.init_app(app)

    # Initialize extensions inside create_app()
    Migrate(app, db)
    # CSRFProtect(app)
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

def send_verification_email(user_email, token):
    verification_url = f"http://localhost:5000/verify_email/{token}"  # Modify with your actual domain

    # Create the email message
    msg = Message(
        'Verify Your Email',
        recipients=[user_email]
    )
    msg.body = f"Click the link to verify your email: {verification_url}"

    # Send the email
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")

#-----------------login-----------------

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
    print("Session after login:", session)

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('No account found with that email.', 'danger')
            return redirect(url_for('login'))

        if user.check_password(password):
            login_user(user)  
            flash('Login successful!', 'success')

            user.last_login = datetime.utcnow()
            db.session.commit()

            # Store employee_id and username in session
            session['_user_id'] = user.user_id
            session['employee_id'] = user.user_id  # Store employee_id
            session['username'] = user.username  # Store username (new)

            if user.role == 'admin':
                session['admin_id'] = user.user_id 

            return redirect(url_for('admin_dashboard')) if user.role == 'admin' else redirect(url_for('employee_dashboard'))
        else:
            flash('Incorrect password.', 'danger')

    return render_template('login.html', user=None)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

#--------------------------Reset Pssword------------------------------
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)

    if not email:
        flash('Invalid or expired token.', 'danger')
        return redirect(url_for('request_password_reset'))
    
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(request.url)

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('request_password_reset'))

    if request.method == 'POST':
        new_password = request.form['password']
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        send_password_change_confirmation(email)
        flash('Password updated successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password_form.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def request_password_reset():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        
        if user:
            send_reset_email(email)
            flash('An email with reset instructions has been sent.', 'info')
            return redirect(url_for('login'))
        else:
            flash('No account found with that email.', 'danger')

    return render_template('reset_request.html')

#------------------------Add department--------------------
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

#--------------------Dashboard---------------------

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

#----------------------------manage employees------------------

@app.route('/employees')
@login_required
def employee_list():
    employees = Employee.query.all()  # Fetches full Employee objects
    return render_template('employee_list.html', employees=employees)

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

        # ✅ Check if the employee already exists
        existing_employee = Employee.query.filter_by(email=email).first()
        if existing_employee:
            flash('Employee already exists.', 'danger')
            return redirect(url_for('employee_create'))

        # ✅ Generate username and temporary password
        username = request.form.get('username', email.split('@')[0])
        temp_password = generate_temp_password()
        password_hash = generate_password_hash(temp_password)

        # ✅ Create Employee record
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
            db.session.commit()  # Ensure Employee is saved first
            print("✅ Employee saved successfully.")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Employee creation failed: {e}")
            flash(f'Error creating employee: {e}', 'danger')
            return redirect(url_for('employee_create'))

        # ✅ Fetch Employee again to ensure it exists in DB
        saved_employee = Employee.query.filter_by(email=email).first()
        if not saved_employee:
            flash('Employee record not found after commit.', 'danger')
            return redirect(url_for('employee_create'))

        # ✅ Check if User with this employee_id already exists
        existing_user = User.query.filter_by(employee_id=saved_employee.employee_id).first()
        if existing_user:
            flash('This Employee already has a User account.', 'danger')
            return redirect(url_for('employee_create'))

        # ✅ Create User record for login
        try:
            new_user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role="employee",
                is_verified=True,
                employee_id=saved_employee.employee_id
            )

            db.session.add(new_user)
            db.session.commit()
            print("✅ User account created successfully.")

        except Exception as e:
            db.session.rollback()
            print(f"❌ User creation failed: {e}")
            flash(f'Error creating user account: {e}', 'danger')
            return redirect(url_for('employee_create'))

        # ✅ Send login credentials email AFTER successful transactions
        email_sent = send_login_email(email, username, temp_password)
        if email_sent:
            flash('Login credentials sent to employee email successfully!', 'success')
            print("📧 Email sent successfully.")
        else:
            flash('Failed to send login email.', 'danger')
            print("❌ Email failed to send.")

        return redirect(url_for('employee_list'))

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
            print('Error:', e)
            flash(f'Error creating employee: {e}', 'danger')

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

#-------------------- Mark Attendance-----------------------
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    try:
        first_name, last_name = current_user.username.split(" ", 1)
    except ValueError:
        first_name = current_user.username
        last_name = ""

    employee = Employee.query.filter_by(username=current_user.username).first()
    if not employee:
        flash("Employee record not found.", "danger")
        return redirect(url_for('index'))

    today = datetime.utcnow().date()
    attendance = Attendance.query.filter_by(employee_id=employee.employee_id, date=today).first()

    if request.method == 'POST':
        action = request.form.get('action')
        current_time = datetime.utcnow().time().replace(microsecond=0)  # ⬅️ Remove microseconds here

        if action == 'check-in' and not attendance:
            new_attendance = Attendance(
                employee_id=employee.employee_id,
                date=today,
                time_in=current_time
            )
            db.session.add(new_attendance)
            db.session.commit()
            flash("Checked in successfully!", "success")

        elif action == 'check-out' and attendance and not attendance.time_out:
            attendance.time_out = current_time  # ⬅️ Use the same microsecond-free time
            db.session.commit()
            flash("Checked out successfully!", "success")

        else:
            flash("Invalid action or already marked!", "warning")

        return redirect(url_for('mark_attendance'))

    return render_template('Emp_Attendance.html', attendance=attendance)


@app.route('/admin/attendance')
@login_required
def admin_attendance():
    if getattr(current_user, 'role', None) != 'admin':
        flash("Unauthorized Access!", "danger")
        return redirect(url_for('index'))

    attendance_records = Attendance.query.order_by(Attendance.date.desc()).all()
    return render_template('admin_attendance.html', attendance_records=attendance_records)

#-----------------meetings---------------------

@app.route('/schedule_meeting', methods=['GET', 'POST'])
def schedule_meeting():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            date_time_str = request.form.get('date_time')
            location = request.form.get('location')
            attendee_ids = request.form.getlist('attendees')

            if not title or not date_time_str or not location:
                return "Missing required fields", 400

            try:
                date_time = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                return "Invalid date format", 400

            fake_link = "https://fakemeetinglink.com"
            organizer_id = session.get('admin_id')
            if not organizer_id:
                return "Organizer (admin) not logged in", 403

            meeting = Meeting(title=title, date_time=date_time, location=location, link=fake_link, organizer_id=organizer_id)
            db.session.add(meeting)
            db.session.commit()

            for emp_id in attendee_ids:
                try:
                    emp_id = int(emp_id)
                    employee = Employee.query.get(emp_id)
                    if employee:
                        attendee = MeetingAttendee(meeting_id=meeting.id, employee_id=employee.employee_id)
                        db.session.add(attendee)
                        # Optional: wrap this in try/except if send_email fails
                        send_email(employee.email, f"{employee.first_name} {employee.last_name}", title, date_time, fake_link)
                except Exception as e:
                    print(f"Error adding attendee {emp_id}: {e}")

            db.session.commit()
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            print(f"Error during POST in schedule_meeting: {e}")
            return f"Internal Server Error: {str(e)}", 500

    # GET method
    employees = Employee.query.all()
    return render_template('scheduled_meeting.html', employees=employees)


@app.route('/employee/meetings')
@login_required
def employee_meetings():
    employee_id = current_user.employee_id
    meetings = db.session.query(Meeting).join(MeetingAttendee).filter(MeetingAttendee.employee_id == employee_id).all()
    return render_template('employee_meeting.html', meetings=meetings)

#---------------------leave----------
@app.route('/leave_form')
@login_required
def leave_form():
    employee_id = session.get('employee_id')
    if not employee_id:
        flash("Session error: Employee ID not found!", "danger")
        return redirect(url_for('employee_dashboard'))

    all_requests = AdminLeaveApproval.query.filter_by(employee_id=employee_id).order_by(AdminLeaveApproval.leave_date.desc()).all()
    return render_template('Leave_application.html', employee_id=employee_id, requests=all_requests)

@app.route('/request_holiday', methods=['POST'])
@login_required
def request_holiday():
    employee_id = request.form.get('employee_id')
    username = request.form.get('username')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    reason = request.form.get('reason')

    if not start_date or not end_date:
        flash("Start and end dates are required!", "danger")
        return redirect(url_for('leave_form'))
    
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

    current_date = start_date_obj
    while current_date <= end_date_obj:
        leave = AdminLeaveApproval(
            employee_id=employee_id,
            username=username,
            leave_date=current_date,
            reason=reason
        )
        db.session.add(leave)
        current_date += timedelta(days=1)

    db.session.commit()
    flash("Leave request submitted successfully!", "success")  
    return redirect(url_for('view_leave_status'))

@app.route('/view_leave_status')
@login_required
def view_leave_status():
    employee_id = session.get('employee_id')
    leaves = AdminLeaveApproval.query.filter_by(employee_id=employee_id).order_by(AdminLeaveApproval.leave_date.desc()).all()
    return render_template('view_leave_status.html', leaves=leaves)

# -------------------- ADMIN - Leave--------------------

@app.route('/manage_leaves')
@login_required
def manage_leaves():
    leaves = AdminLeaveApproval.query.order_by(AdminLeaveApproval.leave_date.desc()).all()
    return render_template('Leave_Request.html', leaves=leaves)

@app.route('/approve_holiday/<int:leave_id>')
@login_required
def approve_holiday(leave_id):
    leave = AdminLeaveApproval.query.get_or_404(leave_id)
    leave.status = 'Approved'
    leave.action = 'Approved'
    db.session.commit()
    flash("Leave approved.", "success")
    return redirect(url_for('manage_leaves'))

@app.route('/reject_holiday/<int:leave_id>')
@login_required
def reject_holiday(leave_id):
    leave = AdminLeaveApproval.query.get_or_404(leave_id)
    leave.status = 'Rejected'
    leave.action = 'Rejected'
    db.session.commit()
    flash("Leave rejected.", "danger")
    return redirect(url_for('manage_leaves'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    