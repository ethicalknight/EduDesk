from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Teacher') # 'Admin', 'Teacher', 'Student', 'Parent'
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    
    subject = db.relationship('Subject', foreign_keys=[subject_id], backref='users_as_teachers')
    notifications = db.relationship('Notification', backref='user', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(50), nullable=True)
    semester = db.Column(db.Integer, nullable=True)
    batch = db.Column(db.String(50), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # For Student Login
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # For Parent Linkage
    
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref='students_mentored')
    user_account = db.relationship('User', foreign_keys=[user_id], backref='student_profile')
    parent = db.relationship('User', foreign_keys=[parent_id], backref='children')
    
    attendances = db.relationship('Attendance', backref='student', lazy=True)
    grades = db.relationship('Grade', backref='student', lazy=True)
    submissions = db.relationship('Submission', backref='student', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False, default=3)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Reference to User (Teacher)

    teacher = db.relationship('User', foreign_keys=[teacher_id], backref='subjects')
    
    attendances = db.relationship('Attendance', backref='subject', lazy=True)
    grades = db.relationship('Grade', backref='subject', lazy=True)
    timetables = db.relationship('Timetable', backref='subject', lazy=True)
    assignments = db.relationship('Assignment', backref='subject', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(10), nullable=False) # 'Present', 'Absent'
    fingerprint = db.Column(db.String(255), nullable=True)

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    assessment = db.Column(db.String(50), nullable=False) # e.g., 'Midterm', 'Assignment 1'
    score = db.Column(db.Float, nullable=False)
    max_score = db.Column(db.Float, nullable=False)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    day = db.Column(db.String(20), nullable=True) # e.g., 'Monday' (nullable for one-off)
    date = db.Column(db.Date, nullable=True) # For specific date events (one-off)
    start_time = db.Column(db.String(5), nullable=False) # e.g., '09:00'
    end_time = db.Column(db.String(5), nullable=False)   # e.g., '10:30'
    room = db.Column(db.String(50), nullable=False)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    author = db.relationship('User', backref='announcements')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False, default='info') # 'info', 'success', 'warning', 'error'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    deadline = db.Column(db.DateTime, nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship('Submission', backref='assignment', lazy=True)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    score = db.Column(db.Float, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
