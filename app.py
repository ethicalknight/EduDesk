import os
import csv
from io import StringIO
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Student, Subject, Attendance, Grade, Timetable
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hackathon_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///edudesk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000 # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def get_serializer():
    return URLSafeTimedSerializer(app.config['SECRET_KEY'])

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_dummy_data():
    if User.query.first() is None:
        admin = User(name="Admin", email="admin@edudesk.com", password_hash=generate_password_hash("admin123"), role="Admin")
        teacher = User(name="Teacher", email="teacher@edudesk.com", password_hash=generate_password_hash("teacher123"), role="Teacher")
        db.session.add_all([admin, teacher])
        db.session.commit()

    if Subject.query.first() is None:
        teacher = User.query.filter_by(email="teacher@edudesk.com").first()
        t_id = teacher.id if teacher else None
        sub1 = Subject(code="CS201", name="Data Structures", credits=4, teacher_id=t_id)
        sub2 = Subject(code="CS202", name="Web Development", credits=3, teacher_id=t_id)
        db.session.add_all([sub1, sub2])
        db.session.commit()

    if Student.query.first() is None:
        teacher = User.query.filter_by(email="teacher@edudesk.com").first()
        t_id = teacher.id if teacher else None
        
        s1 = Student(roll_number="CS101", name="Alice Smith", email="alice@example.com", phone="1234567890", department="Computer Science", semester=3, teacher_id=t_id)
        s2 = Student(roll_number="CS102", name="Bob Johnson", email="bob@example.com", phone="0987654321", department="Computer Science", semester=3, teacher_id=t_id)
        s3 = Student(roll_number="CS103", name="Charlie Brown", email="charlie@example.com", phone="1112223333", department="Computer Science", semester=3, teacher_id=None)
        
        db.session.add_all([s1, s2, s3])
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

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Check if a user with that email already exists
    if User.query.filter_by(email=email).first():
        flash('Email already exists. Please log in.', 'error')
        return redirect(url_for('login'))
        
    # By default, external signups become Teachers
    new_user = User(name=name, email=email, password_hash=generate_password_hash(password), role='Teacher')
    db.session.add(new_user)
    db.session.commit()
    flash('Account created successfully! You can now login.', 'success')
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    total_students = Student.query.count()
    total_subjects = Subject.query.count()
    
    total_attendance_records = Attendance.query.count()
    present_records = Attendance.query.filter_by(status='Present').count()
    absent_records = total_attendance_records - present_records
    attendance_percentage = int((present_records / total_attendance_records * 100)) if total_attendance_records > 0 else 0
    
    import datetime as dt
    today = dt.datetime.utcnow().date()
    dates = [(today - dt.timedelta(days=i)) for i in range(6, -1, -1)]
    date_labels = [d.strftime('%b %d') for d in dates]
    trend_data = []
    for d in dates:
        trend_data.append(Attendance.query.filter_by(date=d, status='Present').count())
        
    students = Student.query.all()
    at_risk_students = []
    for st in students:
        st_total = Attendance.query.filter_by(student_id=st.id).count()
        if st_total >= 3:
            st_present = Attendance.query.filter_by(student_id=st.id, status='Present').count()
            perc = (st_present / st_total) * 100
            if perc < 75:
                at_risk_students.append({'name': st.name, 'roll': st.roll_number, 'percentage': int(perc)})
    at_risk_students = sorted(at_risk_students, key=lambda x: x['percentage'])[:5]
    
    recent_attendance = Attendance.query.order_by(Attendance.date.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                           total_students=total_students, 
                           total_subjects=total_subjects, 
                           attendance_percentage=attendance_percentage,
                           recent_attendance=recent_attendance,
                           present_records=present_records,
                           absent_records=absent_records,
                           date_labels=date_labels,
                           trend_data=trend_data,
                           at_risk_students=at_risk_students)

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    subjects = Subject.query.all()
    if current_user.role == 'Admin':
        students = Student.query.all()
    else:
        students = Student.query.filter_by(teacher_id=current_user.id).all()
    
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
@login_required
def grades():
    subjects = Subject.query.all()
    if current_user.role == 'Admin':
        students = Student.query.all()
        all_grades = Grade.query.join(Student).join(Subject).order_by(Grade.id.desc()).all()
    else:
        students = Student.query.filter_by(teacher_id=current_user.id).all()
        all_grades = Grade.query.join(Student).join(Subject).filter(Student.teacher_id==current_user.id).order_by(Grade.id.desc()).all()
    
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
@login_required
def students():
    if current_user.role == 'Admin':
        all_students = Student.query.all()
        teachers = User.query.filter_by(role='Teacher').all()
    else:
        all_students = Student.query.filter_by(teacher_id=current_user.id).all()
        teachers = []
    return render_template('students.html', students=all_students, teachers=teachers)

