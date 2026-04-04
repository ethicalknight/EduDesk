import os
import csv
from io import StringIO
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Student, Subject, Attendance, Grade, Timetable, Announcement, Notification, Assignment, Submission
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hackathon_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///edudesk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def send_notification(user_id, title, message, type='info'):
    notif = Notification(user_id=user_id, title=title, message=message, type=type)
    db.session.add(notif)
    db.session.commit()

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
        teacher = User.query.filter_by(role="Teacher").first()
        t_id = teacher.id if teacher else None
        
        s1 = Student(roll_number="CS101", name="Alice Smith", email="alice@example.com", phone="1234567890", department="Computer Science", semester=3, teacher_id=t_id)
        s2 = Student(roll_number="CS102", name="Bob Johnson", email="bob@example.com", phone="0987654321", department="Computer Science", semester=3, teacher_id=t_id)
        s3 = Student(roll_number="CS103", name="Charlie Brown", email="charlie@example.com", phone="1112223333", department="Computer Science", semester=3, teacher_id=None)
        
        db.session.add_all([s1, s2, s3])
        db.session.commit()

        # Fetch subjects for timetable
        ds = Subject.query.filter_by(code="CS201").first()
        wd = Subject.query.filter_by(code="CS202").first()
        
        if ds and wd:
            t1 = Timetable(subject_id=ds.id, day="Monday", start_time="09:00", end_time="10:30", room="Room 101")
            t2 = Timetable(subject_id=wd.id, day="Monday", start_time="11:00", end_time="12:30", room="Lab 1")
            t3 = Timetable(subject_id=ds.id, day="Wednesday", start_time="09:00", end_time="10:30", room="Room 101")
            
            db.session.add_all([t1, t2, t3])
            db.session.commit()

            g1 = Grade(student_id=s1.id, subject_id=ds.id, assessment="Midterm", score=85, max_score=100)
            g2 = Grade(student_id=s2.id, subject_id=ds.id, assessment="Midterm", score=92, max_score=100)
            
            db.session.add_all([g1, g2])
            db.session.commit()

    if Announcement.query.first() is None:
        admin = User.query.filter_by(role="Admin").first()
        if admin:
            a1 = Announcement(title="Welcome to EduDesk", content="The new smart academic administration system is now live!", author_id=admin.id)
            a2 = Announcement(title="Holiday Notice", content="Campus will remain closed this Friday for the Spring Festival.", author_id=admin.id)
            db.session.add_all([a1, a2])
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
    role = request.form.get('role', 'Teacher')
    student_roll = request.form.get('student_roll')
    
    # Check if a user with that email already exists
    if User.query.filter_by(email=email).first():
        flash('Email already exists. Please log in.', 'error')
        return redirect(url_for('login'))
        
    if role == 'Parent':
        if not student_roll:
            flash('Roll number is required for Parent signup.', 'error')
            return redirect(url_for('login'))
        student = Student.query.filter_by(roll_number=student_roll).first()
        if not student:
            flash(f'Student with Roll Number {student_roll} not found.', 'error')
            return redirect(url_for('login'))
            
        new_user = User(name=name, email=email, password_hash=generate_password_hash(password), role='Parent')
        db.session.add(new_user)
        db.session.flush() # Get user ID
        student.parent_id = new_user.id
        db.session.commit()
        flash('Parent account created and linked successfully!', 'success')
    else:
        # By default, external signups become Teachers
        new_user = User(name=name, email=email, password_hash=generate_password_hash(password), role='Teacher')
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! You can now login.', 'success')
    return redirect(url_for('login'))

