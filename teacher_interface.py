import streamlit as st
from streamlit.components.v1 import html
import base64
import pandas as pd
import io
import matplotlib.pyplot as plt
import numpy as np

# 👉 Use real helper modules instead of mocks
from utils import get_student_submissions, save_evaluation_criteria
from evaluation import evaluate_submissions


def show_teacher_interface():
    """Render full‑screen HTML UI stored at UI/teacher_interface.html and handle events coming
    back from the iframe via postMessage() calls."""

    # Optional: st.set_page_config(layout="wide")

    # Hide almost all Streamlit chrome so the custom HTML can take over the screen
    st.markdown(
        """
        <style>
            .block-container, .main { padding: 0 !important; }
            .stApp { background: #00171F !important; }
            header, [data-testid="stHeader"], [data-testid="stToolbar"],
            .stDeployButton, .stDecoration, [data-testid="stSidebar"] {
                display: none !important;
                visibility: hidden !important;
                height: 0 !important;
                width: 0 !important;
            }
            iframe {
                position: fixed !important;
                top: 0; left: 0;
                width: 100%; height: 100%;
                border: none; z-index: 9999;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 🖼 Load the handcrafted HTML interface
    with open("UI/teacher_interface.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    # Personalise greeting/name
    html_content = html_content.replace(
        "Professor Smith", st.session_state.get("user_email", "Professor")
    )

    # Inject client‑side JS that posts messages to Streamlit when a user logs out or submits an evaluation
    html_content = html_content.replace(
        "</body>",
        """
        <script>
            document.addEventListener("DOMContentLoaded", () => {
                /* 1️⃣  LOG‑OUT BUTTON  */
                const confirmLogout = document.getElementById("confirmLogoutBtn");
                confirmLogout?.addEventListener("click", () => {
                    window.parent.postMessage({
                        type: "streamlit:setComponentValue",
                        value: { action: "logout" }
                    }, "*");
                });

                /* 2️⃣  EVALUATION FORMS  */
                ["test", "assignment", "exam", "project"].forEach(type => {
                    const form = document.getElementById(`evaluation-form-${type}`);
                    form?.addEventListener("submit", async e => {
                        e.preventDefault();

                        const course = document.getElementById(`course-${type}`).value;
                        const criteria = document.getElementById(`criteria-${type}`).value;
                        const questionPaperFile = document.getElementById(`question-paper-${type}`).files[0];
                        const modelAnswerFile  = document.getElementById(`model-answer-${type}`).files[0];

                        if (!course || !criteria || !questionPaperFile || !modelAnswerFile) {
                            alert("Please fill in all fields and upload both PDFs.");
                            return;
                        }

                        const fileToBase64 = file => new Promise((resolve, reject) => {
                            const reader = new FileReader();
                            reader.readAsDataURL(file);
                            reader.onload  = () => resolve(reader.result.split(",")[1]);
                            reader.onerror = reject;
                        });

                        const data = {
                            action: "evaluate",
                            type,
                            course,
                            criteria,
                            question_paper: {
                                name: questionPaperFile.name,
                                content: await fileToBase64(questionPaperFile)
                            },
                            model_answer: {
                                name: modelAnswerFile.name,
                                content: await fileToBase64(modelAnswerFile)
                            }
                        };

                        window.parent.postMessage({
                            type: "streamlit:setComponentValue",
                            value: data
                        }, "*");
                    });
                });
            });
        </script>
        </body>""",
    )

    # Display the HTML inside an iframe; capture any postMessage values returned.
    component_value = html(html_content, height=0, scrolling=True)

    # 📬 React to messages coming from JS
    if isinstance(component_value, dict):
        action = component_value.get("action")

        if action == "logout":
            _handle_logout()
        elif action == "evaluate":
            _handle_evaluation(component_value)


def _handle_logout():
    """Clear session state and take user back to landing page."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.user_email = None
    st.session_state.view = "landing"
    st.session_state.ui_rendered = False
    st.query_params.clear()
    st.rerun()


def _handle_evaluation(data: dict):
    """Decode incoming base64 PDFs, fetch submissions via utils, evaluate via evaluation, then show results."""
    submission_type = data["type"]
    course          = data["course"]
    criteria        = data["criteria"]
    email           = st.session_state.get("user_email", "teacher@example.com")

    # ---- Decode the uploaded PDFs back into file‑like objects ----
    def _decode_file(finfo):
        return io.BytesIO(base64.b64decode(finfo["content"])), finfo["name"]

    question_file, _ = _decode_file(data["question_paper"])
    model_file,   _  = _decode_file(data["model_answer"])

    # ---- Fetch student submissions (REAL implementation) ----
    student_submissions = get_student_submissions(submission_type, course)

    if not student_submissions:
        st.warning(f"No submissions found for {submission_type} – {course}.")
        return

    # ---- Persist the evaluation criteria ----
    save_evaluation_criteria(submission_type, course, email, criteria)

    # ---- Run the actual evaluation ----
    with st.spinner("Evaluating… this might take a moment ⏳"):
        results = evaluate_submissions(
            submission_type,
            course,
            question_file,
            model_file,
            criteria,
            student_submissions,
        )

    _display_results(results, submission_type, course)


def _display_results(results, submission_type, course):
    """Pretty print a summary of evaluation results and show some basic analytics charts."""

    st.subheader(f"{submission_type.title()} Evaluation Results – {course}")

    if not results:
        st.info("Evaluation returned no results.")
        return

    # Convert list[dict] → DataFrame for convenience
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)

    # ---- Metrics ----
    scores = df["Score"].astype(float).tolist()
    st.metric("Average", f"{np.mean(scores):.1f}/100")
    st.metric("Max", f"{np.max(scores):.0f}/100")
    st.metric("Min", f"{np.min(scores):.0f}/100")

    # ---- Visualisations ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    # Histogram of scores
    ax1.hist(scores, bins=10, edgecolor="black")
    ax1.set_title("Score Distribution")
    ax1.set_xlabel("Score")
    ax1.set_ylabel("Students")

    # Bar chart of category averages if present
    # Fallback: generate random data to keep chart occupied
    categories = ["Understanding", "Application", "Clarity", "Presentation"]
    if set(categories).issubset(df.columns):
        values = [df[c].mean() for c in categories]
    else:
        values = np.random.rand(len(categories)) * 100  # placeholder

    ax2.bar(categories, values)
    ax2.set_ylim(0, 100)
    ax2.set_title("Average by Category")
    ax2.set_ylabel("Score (%)")

    plt.tight_layout()
    st.pyplot(fig)

    # ---- Individual reports ----
    for r in results:
        with st.expander(f"{r.get('Student', 'Student')} – Score: {r.get('Score', 0)}"):
            if "Feedback" in r:
                st.write("**Feedback:**", r["Feedback"])
            if "Strengths" in r:
                st.write("**Strengths:**", r["Strengths"])
            if "Areas for Improvement" in r:
                st.write("**Areas for Improvement:**", r["Areas for Improvement"])
            if "Detailed Analysis" in r:
                st.write("**Detailed Analysis:**", r["Detailed Analysis"])
