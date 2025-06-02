from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import pymysql
pymysql.install_as_MySQLdb()
import MySQLdb
import os
import traceback



app = Flask(__name__)
CORS(app)

print("✅ CONFIRM: RUNNING attendify.py with hardcoded DB config")

def get_db_connection():
    print("✅ Inside get_db_connection - USING HARDCODED VALUES")
    return MySQLdb.connect(
        host='mysql.railway.internal',
        user='root',
        passwd='ZHpIGNdzOMehYeSrGsHtgYAewIowZppQ',
        db='railway',
        port=3306,
        charset='utf8mb4'
    )
@app.route('/')
def home():
    return jsonify({"message": "Flask API is running!"})

@app.route('/api/save-employee', methods=['POST'])
def save_employee():
    try:
        data = request.json
        print("🟡 Received data:", data)

        full_name = data.get('full_name')
        username = data.get('username')
        phone_number = data.get('phone_number')
        email = data.get('email')
        password = data.get('password')
        occupation = data.get('occupation')
        faculty = data.get('faculty')

        print(f"🟡 Parsed fields: Full Name: {full_name}, Username: {username}, Phone: {phone_number}, Email: {email}, Password: {password}, Occupation: {occupation}, Faculty: {faculty}")

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO Employee (full_name, username, phone_number, email, password, occupation, faculty)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (full_name, username, phone_number, email, password, occupation, faculty))

        print("🟢 Row count after insert:", cur.rowcount)  # Should be 1

        conn.commit()
        cur.close()

        # Optional test select to confirm insert
        cur2 = conn.cursor()
        cur2.execute("SELECT * FROM Employee ORDER BY empid DESC LIMIT 1")
        new_entry = cur2.fetchone()
        print("🟢 Latest employee in DB:", new_entry)
        cur2.close()
        conn.close()

        return jsonify({"message": "Employee added successfully"}), 201

    except Exception as e:
        print("🔴 Error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/test-db', methods=['GET'])
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT DATABASE()')
        db_name = cur.fetchone()
        cur.close()
        conn.close()
        print("🟡 Connected to database:", db_name)
        return jsonify({"status": "success", "message": "DB connected!", "database": db_name})
    except Exception as e:
        print("🔴 DB connection error:", e)
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login_employee():
    try:
        data = request.json
        print("🔐 Received login data:", data)

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT empid FROM Employee WHERE BINARY username = %s AND BINARY password = %s", (username, password))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            return jsonify({"success": True, "empid": result[0]})
        else:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

    except Exception as e:
        print("🔴 Login error:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/get-employee/<int:empid>', methods=['GET'])
def get_employee(empid):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT full_name, email FROM Employee WHERE empid = %s", (empid,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            return jsonify({
                "success": True,
                "full_name": result[0],
                "email": result[1]
            }), 200
        else:
            return jsonify({"success": False, "message": "Employee not found"}), 404
    except Exception as e:
        print("🔴 Error:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/get-employee-full/<int:empid>', methods=['GET'])
def get_employee_full(empid):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT full_name, username, email, phone_number, occupation, faculty, empPhoto
            FROM Employee
            WHERE empid = %s
        """, (empid,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            import base64
            # empPhoto_base64 = base64.b64encode(row[6]).decode('utf-8') if row[6] else None

            return jsonify({
                "full_name": row[0],
                "username": row[1],
                "email": row[2],
                "phone_number": row[3],
                "occupation": row[4],
                "faculty": row[5],
                # "empPhoto": empPhoto_base64
            })
        else:
            return jsonify({"error": "Employee not found"}), 404
    except Exception as e:
        print("🔴 Error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/checkin', methods=['POST'])
def checkin():
    try:
        data = request.json
        empid = data.get('empid')
        date = data.get('date')
        time = data.get('time')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO attendance (empid, checkinDate, checkinTime)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE checkinTime = VALUES(checkinTime)
        """, (empid, date, time))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Check-in saved successfully"}), 201

    except Exception as e:
        print("Check-in error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/checkout', methods=['POST'])
def check_out():
    try:
        data = request.json
        empid = data.get('empid')
        date = data.get('date')
        time = data.get('time')

        if not all([empid, date, time]):
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM attendance WHERE empid = %s AND checkoutDate = %s", (empid, date))
        result = cur.fetchone()

        if result:
            cur.execute("UPDATE attendance SET checkoutTime = %s WHERE empid = %s AND checkoutDate = %s",
                        (time, empid, date))
        else:
            cur.execute("INSERT INTO attendance (empid, checkoutDate, checkoutTime) VALUES (%s, %s, %s)",
                        (empid, date, time))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Check-out saved"}), 201

    except Exception as e:
        print("Checkout error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/coffee-break', methods=['POST'])
def save_coffee_break():
    try:
        data = request.json
        empid = data.get('empid')
        time = data.get('time')
        date = data.get('date')

        if not all([empid, time, date]):
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO schedule (start_coffee_break, break_date, empid)
            VALUES (%s, %s, %s)
        """, (time, date, empid))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Coffee break saved successfully"}), 201

    except Exception as e:
        print("Coffee break error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-all-employees', methods=['GET'])
def get_all_employees():
    print("API /api/get-all-employees called")  # Debug log
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT empid, full_name, username, phone_number, email, occupation, faculty FROM Employee")
        employees = []
        for row in cur.fetchall():
            employees.append({
                "empid": row[0],
                "full_name": row[1],
                "username": row[2],
                "phone_number": row[3],
                "email": row[4],
                "occupation": row[5],
                "faculty": row[6]
            })
        cur.close()
        conn.close()

        print(f"Returning {len(employees)} employees wrapped in object")  # Debug log
        return jsonify({"employees": employees}), 200

    except Exception as e:
        print("Get all employees error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/submit-leave', methods=['POST'])
def submit_leave():
    try:
        data = request.json
        empid = data.get('empid')
        start_date = data.get('leave_start_date')
        end_date = data.get('leave_end_date')
        status = data.get('status')
        leave_type = data.get('leave_type')

        conn = get_db_connection()
        cur = conn.cursor()

        # Insert into main leave_request table
        cur.execute("""
            INSERT INTO leave_request (empid, leave_start_date, leave_end_date, status, leave_type)
            VALUES (%s, %s, %s, %s, %s)
        """, (empid, start_date, end_date, status, leave_type))

        # Insert into specific leave type table
        if leave_type == 'annual leave':
            cur.execute("""
                INSERT INTO annual_leave (empid, leave_start_date, leave_end_date, status, leave_type)
                VALUES (%s, %s, %s, %s, %s)
            """, (empid, start_date, end_date, status, leave_type))
        elif leave_type == 'sick leave':
            cur.execute("""
                INSERT INTO sick_leave (empid, leave_start_date, leave_end_date, status, leave_type)
                VALUES (%s, %s, %s, %s, %s)
            """, (empid, start_date, end_date, status, leave_type))
        elif leave_type == 'maternity leave':
            cur.execute("""
                INSERT INTO maternity_leave (empid, leave_start_date, leave_end_date, status, leave_type)
                VALUES (%s, %s, %s, %s, %s)
            """, (empid, start_date, end_date, status, leave_type))
        elif leave_type == 'bereavement leave':
            cur.execute("""
                INSERT INTO bereavement_leave (empid, leave_start_date, leave_end_date, status, leave_type)
                VALUES (%s, %s, %s, %s, %s)
            """, (empid, start_date, end_date, status, leave_type))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Leave request submitted successfully"}), 201

    except Exception as e:
        print("🔴 Leave submission error:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/leave-count/<int:empid>', methods=['GET'])
def get_leave_counts(empid):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        queries = {
            'annual_leave': "SELECT COUNT(*) FROM annual_leave WHERE empid = %s",
            'sick_leave': "SELECT COUNT(*) FROM sick_leave WHERE empid = %s",
            'maternity_leave': "SELECT COUNT(*) FROM maternity_leave WHERE empid = %s",
            'bereavement_leave': "SELECT COUNT(*) FROM bereavement_leave WHERE empid = %s"
        }

        results = {}
        for leave_type, query in queries.items():
            cur.execute(query, (empid,))
            count = cur.fetchone()[0]
            results[leave_type] = count

        cur.close()
        conn.close()

        return jsonify({
            "success": True,
            "empid": empid,
            "leave_counts": results
        }), 200

    except Exception as e:
        print("🔴 Error in get_leave_counts:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/leave-count', methods=['GET'])
def get_leave_count_by_employee():
    emp_id = request.args.get('empId')
    status = request.args.get('status')

    if not emp_id or not status:
        return jsonify({'error': 'Missing empId or status'}), 400

    leave_types = ["Annual Leave", "Sick Leave", "Maternity Leave", "Bereavement Leave"]
    leave_counts = []

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        for leave_type in leave_types:
            cur.execute(
                "SELECT COUNT(*) FROM leave_request WHERE empid = %s AND leave_type = %s AND status = %s",
                (emp_id, leave_type, status)
            )
            result = cur.fetchone()
            count = result[0] if result else 0
            leave_counts.append(f"{leave_type}: {count} requests ({status})")
        cur.close()
        conn.close()

        return jsonify(leave_counts)

    except Exception as e:
        print("SERVER ERROR:", e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/total-count', methods=['GET'])
def total_count():
    employee_id = request.args.get('employeeId', type=int)
    status = request.args.get('status')

    if employee_id is None or not status:
        return jsonify({"error": "Missing required query parameters: employeeId and status"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM leave_request WHERE empid = %s AND status = %s",
            (employee_id, status)
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()

        return jsonify({
            "count": count,
            "success": True,
            "employeeId": employee_id,
            "status": status
        }), 200

    except Exception as e:
        print("🔴 Error in total_count:", e)
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/pending-leave-requests', methods=['GET'])
def get_pending_leave_requests():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                lr.request_id, lr.empid, e.full_name, 
                lr.leave_start_date, lr.leave_end_date, 
                lr.status, lr.leave_type
            FROM 
                leave_request lr
            JOIN 
                Employee e ON lr.empid = e.empid
            WHERE 
                lr.status = 'pending'
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        leave_requests = []
        for row in rows:
            leave_requests.append({
                "requestId": row[0],
                "empId": row[1],
                "employeeName": row[2],
                "leaveStartDate": row[3],
                "leaveEndDate": row[4],
                "status": row[5],
                "leaveType": row[6],
            })

        return jsonify(leave_requests), 200

    except Exception as e:
        print("🔴 Error retrieving pending leave requests:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/update-leave-status', methods=['POST'])
def update_leave_status():
    try:
        data = request.json
        leave_id = data.get('leave_id')
        new_status = data.get('status')
        leave_type = data.get('leave_type')

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE leave_request SET status = %s WHERE request_id = %s
        """, (new_status, leave_id))

        if leave_type == 'annual leave':
            cur.execute("""
                UPDATE annual_leave SET status = %s WHERE id = %s
            """, (new_status, leave_id))
        elif leave_type == 'sick leave':
            cur.execute("""
                UPDATE sick_leave SET status = %s WHERE id = %s
            """, (new_status, leave_id))
        elif leave_type == 'maternity leave':
            cur.execute("""
                UPDATE maternity_leave SET status = %s WHERE id = %s
            """, (new_status, leave_id))
        elif leave_type == 'bereavement leave':
            cur.execute("""
                UPDATE bereavement_leave SET status = %s WHERE id = %s
            """, (new_status, leave_id))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Leave status updated successfully"}), 200

    except Exception as e:
        print("🔴 Error in updating leave status:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/leave-dates', methods=['GET'])
def get_leave_dates():
    empid = request.args.get('empid')

    if not empid:
        return jsonify({"error": "empid is required"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT empid, leave_start_date, leave_end_date FROM leave_request WHERE empid = %s", (empid,))
        rows = cur.fetchall()

        cur.close()
        conn.close()

        leaves = []
        for row in rows:
            leaves.append({
                "empid": row[0],
                "leave_start_date": row[1],
                "leave_end_date": row[2],
            })

        return jsonify(leaves), 200

    except Exception as e:
        print("🔴 Error retrieving leave dates:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/update-employee/<int:empid>', methods=['PUT'])
def update_employee(empid):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        full_name = data.get('full_name')
        username = data.get('username')
        email = data.get('email')
        phone_number = data.get('phone_number')
        occupation = data.get('occupation')
        faculty = data.get('faculty')

        conn = get_db_connection()
        cur = conn.cursor()

        update_query = """
            UPDATE Employee
            SET full_name = %s,
                username = %s,
                email = %s,
                phone_number = %s,
                occupation = %s,
                faculty = %s
            WHERE empid = %s
        """

        cur.execute(update_query, (full_name, username, email, phone_number, occupation, faculty, empid))
        conn.commit()
        rows_affected = cur.rowcount

        cur.close()
        conn.close()

        if rows_affected > 0:
            return jsonify({"message": "Profile updated successfully"}), 200
        else:
            return jsonify({"message": "Update failed or no changes made"}), 400

    except Exception as e:
        print("🔴 Update error:", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/save-meeting', methods=['POST'])
def save_meeting():
    try:
        data = request.json
        print("🟡 Received meeting data:", data)

        title = data.get('title')
        description = data.get('description')
        meeting_date = data.get('meeting_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        location = data.get('location')
        organizer_id = data.get('organizer_id')

        # Use 'Pending' as the default if not explicitly provided
        manager_approval = data.get('manager_approval', 'Pending')
        if manager_approval not in ['Approved', 'Rejected', 'Pending']:
            manager_approval = 'Pending'

        attendees = data.get('attendees', [])

        conn = get_db_connection()
        cur = conn.cursor()

        # Insert meeting with manager_approval as text
        cur.execute("""
            INSERT INTO meetings (title, description, meeting_date, start_time, end_time, location, organizer_id, manager_approval)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (title, description, meeting_date, start_time, end_time, location, organizer_id, manager_approval))

        meeting_id = cur.lastrowid

        # Insert attendees with default role and status
        for emp_id in attendees:
            cur.execute("""
                INSERT INTO meeting_attendees (meeting_id, employee_id, role, status)
                VALUES (%s, %s, %s, %s)
            """, (meeting_id, emp_id, 'Attendee', 'Present'))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Meeting and attendees added successfully!"}), 200

    except Exception as e:
        print("🔴 Error saving meeting:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/employees', methods=['GET'])
def get_employees_checkbox():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT empid, full_name FROM Employee")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        employees = [{"empid": row[0], "full_name": row[1]} for row in rows]

        return jsonify(employees), 200
    except Exception as e:
        print("🔴 Error fetching employees:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-pending-meetings', methods=['GET'])
def get_pending_meetings():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                m.meeting_id,
                m.title,
                m.description,
                m.meeting_date,
                m.start_time,
                m.end_time,
                m.location,
                m.organizer_id,
                m.manager_approval,
                e.full_name
            FROM meetings m
            JOIN Employee e ON m.organizer_id = e.empid
            WHERE LOWER(m.manager_approval) = 'pending'
        """)
        meetings = cur.fetchall()

        for row in meetings:
            print(f"Meeting ID: {row[0]}, Date: {row[3]}, Type: {type(row[3])}")

        cur.close()
        conn.close()

        result = []
        for row in meetings:
            result.append({
                "meeting_id": row[0],
                "title": row[1],
                "description": row[2],
                "meeting_date": str(row[3]) if row[3] else None,
                "start_time": str(row[4]) if row[4] else None,
                "end_time": str(row[5]) if row[5] else None,
                "location": row[6],
                "organizer_id": row[7],
                "manager_approval": row[8],
                "employee_name": row[9]
            })

        return jsonify(result), 200

    except Exception as e:
        print("🔴 Error fetching pending meetings:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/update-meeting-status', methods=['POST'])
def update_meeting_status():
    try:
        data = request.json
        print("Data received:", data)

        meeting_id = data.get('meeting_id')
        new_status = data.get('manager_approval')  # Expecting string: "Approved" or "Rejected"

        if new_status not in ['Approved', 'Rejected']:
            return jsonify({"error": "Invalid status. Must be 'Approved' or 'Rejected'."}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE meetings SET manager_approval = %s WHERE meeting_id = %s
        """, (new_status, meeting_id))

        conn.commit()

        if cur.rowcount == 0:
            return jsonify({"error": "No meeting found with the given ID"}), 404

        cur.close()
        conn.close()

        return jsonify({"message": "Meeting status updated successfully"}), 200

    except Exception as e:
        print("🔴 Error in updating meeting status:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-my-meetings', methods=['POST'])
def get_my_meetings():
    try:
        data = request.json
        empid = data.get('empid')
        if not empid:
            return jsonify({"error": "Employee ID not provided"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # Query to get all meetings where employee is an attendee
        cur.execute("""
    SELECT 
        m.meeting_id,
        m.title,
        m.description,
        m.meeting_date,
        m.start_time,
        m.end_time,
        m.location,
        m.organizer_id,
        e.full_name as organizer_name,
        m.manager_approval,
        ma.role,
        ma.status,
        ma.check_in_time,
        ma.check_out_time
    FROM meeting_attendees ma
    JOIN meetings m ON ma.meeting_id = m.meeting_id
    JOIN Employee e ON m.organizer_id = e.empid
    WHERE ma.employee_id = %s
      AND m.manager_approval = 'Approved'
    ORDER BY m.meeting_date DESC, m.start_time DESC
""", (empid,))


        meetings = cur.fetchall()

        # Build a list of dictionaries for JSON response
        meetings_list = []
        for row in meetings:
            meetings_list.append({
                "meeting_id": row[0],
                "title": row[1],
                "description": row[2],
                "meeting_date": str(row[3]),       # Convert date/time to string for JSON
                "start_time": str(row[4]),
                "end_time": str(row[5]),
                "location": row[6],
                "organizer_id": row[7],
                "organizer_name": row[8],
                "manager_approval": row[9],
                "role": row[10],
                "status": row[11],
                "check_in_time": str(row[12]) if row[12] else None,
                "check_out_time": str(row[13]) if row[13] else None
            })

        cur.close()
        conn.close()

        return jsonify(meetings_list), 200

    except Exception as e:
        print("🔴 Error fetching meetings for employee:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# STEP 8: Ensure Flask is in debug mode for full error logs
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host="0.0.0.0", port=5001)
