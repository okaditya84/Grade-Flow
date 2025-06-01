import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from utils import get_student_submissions, save_evaluation_criteria
from evaluation import evaluate_submissions
from streamlit.components.v1 import html

def show_teacher_interface():
    st.title("Teacher Dashboard")

    # Create tabs for different teacher functionalities
    tabs = st.tabs(
        [
            "Evaluate Tests",
            "Evaluate Assignments",
            "Evaluate Exams",
            "Evaluate Projects",
        ]
    )

    # Handle each tab
    with tabs[0]:
        show_evaluation_interface("test")

    with tabs[1]:
        show_evaluation_interface("assignment")

    with tabs[2]:
        show_evaluation_interface("exam")

    with tabs[3]:
        show_evaluation_interface("project")


def show_evaluation_interface(submission_type):
    st.header(f"Evaluate {submission_type.title()}s")

    # Course selection
    course = st.text_input(f"Course Code for {submission_type.title()}")

    # Question paper upload
    question_paper = st.file_uploader(
        f"Upload Question Paper for {submission_type.title()} (PDF)",
        key=f"question_{submission_type}",
        type="pdf",
    )

    # Model answer upload
    model_answer = st.file_uploader(
        f"Upload Model Answer for {submission_type.title()} (PDF)",
        key=f"answer_{submission_type}",
        type="pdf",
    )

    # Evaluation criteria
    st.subheader("Evaluation Criteria")

    default_criteria = get_default_criteria(submission_type)

    evaluation_criteria = st.text_area(
        "Define Evaluation Criteria",
        value=default_criteria,
        height=200,
        key=f"criteria_{submission_type}",
    )

    # Get list of student submissions
    if course:
        student_submissions = get_student_submissions(submission_type, course)

        if not student_submissions:
            st.info(f"No {submission_type} submissions found for {course}.")
        else:
            st.subheader("Student Submissions")

            # Display submissions in a table
            submissions_df = pd.DataFrame(student_submissions)
            st.dataframe(submissions_df, use_container_width=True)

            # Evaluate button
            if st.button(
                f"Evaluate {submission_type.title()}s", key=f"eval_{submission_type}"
            ):
                if not question_paper or not model_answer:
                    st.error("Please upload both question paper and model answer.")
                    return

                # Save criteria
                save_evaluation_criteria(
                    submission_type,
                    course,
                    st.session_state.user_email,
                    evaluation_criteria,
                )

                # Perform evaluation
                with st.spinner("Evaluating submissions... This may take some time."):
                    results = evaluate_submissions(
                        submission_type,
                        course,
                        question_paper,
                        model_answer,
                        evaluation_criteria,
                        student_submissions,
                    )

                    # Display results
                    display_evaluation_results(results, submission_type, course)


def get_default_criteria(submission_type):
    """Return default evaluation criteria based on submission type"""
    if submission_type == "test":
        return """Evaluation Criteria for Tests:
1. Correctness: 60 points - Answer matches the expected solution
2. Completeness: 20 points - All parts of the question are addressed
3. Clarity: 10 points - Clear explanation of steps and reasoning
4. Presentation: 10 points - Neat and well-organized

For complex problems worth more marks, prioritize understanding of concepts over minor calculation errors.
For simpler problems (1-2 marks), focus on the final answer being correct."""

    elif submission_type == "assignment":
        return """Evaluation Criteria for Assignments:
1. Understanding: 30 points - Demonstrates grasp of concepts and theories
2. Application: 30 points - Correctly applies concepts to problems
3. Thoroughness: 20 points - Covers all aspects of the assignment
4. Creativity: 10 points - Shows original thinking when appropriate
5. Presentation: 10 points - Well-structured and professionally presented

Higher weight questions should demonstrate deeper understanding and application.
Lower weight questions focus on basic concept correctness."""

    elif submission_type == "exam":
        return """Evaluation Criteria for Exams:
1. Knowledge: 40 points - Accurate recall of course material
2. Understanding: 30 points - Demonstrates comprehension of concepts
3. Application: 20 points - Applies knowledge to solve problems
4. Analysis: 10 points - Critical thinking and evaluation of information

For questions with higher marks, prioritize conceptual understanding and application.
For questions with lower marks (1-2), correctness of answer is most important."""

    elif submission_type == "project":
        return """Evaluation Criteria for Projects:
1. Research: 20 points - Depth and breadth of research conducted
2. Methodology: 20 points - Appropriate and well-executed approach
3. Analysis: 20 points - Critical evaluation of data and findings
4. Innovation: 15 points - Original contributions and creative solutions
5. Presentation: 15 points - Professional report and organization
6. Documentation: 10 points - Clear and comprehensive documentation

Focus on the overall quality and cohesiveness of the project.
Give credit for ambitious attempts even if implementation has minor flaws."""


def display_evaluation_results(results, submission_type, course):
    st.subheader(f"Evaluation Results for {course} {submission_type.title()}")

    # Display summary statistics
    if results:
        scores = [r.get("Score", 0) for r in results]
        avg_score = sum(scores) / len(scores) if scores else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Average Score", f"{avg_score:.1f}/100")
        col2.metric("Highest Score", f"{max(scores) if scores else 0}/100")
        col3.metric("Lowest Score", f"{min(scores) if scores else 0}/100")

        # Create a dataframe for the results
        results_df = pd.DataFrame(
            [
                {
                    "Student": r.get("Student", ""),
                    "Score": r.get("Score", 0),
                    "Strengths": (
                        r.get("Strengths", "")[:50] + "..."
                        if r.get("Strengths", "")
                        else ""
                    ),
                    "Areas for Improvement": (
                        r.get("Areas for Improvement", "")[:50] + "..."
                        if r.get("Areas for Improvement", "")
                        else ""
                    ),
                }
                for r in results
            ]
        )

        st.dataframe(results_df, use_container_width=True)

        # Generate and display visualizations
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Score distribution histogram
        ax1.hist(scores, bins=10, edgecolor="black")
        ax1.set_title("Score Distribution")
        ax1.set_xlabel("Score")
        ax1.set_ylabel("Number of Students")

        # Score breakdown by different components (assuming we have this data)
        categories = ["Understanding", "Application", "Clarity", "Presentation"]
        example_values = np.random.rand(len(categories)) * 100  # Placeholder data

        ax2.bar(categories, example_values)
        ax2.set_title("Average Score by Category")
        ax2.set_ylabel("Score (%)")
        ax2.set_ylim(0, 100)

        plt.tight_layout()
        st.pyplot(fig)

        # Download buttons
        st.download_button(
            label="Download Results as CSV",
            data=results_df.to_csv(index=False),
            file_name=f"{course}_{submission_type}_results.csv",
            mime="text/csv",
        )

        # Detailed individual reports
        st.subheader("Individual Student Reports")
        for result in results:
            with st.expander(
                f"Student: {result.get('Student', 'Unknown')} - Score: {result.get('Score', 0)}/100"
            ):
                st.markdown(f"### Feedback for {result.get('Student', 'Student')}")

                st.markdown("#### Strengths")
                st.write(result.get("Strengths", "No specific strengths identified."))

                st.markdown("#### Areas for Improvement")
                st.write(
                    result.get(
                        "Areas for Improvement",
                        "No specific areas for improvement identified.",
                    )
                )

                st.markdown("#### Detailed Analysis")
                st.write(
                    result.get("Detailed Analysis", "No detailed analysis available.")
                )
