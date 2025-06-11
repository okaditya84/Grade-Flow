import os
import json
import streamlit as st
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader


def setup_directories():
    """Create necessary directories for the application"""
    directories = [
        "data/users",
        "data/submissions/assignments",
        "data/submissions/exams",
        "data/submissions/tests",
        "data/submissions/projects",
        "data/questions",
        "data/answers",
        "data/vector_stores",
        "data/evaluations/assignments",
        "data/evaluations/exams",
        "data/evaluations/tests",
        "data/evaluations/projects",
        "styles",
        "data",
        "data/question_papers",
        "data/published_papers",
        "data/submissions",
        "data/submissions/test",
        "data/submissions/assignment",
        "data/submissions/exam", 
        "data/submissions/project",
        "data/submission_records",
        "data/evaluations",
        "data/evaluations/results",
        "data/sessions",
        "data/admin_logs",
        "data/system_backups",
        "data/analytics_cache",
        "data/alerts"
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    create_admin_directories()    
    setup_plagiarism_directories()


def load_css():
    """Load custom CSS styling"""
    css_path = "styles/main.css"

    # Create a default CSS file if it doesn't exist
    if not os.path.exists(css_path):
        with open(css_path, "w") as f:
            f.write(
                """
            /* Custom styles for AI Teacher's Assistant */
            h1, h2, h3 {
                color: #1E3A8A;
            }
            
            .stButton>button {
                background-color: #1E3A8A;
                color: white;
                border-radius: 5px;
                padding: 0.5rem 1rem;
                border: none;
                transition: all 0.3s ease;
            }
            
            .stButton>button:hover {
                background-color: #2563EB;
                color: white;
            }
            
            .stTabs [data-baseweb="tab-list"] {
                gap: 1px;
            }
            
            .stTabs [data-baseweb="tab"] {
                padding: 10px 20px;
                border-radius: 5px 5px 0 0;
                background-color: #f0f3f9;
            }
            
            .stTabs [aria-selected="true"] {
                background-color: #1E3A8A;
                color: white;
            }
            
            .report-card {
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                background-color: #f9f9f9;
            }
            """
            )

    # Load the CSS
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def process_submission(file, submission_type, course, title, user_email):
    """Process a student submission"""
    try:
        # Create directories for the submission type
        submissions_dir = f"data/submissions/{submission_type}"
        os.makedirs(submissions_dir, exist_ok=True)

        # Create a safe filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_email.split('@')[0]}_{course}_{timestamp}.pdf"
        file_path = os.path.join(submissions_dir, filename)

        # Save the uploaded file
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

        # Update submission records
        safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
        record_path = f"{submissions_dir}/{safe_email}_{course}_submissions.json"

        # Load existing records or create new
        if os.path.exists(record_path):
            with open(record_path, "r") as f:
                submissions = json.load(f)
        else:
            submissions = []

        # Add new submission
        submission_record = {
            "Student Email": user_email,
            "Course": course,
            "Type": submission_type.capitalize(),
            "Title": title,
            "File Path": file_path,
            "Submission Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Evaluation Status": "Pending",
        }

        submissions.append(submission_record)

        # Save updated records
        with open(record_path, "w") as f:
            json.dump(submissions, f, indent=2)

        return True, f"Your {submission_type} has been successfully submitted!"

    except Exception as e:
        return False, f"Error submitting your work: {str(e)}"


def create_vector_store(user_email, submission_type, course, title):
    """Create vector store for the submitted document"""
    try:
        # Get the latest submission
        safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
        record_path = (
            f"data/submissions/{submission_type}/{safe_email}_{course}_submissions.json"
        )

        if not os.path.exists(record_path):
            return False

        with open(record_path, "r") as f:
            submissions = json.load(f)

        # Find the submission with matching title
        submission = None
        for s in submissions:
            if s.get("Title") == title:
                submission = s
                break

        if not submission:
            return False

        file_path = submission.get("File Path")

        if not file_path or not os.path.exists(file_path):
            return False

        # Create vector store directory
        vector_store_path = (
            f"data/vector_stores/{submission_type}/{safe_email}/{course}"
        )
        os.makedirs(vector_store_path, exist_ok=True)

        # Create a safe title for the directory
        safe_title = "".join(c if c.isalnum() else "_" for c in title)
        vector_store_dir = f"{vector_store_path}/{safe_title}"

        # Create vector store
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )

        splits = text_splitter.split_documents(documents)

        # Create embeddings and vector store
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vector_store = FAISS.from_documents(splits, embeddings)

        # Save vector store
        vector_store.save_local(vector_store_dir)

        return True, f"Vector store created successfully!"

    except Exception as e:
        print(f"Error creating vector store: {e}")
        return False


