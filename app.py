from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
import json
import os
import io

app = Flask(__name__)

DATA_FILE = '/tmp/library_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "issues": [
            {
                "id": 1,
                "admission_no": "544421",
                "name": "Joshith Sai",
                "class_section": "10-B",
                "book_name": "Advanced Mathematics Vol. 1",
                "issue_date": datetime.now().strftime("%Y-%m-%d"),
                "due_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
            }
        ],
        "history": [],
        "announcements": [
            { "id": 1, "date": "09/Aug/2026", "type": "Notice", "title": "Library Hours Updated", "desc": "The library will remain open until 5:00 PM during examination prep weeks." }
        ]
    }

def save_data(issues, history, announcements=None):
    db = load_data()
    if announcements is None:
        announcements = db.get("announcements", [])
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({"issues": issues, "history": history, "announcements": announcements}, f)
    except Exception as e:
        print("Storage error:", e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get('password') == 'librarian123':
        return jsonify({"success": True}), 200
    return jsonify({"success": False}), 401

@app.route('/api/stats', methods=['GET'])
def get_stats():
    db = load_data()
    active_loans = len(db["issues"])
    unique_students = len(set(item['admission_no'] for item in db["issues"] + db["history"]))
    return jsonify({
        "active_loans": active_loans,
        "registered_students": max(unique_students, len(set(i['admission_no'] for i in db["issues"])))
    })

@app.route('/api/students', methods=['GET'])
def get_students():
    db = load_data()
    students = list(set(item['admission_no'] for item in db["issues"] + db["history"]))
    return jsonify(students)

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    db = load_data()
    counts = {}
    for item in db["issues"] + db["history"]:
        adm = item['admission_no']
        if adm not in counts:
            counts[adm] = {
                "admission_no": adm,
                "name": item['name'],
                "class_section": item['class_section'],
                "total_borrowed": 0
            }
        counts[adm]["total_borrowed"] += 1
    
    sorted_leaderboard = sorted(counts.values(), key=lambda x: x['total_borrowed'], reverse=True)
    return jsonify(sorted_leaderboard)

@app.route('/api/issues', methods=['GET'])
def get_issues():
    db = load_data()
    return jsonify(db["issues"])

@app.route('/api/history', methods=['GET'])
def get_history():
    db = load_data()
    return jsonify(db["history"])

@app.route('/api/announcements', methods=['GET'])
def get_announcements():
    db = load_data()
    return jsonify(db.get("announcements", []))

@app.route('/api/announcements/add', methods=['POST'])
def add_announcement():
    db = load_data()
    announcements = db.get("announcements", [])
    data = request.json
    
    new_ann = {
        "id": int(datetime.now().timestamp() * 1000),
        "date": datetime.now().strftime("%d/%b/%Y"),
        "type": data.get("type", "Notice"),
        "title": data.get("title"),
        "desc": data.get("desc")
    }
    announcements.insert(0, new_ann)
    save_data(db["issues"], db["history"], announcements)
    return jsonify({"success": True, "announcement": new_ann}), 200

@app.route('/api/announcements/delete/<int:ann_id>', methods=['POST'])
def delete_announcement(ann_id):
    db = load_data()
    announcements = db.get("announcements", [])
    announcements = [a for a in announcements if a['id'] != ann_id]
    save_data(db["issues"], db["history"], announcements)
    return jsonify({"success": True}), 200

@app.route('/api/issue', methods=['POST'])
def issue_book():
    db = load_data()
    issues_db = db["issues"]
    history_db = db["history"]

    data = request.json
    admission_no = data.get('admission_no')
    book_name = data.get('book_name')
    
    existing = next((i for i in issues_db + history_db if i['admission_no'] == admission_no), None)
    
    if existing:
        name = existing['name']
        class_section = existing['class_section']
    else:
        name = data.get('student_name', 'Unknown Student')
        class_section = data.get('class_section', '10-A')

    new_entry = {
        "id": int(datetime.now().timestamp() * 1000),
        "admission_no": admission_no,
        "name": name,
        "class_section": class_section,
        "book_name": book_name,
        "issue_date": datetime.now().strftime("%Y-%m-%d"),
        "due_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    }
    
    issues_db.append(new_entry)
    save_data(issues_db, history_db, db.get("announcements", []))
    return jsonify({"success": True, "entry": new_entry}), 200

@app.route('/api/return/<item_id>', methods=['POST'])
def return_book(item_id):
    db = load_data()
    issues_db = db.get("issues", [])
    history_db = db.get("history", [])

    matched = next((i for i in issues_db if str(i.get('id')) == str(item_id)), None)
    
    if matched:
        matched['return_date'] = datetime.now().strftime("%Y-%m-%d")
        history_db.insert(0, matched)
        
        db["issues"] = [i for i in issues_db if str(i.get('id')) != str(item_id)]
        db["history"] = history_db

        save_data(db["issues"], db["history"], db.get("announcements", []))
        return jsonify({"success": True}), 200
        
    return jsonify({"success": False, "error": "Item not found"}), 404

@app.route('/api/update-date', methods=['POST'])
def update_date():
    db = load_data()
    issues_db = db["issues"]
    history_db = db["history"]

    data = request.json
    item_id = data.get('id')
    new_due_date = data.get('due_date')
    
    for item in issues_db:
        if str(item['id']) == str(item_id):
            item['due_date'] = new_due_date
            save_data(issues_db, history_db, db.get("announcements", []))
            return jsonify({"success": True}), 200
            
    return jsonify({"success": False}), 404

@app.route('/api/backup/export', methods=['GET'])
def export_backup():
    db = load_data()
    data_str = json.dumps(db, indent=4)
    return send_file(
        io.BytesIO(data_str.encode('utf-8')),
        mimetype='application/json',
        as_attachment=True,
        download_name=f'library_backup_{datetime.now().strftime("%Y-%m-%d")}.json'
    )

@app.route('/api/backup/import', methods=['POST'])
def import_backup():
    if not request.json:
        return jsonify({"success": False, "error": "Invalid payload"}), 400
    try:
        data = request.json
        save_data(data.get("issues", []), data.get("history", []), data.get("announcements", []))
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
