from flask import Flask, render_template, request, redirect, url_for, g
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

DATABASE = 'students.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                student_name TEXT NOT NULL,
                branch TEXT NOT NULL,
                email TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                id_card TEXT,
                activated INTEGER DEFAULT 0,
                photo TEXT
            )
        ''')
        cursor.execute('SELECT COUNT(*) FROM students')
        if cursor.fetchone()[0] == 0:
            students_data = [
                ("101", "Alice Johnson", "Computer Science", "alice@example.com", "2002-05-14", None, 0, None),
                ("102", "Bob Smith", "Mechanical", "bob@example.com", "2001-09-23", None, 0, None),
                ("103", "Charlie Brown", "Electrical", "charlie@example.com", "2003-02-10", None, 0, None)
            ]
            cursor.executemany('INSERT INTO students VALUES (?, ?, ?, ?, ?, ?, ?, ?)', students_data)
        db.commit()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search_student', methods=['POST'])
def search_student():
    student_id = request.form['student_id']
    student_name = request.form['student_name']
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE student_id = ? AND student_name = ?',
                         (student_id, student_name)).fetchone()
    return render_template('search_results.html', student=student, error="Student Not Found" if not student else None)

@app.route('/status')
def status():
    db = get_db()
    students = db.execute('SELECT * FROM students').fetchall()
    return render_template('status.html', students=students)

@app.route('/issue_card', methods=['POST'])
def issue_card():
    student_id = request.form['student_id']
    id_card_number = request.form['id_card_number']
    db = get_db()
    db.execute('UPDATE students SET id_card = ?, activated = 0 WHERE student_id = ?', (id_card_number, student_id))
    db.commit()
    return redirect(url_for('status'))

@app.route('/activate_card/<student_id>')
def activate_card(student_id):
    return render_template('upload_photo.html', student_id=student_id)


@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    student_id = request.form['student_id']
    if 'photo' not in request.files:
        return "No file uploaded"
    file = request.files['photo']
    if file.filename == '':
        return "No selected file"
    
    # Ensure the upload folder exists
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)  # Create folder if not exists

    # Save the file
    filename = secure_filename(file.filename)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)

    # Update the database with the photo path
    db = get_db()
    db.execute('UPDATE students SET photo = ?, activated = 1 WHERE student_id = ?', (file_path, student_id))
    db.commit()

    return redirect(url_for('id_card_preview', student_id=student_id))



@app.route('/id_card/<student_id>')
def id_card_preview(student_id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
    return render_template('id_card.html', student=student)

@app.route('/delete_card/<student_id>')
def delete_card(student_id):
    db = get_db()
    db.execute('UPDATE students SET id_card = NULL, activated = 0, photo = NULL WHERE student_id = ?', (student_id,))
    db.commit()
    return redirect(url_for('status'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
