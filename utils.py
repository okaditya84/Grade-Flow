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
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)


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
    """Get submission history for a student"""
    submissions = []
    safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")

    # Check each submission type
    for submission_type in ["assignment", "exam", "test", "project"]:
        submissions_dir = f"data/submissions/{submission_type}"

        if not os.path.exists(submissions_dir):
            continue

        # Look for submission records for this user
        for filename in os.listdir(submissions_dir):
            if filename.startswith(safe_email) and filename.endswith(
                "_submissions.json"
            ):
                record_path = os.path.join(submissions_dir, filename)

                try:
                    with open(record_path, "r") as f:
                        user_submissions = json.load(f)
                        submissions.extend(user_submissions)
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