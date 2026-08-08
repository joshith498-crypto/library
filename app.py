from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# Active borrowings store
issues_db = [
    {
        "id": 1,
        "admission_no": "544421",
        "name": "Tester",
        "class_section": "10-B",
        "book_name": "Mathematics Vol. 1",
        "issue_date": datetime.now().strftime("%Y-%m-%d"),
        "due_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    }
]

# Permanent historical archive for returned/all-time transactions
history_db = []

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
    active_loans = len(issues_db)
    unique_students = len(set(item['admission_no'] for item in issues_db + history_db))
    return jsonify({
        "active_loans": active_loans,
        "registered_students": max(unique_students, len(set(i['admission_no'] for i in issues_db)))
    })

@app.route('/api/students', methods=['GET'])
def get_students():
    students = list(set(item['admission_no'] for item in issues_db + history_db))
    return jsonify(students)

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    counts = {}
    for item in issues_db + history_db:
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
    return jsonify(issues_db)

@app.route('/api/history', methods=['GET'])
def get_history():
    return jsonify(history_db)

@app.route('/api/issue', methods=['POST'])
def issue_book():
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
    return jsonify({"success": True, "entry": new_entry}), 200

@app.route('/api/return/<int:item_id>', methods=['POST'])
def return_book(item_id):
    global issues_db
    matched = next((i for i in issues_db if i['id'] == item_id), None)
    if matched:
        matched['return_date'] = datetime.now().strftime("%Y-%m-%d")
        history_db.insert(0, matched)
        issues_db = [i for i in issues_db if i['id'] != item_id]
        return jsonify({"success": True}), 200
    return jsonify({"success": False}), 404

@app.route('/api/update-date', methods=['POST'])
def update_date():
    data = request.json
    item_id = data.get('id')
    new_due_date = data.get('due_date')
    
    for item in issues_db:
        if item['id'] == item_id:
            item['due_date'] = new_due_date
            return jsonify({"success": True}), 200
            
    return jsonify({"success": False}), 404

if __name__ == '__main__':
    app.run(debug=True)
