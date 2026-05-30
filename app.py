from database import get_db, init_db

# Force initialize database
init_db()
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from database import get_db, init_db
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'greenland@2026secret'

# ============ HELPERS ============

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Access denied!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') not in ['admin', 'teacher']:
            flash('Access denied!', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def get_grade(score):
    if score >= 70: return 'A'
    elif score >= 60: return 'B'
    elif score >= 50: return 'C'
    elif score >= 45: return 'D'
    elif score >= 40: return 'E'
    else: return 'F'

# ============ PUBLIC ROUTES ============

@app.route('/')
def index():
    db = get_db()
    announcements = db.execute('''SELECT a.*, u.full_name as author 
        FROM announcements a JOIN users u ON a.author_id = u.id 
        WHERE a.target IN ("all", "public") 
        ORDER BY a.id DESC LIMIT 5''').fetchall()
    db.close()
    return render_template('index.html', announcements=announcements)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ? AND password = ?',
                         [email, password]).fetchone()
        db.close()
        if user:
            if user['status'] == 'pending':
                flash('Your account is pending approval. Please wait!', 'warning')
                return render_template('login.html')
            session['user_id'] = user['id']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        db = get_db()
        try:
            status = 'approved' if role == 'parent' else 'pending'
            db.execute('''INSERT INTO users 
                (full_name, email, password, role, status, phone, address) 
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                [full_name, email, password, role, status, phone, address])
            db.commit()
            db.close()
            if role == 'teacher':
                flash('Registration successful! Wait for admin approval.', 'success')
            else:
                flash('Registration successful! You can now login.', 'success')
            return redirect(url_for('login'))
        except:
            db.close()
            flash('Email already exists!', 'error')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ============ DASHBOARD ROUTER ============

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    elif role == 'parent':
        return redirect(url_for('parent_dashboard'))
    return redirect(url_for('login'))

# ============ ADMIN ROUTES ============

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    db = get_db()
    total_students = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    total_teachers = db.execute('SELECT COUNT(*) FROM users WHERE role = "teacher" AND status = "approved"').fetchone()[0]
    total_parents = db.execute('SELECT COUNT(*) FROM users WHERE role = "parent"').fetchone()[0]
    pending_teachers = db.execute('SELECT COUNT(*) FROM users WHERE role = "teacher" AND status = "pending"').fetchone()[0]
    recent_students = db.execute('SELECT * FROM students ORDER BY id DESC LIMIT 5').fetchall()
    announcements = db.execute('''SELECT a.*, u.full_name as author 
        FROM announcements a JOIN users u ON a.author_id = u.id 
        ORDER BY a.id DESC LIMIT 5''').fetchall()
    db.close()
    return render_template('admin/dashboard.html',
                         total_students=total_students,
                         total_teachers=total_teachers,
                         total_parents=total_parents,
                         pending_teachers=pending_teachers,
                         recent_students=recent_students,
                         announcements=announcements)

@app.route('/admin/students', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_students():
    db = get_db()
    if request.method == 'POST':
        full_name = request.form['full_name']
        admission_number = request.form['admission_number']
        class_ = request.form['class']
        section = request.form.get('section', 'A')
        gender = request.form['gender']
        date_of_birth = request.form.get('date_of_birth', '')
        parent_id = request.form.get('parent_id', None)
        address = request.form.get('address', '')
        try:
            db.execute('''INSERT INTO students 
                (full_name, admission_number, class, section, gender, 
                date_of_birth, parent_id, address) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                [full_name, admission_number, class_, section,
                 gender, date_of_birth, parent_id, address])
            db.commit()
            flash('Student registered successfully!', 'success')
        except:
            flash('Admission number already exists!', 'error')

    search = request.args.get('search', '')
    class_filter = request.args.get('class', '')
    if search:
        students = db.execute('''SELECT s.*, u.full_name as parent_name 
            FROM students s LEFT JOIN users u ON s.parent_id = u.id 
            WHERE s.full_name LIKE ? OR s.admission_number LIKE ?
            ORDER BY s.full_name''',
            ['%'+search+'%', '%'+search+'%']).fetchall()
    elif class_filter:
        students = db.execute('''SELECT s.*, u.full_name as parent_name 
            FROM students s LEFT JOIN users u ON s.parent_id = u.id 
            WHERE s.class = ? ORDER BY s.full_name''',
            [class_filter]).fetchall()
    else:
        students = db.execute('''SELECT s.*, u.full_name as parent_name 
            FROM students s LEFT JOIN users u ON s.parent_id = u.id 
            ORDER BY s.full_name''').fetchall()

    parents = db.execute('SELECT * FROM users WHERE role = "parent"').fetchall()
    total = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    db.close()
    return render_template('admin/students.html',
                         students=students,
                         parents=parents,
                         total=total,
                         search=search,
                         class_filter=class_filter)

