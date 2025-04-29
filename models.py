from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///office_management.db'
db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # nullable, because admin doesn't set it
    role = db.Column(db.String(255), default='employee')
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.employee_id'), unique=True, nullable=True)
    employee = db.relationship("Employee", back_populates="user", uselist=False)
    last_login = db.Column(db.DateTime)
    is_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    def get_id(self):
        return str(self.user_id)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def generate_verification_token():
        return serializer.dumps(email, salt='email-verification')
    
    

class Admin(db.Model):
    admin_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('username', name='uq_admin_username'),
        db.UniqueConstraint('email', name='uq_admin_email')
    )
    
class Employee(db.Model):
    __tablename__ = 'employee'
    employee_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False) 
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.department_id'))
    department = db.relationship('Department', backref='employees')
    position = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    hire_date = db.Column(db.Date)
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship("User", back_populates="employee", uselist=False, cascade="all, delete")

    def set_username(self):
        self.username = self.first_name.lower()

class Department(db.Model):
    department_id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(255), unique=True, nullable=False)
    location = db.Column(db.String(255))

class Project(db.Model):
    project_id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    description = db.Column(db.Text)
    project_manager_id = db.Column(db.Integer, db.ForeignKey('employee.employee_id'))

class Task(db.Model):
    task_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.project_id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('employee.employee_id'))
    task_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(255))

class Meeting(db.Model):
    __tablename__ = 'meetings'

    meeting_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('employee.employee_id'), nullable=False)
    attendees = db.relationship('MeetingAttendee', backref='meeting', lazy='dynamic')

class MeetingAttendee(db.Model):
    __tablename__ = 'meeting_attendees'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.meeting_id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.employee_id'), nullable=False)
    employee = db.relationship('Employee', backref='attendee_meetings')

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False) 
    leave_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Accept/Reject

class AdminLeaveApproval(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer,  nullable=False)
    username = db.Column(db.String(50), nullable=False) 
    leave_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Accept/Reject
    action = db.Column(db.String(20), default="Pending")  # Admin action

class Attendance(db.Model):
    attendance_id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.employee_id'))
    date = db.Column(db.Date)
    time_in = db.Column(db.Time)
    time_out = db.Column(db.Time)

class Notification(db.Model):
    notification_id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.employee_id'))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

