from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "project_management_secret_key"

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            start_date TEXT,
            end_date TEXT,
            created_by INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            assigned_to INTEGER,
            status TEXT DEFAULT 'To Do',
            due_date TEXT
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password)
            )

            conn.commit()
            conn.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            conn.close()
            return "Email already registered."

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, password)
        ).fetchone()

        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("dashboard"))

        return "Invalid email or password."

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    projects = conn.execute(
        "SELECT * FROM projects WHERE created_by = ?",
        (session["user_id"],)
    ).fetchall()

    tasks = conn.execute("""
        SELECT tasks.*, projects.name AS project_name
        FROM tasks
        JOIN projects ON tasks.project_id = projects.id
        WHERE projects.created_by = ?
    """, (session["user_id"],)).fetchall()

    conn.close()

    total_tasks = len(tasks)

    completed_tasks = len(
        [task for task in tasks if task["status"] == "Completed"]
    )

    return render_template(
        "dashboard.html",
        projects=projects,
        tasks=tasks,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks
    )


@app.route("/projects")
def projects():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    projects = conn.execute(
        "SELECT * FROM projects WHERE created_by = ?",
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "projects.html",
        projects=projects
    )


@app.route("/create-project", methods=["GET", "POST"])
def create_project():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        conn = get_db()

        conn.execute("""
            INSERT INTO projects
            (name, description, start_date, end_date, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            description,
            start_date,
            end_date,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("projects"))

    return render_template("create_project.html")


@app.route("/project/<int:project_id>")
def project_details(project_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    project = conn.execute(
        "SELECT * FROM projects WHERE id = ?",
        (project_id,)
    ).fetchone()

    tasks = conn.execute(
        "SELECT * FROM tasks WHERE project_id = ?",
        (project_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "project_details.html",
        project=project,
        tasks=tasks
    )


@app.route("/create-task/<int:project_id>", methods=["GET", "POST"])
def create_task(project_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        due_date = request.form["due_date"]

        conn = get_db()

        conn.execute("""
            INSERT INTO tasks
            (project_id, title, description, due_date)
            VALUES (?, ?, ?, ?)
        """, (
            project_id,
            title,
            description,
            due_date
        ))

        conn.commit()
        conn.close()

        return redirect(
            url_for("project_details", project_id=project_id)
        )

    return render_template(
        "create_task.html",
        project_id=project_id
    )


@app.route("/update-task/<int:task_id>/<status>")
def update_task(task_id, status):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    task = conn.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    if task:

        conn.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id)
        )

        conn.commit()

        project_id = task["project_id"]

    else:
        project_id = None

    conn.close()

    if project_id:
        return redirect(
            url_for("project_details", project_id=project_id)
        )

    return redirect(url_for("dashboard"))

  create_tables()

if __name__ == "__main__":
    app.run(debug=True)