@app.route('/admin/delete_student/<int:id>')
@login_required
@admin_required
def admin_delete_student(id):
    db = get_db()
    db.execute('DELETE FROM students WHERE id = ?', [id])
    db.execute('DELETE FROM grades WHERE student_id = ?', [id])
    db.execute('DELETE FROM attendance WHERE student_id = ?', [id])
    db.execute('DELETE FROM fees WHERE student_id = ?', [id])
    db.commit()
    db.close()
    flash('Student deleted!', 'success')
    return redirect(url_for('admin_students'))

@app.route('/admin/teachers')
@login_required
@admin_required
def admin_teachers():
    db = get_db()
    teachers = db.execute('SELECT * FROM users WHERE role = "teacher" ORDER BY status, full_name').fetchall()
    db.close()
    return render_template('admin/teachers.html', teachers=teachers)

@app.route('/admin/approve_teacher/<int:id>')
@login_required
@admin_required
def approve_teacher(id):
    db = get_db()
    db.execute('UPDATE users SET status = "approved" WHERE id = ?', [id])
    db.commit()
    db.close()
    flash('Teacher approved!', 'success')
    return redirect(url_for('admin_teachers'))

@app.route('/admin/reject_teacher/<int:id>')
@login_required
@admin_required
def reject_teacher(id):
    db = get_db()
    db.execute('DELETE FROM users WHERE id = ?', [id])
    db.commit()
    db.close()
    flash('Teacher rejected and removed!', 'success')
    return redirect(url_for('admin_teachers'))

@app.route('/admin/parents')
@login_required
@admin_required
def admin_parents():
    db = get_db()
    parents = db.execute('''SELECT u.*, COUNT(s.id) as children_count 
        FROM users u LEFT JOIN students s ON u.id = s.parent_id 
        WHERE u.role = "parent" GROUP BY u.id 
        ORDER BY u.full_name''').fetchall()
    db.close()
    return render_template('admin/parents.html', parents=parents)

