from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Teacher') # 'Admin' or 'Teacher'
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    
    subject = db.relationship('Subject', backref='teachers')

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
    
    teacher = db.relationship('User', backref='students')
    
    attendances = db.relationship('Attendance', backref='student', lazy=True)
    grades = db.relationship('Grade', backref='student', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False, default=3)
    
    attendances = db.relationship('Attendance', backref='subject', lazy=True)
    grades = db.relationship('Grade', backref='subject', lazy=True)
    timetables = db.relationship('Timetable', backref='subject', lazy=True)

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
    day = db.Column(db.String(20), nullable=False) # e.g., 'Monday'
    start_time = db.Column(db.String(5), nullable=False) # e.g., '09:00'
    end_time = db.Column(db.String(5), nullable=False)   # e.g., '10:30'
    room = db.Column(db.String(50), nullable=False)
