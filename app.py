import os
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Student, Subject, Attendance, Grade, Timetable
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hackathon_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///edudesk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def create_dummy_data():
    if Student.query.first() is None:
        s1 = Student(roll_number="CS101", name="Alice Smith", email="alice@example.com", phone="1234567890", department="Computer Science", semester=3)
        s2 = Student(roll_number="CS102", name="Bob Johnson", email="bob@example.com", phone="0987654321", department="Computer Science", semester=3)
        s3 = Student(roll_number="CS103", name="Charlie Brown", email="charlie@example.com", phone="1112223333", department="Computer Science", semester=3)
        
        sub1 = Subject(code="CS201", name="Data Structures", credits=4)
        sub2 = Subject(code="CS202", name="Web Development", credits=3)

        db.session.add_all([s1, s2, s3, sub1, sub2])
        db.session.commit()

        t1 = Timetable(subject_id=sub1.id, day="Monday", start_time="09:00", end_time="10:30", room="Room 101")
        t2 = Timetable(subject_id=sub2.id, day="Monday", start_time="11:00", end_time="12:30", room="Lab 1")
        t3 = Timetable(subject_id=sub1.id, day="Wednesday", start_time="09:00", end_time="10:30", room="Room 101")
        
        db.session.add_all([t1, t2, t3])
        db.session.commit()

        g1 = Grade(student_id=s1.id, subject_id=sub1.id, assessment="Midterm", score=85, max_score=100)
        g2 = Grade(student_id=s2.id, subject_id=sub1.id, assessment="Midterm", score=92, max_score=100)
        
        db.session.add_all([g1, g2])
        db.session.commit()

with app.app_context():
    db.create_all()
    create_dummy_data()

@app.route('/')
def dashboard():
    total_students = Student.query.count()
    total_subjects = Subject.query.count()
    
    # Calculate overall attendance percentage (dummy logic for display)
    total_attendance_records = Attendance.query.count()
    present_records = Attendance.query.filter_by(status='Present').count()
    attendance_percentage = int((present_records / total_attendance_records * 100)) if total_attendance_records > 0 else 0
    
    recent_attendance = Attendance.query.order_by(Attendance.date.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                           total_students=total_students, 
                           total_subjects=total_subjects, 
                           attendance_percentage=attendance_percentage,
                           recent_attendance=recent_attendance)

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    subjects = Subject.query.all()
    students = Student.query.all()
    
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        date_str = request.form.get('date')
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('attendance'))
        
        for student in students:
            status = request.form.get(f'status_{student.id}')
            if status:
                existing = Attendance.query.filter_by(student_id=student.id, subject_id=subject_id, date=date_obj).first()
                if existing:
                    existing.status = status
                else:
                    new_attendance = Attendance(student_id=student.id, subject_id=subject_id, date=date_obj, status=status)
                    db.session.add(new_attendance)
        db.session.commit()
        flash('Attendance updated successfully!', 'success')
        return redirect(url_for('attendance'))
    
    return render_template('attendance.html', subjects=subjects, students=students, today=datetime.utcnow().date())

@app.route('/grades', methods=['GET', 'POST'])
def grades():
    subjects = Subject.query.all()
    students = Student.query.all()
    all_grades = Grade.query.join(Student).join(Subject).order_by(Grade.id.desc()).all()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        subject_id = request.form.get('subject_id')
        assessment = request.form.get('assessment')
        score = request.form.get('score')
        max_score = request.form.get('max_score')
        
        new_grade = Grade(student_id=student_id, subject_id=subject_id, assessment=assessment, score=score, max_score=max_score)
        db.session.add(new_grade)
        db.session.commit()
        flash('Grade added successfully!', 'success')
        return redirect(url_for('grades'))
        
    return render_template('grades.html', subjects=subjects, students=students, grades=all_grades)

@app.route('/students')
def students():
    all_students = Student.query.all()
    return render_template('students.html', students=all_students)

@app.route('/timetable')
def timetable():
    schedule = Timetable.query.join(Subject).order_by(Timetable.day, Timetable.start_time).all()
    return render_template('timetable.html', schedule=schedule)

if __name__ == '__main__':
    app.run(debug=True)