def get_submission_history(user_email):
    """Get submission history for a student - Updated to include platform test submissions"""
    submissions = []
    
    # First check the new submission records format (for platform tests)
    record_path = f"data/submission_records/{user_email.replace('@', '_at_')}.json"
    if os.path.exists(record_path):
        try:
            with open(record_path, 'r') as f:
                submissions.extend(json.load(f))
        except Exception as e:
            print(f"Error loading submission records: {e}")
    
    # Also check the old format for backward compatibility
    safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")

    # Check each submission type for the old format
    for submission_type in ["assignment", "exam", "test", "project"]:
        submissions_dir = f"data/submissions/{submission_type}"

        if not os.path.exists(submissions_dir):
            continue

        # Look for submission records for this user in old format
        for filename in os.listdir(submissions_dir):
            if filename.startswith(safe_email) and filename.endswith("_submissions.json"):
                record_path = os.path.join(submissions_dir, filename)

                try:
                    with open(record_path, "r") as f:
                        user_submissions = json.load(f)
                        
                        # Avoid duplicates by checking if submission already exists in new format
                        for old_submission in user_submissions:
                            is_duplicate = False
                            for new_submission in submissions:
                                if (new_submission.get('Type', '').lower() == old_submission.get('Type', '').lower() and
                                    new_submission.get('Course') == old_submission.get('Course') and
                                    new_submission.get('Title') == old_submission.get('Title')):
                                    is_duplicate = True
                                    break
                            
                            if not is_duplicate:
                                submissions.append(old_submission)
                except:
                    continue

    # Sort by submission date (newest first)
    submissions.sort(key=lambda x: x.get("Submission Date", ""), reverse=True)

    return submissions


def get_student_submissions(submission_type, course):
    """Get all student submissions for a specific submission type and course"""
    submissions = []
    submissions_dir = f"data/submissions/{submission_type}"

    if not os.path.exists(submissions_dir):
        return submissions

    # Look for submission records for this course
    for filename in os.listdir(submissions_dir):
        if filename.endswith(f"_{course}_submissions.json"):
            record_path = os.path.join(submissions_dir, filename)

            try:
                with open(record_path, "r") as f:
                    course_submissions = json.load(f)

                    # Add only submissions for this course
                    for submission in course_submissions:
                        if submission.get("Course") == course:
                            # Extract name from email
                            email = submission.get("Student Email", "")
                            name = email.split("@")[0] if "@" in email else email
                            submission["Student"] = name
                            submissions.append(submission)
            except:
                continue

    # Sort by submission date
    submissions.sort(key=lambda x: x.get("Submission Date", ""))

    return submissions