@app.route('/add_student', methods=['POST'])
@login_required
def add_student():
    name = request.form.get('name')
    roll_number = request.form.get('roll_number')
    email = request.form.get('email')
    phone = request.form.get('phone')
    department = request.form.get('department')
    semester = request.form.get('semester')
    
    if current_user.role == 'Admin':
        teacher_id = request.form.get('teacher_id') or None
    else:
        teacher_id = current_user.id

    existing = Student.query.filter_by(roll_number=roll_number).first()
    if existing:
        flash('Student with this roll number already exists.', 'error')
    else:
        new_student = Student(roll_number=roll_number, name=name, email=email, phone=phone, department=department, semester=semester, teacher_id=teacher_id)
        db.session.add(new_student)
        db.session.commit()
        flash('Student added successfully!', 'success')
        
    return redirect(url_for('students'))

@app.route('/timetable')
@login_required
def timetable():
    schedule = Timetable.query.join(Subject).order_by(Timetable.day, Timetable.start_time).all()
    subjects = Subject.query.all()
    return render_template('timetable.html', schedule=schedule, subjects=subjects)

@app.route('/add_timetable', methods=['POST'])
@login_required
def add_timetable():
    if current_user.role != 'Admin':
        flash('Access Denied', 'error')
        return redirect(url_for('dashboard'))
        
    subject_id = request.form.get('subject_id')
    day = request.form.get('day')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    room = request.form.get('room')
    
    new_tt = Timetable(subject_id=subject_id, day=day, start_time=start_time, end_time=end_time, room=room)
    db.session.add(new_tt)
    db.session.commit()
    flash('Timetable entry added successfully!', 'success')
        
    return redirect(url_for('timetable'))

@app.route('/teachers')
@login_required
def teachers():
    if current_user.role != 'Admin':
        flash('Access Denied: Only Admins can view teachers.', 'error')
        return redirect(url_for('dashboard'))
    all_teachers = User.query.filter_by(role='Teacher').all()
    subjects = Subject.query.all()
    return render_template('teachers.html', teachers=all_teachers, subjects=subjects)

@app.route('/add_teacher', methods=['POST'])
@login_required
def add_teacher():
    if current_user.role != 'Admin':
        flash('Access Denied', 'error')
        return redirect(url_for('dashboard'))
        
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    subject_name = request.form.get('subject_name')
    
    subject_id = None
    if subject_name:
        subject = Subject.query.filter_by(name=subject_name).first()
        if not subject:
            subject = Subject(code=subject_name.upper().replace(' ', '_')[:20], name=subject_name, credits=3)
            db.session.add(subject)
            db.session.commit()
        subject_id = subject.id
    
    existing = User.query.filter_by(email=email).first()
    if existing:
        flash('User with this email already exists.', 'error')
    else:
        new_teacher = User(name=name, email=email, password_hash=generate_password_hash(password), role='Teacher', subject_id=subject_id)
        db.session.add(new_teacher)
        db.session.commit()
        flash('Teacher added successfully!', 'success')
        
    return redirect(url_for('teachers'))

@app.route('/generate_qr_token', methods=['POST'])
@login_required
def generate_qr_token():
    subject_id = request.form.get('subject_id')
    date_str = str(datetime.utcnow().date())
    lat = request.form.get('lat')
    lon = request.form.get('lon')
    
    s = get_serializer()
    payload = {'subject_id': subject_id, 'date': date_str, 'lat': lat, 'lon': lon}
    token = s.dumps(payload)
    
    qr_url = url_for('scan_qr', token=token, _external=True)
    return jsonify({'url': qr_url})

