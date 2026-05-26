import sqlite3

DB_PATH = 'greenland.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        phone TEXT,
        address TEXT,
        date_registered TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        admission_number TEXT UNIQUE NOT NULL,
        class TEXT NOT NULL,
        section TEXT DEFAULT 'A',
        gender TEXT NOT NULL,
        date_of_birth TEXT,
        parent_id INTEGER,
        address TEXT,
        date_enrolled TEXT DEFAULT CURRENT_DATE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        ca_score REAL DEFAULT 0,
        exam_score REAL DEFAULT 0,
        total_score REAL DEFAULT 0,
        grade TEXT,
        term TEXT NOT NULL,
        session TEXT NOT NULL,
        teacher_id INTEGER,
        date_recorded TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        class TEXT NOT NULL,
        teacher_id INTEGER,
        remark TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS fees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        fee_type TEXT NOT NULL,
        term TEXT NOT NULL,
        session TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        date_paid TEXT,
        remark TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        target TEXT DEFAULT 'all',
        priority TEXT DEFAULT 'normal',
        author_id INTEGER,
        date_posted TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        subject TEXT,
        content TEXT NOT NULL,
        date_sent TEXT DEFAULT CURRENT_TIMESTAMP,
        is_read INTEGER DEFAULT 0
    )''')

    # Create default admin
    try:
        c.execute('''INSERT INTO users 
            (full_name, email, password, role, status) 
            VALUES (?, ?, ?, ?, ?)''',
            ['Administrator', 'admin@greenland.com',
             'admin@2026', 'admin', 'approved'])
    except:
        pass

    conn.commit()
    conn.close()

init_db()