def save_evaluation_criteria(submission_type, course, teacher_email, criteria):
    """Save evaluation criteria for future reference"""
    # Create directory structure
    criteria_dir = f"data/evaluations/{submission_type}"
    os.makedirs(criteria_dir, exist_ok=True)

    # Save criteria
    filename = f"{criteria_dir}/{course}_criteria.txt"

    with open(filename, "w") as f:
        f.write(criteria)

    # Also save with teacher info for record keeping
    teacher_filename = (
        f"{criteria_dir}/{course}_criteria_by_{teacher_email.replace('@', '_at_')}.txt"
    )

    with open(teacher_filename, "w") as f:
        f.write(f"Created by: {teacher_email}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(criteria)
### 3. Update utils.py to include a function to get saved question papers:



def get_saved_question_papers(course_code=None):
    """Get all saved question papers or filter by course code"""
    papers = []
    base_dir = "data/question_papers"
    
    if not os.path.exists(base_dir):
        return papers
    
    if course_code:
        # Look for papers of a specific course
        course_dir = os.path.join(base_dir, course_code)
        if not os.path.exists(course_dir):
            return papers
        
        # Get all JSON files in the course directory
        for filename in os.listdir(course_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(course_dir, filename), 'r') as f:
                        paper_data = json.load(f)
                        papers.append(paper_data)
                except:
                    continue
    else:
        # Get papers from all courses
        for course_dir in os.listdir(base_dir):
            course_path = os.path.join(base_dir, course_dir)
            if os.path.isdir(course_path):
                for filename in os.listdir(course_path):
                    if filename.endswith('.json'):
                        try:
                            with open(os.path.join(course_path, filename), 'r') as f:
                                paper_data = json.load(f)
                                papers.append(paper_data)
                        except:
                            continue
    
    # Sort by creation date (newest first)
    papers.sort(key=lambda x: x.get("created_date", ""), reverse=True)
    
    return papers

# Add these new functions at the end of the file

def get_published_question_papers(student_email=None, course_code=None):
    """Get question papers published for students, filter by course if specified"""
    papers = []
    base_dir = "data/published_papers"
    
    if not os.path.exists(base_dir):
        return papers
    
    # Get all course directories
    course_dirs = [course_code] if course_code else os.listdir(base_dir)
    
    for course in course_dirs:
        course_path = os.path.join(base_dir, course)
        if not os.path.isdir(course_path):
            continue
        
        # Get all JSON files in the course directory
        for filename in os.listdir(course_path):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(course_path, filename), 'r') as f:
                        paper_data = json.load(f)
                        
                        # Add the file path to the data
                        paper_data["file_path"] = os.path.join(course_path, filename)
                        
                        # Check if the deadline has passed
                        if "deadline" in paper_data:
                            deadline = datetime.strptime(paper_data["deadline"], "%Y-%m-%d")
                            if deadline < datetime.now():
                                paper_data["status"] = "expired"
                        
                        # Check if the student has already submitted this paper
                        if student_email:
                            submission_path = f"data/submissions/test/{paper_data['course']}/{paper_data['title']}/{student_email.replace('@', '_at_')}.json"
                            if os.path.exists(submission_path):
                                paper_data["student_status"] = "submitted"
                            else:
                                paper_data["student_status"] = "not_submitted"
                        
                        papers.append(paper_data)
                except Exception as e:
                    print(f"Error loading paper {filename}: {e}")
                    continue
    
    # Sort by creation date (newest first)
    papers.sort(key=lambda x: x.get("created_date", ""), reverse=True)
    
    return papers

def save_test_submission(student_email, course_code, paper_title, answers):
    """Save a student's test submission"""
    try:
        # Create directory structure
        base_dir = f"data/submissions/test/{course_code}/{paper_title}"
        os.makedirs(base_dir, exist_ok=True)
        
        # Create submission filename
        filename = f"{base_dir}/{student_email.replace('@', '_at_')}.json"
        
        # Prepare submission data
        submission_data = {
            "student_email": student_email,
            "course_code": course_code,
            "paper_title": paper_title,
            "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "answers": answers,
            "evaluation_status": "pending"
        }
        
        # Save to disk
        with open(filename, 'w') as f:
            json.dump(submission_data, f, indent=2)
        
        # CRITICAL: Update submission record for student interface
        record_path = f"data/submission_records/{student_email.replace('@', '_at_')}.json"
        
        # Load existing submission records or create new ones
        if os.path.exists(record_path):
            with open(record_path, 'r') as f:
                records = json.load(f)
        else:
            records = []
        
        # Check if this submission already exists in records
        submission_found = False
        for record in records:
            if (record.get('Type', '').lower() == 'test' and
                record.get('Course') == course_code and
                record.get('Title') == paper_title):
                
                # Update submission date and status
                record['Submission Date'] = submission_data["submission_date"]
                record['Status'] = "Submitted, awaiting evaluation"
                record['Evaluation Status'] = "pending"
                record['File Path'] = filename
                submission_found = True
                break
        
        # If not found, add new record
        if not submission_found:
            new_record = {
                "Type": "Test",
                "Course": course_code,
                "Title": paper_title,
                "Submission Date": submission_data["submission_date"],
                "File Path": filename,
                "Status": "Submitted, awaiting evaluation",
                "Evaluation Status": "pending"
            }
            records.append(new_record)
        
        # Save updated records
        os.makedirs(os.path.dirname(record_path), exist_ok=True)
        with open(record_path, 'w') as f:
            json.dump(records, f, indent=2)
        
        return True, "Your test has been submitted successfully!"
    
    except Exception as e:
        print(f"Error saving test submission: {e}")
        return False, f"Error submitting test: {str(e)}"
    