@app.route('/scan/<token>', methods=['GET', 'POST'])
def scan_qr(token):
    s = get_serializer()
    try:
        # Token valid for 60 seconds
        payload = s.loads(token, max_age=120)
        subject_id = payload['subject_id']
        date_str = payload['date']
        teacher_lat = payload.get('lat')
        teacher_lon = payload.get('lon')
    except SignatureExpired:
        return "This QR code has expired. Please ask the instructor for the latest code.", 400
    except BadTimeSignature:
        return "Invalid QR code.", 400

    subject = Subject.query.get(subject_id)
    if not subject:
        return "Invalid Subject", 400

    if request.method == 'POST':
        roll_number = request.form.get('roll_number')
        fingerprint = request.form.get('fingerprint')
        student_lat = request.form.get('lat')
        student_lon = request.form.get('lon')

        # Geofencing check
        if teacher_lat and teacher_lon and student_lat and student_lon:
            try:
                dist = haversine(float(teacher_lat), float(teacher_lon), float(student_lat), float(student_lon))
                if dist > 100:
                    flash(f"Geofence Alert: You are {int(dist)} meters away from the classroom. Attendance rejected.", 'error')
                    return redirect(url_for('scan_qr', token=token))
            except ValueError:
                pass # ignore parsing errors

        # Discourage Proxy attendance
        existing_fingerprint = Attendance.query.filter_by(
            subject_id=subject.id, 
            date=datetime.strptime(date_str, '%Y-%m-%d').date(), 
            fingerprint=fingerprint
        ).first()

        student = Student.query.filter_by(roll_number=roll_number).first()
        if not student:
            flash(f"Student with Roll No {roll_number} not found. Please contact admin.", 'error')
            return redirect(url_for('scan_qr', token=token))
            
        if existing_fingerprint and existing_fingerprint.student_id != student.id:
            flash("Proxy attendance detected. This device has already marked attendance for someone else.", "error")
            return redirect(url_for('scan_qr', token=token))

        existing_attendance = Attendance.query.filter_by(student_id=student.id, subject_id=subject.id, date=datetime.strptime(date_str, '%Y-%m-%d').date()).first()
        if existing_attendance:
            existing_attendance.status = 'Present'
            if not existing_attendance.fingerprint:
                existing_attendance.fingerprint = fingerprint
        else:
            new_attendance = Attendance(student_id=student.id, subject_id=subject.id, 
                                        date=datetime.strptime(date_str, '%Y-%m-%d').date(), 
                                        status='Present', fingerprint=fingerprint)
            db.session.add(new_attendance)
        
        db.session.commit()
        return "Attendance Marked Successfully as Present!"

    return render_template('smart_form.html', subject=subject, token=token)

@app.route('/cron/daily_absent_hook', methods=['POST'])
def daily_absent_hook():
    today = datetime.utcnow().date()
    students = Student.query.all()
    
    # We find all subjects that had at least one attendance entry today
    active_subjects_today = db.session.query(Attendance.subject_id).filter_by(date=today).distinct().all()
    active_subject_ids = [s[0] for s in active_subjects_today]

    for subject_id in active_subject_ids:
        for student in students:
            # We assume all students need to be marked absent if they didn't attend
            att = Attendance.query.filter_by(student_id=student.id, subject_id=subject_id, date=today).first()
            if not att:
                absent = Attendance(student_id=student.id, subject_id=subject_id, date=today, status='Absent')
                db.session.add(absent)
                
    db.session.commit()
    return jsonify({"message": "Daily absent hook completed", "date": str(today)})

@app.route('/reports')
@login_required
def reports():
    student_id = request.args.get('student_id')
    students = Student.query.all()
    
    selected_student = None
    present_days = 0
    absent_days = 0
    student_grades = []
    
    if student_id:
        selected_student = Student.query.get(student_id)
        if selected_student:
            present_days = Attendance.query.filter_by(student_id=student_id, status='Present').count()
            absent_days = Attendance.query.filter_by(student_id=student_id, status='Absent').count()
            student_grades = Grade.query.filter_by(student_id=student_id).all()
            
    return render_template('reports.html', 
                           students=students, 
                           selected_student=selected_student,
                           present_days=present_days,
                           absent_days=absent_days,
                           student_grades=student_grades)

@app.route('/analytics')
@login_required
def analytics():
    import datetime as dt
    today = dt.datetime.utcnow().date()
    dates = [(today - dt.timedelta(days=i)) for i in range(14, -1, -1)]
    date_labels = [d.strftime('%b %d') for d in dates]
    
    trend_data = []
    for d in dates:
        trend_data.append(Attendance.query.filter_by(date=d, status='Present').count())
        
    total_present = Attendance.query.filter_by(status='Present').count()
    total_absent = Attendance.query.filter_by(status='Absent').count()
    
    return render_template('analytics.html',
                           date_labels=date_labels,
                           trend_data=trend_data,
                           total_present=total_present,
                           total_absent=total_absent)

@app.route('/export/attendance')
@login_required
def export_attendance():
    if current_user.role != 'Admin' and current_user.role != 'Teacher':
         return redirect(url_for('dashboard'))
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Date', 'Student Name', 'Roll Number', 'Subject', 'Status']) # Header
    
    logs = Attendance.query.all()
    for log in logs:
        cw.writerow([log.id, log.date, log.student.name, log.student.roll_number, log.subject.name, log.status])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=attendance_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/export/grades')
@login_required
def export_grades():
    if current_user.role != 'Admin' and current_user.role != 'Teacher':
         return redirect(url_for('dashboard'))
         
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Student Name', 'Roll Number', 'Subject', 'Assessment', 'Score', 'Max Score', 'Percentage'])
    
    grades = Grade.query.all()
    for g in grades:
        perc = round((g.score / g.max_score) * 100, 2) if g.max_score > 0 else 0
        cw.writerow([g.id, g.student.name, g.student.roll_number, g.subject.name, g.assessment, g.score, g.max_score, f"{perc}%"])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=grades_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

if __name__ == '__main__':
    app.run(debug=True)