@app.route('/admin/fees', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_fees():
    db = get_db()
    if request.method == 'POST':
        student_id = request.form['student_id']
        amount = float(request.form['amount'])
        fee_type = request.form['fee_type']
        term = request.form['term']
        session_ = request.form['session']
        status = request.form['status']
        date_paid = request.form.get('date_paid', '')
        remark = request.form.get('remark', '')
        db.execute('''INSERT INTO fees 
            (student_id, amount, fee_type, term, session, status, date_paid, remark) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            [student_id, amount, fee_type, term, session_, status, date_paid, remark])
        db.commit()
        flash('Fee record saved!', 'success')

    students = db.execute('SELECT * FROM students ORDER BY full_name').fetchall()
    fees = db.execute('''SELECT f.*, s.full_name, s.class, s.admission_number 
        FROM fees f JOIN students s ON f.student_id = s.id 
        ORDER BY f.id DESC''').fetchall()
    total_paid = db.execute('SELECT SUM(amount) FROM fees WHERE status = "paid"').fetchone()[0] or 0
    total_pending = db.execute('SELECT SUM(amount) FROM fees WHERE status = "pending"').fetchone()[0] or 0
    db.close()
    return render_template('admin/fees.html',
                         students=students,
                         fees=fees,
                         total_paid=total_paid,
                         total_pending=total_pending)

@app.route('/admin/announcements', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_announcements():
    db = get_db()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        target = request.form['target']
        priority = request.form.get('priority', 'normal')
        db.execute('''INSERT INTO announcements 
            (title, content, target, priority, author_id) 
            VALUES (?, ?, ?, ?, ?)''',
            [title, content, target, priority, session['user_id']])
        db.commit()
        flash('Announcement posted!', 'success')

    announcements = db.execute('''SELECT a.*, u.full_name as author 
        FROM announcements a JOIN users u ON a.author_id = u.id 
        ORDER BY a.id DESC''').fetchall()
    db.close()
    return render_template('admin/announcements.html', announcements=announcements)

@app.route('/admin/delete_announcement/<int:id>')
@login_required
@admin_required
def admin_delete_announcement(id):
    db = get_db()
    db.execute('DELETE FROM announcements WHERE id = ?', [id])
    db.commit()
    db.close()
    flash('Announcement deleted!', 'success')
    return redirect(url_for('admin_announcements'))

@app.route('/admin/report/<int:student_id>')
@login_required
@admin_required
def admin_report(student_id):
    return redirect(url_for('student_report', student_id=student_id))

# ============ TEACHER ROUTES ============

@app.route('/teacher/dashboard')
@login_required
@teacher_required
def teacher_dashboard():
    db = get_db()
    total_students = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    my_grades = db.execute('SELECT COUNT(*) FROM grades WHERE teacher_id = ?',
                          [session['user_id']]).fetchone()[0]
    my_attendance = db.execute('SELECT COUNT(*) FROM attendance WHERE teacher_id = ?',
                              [session['user_id']]).fetchone()[0]
    recent_students = db.execute('SELECT * FROM students ORDER BY id DESC LIMIT 5').fetchall()
    announcements = db.execute('''SELECT a.*, u.full_name as author 
        FROM announcements a JOIN users u ON a.author_id = u.id 
        WHERE a.target IN ("all", "teachers") 
        ORDER BY a.id DESC LIMIT 5''').fetchall()
    db.close()
    return render_template('teacher/dashboard.html',
                         total_students=total_students,
                         my_grades=my_grades,
                         my_attendance=my_attendance,
                         recent_students=recent_students,
                         announcements=announcements)

@app.route('/teacher/students')
@login_required
@teacher_required
def teacher_students():
    db = get_db()
    search = request.args.get('search', '')
    class_filter = request.args.get('class', '')
    if search:
        students = db.execute('''SELECT s.*, u.full_name as parent_name 
            FROM students s LEFT JOIN users u ON s.parent_id = u.id 
            WHERE s.full_name LIKE ? OR s.admission_number LIKE ?
            ORDER BY s.full_name''',
            ['%'+search+'%', '%'+search+'%']).fetchall()
    elif class_filter:
        students = db.execute('''SELECT s.*, u.full_name as parent_name 
            FROM students s LEFT JOIN users u ON s.parent_id = u.id 
            WHERE s.class = ? ORDER BY s.full_name''',
            [class_filter]).fetchall()
    else:
        students = db.execute('''SELECT s.*, u.full_name as parent_name 
            FROM students s LEFT JOIN users u ON s.parent_id = u.id 
            ORDER BY s.full_name''').fetchall()
    total = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    db.close()
    return render_template('teacher/students.html',
                         students=students,
                         total=total,
                         search=search,
                         class_filter=class_filter)

@app.route('/teacher/edit_student/<int:id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_student(id):
    db = get_db()
    if request.method == 'POST':
        full_name = request.form['full_name']
        class_ = request.form['class']
        section = request.form.get('section', 'A')
        gender = request.form['gender']
        date_of_birth = request.form.get('date_of_birth', '')
        address = request.form.get('address', '')
        db.execute('''UPDATE students SET full_name=?, class=?, section=?, 
            gender=?, date_of_birth=?, address=? WHERE id=?''',
            [full_name, class_, section, gender, date_of_birth, address, id])
        db.commit()
        db.close()
        flash('Student updated!', 'success')
        return redirect(url_for('teacher_students'))
    student = db.execute('SELECT * FROM students WHERE id = ?', [id]).fetchone()
    db.close()
    return render_template('teacher/edit_student.html', student=student)

@app.route('/teacher/grades', methods=['GET', 'POST'])
@login_required
@teacher_required
def teacher_grades():
    db = get_db()
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject = request.form['subject']
        ca_score = float(request.form.get('ca_score', 0))
        exam_score = float(request.form.get('exam_score', 0))
        total_score = ca_score + exam_score
        grade = get_grade(total_score)
        term = request.form['term']
        session_ = request.form['session']
        db.execute('''INSERT INTO grades 
            (student_id, subject, ca_score, exam_score, total_score, 
            grade, term, session, teacher_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [student_id, subject, ca_score, exam_score, total_score,
             grade, term, session_, session['user_id']])
        db.commit()
        flash('Grade recorded!', 'success')

    students = db.execute('SELECT * FROM students ORDER BY full_name').fetchall()
    grades = db.execute('''SELECT g.*, s.full_name, s.class, s.admission_number,
        u.full_name as teacher_name
        FROM grades g 
        JOIN students s ON g.student_id = s.id
        JOIN users u ON g.teacher_id = u.id
        ORDER BY g.id DESC LIMIT 50''').fetchall()
    db.close()
    return render_template('teacher/grades.html',
                         students=students,
                         grades=grades)

@app.route('/teacher/delete_grade/<int:id>')
@login_required
@teacher_required
def delete_grade(id):
    db = get_db()
    db.execute('DELETE FROM grades WHERE id = ? AND teacher_id = ?',
              [id, session['user_id']])
    db.commit()
    db.close()
    flash('Grade deleted!', 'success')
    return redirect(url_for('teacher_grades'))

@app.route('/teacher/attendance', methods=['GET', 'POST'])
@login_required
@teacher_required
def teacher_attendance():
    db = get_db()
    if request.method == 'POST':
        date_ = request.form['date']
        class_ = request.form['class']
        students = db.execute('SELECT * FROM students WHERE class = ?', [class_]).fetchall()
        for student in students:
            status = request.form.get(f'status_{student["id"]}', 'absent')
            remark = request.form.get(f'remark_{student["id"]}', '')
            db.execute('''INSERT INTO attendance 
                (student_id, date, status, class, teacher_id, remark) 
                VALUES (?, ?, ?, ?, ?, ?)''',
                [student['id'], date_, status, class_,
                 session['user_id'], remark])
        db.commit()
        flash('Attendance recorded!', 'success')

    students = db.execute('SELECT * FROM students ORDER BY class, full_name').fetchall()
    attendance = db.execute('''SELECT a.*, s.full_name, s.class 
        FROM attendance a JOIN students s ON a.student_id = s.id 
        ORDER BY a.date DESC LIMIT 50''').fetchall()
    db.close()
    return render_template('teacher/attendance.html',
                         students=students,
                         attendance=attendance)

# ============ PARENT ROUTES ============

@app.route('/parent/dashboard')
@login_required
def parent_dashboard():
    if session.get('role') != 'parent':
        return redirect(url_for('dashboard'))
    db = get_db()
    children = db.execute('SELECT * FROM students WHERE parent_id = ?',
                         [session['user_id']]).fetchall()
    announcements = db.execute('''SELECT a.*, u.full_name as author 
        FROM announcements a JOIN users u ON a.author_id = u.id 
        WHERE a.target IN ("all", "parents") 
        ORDER BY a.id DESC LIMIT 5''').fetchall()
    db.close()
    return render_template('parent/dashboard.html',
                         children=children,
                         announcements=announcements)

@app.route('/parent/grades/<int:student_id>')
@login_required
def parent_grades(student_id):
    if session.get('role') != 'parent':
        return redirect(url_for('dashboard'))
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ? AND parent_id = ?',
                        [student_id, session['user_id']]).fetchone()
    if not student:
        flash('Access denied!', 'error')
        return redirect(url_for('parent_dashboard'))
    grades = db.execute('''SELECT g.*, u.full_name as teacher_name 
        FROM grades g JOIN users u ON g.teacher_id = u.id 
        WHERE g.student_id = ? ORDER BY g.term, g.subject''',
        [student_id]).fetchall()
    db.close()
    return render_template('parent/grades.html',
                         student=student,
                         grades=grades)

@app.route('/parent/attendance/<int:student_id>')
@login_required
def parent_attendance(student_id):
    if session.get('role') != 'parent':
        return redirect(url_for('dashboard'))
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ? AND parent_id = ?',
                        [student_id, session['user_id']]).fetchone()
    if not student:
        flash('Access denied!', 'error')
        return redirect(url_for('parent_dashboard'))
    attendance = db.execute('''SELECT * FROM attendance 
        WHERE student_id = ? ORDER BY date DESC''',
        [student_id]).fetchall()
    present = db.execute('''SELECT COUNT(*) FROM attendance 
        WHERE student_id = ? AND status = "present"''',
        [student_id]).fetchone()[0]
    total = db.execute('SELECT COUNT(*) FROM attendance WHERE student_id = ?',
                      [student_id]).fetchone()[0]
    db.close()
    return render_template('parent/attendance.html',
                         student=student,
                         attendance=attendance,
                         present=present,
                         total=total)

