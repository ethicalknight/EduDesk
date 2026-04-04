import random
from datetime import datetime, timedelta
from app import app, db, User, Student, Subject, Attendance, Grade, Timetable

def seed_students():
    with app.app_context():
        # Get the default teacher if exists
        teacher = User.query.filter_by(role='Teacher').first()
        t_id = teacher.id if teacher else None
        
        # Get subjects
        subjects = Subject.query.all()
        if not subjects:
            print("No subjects found. Please run the app once to create dummy subjects.")
            return

        names = [
            "Arjun Mehta", "Sanya Sharma", "Rahul Kapoor", "Priya Singh", "Amit Patel",
            "Ananya Iyer", "Vikram Rathore", "Ishita Gupta", "Karan Malhotra", "Sneha Reddy",
            "Rohan Verma", "Kavya Nair", "Aditya Joshi", "Riya Saxena", "Manish Tiwari",
            "Shreya Bansal", "Abhishek Chaudhary", "Meera Deshmukh", "Siddharth Kulkarni", "Neha Bhat",
            "Gaurav Pandey", "Tanvi Shah", "Yash Wardhan", "Pooja Hegde", "Varun Dhawan",
            "Kiara Advani", "Ranbir Singh", "Alia Bhatt", "Ayushmann Khurrana", "Deepika Padukone"
        ]

        departments = ["Computer Science", "Information Technology", "Electronics Engineering", "Mechanical Engineering"]
        batches = ["2022-2026", "2023-2027", "2024-2028"]

        print(f"Seeding {len(names)} students...")

        for i, name in enumerate(names):
            roll = f"STU-{2023000 + i + 1}"
            email = f"{name.lower().replace(' ', '.')}@edudesk-demo.com"
            phone = f"{random.randint(7000000000, 9999999999)}"
            dept = random.choice(departments)
            sem = random.randint(1, 8)
            batch = random.choice(batches)
            
            # Check if student already exists
            existing = Student.query.filter_by(roll_number=roll).first()
            if not existing:
                student = Student(
                    roll_number=roll,
                    name=name,
                    email=email,
                    phone=phone,
                    department=dept,
                    semester=sem,
                    batch=batch,
                    teacher_id=t_id
                )
                db.session.add(student)
        
        db.session.commit()
        print("Student seeding complete.")

        # Seed some attendance records for the last 14 days
        all_students = Student.query.all()
        today = datetime.utcnow().date()
        
        print("Seeding attendance records for the last 14 days...")
        for i in range(14):
            date = today - timedelta(days=i)
            for sub in subjects:
                for student in all_students:
                    # Don't add attendance for every single day/subject combo (too many)
                    # Use a 70% probability to skip or mark
                    if random.random() > 0.4:
                        status = 'Present' if random.random() > 0.15 else 'Absent'
                        # Check if record exists
                        existing = Attendance.query.filter_by(student_id=student.id, subject_id=sub.id, date=date).first()
                        if not existing:
                            att = Attendance(
                                student_id=student.id,
                                subject_id=sub.id,
                                date=date,
                                status=status
                            )
                            db.session.add(att)
            
            # Commit periodically to avoid memory issues
            if i % 3 == 0:
                db.session.commit()
        
        db.session.commit()
        print("Attendance seeding complete.")

        # Seed some grades
        print("Seeding grade records...")
        assessments = ["Midterm", "Assignment 1", "Quiz 1", "Final Project"]
        for student in all_students:
            for sub in subjects:
                for assessment in assessments:
                    # 50% chance of having a grade for each assessment
                    if random.random() > 0.5:
                        max_score = 100
                        score = random.randint(40, 100)
                        existing = Grade.query.filter_by(student_id=student.id, subject_id=sub.id, assessment=assessment).first()
                        if not existing:
                            grade = Grade(
                                student_id=student.id,
                                subject_id=sub.id,
                                assessment=assessment,
                                score=score,
                                max_score=max_score
                            )
                            db.session.add(grade)
        
        db.session.commit()
        print("Grade seeding complete.")

if __name__ == "__main__":
    seed_students()