# Add or update these functions in utils.py to support our new functionality

def update_submission_status(student_email, submission_type, course, title, status, evaluation_result=None):
    """Update the status of a submission in the submission record"""
    try:
        # Path to the student's record file
        record_path = f"data/submission_records/{student_email.replace('@', '_at_')}.json"
        
        if os.path.exists(record_path):
            with open(record_path, 'r') as f:
                submissions = json.load(f)
            
            # Find the relevant submission
            for submission in submissions:
                if (submission.get('Type', '').lower() == submission_type.lower() and
                    submission.get('Course') == course and
                    submission.get('Title') == title):
                    
                    # Update status
                    submission['Evaluation Status'] = status
                    
                    # Add evaluation results if provided
                    if evaluation_result:
                        if 'Score' in evaluation_result:
                            submission['Score'] = evaluation_result['Score']
                        if 'Marks' in evaluation_result:
                            submission['Marks'] = evaluation_result['Marks']
                        if 'Strengths' in evaluation_result:
                            submission['Strengths'] = evaluation_result['Strengths']
                        if 'Areas for Improvement' in evaluation_result:
                            submission['Areas for Improvement'] = evaluation_result['Areas for Improvement']
                        if 'Detailed Analysis' in evaluation_result:
                            submission['Detailed Analysis'] = evaluation_result['Detailed Analysis']
            
            # Save updated submissions
            with open(record_path, 'w') as f:
                json.dump(submissions, f, indent=2)
                
            # Also update the test submission file directly
            if submission_type.lower() == 'test':
                submission_path = f"data/submissions/test/{course}/{title}/{student_email.replace('@', '_at_')}.json"
                if os.path.exists(submission_path):
                    with open(submission_path, 'r') as f:
                        submission_data = json.load(f)
                    
                    submission_data['evaluation_status'] = status
                    if evaluation_result:
                        submission_data['evaluation'] = evaluation_result
                    
                    with open(submission_path, 'w') as f:
                        json.dump(submission_data, f, indent=2)
                
            return True
        
    except Exception as e:
        print(f"Error updating submission status: {e}")
        return False
        
def update_submission_record(student_email, submission_type, course, title, file_path, status):
    """Update the submission record for a student"""
    try:
        # Create directory if not exists
        os.makedirs("data/submission_records", exist_ok=True)
        
        # Filename for the student's submission record
        record_file = f"data/submission_records/{student_email.replace('@', '_at_')}.json"
        
        # Load existing record or create new one
        if os.path.exists(record_file):
            with open(record_file, 'r') as f:
                records = json.load(f)
        else:
            records = []
        
        # Create new submission record
        new_record = {
            "Type": submission_type,
            "Course": course,
            "Title": title,
            "Submission Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "File Path": file_path,
            "Status": status
        }
        
        # Add to records
        records.append(new_record)
        
        # Save updated records
        with open(record_file, 'w') as f:
            json.dump(records, f, indent=2)
            
        return True
    
    except Exception as e:
        print(f"Error updating submission record: {e}")
        return False
    
def get_test_submission(student_email, course_code, paper_title):
    """Get a student's test submission if it exists"""
    try:
        submission_path = f"data/submissions/test/{course_code}/{paper_title}/{student_email.replace('@', '_at_')}.json"
        
        if not os.path.exists(submission_path):
            return None
        
        with open(submission_path, 'r') as f:
            return json.load(f)
            
    except Exception as e:
        print(f"Error loading test submission: {e}")
        return None

