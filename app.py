from datetime import datetime
import os
from functools import wraps

from dotenv import load_dotenv
load_dotenv()

from flask import(
    Flask, render_template, redirect, url_for, request, flash, send_from_directory, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    UserMixin, LoginManager, login_user, login_required, logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func

print("Loaded app.py from:", __file__)

# ----- config -----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "resumes")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf","doc", "docx"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///jobs.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# ----- Models -----
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    # Roles
    is_admin = db.Column(db.Boolean, default=False)
    is_employer = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.String(50))
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(50))
    job_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    posted_by_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    posted_by = db.relationship("User", backref=db.backref("posted_jobs", cascade="all, delete-orphan"))

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    cover_letter = db.Column(db.Text)
    resume_path = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    job = db.relationship("Job", backref=db.backref("applications", cascade="all, delete-orphan"))
    applicant = db.relationship("User", backref=db.backref("applications", cascade="all, delete-orphan"))
    
# ----- Create DB and default admin -----
with app.app_context():
    db.create_all()

    # created hard-coded admin (we can use env variables in real projects)
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@gmail.com")
    ADMIN_PWD = os.getenv("ADMIN_PWD", "Admin@123")

    admin = User.query.filter_by(email = ADMIN_EMAIL).first()
    if not admin:
        admin = User(fullname="Site Admin", email = ADMIN_EMAIL, is_admin=True, is_employer = True)
        admin.set_password(ADMIN_PWD)
        db.session.add(admin)
        db.session.commit()
        print(f"[setup] Admin created: {ADMIN_EMAIL} / {ADMIN_PWD}")
    else:
        #ensure flags are set
        updated = False
        if not admin.is_admin:
            admin.is_admin = True
            updated = True
        if not admin.is_employer:
            admin.is_employer = True
            updated =True
        if updated:
            db.session.commit()

# ----- Login -----
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----- Helpers -----
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
            abort(403)
        return f(*args, **kwargs)
    return decorated

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ----- Routes -----

@app.route("/")
def index():
    #filters from query params
    q = request.args.get("q", "").strip()
    company = request.args.get("company", "").strip()
    location = request.args.get("location", "").strip()
    job_type = request.args.get("job_type", "").strip()

    query = Job.query

    if q:
        q_like = f"%{q}%"
        query = query.filter(
            (Job.job_title.ilike(q_like)) | (Job.description.ilike(q_like))
        )
    if company:
        query = query.filter(func.lower(Job.company) == func.lower(company))
    if location:
        query = query.filter(func.lower(Job.location) == func.lower(location))
    if job_type:
        query = query.filter(func.lower(Job.job_type) == func.lower(job_type))
    
    jobs = query.order_by(Job.created_at.desc()).all()

    #dropdown values
    companies = [c[0] for c in db.session.query(Job.company).filter(Job.company != None).distinct().all()]
    job_types = [c[0] for c in db.session.query(Job.job_type).filter(Job.job_type != None).distinct().all()]

    return render_template(
        "index.html",
        jobs = jobs,
        q=q,
        company = company,
        location = location,
        job_type = job_type,
        companies = companies, 
        job_types=job_types
    )

# ----- Auth -----
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm","")

        if not fullname or not email or not password or not confirm:
            flash("Please fill all the required fields.", "warning")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.","warning")
            return redirect(url_for("register"))

        #employer checkbox
        is_employer_flag = True if request.form.get("is_employer") == "on" else False

        # defensive check
        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please log in.", "warning")
            return redirect(url_for("login"))
        
        user = User(fullname=fullname, email=email, is_employer=is_employer_flag)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Registered and Logged in successfully.","success")
        return redirect(url_for("index"))

    return render_template("register.html") 

@app.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password","")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Logged in Successfully.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("Invalid credentials.", "danger")
            return redirect(url_for("login"))
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged Out.", "info")
    return redirect(url_for("index"))

# ----- Job CRUD -----
@app.route("/job/create", methods=["GET", "POST"])
@login_required
def create_job():
    # only employer or admin can post
    if not (getattr(current_user, "is_employer", False) or getattr(current_user,"is_admin", False)):
        flash("Only employers can post jobs. Register as an emplyer or contact admin.", "danger")
        return redirect(url_for("index"))
    if request.method == "POST":
        title = request.form.get("job_title", "").strip()
        company = request.form.get("company", "").strip()
        salary = request.form.get("salary","").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        job_type = request.form.get("job_type", "").strip()

        if not title or not company or not description:
            flash("Please fill Title, Company and Description.", "warning")
            return redirect(url_for("create_job"))
        
        job = Job(
            job_title = title,
            company = company,
            salary = salary,
            description = description,
            location = location,
            job_type = job_type,
            posted_by = current_user
        )
        db.session.add(job)
        db.session.commit()
        flash("Job posted successfully.", "success")
        return redirect(url_for("job_detail", job_id=job.id))
    
    return render_template("create_job.html")

