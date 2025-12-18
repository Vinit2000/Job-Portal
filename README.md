# 🧑‍💼 Job Portal Web Application  
A beginner-friendly web application where users can post jobs, search jobs, and apply for jobs.  
This project is built using **Flask, SQLite, Bootstrap, and Python**, designed as a training/final project.

---

## 🌟 Project Overview

The Job Portal allows multiple types of users:

### 🔹 Job Seekers can:
✔ Register & Login  
✔ Browse job openings  
✔ Search jobs using filters (Company, Location, Job Type)  
✔ Apply for jobs  
✔ Upload resume  
✔ View applied jobs in personal dashboard  

### 🔹 Employers can:
✔ Post job openings  
✔ Edit/Delete their jobs  
✔ View applicants  

### 🔹 Admin can:
✔ View total users and job posts  
✔ Delete users  
✔ Delete job postings  

---

## 🎯 Features Summary

### 🔐 Authentication
- Signup, Login & Logout  
- Password hashing  
- Session-based login  
- Access restrictions  

### 🧑‍💼 User Roles
| Role       | Privileges |
|------------|------------|
| Admin      | Manage users & jobs |
| Employer   | Create & manage job posts |
| Job Seeker | Search & apply to jobs |

---

## 🗄 Database Structure

### 👤 User Table
| Column | Description |
|--------|-------------|
| fullname | Name of the user |
| email | Unique Email |
| password_hash | Encrypted password |
| is_admin | True if admin |
| is_employer | True if employer |

### 💼 Job Table
| Column | Description |
|--------|-------------|
| job_title | Job Name |
| company | Company Name |
| salary | Offered salary |
| description | Job details |
| location | Job location |
| job_type | Full-time/Part-time/Internship |
| posted_by | User (Employer/Admin) |

### 📄 Application Table
| Column | Description |
|--------|-------------|
| applicant_id | User who applied |
| job_id | Job applied to |
| cover_letter | Optional |
| resume_path | Uploaded resume filename |

---

## 💻 Tech Stack Used

| Category | Tech |
|----------|------|
| Backend | Python + Flask |
| Database | SQLite |
| ORM | SQLAlchemy |
| Templates | Jinja2 |
| UI | HTML, CSS, Bootstrap |
| Storage | Local file upload |

---

## 🛠 Setup Instructions

Follow these steps to run the project:

- git clone https://github.com/Vinit2000/Job-Portal.git
- cd job-portal
- python -m venv venv
- venv\Scripts\activate.ps1
- pip install -r requirements.txt
- python app.py
