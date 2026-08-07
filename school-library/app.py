from datetime import datetime, timedelta
import sqlite3
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def init_db():
  conn = sqlite3.connect('library.db')
  c = conn.cursor()
  c.execute('''CREATE TABLE IF NOT EXISTS students
                 (admission_no TEXT PRIMARY KEY, name TEXT, class_section TEXT)''')
  c.execute('''CREATE TABLE IF NOT EXISTS issues
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, admission_no TEXT, book_name TEXT, issue_date TEXT, due_date TEXT)''')
  c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, admission_no TEXT, book_name TEXT, issue_date TEXT)''')

  # Safe schema migrations
  for table, col, col_type in [
      ('issues', 'due_date', 'TEXT'),
      ('issues', 'issue_date', 'TEXT'),
  ]:
    try:
      c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_type}')
    except sqlite3.OperationalError:
      pass

  conn.commit()
  conn.close()


init_db()


@app.route('/')
def index():
  return render_template('index.html')


@app.route('/api/login', methods=['POST'])
def login():
  data = request.json
  if data.get('password') == 'librarian123':
    return jsonify({'status': 'success'})
  return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/api/stats', methods=['GET'])
def get_stats():
  try:
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM issues')
    active_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM students')
    student_count = c.fetchone()[0]
    conn.close()
    return jsonify(
        {'active_loans': active_count, 'registered_students': student_count}
    )
  except Exception as e:
    return jsonify({'error': str(e)}), 500


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
  try:
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('''SELECT h.admission_no, 
                        COALESCE(s.name, 'Patron'), 
                        COALESCE(s.class_section, 'N/A'), 
                        COUNT(h.id) as total_borrowed 
                 FROM history h 
                 LEFT JOIN students s ON h.admission_no = s.admission_no 
                 GROUP BY h.admission_no 
                 ORDER BY total_borrowed DESC 
                 LIMIT 5''')
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'admission_no': r[0],
        'name': r[1],
        'class_section': r[2],
        'total_borrowed': r[3],
    } for r in rows])
  except Exception as e:
    return jsonify({'error': str(e)}), 500


@app.route('/api/students', methods=['GET'])
def get_students():
  conn = sqlite3.connect('library.db')
  c = conn.cursor()
  c.execute('SELECT admission_no FROM students')
  rows = c.fetchall()
  conn.close()
  return jsonify([r[0] for r in rows])


@app.route('/api/issue', methods=['POST'])
def issue_book():
  try:
    data = request.json
    adm = data.get('admission_no')
    name = data.get('name')
    cls = data.get('class_section')
    book = data.get('book_name')

    if not adm or not book:
      return jsonify({'error': 'Missing required fields'}), 400

    conn = sqlite3.connect('library.db')
    c = conn.cursor()

    c.execute('SELECT * FROM students WHERE admission_no = ?', (adm,))
    if not c.fetchone():
      c.execute(
          'INSERT INTO students VALUES (?, ?, ?)',
          (adm, name or f'Patron {adm}', cls or 'N/A'),
      )

    issue_date = datetime.now().strftime('%Y-%m-%d')
    due_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')

    c.execute(
        'INSERT INTO issues (admission_no, book_name, issue_date, due_date)'
        ' VALUES (?, ?, ?, ?)',
        (adm, book, issue_date, due_date),
    )
    c.execute(
        'INSERT INTO history (admission_no, book_name, issue_date) VALUES (?, ?,'
        ' ?)',
        (adm, book, issue_date),
    )

    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})
  except Exception as e:
    return jsonify({'error': str(e)}), 500


@app.route('/api/issues', methods=['GET'])
def get_issues():
  try:
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('''SELECT i.id, s.admission_no, 
                        COALESCE(s.name, 'Patron'), 
                        COALESCE(s.class_section, 'N/A'), 
                        i.book_name, i.issue_date, i.due_date 
                 FROM issues i 
                 LEFT JOIN students s ON i.admission_no = s.admission_no''')
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'id': r[0],
        'admission_no': r[1],
        'name': r[2],
        'class_section': r[3],
        'book_name': r[4],
        'issue_date': r[5],
        'due_date': r[6],
    } for r in rows])
  except Exception as e:
    return jsonify({'error': str(e)}), 500


@app.route('/api/return/<int:id>', methods=['POST'])
def return_book(id):
  conn = sqlite3.connect('library.db')
  c = conn.cursor()
  c.execute('DELETE FROM issues WHERE id = ?', (id,))
  conn.commit()
  conn.close()
  return jsonify({'status': 'success'})


@app.route('/api/update-date', methods=['POST'])
def update_date():
  data = request.json
  conn = sqlite3.connect('library.db')
  c = conn.cursor()
  c.execute(
      'UPDATE issues SET due_date = ? WHERE id = ?',
      (data.get('due_date'), data.get('id')),
  )
  conn.commit()
  conn.close()
  return jsonify({'status': 'success'})


if __name__ == '__main__':
  app.run(debug=True, port=5000)