@app.route('/parent/fees/<int:student_id>')
@login_required
def parent_fees(student_id):
    if session.get('role') != 'parent':
        return redirect(url_for('dashboard'))
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id = ? AND parent_id = ?',
                        [student_id, session['user_id']]).fetchone()
    if not student:
        flash('Access denied!', 'error')
        return redirect(url_for('parent_dashboard'))
    fees = db.execute('SELECT * FROM fees WHERE student_id = ? ORDER BY id DESC',
                     [student_id]).fetchall()
    db.close()
    return render_template('parent/fees.html',
                         student=student,
                         fees=fees)

# ============ SHARED ROUTES ============

@app.route('/report/<int:student_id>')
@login_required
def student_report(student_id):
    db = get_db()
    student = db.execute('''SELECT s.*, u.full_name as parent_name, 
        u.phone as parent_phone 
        FROM students s LEFT JOIN users u ON s.parent_id = u.id 
        WHERE s.id = ?''', [student_id]).fetchone()
    grades = db.execute('''SELECT g.*, u.full_name as teacher_name 
        FROM grades g JOIN users u ON g.teacher_id = u.id 
        WHERE g.student_id = ? ORDER BY g.subject''',
        [student_id]).fetchall()
    present = db.execute('''SELECT COUNT(*) FROM attendance 
        WHERE student_id = ? AND status = "present"''',
        [student_id]).fetchone()[0]
    total_days = db.execute('SELECT COUNT(*) FROM attendance WHERE student_id = ?',
                           [student_id]).fetchone()[0]
    fees = db.execute('SELECT * FROM fees WHERE student_id = ?',
                     [student_id]).fetchall()
    db.close()
    return render_template('report.html',
                         student=student,
                         grades=grades,
                         present=present,
                         total_days=total_days,
                         fees=fees)

if __name__ == '__main__':
    app.run(debug=True)