@app.route('/admin/create_student_login', methods=['POST'])
@login_required
def create_student_login():
    if current_user.role != 'Admin':
        flash('Access Denied', 'error')
        return redirect(url_for('dashboard'))
        
    student_id = request.form.get('student_id')
    password = request.form.get('password')
    
    student = Student.query.get(student_id)
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('students'))
        
    if student.user_id:
        flash('Student already has a login account.', 'error')
        return redirect(url_for('students'))
        
    # Create User account for student
    new_user = User(
        name=student.name, 
        email=student.email or f"{student.roll_number.lower()}@edudesk.edu", 
        password_hash=generate_password_hash(password), 
        role='Student'
    )
    db.session.add(new_user)
    db.session.flush()
    student.user_id = new_user.id
    db.session.commit()
    
    flash(f'Login account created for {student.name}. Email: {new_user.email}', 'success')
    return redirect(url_for('students'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    if current_user.role == 'Student':
        return redirect(url_for('student_dashboard'))
    if current_user.role == 'Parent':
        return redirect(url_for('parent_dashboard'))
        
    # Admin/Teacher Dashboard Logic
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
                # Add Success Probability (simple version for dashboard)
                grades = Grade.query.filter_by(student_id=st.id).all()
                avg_grade = sum([g.score/g.max_score for g in grades]) / len(grades) if grades else 0
                success_prob = int((perc/100 * 40) + (avg_grade * 60))
                at_risk_students.append({
                    'name': st.name, 
                    'roll': st.roll_number, 
                    'percentage': int(perc), 
                    'success_prob': success_prob
                })
    at_risk_students = sorted(at_risk_students, key=lambda x: x['percentage'])[:5]
    
    recent_attendance = Attendance.query.order_by(Attendance.date.desc()).limit(5).all()
    
    announcements = Announcement.query.order_by(Announcement.date.desc()).limit(3).all()
    
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                           total_students=total_students, 
                           total_subjects=total_subjects, 
                           attendance_percentage=attendance_percentage,
                           recent_attendance=recent_attendance,
                           present_records=present_records,
                           absent_records=absent_records,
                           date_labels=date_labels,
                           trend_data=trend_data,
                           at_risk_students=at_risk_students,
                           announcements=announcements,
                           notifications=notifications)

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'Student':
        return redirect(url_for('dashboard'))
    
    student = current_user.student_profile[0] if current_user.student_profile else None
    if not student:
        flash('No student profile linked to this account.', 'error')
        return redirect(url_for('logout'))
        
    present_days = Attendance.query.filter_by(student_id=student.id, status='Present').count()
    absent_days = Attendance.query.filter_by(student_id=student.id, status='Absent').count()
    total_days = present_days + absent_days
    att_rate = int((present_days / total_days * 100)) if total_days > 0 else 0
    
    grades = Grade.query.filter_by(student_id=student.id).order_by(Grade.id.desc()).limit(5).all()
    assignments = Assignment.query.join(Subject).order_by(Assignment.deadline.asc()).limit(5).all()
    timetable = Timetable.query.join(Subject).order_by(Timetable.start_time).all()
    
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('student_dashboard.html', 
                           student=student, 
                           att_rate=att_rate, 
                           recent_grades=grades, 
                           upcoming_assignments=assignments,
                           timetable=timetable,
                           notifications=notifications)

@app.route('/parent_dashboard')
@login_required
def parent_dashboard():
    if current_user.role != 'Parent':
        return redirect(url_for('dashboard'))
    
    children = current_user.children
    if not children:
        flash('No children linked to this account.', 'error')
        return redirect(url_for('logout'))
        
    # For now, let's just focus on the first child if multiple exist
    student = children[0]
    
    present_days = Attendance.query.filter_by(student_id=student.id, status='Present').count()
    absent_days = Attendance.query.filter_by(student_id=student.id, status='Absent').count()
    total_days = present_days + absent_days
    att_rate = int((present_days / total_days * 100)) if total_days > 0 else 0
    
    grades = Grade.query.filter_by(student_id=student.id).order_by(Grade.id.desc()).limit(5).all()
    timetable = Timetable.query.join(Subject).order_by(Timetable.start_time).all()
    
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('parent_dashboard.html', 
                           student=student, 
                           att_rate=att_rate, 
                           recent_grades=grades, 
                           timetable=timetable,
                           notifications=notifications)

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
    # Fetch recurring (weekly) and one-off events
    schedule = Timetable.query.join(Subject).order_by(Timetable.date, Timetable.day, Timetable.start_time).all()
    subjects = Subject.query.all()
    return render_template('timetable.html', schedule=schedule, subjects=subjects)

@app.route('/add_timetable', methods=['POST'])
@login_required
def add_timetable():
    if current_user.role != 'Admin':
        flash('Access Denied', 'error')
        return redirect(url_for('dashboard'))
        
    subject_id = request.form.get('subject_id')
    day = request.form.get('day') or None
    date_str = request.form.get('date')
    date_obj = None
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
        
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    room = request.form.get('room')
    
    new_tt = Timetable(subject_id=subject_id, day=day, date=date_obj, start_time=start_time, end_time=end_time, room=room)
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

@app.route('/admin/trigger_absent_hook', methods=['POST'])
@login_required
def trigger_absent_hook():
    if current_user.role != 'Admin':
        return jsonify({"error": "Unauthorized"}), 403
    
    # Reuse the logic from daily_absent_hook
    today = datetime.utcnow().date()
    students = Student.query.all()
    active_subjects_today = db.session.query(Attendance.subject_id).filter_by(date=today).distinct().all()
    active_subject_ids = [s[0] for s in active_subjects_today]

    count = 0
    for subject_id in active_subject_ids:
        for student in students:
            att = Attendance.query.filter_by(student_id=student.id, subject_id=subject_id, date=today).first()
            if not att:
                absent = Attendance(student_id=student.id, subject_id=subject_id, date=today, status='Absent')
                db.session.add(absent)
                count += 1
                
    db.session.commit()
    flash(f"Success: Processed {count} students as absent for today.", "success")
    return redirect(url_for('dashboard'))

@app.route('/reports')
@login_required
def reports():
    student_id = request.args.get('student_id', type=int)
    selected_student = None
    student_grades = []
    present_days = 0
    absent_days = 0
    
    # Leaderboard Logic
    all_students = Student.query.all()
    leaderboard_att = []
    leaderboard_perf = []
    
    for s in all_students:
        # Attendance %
        total_att = Attendance.query.filter_by(student_id=s.id).count()
        present = Attendance.query.filter_by(student_id=s.id, status='Present').count()
        att_rate = round((present / total_att * 100), 1) if total_att > 0 else 0
        leaderboard_att.append({'name': s.name, 'rate': att_rate, 'id': s.id})
        
        # Average Grade
        grades = Grade.query.filter_by(student_id=s.id).all()
        if grades:
            avg_perc = sum([(g.score/g.max_score)*100 for g in grades]) / len(grades)
            leaderboard_perf.append({'name': s.name, 'score': round(avg_perc, 1), 'id': s.id})
        else:
            leaderboard_perf.append({'name': s.name, 'score': 0, 'id': s.id})
            
    leaderboard_att = sorted(leaderboard_att, key=lambda x: x['rate'], reverse=True)[:10]
    leaderboard_perf = sorted(leaderboard_perf, key=lambda x: x['score'], reverse=True)[:10]

    if student_id:
        selected_student = Student.query.get(student_id)
        if selected_student:
             student_grades = Grade.query.filter_by(student_id=student_id).all()
             present_days = Attendance.query.filter_by(student_id=student_id, status='Present').count()
             absent_days = Attendance.query.filter_by(student_id=student_id, status='Absent').count()
             
             # Success prob & badges (mock logic for presentation)
             selected_student.badges = []
             if present_days > 10: selected_student.badges.append({'name': 'Perfect Attendance', 'icon': 'fa-calendar-check', 'color': '#10B981'})
             
             total = present_days + absent_days
             att_rate_val = (present_days / total * 100) if total > 0 else 0
             avg_grade = sum([(g.score/g.max_score)*100 for g in student_grades]) / len(student_grades) if student_grades else 0
             selected_student.success_probability = int((att_rate_val * 0.4) + (avg_grade * 0.6))

    students = Student.query.all()
    return render_template('reports.html', 
                          students=students, 
                          selected_student=selected_student,
                          student_grades=student_grades,
                          present_days=present_days,
                          absent_days=absent_days,
                          leaderboard_att=leaderboard_att,
                          leaderboard_perf=leaderboard_perf,
                          today=datetime.now())

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

@app.route('/api/recent_checkins/<int:subject_id>')
@login_required
def api_recent_checkins(subject_id):
    today = datetime.utcnow().date()
    # Get the 10 most recent "Present" records for today
    checkins = Attendance.query.filter_by(subject_id=subject_id, date=today, status='Present').order_by(Attendance.id.desc()).limit(10).all()
    return jsonify({
        'count': Attendance.query.filter_by(subject_id=subject_id, date=today, status='Present').count(),
        'recent': [{'name': c.student.name, 'roll': c.student.roll_number, 'time': 'Just now'} for c in checkins]
    })

@app.route('/api/search')
@login_required
def api_search():
    q = request.args.get('q', '').lower()
    if not q:
        return jsonify({'results': []})
    
    results = []
    
    # Search Students
    students = Student.query.filter(
        (Student.name.ilike(f'%{q}%')) | (Student.roll_number.ilike(f'%{q}%'))
    ).limit(5).all()
    for s in students:
        results.append({'type': 'Student', 'title': s.name, 'subtitle': s.roll_number, 'url': url_for('reports', student_id=s.id)})
        
    # Search Subjects
    subjects = Subject.query.filter(
        (Subject.name.ilike(f'%{q}%')) | (Subject.code.ilike(f'%{q}%'))
    ).limit(3).all()
    for sub in subjects:
        results.append({'type': 'Subject', 'title': sub.name, 'subtitle': sub.code, 'url': url_for('attendance', subject_id=sub.id)})
        
    return jsonify({'results': results})

@app.route('/api/performance_correlation')
@login_required
def api_performance_correlation():
    # Calculate Attendance % vs Average Grade for each student
    students = Student.query.all()
    data = []
    for s in students:
        total_att = Attendance.query.filter_by(student_id=s.id).count()
        if total_att == 0: continue
        present_att = Attendance.query.filter_by(student_id=s.id, status='Present').count()
        att_perc = (present_att / total_att) * 100
        
        grades = Grade.query.filter_by(student_id=s.id).all()
        if not grades: continue
        avg_grade = sum([g.score/g.max_score for g in grades]) / len(grades) * 100
        
        data.append({
            'name': s.name,
            'x': round(att_perc, 1),
            'y': round(avg_grade, 1)
        })
    return jsonify(data)

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

@app.route('/assignments', methods=['GET', 'POST'])
@login_required
def assignments():
    if current_user.role == 'Student':
        student = current_user.student_profile[0] if current_user.student_profile else None
        # Student sees assignments for all their subjects
        all_assignments = Assignment.query.order_by(Assignment.deadline.asc()).all()
        return render_template('assignments.html', assignments=all_assignments)
    
    # Teachers and Admins
    if current_user.role == 'Admin':
        subjects = Subject.query.all()
        all_assignments = Assignment.query.order_by(Assignment.deadline.asc()).all()
    else:
        subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
        all_assignments = Assignment.query.filter_by(teacher_id=current_user.id).order_by(Assignment.deadline.asc()).all()
        
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        title = request.form.get('title')
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        
        file = request.files.get('file')
        file_path = None
        if file:
            filename = f"asm_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            file_path = os.path.join('uploads', filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        new_asm = Assignment(subject_id=subject_id, teacher_id=current_user.id, title=title, 
                             description=description, deadline=deadline, file_path=file_path)
        db.session.add(new_asm)
        db.session.commit()
        
        # Notify all students in this subject (simple: notify all students)
        students = Student.query.all()
        for s in students:
            if s.user_id:
                send_notification(s.user_id, "New Assignment", f"A new assignment '{title}' has been posted for {new_asm.subject.name}.", "info")
        
        flash('Assignment posted successfully!', 'success')
        return redirect(url_for('assignments'))
        
    return render_template('assignments.html', subjects=subjects, assignments=all_assignments)