@app.route("/job/<int:job_id>")
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    applied = False
    if current_user.is_authenticated:
        applied = Application.query.filter_by(job_id=job.id, applicant_id=current_user.id).first() is not None
    return render_template("job_detail.html", job=job, applied=applied)

# ----- Apply -----
@app.route("/job/<int:job_id>/apply", methods=["GET", "POST"])
@login_required
def apply(job_id):
    job = Job.query.get_or_404(job_id)

    existing = Application.query.filter_by(job_id=job.id, applicant_id=current_user.id).first()
    if existing:
        flash("You have already applied to this job.", "info")
        return redirect(url_for("job_detail", job_id= job.id))
    
    if request.method == "POST":
        cover_letter = request.form.get("cover_letter", "").strip()
        resume_file = request.files.get("resume")
        resume_filename = None

        if resume_file and resume_file.filename:
            if allowed_file(resume_file.filename):
                fname = secure_filename(f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{resume_file.filename}")
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
                resume_file.save(save_path)
                resume_filename = fname
            else:
                flash("Invalid resume format. Allowed: pdf, doc, docx", "warning")
                return redirect(url_for("apply", job_id=job.id))
        
        application = Application(
            cover_letter=cover_letter,
            resume_path = resume_filename,
            job_id = job.id,
            applicant_id = current_user.id
        )
        db.session.add(application)
        db.session.commit()
        flash("Application submitted. Good luck!", "success")
        return redirect(url_for("job_detail", job_id=job.id))
    
    return render_template("apply.html", job=job)

# ----- Edit/Delete (Job Poster or Admin) -----
@app.route("/job/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    if job.posted_by_id != current_user.id and not getattr(current_user, "is_admin", False):
        flash("You are not allowed to edit this job.", "danger")
        return redirect(url_for("job_detail", job_id=job.id))
    if request.method == "POST":
        job.job_title = request.form.get("job_title", job.job_title).strip()
        job.company = request.form.get("company", job.company).strip()
        job.salary = request.form.get("salary", job.salary).strip()
        job.location = request.form.get("location", job.location).strip()
        job.job_type = request.form.get("job_type", job.job_type).strip()
        job.description = request.form.get("description", job.description).strip()
        db.session.commit()
        flash("Job updated.", "success")
        return redirect(url_for("job_detail", job_id=job.id))
    return render_template("edit_job.html", job=job)

@app.route("/job/<int:job_id>/delete", methods=["POST"])
@login_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    if job.posted_by_id != current_user.id and not getattr(current_user, "is_admin", False):
        flash("You are not allowed to delete this job.", "danger")
        return redirect(url_for("job_detail", job_id=job.id))

    db.session.delete(job)
    db.session.commit()
    flash("Job Deleted.", "info")
    return redirect(url_for("index"))

# ----- Serve Resumes (Filename only not the actual file) -----
@app.route("/uploads/resumes/<path:filename>")
@login_required
def uploaded_resume(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment =True)

# ----- Dashboard -----
@app.route("/dashboard")
@login_required
def dashboard():
    my_jobs = Job.query.filter_by(posted_by_id=current_user.id).order_by(Job.created_at.desc()).all()
    my_applications = Application.query.filter_by(applicant_id=current_user.id).order_by(Application.created_at.desc()).all()
    return render_template("dashboard.html", my_jobs = my_jobs, my_applications = my_applications)

# ----- Admin -----
@app.route("/admin")
@login_required
@admin_required
def admin_index():
    total_users = User.query.count()
    total_jobs = Job.query.count()
    return render_template("admin/index.html", total_users=total_users, total_jobs=total_jobs)

@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)

@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("you cannot delete your own admin account.", "warning")
        return redirect(url_for("admin_users"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted", "info")
    return redirect(url_for("admin_users"))

@app.route("/admin/jobs")
@login_required
@admin_required
def admin_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template("admin/jobs.html", jobs=jobs)

@app.route("/admin/jobs/<int:job_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    db.session.delete(job)
    db.session.commit()
    flash("Job deleted.", "info")
    return redirect(url_for("admin_jobs"))

# ----- Run -----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)