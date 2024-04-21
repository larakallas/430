from flask import Flask, render_template, request, redirect, send_file, url_for, session
from flask import Flask, render_template, request, jsonify
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
import os
from datetime import date, datetime
from flask import url_for

from flask_wtf import FlaskForm
from wtforms import FileField
from wtforms.validators import DataRequired
import os

from flask import send_from_directory
app = Flask(__name__)

# Define the path for the uploads directory
uploads_dir = os.path.join(os.getcwd(), 'static', 'uploads')

# Create the uploads directory if it doesn't exist
os.makedirs(uploads_dir, exist_ok=True)

# Set the UPLOAD_FOLDER configuration
app.config['UPLOAD_FOLDER'] = uploads_dir

class DocumentUploadForm(FlaskForm):
    document = FileField('Document', validators=[DataRequired()])

app.secret_key = 'your_secret_key'  # Change this to a secure secret key

# Sample data for employees and managers (you can replace this with a database)
conn = sqlite3.connect('employees.db', check_same_thread=False)
c = conn.cursor()



# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS employees
             (username TEXT PRIMARY KEY, password TEXT, department TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS managers
             (username TEXT PRIMARY KEY, password TEXT, department TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS attendance
             (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, status TEXT, FOREIGN KEY(username) REFERENCES employees(username))''')
c.execute('''CREATE TABLE IF NOT EXISTS tasks
             (task_id INTEGER PRIMARY KEY AUTOINCREMENT,
             employee_username TEXT,
             manager_username TEXT,
             task_name TEXT,
             start_date DATE,  -- Add start_date column here
             end_date DATE,
             progress INTEGER,
             FOREIGN KEY (employee_username) REFERENCES employees(username),
             FOREIGN KEY (manager_username) REFERENCES managers(username))''')

c.execute('''CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name TEXT NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    employee_username TEXT,
    FOREIGN KEY (employee_username) REFERENCES employees(username)
)
''')
c.execute('''DROP TABLE IF EXISTS course_videos''')

c.execute('''CREATE TABLE course_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    video_title TEXT,
    video_url TEXT,
    FOREIGN KEY (course_id) REFERENCES courses(id)
)''')
c.execute('''CREATE TABLE IF NOT EXISTS availability
             (employee_username TEXT, manager_username TEXT, date DATE, start_time TIME, end_time TIME,
             PRIMARY KEY (employee_username, manager_username, date),
             FOREIGN KEY (employee_username) REFERENCES employees(username),
             FOREIGN KEY (manager_username) REFERENCES managers(username))''')
c.execute('''CREATE TABLE IF NOT EXISTS employee_attendance
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              employee_username TEXT,
              date DATE,
              status TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS employee_attendance_new
             (employee_username TEXT,
              date DATE,
              status TEXT,
              PRIMARY KEY (employee_username, date))''')
c.execute('''CREATE TABLE IF NOT EXISTS employee_feedback
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             manager_username TEXT,
             employee_username TEXT,
             feedback TEXT,
             date_given DATE,
             FOREIGN KEY (manager_username) REFERENCES managers(username),
             FOREIGN KEY (employee_username) REFERENCES employees(username))''')
conn.commit()
# Copy data from the existing table to the new table
c.execute('''INSERT INTO employee_attendance_new (employee_username, date, status)
             SELECT employee_username, date, status
             FROM employee_attendance
             GROUP BY employee_username, date''')

c.execute('''CREATE TABLE IF NOT EXISTS announcements
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             manager_username TEXT,
             announcement TEXT,
             date_created DATE,
             FOREIGN KEY (manager_username) REFERENCES managers(username))''')

c.execute('''CREATE TABLE IF NOT EXISTS messages
             (message_id INTEGER PRIMARY KEY AUTOINCREMENT,
             sender_username TEXT,
             message TEXT,
             date_sent DATE,
             FOREIGN KEY (sender_username) REFERENCES employees(username) ON DELETE CASCADE,
             FOREIGN KEY (sender_username) REFERENCES managers(username) ON DELETE CASCADE)''')
# Drop the existing table
c.execute('''CREATE TABLE IF NOT EXISTS employee_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_username TEXT,
    document_path TEXT,
    FOREIGN KEY (employee_username) REFERENCES employees(username)
)
''')
c.execute('''DROP TABLE employee_attendance''')

# Rename the new table to match the original table name
c.execute('''ALTER TABLE employee_attendance_new RENAME TO employee_attendance''')


# Commit the changes
conn.commit()
# Commit the transaction to apply the changes
conn.commit()

c.execute("SELECT * FROM employee_attendance")
c.execute("Select * from messages")

# Fetch all rows from the result set
rows = c.fetchall()

# Print the selected records
for row in rows:
    print(row)
c.execute("SELECT * FROM announcements")
c.execute("SELECT * FROM messages")

# Fetch all rows from the result set

announcements = c.fetchall()

# Print each announcement
for announcement in announcements:
    print("Announcement ID:", announcement[0])
    print("Manager Username:", announcement[1])
    print("Announcement:", announcement[2])
    print("Date Created:", announcement[3])
    print("--------------------------------------")

attendance_report = []
# Insert manager (if not exists)
c.execute("INSERT OR IGNORE INTO managers VALUES (?, ?, ?)", ('manager1', 'pass1', 'IT'))
conn.commit()



# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if role == 'employee':
            c.execute("SELECT * FROM employees WHERE username = ? AND password = ?", (username, password))
            user = c.fetchone()
            if user:
                session['username'] = username
                return redirect(url_for('employee_dashboard'))
            else:
                return render_template('login.html', error='Invalid employee credentials')

        elif role == 'manager':
            c.execute("SELECT * FROM managers WHERE username = ? AND password = ?", (username, password))
            user = c.fetchone()
            if user:
                session['username'] = username
                return redirect(url_for('manager_dashboard'))  # Corrected redirection to manager_dashboard
            else:
                return render_template('login.html', error='Invalid manager credentials')

    return render_template('login.html')

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' in session:
        if request.method == 'POST':
            old_username = session['username']  # Get the current username from the session
            old_password = request.form['old_password']
            new_password = request.form['new_password']

            # Check if the user exists in either employees or managers table
            c.execute("SELECT * FROM employees WHERE username = ? AND password = ?", (old_username, old_password))
            employee = c.fetchone()
            if not employee:
                c.execute("SELECT * FROM managers WHERE username = ? AND password = ?", (old_username, old_password))
                manager = c.fetchone()

            if employee or manager:
                # Update the password for the user
                if employee:
                    c.execute("UPDATE employees SET password = ? WHERE username = ?", (new_password, old_username))
                else:
                    c.execute("UPDATE managers SET password = ? WHERE username = ?", (new_password, old_username))
                conn.commit()
                return redirect(url_for('login'))
            else:
                error = 'Invalid old password or username.'
                return render_template('change_password.html', error=error)
        else:
            return render_template('change_password.html')
    else:
        return redirect(url_for('login'))



@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))
@app.route('/employee_dashboard', methods=['GET', 'POST'])
def employee_dashboard():
    if 'username' in session:
        username = session['username']
        form = DocumentUploadForm()  # Create an instance of the form

        if request.method == 'POST':
            # Handling attendance submission
            status = request.form.get('status')  # Use .get() to avoid KeyError
            manager_username = request.form.get('username')
            today = datetime.now().date()
            if status is not None:  # Check if status field is present in the form
                c.execute("INSERT INTO attendance (employee_username, manager_username, date, status) VALUES (?, ?, ?, ?)",
                          (username, manager_username, today, status))
                conn.commit()

            # Handling task progress update
            task_name = request.form.get('task_name')
            new_progress = int(request.form.get('progress', 0))  # Provide a default value if progress is not present
            if task_name is not None:  # Check if task_name field is present in the form
                c.execute("UPDATE tasks SET progress = ? WHERE employee_username = ? AND task_name = ?",
                          (new_progress, username, task_name))
                conn.commit()

            # Handling document upload
            if form.validate_on_submit():
                document = form.document.data  # Get the uploaded document
                filename = document.filename  # Get the filename without securing it
                document_path = os.path.join('static/uploads', filename)
                document.save(document_path)  # Save the document to the specified path
                # Store the document path in the database for the logged-in employee
                c.execute("INSERT INTO employee_documents (employee_username, document_path) VALUES (?, ?)",
                          (username, document_path))
                conn.commit()

            # Redirect to refresh the page and prevent form resubmission
            return redirect(url_for('employee_dashboard'))

        # Fetch tasks assigned to the current employee from the database
        c.execute("SELECT * FROM tasks WHERE employee_username = ?", (username,))
        tasks = c.fetchall()

        # Fetch scheduled meetings for the current employee from the database
        c.execute("SELECT a.date, a.start_time, a.end_time, e.username AS employee_username, m.username AS manager_username FROM availability a INNER JOIN employees e ON a.employee_username = e.username INNER JOIN managers m ON a.manager_username = m.username WHERE a.employee_username = ? ORDER BY a.date ASC, a.start_time ASC", (username,))
        meetings = c.fetchall()

        # Fetch uploaded documents for the current employee from the database
        c.execute("SELECT document_path FROM employee_documents WHERE employee_username = ?", (username,))
        employee_documents = c.fetchall()

        # Fetch feedback for the current employee from the database
        c.execute("SELECT f.feedback, f.date_given, m.username AS manager_username FROM employee_feedback f JOIN managers m ON f.manager_username = m.username WHERE f.employee_username = ?", (username,))
        employee_feedback = c.fetchall()

        return render_template('employee_dashboard.html', form=form, tasks=tasks, meetings=meetings, employee_documents=employee_documents, employee_feedback=employee_feedback)
    else:
        return redirect(url_for('login'))
    
@app.route('/scheduled_meetings', methods=['GET', 'POST'])
def scheduled_meetings():
    if 'username' in session:
        username = session['username']
        if request.method == 'POST':
            selected_date = request.form['selected_date']
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            c.execute("SELECT * FROM availability WHERE employee_username = ? AND date = ?", (username, selected_date))
            meetings = c.fetchall()
            return render_template('scheduled_meetings.html', meetings=meetings)
        else:
            c.execute("SELECT * FROM availability WHERE employee_username = ?", (username,))
            meetings = c.fetchall()
            return render_template('scheduled_meetings.html', meetings=meetings)
    else:
        return redirect(url_for('login'))

@app.route('/view_tasks', methods=['GET', 'POST'])
def view_tasks():
    if 'username' in session:
        username = session['username']
        if request.method == 'POST':
            task_name = request.form['task_name']
            new_progress = int(request.form['progress'])
            c.execute("UPDATE tasks SET progress = ? WHERE employee_username = ? AND task_name = ?", (new_progress, username, task_name))
            conn.commit()
            return redirect(url_for('employee_dashboard'))
        else:
            c.execute("SELECT * FROM tasks WHERE employee_username = ?", (username,))
            tasks = c.fetchall()
            return render_template('view_tasks.html', tasks=tasks)
    else:
        return redirect(url_for('login'))

@app.route('/upload_document', methods=['GET', 'POST'])
def upload_document():
    if 'username' in session:
        username = session['username']
        if request.method == 'POST':
            document = request.files['document']
            document.save(os.path.join(app.config['UPLOAD_FOLDER'], document.filename))
            c.execute("INSERT INTO employee_documents (employee_username, document_path) VALUES (?, ?)",
                      (username, document.filename))
            conn.commit()
            return redirect(url_for('employee_dashboard'))
        else:
            return render_template('upload_document.html')
    else:
        return redirect(url_for('login'))
        
    






@app.route('/submit_feedback', methods=['GET', 'POST'])
def submit_feedback():
    if 'username' in session and session['username'] in [user[0] for user in c.execute("SELECT username FROM managers").fetchall()]:
        if request.method == 'POST':
            manager_username = session['username']
            employee_username = request.form['employee_username']
            feedback_text = request.form['feedback_text']
            date_given = datetime.now().date()

            c.execute("INSERT INTO employee_feedback (manager_username, employee_username, feedback, date_given) VALUES (?, ?, ?, ?)",
                      (manager_username, employee_username, feedback_text, date_given))
            conn.commit()
            return redirect(url_for('manager_dashboard'))
        else:
            c.execute("SELECT username FROM employees")
            employees = c.fetchall()
            return render_template('submit_feedback.html', employees=employees)
    else:
        return redirect(url_for('login'))
@app.route('/view_pdf_documents')
def view_pdf_documents():
    # Assuming you have a function get_pdf_files() that fetches the list of available PDF documents
    pdf_files = get_pdf_files()
    return render_template('view_employee_documents.html', pdf_files=pdf_files)


@app.route('/open_pdf/<filename>')
def open_pdf(filename):
    document_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(document_path, as_attachment=False)

@app.route('/view_feedback', methods=['GET'])
def view_feedback():
    if 'username' in session:
        username = session['username']
        if username in [user[0] for user in c.execute("SELECT username FROM managers").fetchall()]:
            c.execute("SELECT e.username, f.feedback, f.date_given FROM employees e JOIN employee_feedback f ON e.username = f.employee_username")
            feedback_data = c.fetchall()
            return render_template('view_feedback.html', feedback_data=feedback_data)
        else:
            c.execute("SELECT f.feedback, f.date_given, m.username FROM employee_feedback f JOIN managers m ON f.manager_username = m.username WHERE f.employee_username = ?", (username,))
            feedback_data = c.fetchall()
            return render_template('view_feedback.html', feedback_data=feedback_data)
    else:
        return redirect(url_for('login'))
@app.route('/employee_list', methods=['GET', 'POST'])
def employee_list():
    if 'username' in session:  # Assuming 'username' is the key for the logged-in user in the session
        # Fetch all employees and their tasks for task assignment
        c.execute("SELECT * FROM employees")
        employees = c.fetchall()
        employees_with_tasks = []
        for employee in employees:
            c.execute("SELECT * FROM tasks WHERE employee_username = ?", (employee[0],))
            tasks = c.fetchall()
            employees_with_tasks.append((employee, tasks))

        # Fetch scheduled meetings from the database
        manager_username = session['username']  # Assuming manager's username is stored in session
        c.execute("SELECT a.date, a.start_time, a.end_time, e.username AS employee_username, m.username AS manager_username FROM availability a INNER JOIN employees e ON a.employee_username = e.username INNER JOIN managers m ON a.manager_username = m.username WHERE a.manager_username = ? ORDER BY a.date ASC, a.start_time ASC", (manager_username,))
        scheduled_meetings = c.fetchall()

        return render_template('manager_dashboard.html', employees_with_tasks=employees_with_tasks, scheduled_meetings=scheduled_meetings)
    else:
        return redirect(url_for('login'))  # Redirect to login if not logged in


@app.route('/schedule_meeting', methods=['GET', 'POST'])
def schedule_meeting():
    if 'username' in session:
        if request.method == 'POST':
            manager_username = session['username']
            employee_username = request.form['employee_username']
            meeting_date = request.form['meeting_date']
            start_time = request.form['start_time']
            end_time = request.form['end_time']

            if check_availability(employee_username, manager_username, meeting_date, start_time, end_time):
                c.execute("INSERT INTO availability (employee_username, manager_username, date, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
                          (employee_username, manager_username, meeting_date, start_time, end_time))
                conn.commit()
                return redirect(url_for('manager_dashboard'))
            else:
                return "Employee or manager is not available at the selected date and time."
        else:
            # Handle GET request (rendering form or other content)
            # For example, you could render a form to schedule a meeting here
            return render_template('schedule_meeting.html')
    else:
        return redirect(url_for('login_page'))

c.execute("SELECT * FROM tasks")

# Fetch all rows
tasks_data = c.fetchall()

@app.route('/view_calendar', methods=['GET', 'POST'])
def view_calendar():
    if 'username' in session:
        # Assuming your database connection and cursor are defined as 'conn' and 'c'
        c.execute("SELECT * FROM availability WHERE employee_username = ?", (session['username'],))
        meetings_data = c.fetchall()  # Fetch all meetings for the logged-in employee

        # Now you can pass the meetings_data to your template for rendering
        return render_template('view_calendar.html', meetings_data=meetings_data)
    else:
        return redirect(url_for('manager_dashboard'))



@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if 'username' in session:
        if request.method == 'POST':
            manager_username = session['username']
            username = request.form['username']
            password = request.form['password']
            department = request.form['department']

            # Check for existing username
            c.execute("SELECT * FROM employees WHERE username = ?", (username,))
            existing_user = c.fetchone()
            if existing_user:
                return jsonify(message="Username already exists!")

            c.execute("INSERT INTO employees (username, password, department) VALUES (?, ?, ?)",
                      (username, password, department))
            conn.commit()
            return redirect(url_for('manager_dashboard'))
        else:
            # Handle GET request to render the form
            return render_template('add_employee.html')
    else:
        return redirect(url_for('login_page'))







from datetime import date

@app.route('/assign_task', methods=['GET', 'POST'])
def assign_task():
    if 'username' in session:
        if request.method == 'POST':
            manager_username = session['username']
            employee_username = request.form['employee_username']
            task_name = request.form['task_name']
            start_date = request.form['start_date']
            end_date = request.form['end_date']

            # Validate date formats (assuming YYYY-MM-DD format)
            try:
                start_date_obj = date.fromisoformat(start_date)
                end_date_obj = date.fromisoformat(end_date)
            except ValueError:
                return "Invalid date format. Please use YYYY-MM-DD."

            # Check for past start date and invalid date order
            if start_date_obj < date.today():
                return "Start date cannot be before today."
            elif start_date_obj > end_date_obj:
                return "Start date cannot be after end date."

            # Check if the task is already assigned to the employee
            c.execute("SELECT * FROM tasks WHERE employee_username = ? AND manager_username = ? AND task_name = ?",
                      (employee_username, manager_username, task_name))
            existing_task = c.fetchone()
            if existing_task:
                return "Task already assigned to the employee."

            # Insert the new task into the tasks table
            c.execute("INSERT INTO tasks (employee_username, manager_username, task_name, start_date, end_date, progress) VALUES (?, ?, ?, ?, ?, ?)",
                      (employee_username, manager_username, task_name, start_date, end_date, 0))
            conn.commit()
            return redirect(url_for('manager_dashboard'))
        else:
            # Handle GET request (rendering form or other content)
            return render_template('assign_task.html')
    else:
        return redirect(url_for('login_page'))




from flask import flash

@app.route('/submit_attendance', methods=['GET', 'POST'])
def submit_attendance():
    if 'username' in session:
        if request.method == 'POST':
            username = session['username']
            status = request.form.get('status')
            today = datetime.now().date()
            c.execute("INSERT INTO employee_attendance (employee_username, date, status) VALUES (?, ?, ?)",
                      (username, today, status))
            conn.commit()

            # Return success message as JSON
            return jsonify(message="Attendance submitted successfully!")
        else:
            # Handle GET request (rendering form or other content)
            return render_template('submit_attendance.html')
    else:
        return redirect(url_for('login'))




    
def check_availability(employee_username, manager_username, date, start_time, end_time):
    # Query the availability table to check for conflicting schedules
    c.execute('''SELECT * FROM availability 
                 WHERE employee_username = ? AND manager_username = ? AND date = ?
                 AND ((start_time <= ? AND end_time >= ?) OR (start_time <= ? AND end_time >= ?))''',
              (employee_username, manager_username, date, start_time, start_time, end_time, end_time))
    conflict = c.fetchone()
    if conflict:
        return False  # Conflicting schedule found
    else:
        return True  # No conflicting schedule found

@app.route('/manager_dashboard', methods=['GET', 'POST'])
def manager_dashboard():
    if 'username' in session:
        manager_username = session['username']

        if request.method == 'POST':
            employee_username = request.form['username']
            meeting_date = request.form['meeting_date']
            start_time = request.form['start_time']
            end_time = request.form['end_time']

            # Check if the meeting date is at least today's date
            today = date.today()
            meeting_date = datetime.strptime(meeting_date, '%Y-%m-%d').date()
            if meeting_date >= today:
                # Check if the employee and manager are available on the meeting date and time
                c.execute("SELECT * FROM availability WHERE employee_username = ? AND manager_username = ? AND date = ? AND start_time = ? AND end_time = ?",
                          (employee_username, manager_username, meeting_date, start_time, end_time))
                availability = c.fetchone()

                if not availability:
                    # Both employee and manager are available, proceed with scheduling the meeting
                    # Insert the meeting into the availability table
                    c.execute("INSERT INTO availability (employee_username, manager_username, date, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
                              (employee_username, manager_username, meeting_date, start_time, end_time))
                    conn.commit()
                    # Redirect or render a success message
                    return redirect(url_for('manager_dashboard'))
                else:
                    # The employee or manager is not available at the selected date and time
                    error = 'Employee or manager is not available at the selected date and time.'
            else:
                # The meeting date is not valid (before today's date)
                error = 'Meeting date must be today or later.'

            # Render the manager dashboard with an error message
            c.execute("SELECT * FROM employees")
            employees = c.fetchall()
            employees_list = [employee[0] for employee in employees]  # Fetch only the usernames
            return render_template('manager_dashboard.html', employees_list=employees_list, error=error)

        else:
            # Handle GET request for the manager dashboard
            c.execute("SELECT * FROM employees")
            employees = c.fetchall()
            employees_list = []
            for employee in employees:
                c.execute("SELECT * FROM tasks WHERE employee_username = ?", (employee[0],))
                tasks = c.fetchall()
                employees_list.append((employee[0], tasks))
            return render_template('manager_dashboard.html', employees_list=employees_list)
    else:
        # Redirect to login if not logged in
        return redirect(url_for('login'))

def get_employees_with_tasks():
    # Replace this with your actual database query to fetch employees and their tasks
    employees_with_tasks = []
    # Example query: employees_with_tasks = db.query("SELECT * FROM employees_with_tasks")
    return employees_with_tasks

def get_pdf_files():
    # Replace this with your actual code to get the list of PDF files in the uploads folder
    pdf_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.pdf')]
    return pdf_files

    return employees_with_tasks


@app.route('/view_attendance', methods=['GET', 'POST'])
def view_attendance():
    if 'username' in session:
        username = session['username']
        if request.method == 'POST':
            selected_date = request.form['selected_date']
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            c.execute("SELECT * FROM employee_attendance WHERE date = ?", (selected_date,))
            attendance_records = c.fetchall()
            return render_template('view_attendance.html', attendance_records=attendance_records)
        else:
            c.execute("SELECT * FROM employee_attendance")
            attendance_records = c.fetchall()
            return render_template('view_attendance.html', attendance_records=attendance_records)
    else:
        return redirect(url_for('login'))

@app.route('/create_announcement', methods=['GET', 'POST'])
def create_announcement():
    if 'username' in session:
        if request.method == 'POST':
            # Extract the announcement text from the form data
            announcement_text = request.form['announcement_text']
            
            # Get the manager's username from the session
            manager_username = session['username']
            
            # Get the current date
            date_created = datetime.now().date()
            
            # Insert the announcement into the database
            c.execute("INSERT INTO announcements (manager_username, announcement, date_created) VALUES (?, ?, ?)",
                      (manager_username, announcement_text, date_created))
            conn.commit()
            
            # Redirect to the manager dashboard after successfully inserting the announcement
            return redirect(url_for('manager_dashboard'))
        else:
            # Render the form to create an announcement
            return render_template('create_announcement.html')
    else:
        return redirect(url_for('login'))

@app.route('/view_announcements')
def view_announcements():
    if 'username' in session:
        # Fetch all announcements from the database
        c.execute("SELECT * FROM announcements")
        announcements = c.fetchall()
        return render_template('view_announcement.html', announcements=announcements)
    else:
        return redirect(url_for('login'))
@app.route('/messaging', methods=['GET', 'POST'])
def messaging():
    if 'username' in session:
        if request.method == 'POST':
            # Get the sender's username from the session
            sender_username = session['username']

            # Extract the message text from the form data
            message_text = request.form['message_text']

            # Get the current date
            date_sent = datetime.now().date()

            # Insert the message into the database
            c.execute("INSERT INTO messages (sender_username, message, date_sent) VALUES (?, ?, ?)",
                      (sender_username, message_text, date_sent))
            conn.commit()

            # Redirect to the messaging page after successfully inserting the message
            return redirect(url_for('messaging'))
        else:
            # Fetch all messages from the database
            c.execute("SELECT sender_username, message, date_sent FROM messages")
            messages = c.fetchall()
            return render_template('messaging.html', messages=messages)
    else:
        return redirect(url_for('login'))
from flask import render_template, request, session, redirect, url_for

@app.route('/delete_employee', methods=['GET', 'POST'])
def delete_employee():
    if 'username' in session:
        if request.method == 'POST':
        
            manager_username = session['username']

            # Get the username of the employee to be deleted from the form data
            employee_username = request.form['employee_username']

            # Check if the employee exists
            c.execute("SELECT * FROM employees WHERE username = ?", (employee_username,))
            employee = c.fetchone()

            if employee:
                c.execute("DELETE FROM employees WHERE username = ?", (employee_username,))
                conn.commit()

                
                c.execute("DELETE FROM tasks WHERE employee_username = ?", (employee_username,))
                conn.commit()

                return redirect(url_for('manager_dashboard'))
            else:
                error = 'Employee does not exist.'
                return render_template('delete_employee.html', error=error)
        else:
            return render_template('delete_employee.html', error=None) 
    else:
        error = 'You must be logged in to perform this action.'
        return render_template('delete_employee.html', error=error)



@app.route('/courses')
def list_courses():
    if 'username' in session:
        # Fetch all courses from the database
        c.execute("SELECT * FROM courses")
        courses = c.fetchall()
        return render_template('courses.html', courses=courses)
    else:
        return redirect(url_for('login'))

@app.route('/course/<int:course_id>')
def view_course(course_id):
    if 'username' in session:
        # Fetch the details of the selected course from the database
        c.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,))
        course = c.fetchone()
        if course:
            return render_template('course_details.html', course=course)
        else:
            return "Course not found."
    else:
        return redirect(url_for('login'))
from wtforms import Form, StringField, TextAreaField, DateField, SelectField, validators

class CourseForm(FlaskForm):
    course_name = StringField('Course Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])
    employee_username = SelectField('Assign to Employee', coerce=int, validators=[DataRequired()])
    video_titles = StringField('Video Title')
    video_urls = StringField('Video URL')
from flask import request

from flask import render_template

from flask import Flask, render_template, request, redirect, url_for, session


@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    form = CourseForm(request.form)
    
    if 'username' in session:
        if request.method == 'POST':
            manager_username = session['username']
            course_name = form.course_name.data
            description = form.description.data
            start_date = form.start_date.data
            end_date = form.end_date.data
            employee_username = form.employee_username.data

            # Save uploaded videos to a folder
            video_titles = request.form.getlist('video_titles[]')
            video_urls = request.form.getlist('video_urls[]')
            
            # Assuming you have a table 'courses' with appropriate columns
            c.execute("INSERT INTO courses (course_name, description, start_date, end_date, employee_username) VALUES (?, ?, ?, ?, ?)",
                      (course_name, description, start_date, end_date, employee_username))
            course_id = c.lastrowid  # Get the ID of the inserted course
            
            # Insert video information into a 'course_videos' table
            for title, url in zip(video_titles, video_urls):
                c.execute("INSERT INTO course_videos (course_id, video_title, video_url) VALUES (?, ?, ?)",
                          (course_id, title, url))
                conn.commit()

            return redirect(url_for('manager_dashboard'))
        
        else:
            # Fetch the list of employees from your database
            c.execute("SELECT username FROM employees")
            employees = c.fetchall()
            # Render the form to create a course along with the list of employees
            return render_template('create_course.html', form=form, employees=employees)
    else:
        return redirect(url_for('login'))



@app.route('/employee_courses')
def employee_courses():
    if 'username' in session:
        username = session['username']
        # Fetch courses assigned to the current employee from the database
        c.execute("SELECT * FROM courses WHERE employee_username = ?", (username,))
        courses = c.fetchall()
        return render_template('employee_courses.html', courses=courses)
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