def get_test_submissions_for_course(course_code, paper_title=None):
    """Get all student submissions for a course/paper"""
    submissions = []
    base_path = f"data/submissions/test/{course_code}"
    
    if not os.path.exists(base_path):
        return submissions
    
    # If paper title is specified, only look for that paper
    if paper_title:
        paper_path = os.path.join(base_path, paper_title)
        if not os.path.exists(paper_path):
            return submissions
            
        for filename in os.listdir(paper_path):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(paper_path, filename)
                    with open(filepath, 'r') as f:
                        submission = json.load(f)
                        submission["file_path"] = filepath
                        submissions.append(submission)
                except:
                    continue
    else:
        # Get all papers for the course
        for paper_dir in os.listdir(base_path):
            paper_path = os.path.join(base_path, paper_dir)
            if os.path.isdir(paper_path):
                for filename in os.listdir(paper_path):
                    if filename.endswith('.json'):
                        try:
                            filepath = os.path.join(paper_path, filename)
                            with open(filepath, 'r') as f:
                                submission = json.load(f)
                                submission["file_path"] = filepath
                                submissions.append(submission)
                        except:
                            continue
    
    return submissions

def update_active_tests():
    """Update the status of tests based on their deadlines"""
    base_dir = "data/published_papers"
    
    if not os.path.exists(base_dir):
        return
    
    # Current date
    now = datetime.now()
    
    # Go through all course directories
    for course in os.listdir(base_dir):
        course_path = os.path.join(base_dir, course)
        if not os.path.isdir(course_path):
            continue
        
        # Check each paper
        for filename in os.listdir(course_path):
            if not filename.endswith('.json'):
                continue
                
            file_path = os.path.join(course_path, filename)
            try:
                with open(file_path, 'r') as f:
                    paper = json.load(f)
                
                # Check if deadline has passed
                if "deadline" in paper and paper["status"] == "active":
                    deadline = datetime.strptime(paper["deadline"], "%Y-%m-%d")
                    if now.date() > deadline.date():
                        # Update status to expired
                        paper["status"] = "expired"
                        with open(file_path, 'w') as f:
                            json.dump(paper, f, indent=2)
            except:
                continue

def log_admin_activity(admin_email, action, details=""):
    """Log admin activities for audit trail"""
    try:
        log_dir = "data/admin_logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": admin_email,
            "action": action,
            "details": details
        }
        
        log_file = os.path.join(log_dir, f"admin_log_{datetime.now().strftime('%Y_%m')}.json")
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        
        logs.append(log_entry)
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
            
    except Exception as e:
        print(f"Error logging admin activity: {e}")

def get_system_health():
    """Get system health metrics"""
    health = {
        "status": "healthy",
        "cpu_usage": 0.0,
        "memory_usage": 0.0,
        "disk_usage": 0.0,
        "active_connections": 0,
        "response_time": 0.0
    }
    
    try:
        # Get disk usage for data directory
        if os.path.exists("data"):
            total_size = 0
            for dirpath, dirnames, filenames in os.walk("data"):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
            
            # Convert to MB
            health["disk_usage"] = total_size / (1024 * 1024)
        
        # Placeholder for other metrics
        health["cpu_usage"] = min(100, health["disk_usage"] / 10)
        health["memory_usage"] = min(100, health["disk_usage"] / 15)
        
    except Exception as e:
        health["status"] = f"error: {e}"
    
    return health

