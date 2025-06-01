import streamlit as st
from streamlit.components.v1 import html
import base64
import pandas as pd
import io
import random

def show_teacher_interface():
    # st.set_page_config(layout="wide")

    # Hide Streamlit chrome
    st.markdown("""
    <style>
        .block-container, .main {
            padding: 0 !important;
        }
        .stApp {
            background: #00171F !important;
        }
        header, [data-testid="stHeader"], [data-testid="stToolbar"],
        .stDeployButton, .stDecoration, [data-testid="stSidebar"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            width: 0 !important;
        }
        iframe {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100% !important;
            border: none !important;
            z-index: 9999 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Load HTML content
    with open("UI/teacher_interface.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    html_content = html_content.replace("Professor Smith", st.session_state.get("user_email", "Professor"))

    # Inject JS for logout + postMessage form
    html_content = html_content.replace("</body>", """
    <script>
        document.addEventListener("DOMContentLoaded", function () {
            const confirmLogout = document.getElementById("confirmLogoutBtn");
            if (confirmLogout) {
                confirmLogout.addEventListener("click", () => {
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        value: { action: 'logout' }
                    }, '*');
                });
            }

            const formTypes = ['test', 'assignment', 'exam', 'project'];
            formTypes.forEach(type => {
                const form = document.getElementById(`evaluation-form-${type}`);
                form.addEventListener('submit', async function(e) {
                    e.preventDefault();

                    const course = document.getElementById(`course-${type}`).value;
                    const criteria = document.getElementById(`criteria-${type}`).value;
                    const questionPaperFile = document.getElementById(`question-paper-${type}`).files[0];
                    const modelAnswerFile = document.getElementById(`model-answer-${type}`).files[0];

                    if (!course || !criteria || !questionPaperFile || !modelAnswerFile) {
                        alert("Please fill in all fields and upload both PDFs.");
                        return;
                    }

                    const toBase64 = file => new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.readAsDataURL(file);
                        reader.onload = () => resolve(reader.result.split(",")[1]);
                        reader.onerror = error => reject(error);
                    });

                    const questionBase64 = await toBase64(questionPaperFile);
                    const modelBase64 = await toBase64(modelAnswerFile);

                    const data = {
                        action: 'evaluate',
                        type,
                        course,
                        criteria,
                        question_paper: {
                            name: questionPaperFile.name,
                            content: questionBase64
                        },
                        model_answer: {
                            name: modelAnswerFile.name,
                            content: modelBase64
                        }
                    };

                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        value: data
                    }, '*');
                });
            });
        });
    </script>
    </body>""")

    # Render the UI
    component_value = html(html_content, height=0, scrolling=True)

    # Handle logout or evaluate action
    if isinstance(component_value, dict):
        action = component_value.get("action")

        if action == "logout":
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.authenticated = False
            st.session_state.user_role = None
            st.session_state.user_email = None
            st.session_state.view = "landing"
            st.session_state.ui_rendered = False
            st.query_params.clear()
            st.rerun()

        elif action == "evaluate":
            handle_evaluation(component_value)


def handle_evaluation(data):
    submission_type = data["type"]
    course = data["course"]
    criteria = data["criteria"]
    email = st.session_state.get("user_email", "teacher@example.com")

    # Decode PDF files
    def decode_file(file_data):
        return io.BytesIO(base64.b64decode(file_data["content"])), file_data["name"]

    question_file, question_name = decode_file(data["question_paper"])
    model_file, model_name = decode_file(data["model_answer"])

    # Get submissions (mocked)
    student_submissions = get_student_submissions(submission_type, course)

    if not student_submissions:
        st.warning(f"No submissions found for {submission_type} - {course}")
        return

    # Save criteria (mock)
    save_evaluation_criteria(submission_type, course, email, criteria)

    with st.spinner("Evaluating..."):
        results = evaluate_submissions(
            submission_type,
            course,
            question_file,
            model_file,
            criteria,
            student_submissions
        )
        display_results(results, submission_type, course)


def get_student_submissions(submission_type, course):
    """Mock: Return fake submissions for testing"""
    return [
        {"Student": "S001", "Title": f"{submission_type.title()} 1", "Course": course},
        {"Student": "S002", "Title": f"{submission_type.title()} 2", "Course": course},
        {"Student": "S003", "Title": f"{submission_type.title()} 3", "Course": course},
    ]


def save_evaluation_criteria(submission_type, course, email, criteria):
    """Mock: Print to console"""
    print(f"[LOG] Saving criteria for {submission_type}-{course} by {email}")
    print(criteria)


def evaluate_submissions(submission_type, course, question_file, model_file, criteria, submissions):
    """Mock: Generate fake scores and feedback"""
    results = []
    for s in submissions:
        score = random.randint(65, 95)
        results.append({
            "Student": s["Student"],
            "Score": score,
            "Feedback": f"Well done, {s['Student']}! Score: {score}",
            "Detailed Analysis": "This is a mock detailed analysis for demonstration purposes."
        })
    return results


def display_results(results, submission_type, course):
    st.subheader(f"{submission_type.title()} Evaluation Results – {course}")

    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)

    scores = df["Score"].tolist()
    st.metric("Average", f"{sum(scores)/len(scores):.1f}/100")
    st.metric("Max", f"{max(scores)}/100")
    st.metric("Min", f"{min(scores)}/100")

    for r in results:
        with st.expander(f"{r['Student']} – Score: {r['Score']}"):
            st.write("**Feedback:**", r["Feedback"])
            st.write("**Detailed Analysis:**", r["Detailed Analysis"])