@app.route('/submit_assignment/<int:assignment_id>', methods=['POST'])
@login_required
def submit_assignment(assignment_id):
    if current_user.role != 'Student':
        flash('Access Denied', 'error')
        return redirect(url_for('dashboard'))
        
    student = current_user.student_profile[0] if current_user.student_profile else None
    if not student:
        flash('Student profile not found.', 'error')
        return redirect(url_for('assignments'))

    file = request.files.get('file')
    if not file:
        flash('No file provided.', 'error')
        return redirect(url_for('assignments'))
        
    filename = f"sub_{assignment_id}_{student.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file_path = os.path.join('uploads', filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    new_sub = Submission(assignment_id=assignment_id, student_id=student.id, file_path=file_path)
    db.session.add(new_sub)
    db.session.commit()
    
    # Notify Teacher
    asm = Assignment.query.get(assignment_id)
    send_notification(asm.teacher_id, "New Submission", f"{student.name} submitted assignment: {asm.title}.", "success")
    
    flash('Assignment submitted successfully!', 'success')
    return redirect(url_for('assignments'))

@app.route('/api/notifications/read/<int:id>', methods=['POST'])
@login_required
def mark_notification_read(id):
    notif = Notification.query.get(id)
    if notif and notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 403

from flask import send_from_directory
@app.route('/uploads/<path:filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