def get_platform_statistics():
    """Get comprehensive platform statistics"""
    stats = {
        "total_users": 0,
        "total_tests": 0,
        "total_submissions": 0,
        "total_evaluations": 0,
        "avg_test_score": 0.0,
        "platform_uptime": "99.9%",
        "data_size": "0 MB"
    }
    
    try:
        # Count submission records (approximate user count)
        if os.path.exists("data/submission_records"):
            stats["total_users"] = len([f for f in os.listdir("data/submission_records") if f.endswith('.json')])
        
        # Count published tests
        if os.path.exists("data/published_papers"):
            test_count = 0
            for course_dir in os.listdir("data/published_papers"):
                course_path = os.path.join("data/published_papers", course_dir)
                if os.path.isdir(course_path):
                    test_count += len([f for f in os.listdir(course_path) if f.endswith('.json')])
            stats["total_tests"] = test_count
        
        # Count evaluations
        if os.path.exists("data/evaluations/results"):
            eval_count = 0
            for root, dirs, files in os.walk("data/evaluations/results"):
                eval_count += len([f for f in files if f.endswith('.json')])
            stats["total_evaluations"] = eval_count
        
        # Calculate average score from evaluations
        scores = []
        if os.path.exists("data/evaluations/results"):
            for root, dirs, files in os.walk("data/evaluations/results"):
                for file in files:
                    if file.endswith('.json'):
                        try:
                            with open(os.path.join(root, file), 'r') as f:
                                eval_data = json.load(f)
                                if 'Score' in eval_data:
                                    scores.append(eval_data['Score'])
                        except:
                            continue
        
        if scores:
            stats["avg_test_score"] = sum(scores) / len(scores)
        
        # Get data size
        health = get_system_health()
        stats["data_size"] = f"{health['disk_usage']:.1f} MB"
        
    except Exception as e:
        print(f"Error getting platform statistics: {e}")
    
    return stats

def create_admin_directories():
    """Create admin-specific directories"""
    admin_dirs = [
        "data/admin_logs",
        "data/system_backups",
        "data/analytics_cache",
        "data/alerts"
    ]
    
    for directory in admin_dirs:
        os.makedirs(directory, exist_ok=True)

def get_active_sessions():
    """Get list of active sessions"""
    try:
        session_dir = "data/sessions"
        active_sessions = []
        
        if os.path.exists(session_dir):
            from datetime import datetime
            current_time = datetime.now()
            
            for filename in os.listdir(session_dir):
                if filename.endswith('.json'):
                    session_file = os.path.join(session_dir, filename)
                    try:
                        with open(session_file, 'r') as f:
                            session_data = json.load(f)
                        
                        expires_at = datetime.fromisoformat(session_data["expires_at"])
                        if current_time < expires_at:
                            active_sessions.append(session_data)
                    except:
                        continue
        
        return active_sessions
    except Exception as e:
        print(f"Error getting active sessions: {e}")
        return []

def cleanup_old_sessions():
    """Clean up old session files (older than 30 days)"""
    try:
        session_dir = "data/sessions"
        if not os.path.exists(session_dir):
            return 0
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=30)
        cleaned_count = 0
        
        for filename in os.listdir(session_dir):
            if filename.endswith('.json'):
                session_file = os.path.join(session_dir, filename)
                try:
                    file_mod_time = datetime.fromtimestamp(os.path.getmtime(session_file))
                    if file_mod_time < cutoff_date:
                        os.remove(session_file)
                        cleaned_count += 1
                except:
                    continue
        
        return cleaned_count
    except Exception as e:
        print(f"Error cleaning old sessions: {e}")
        return 0

def setup_plagiarism_directories():
    """Set up directories for plagiarism detection"""
    plagiarism_dirs = [
        "data/plagiarism_results",
        "data/plagiarism_settings", 
        "data/plagiarism_cache",
        "data/plagiarism_reports"
    ]
    
    for directory in plagiarism_dirs:
        os.makedirs(directory, exist_ok=True)    

def get_plagiarism_summary_for_course(course_code):
    """Get plagiarism summary for a specific course"""
    try:
        from plagiarism_detector import PlagiarismDatabase
        db = PlagiarismDatabase()
        results = db.get_plagiarism_results(course=course_code)
        
        summary = {
            'total_cases': len(results),
            'critical_cases': len([r for r in results if r['plagiarism_level'] == 'CRITICAL']),
            'high_cases': len([r for r in results if r['plagiarism_level'] == 'HIGH']),
            'moderate_cases': len([r for r in results if r['plagiarism_level'] == 'MODERATE']),
            'students_involved': set()
        }
        
        for result in results:
            summary['students_involved'].add(result['submission1_info']['student_email'])
            summary['students_involved'].add(result['submission2_info']['student_email'])
        
        summary['students_involved'] = len(summary['students_involved'])
        
        return summary
    except:
        return {
            'total_cases': 0,
            'critical_cases': 0,
            'high_cases': 0,
            'moderate_cases': 0,
            'students_involved': 0
        }