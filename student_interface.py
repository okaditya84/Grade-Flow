import os
import streamlit as st
import pandas as pd
from datetime import datetime
import time
from utils import process_submission, create_vector_store, get_submission_history


def show_student_interface():
    st.title("Student Dashboard")

    # Create tabs for different student functionalities
    tab1, tab2 = st.tabs(["Submit Documents", "View Submissions"])

    with tab1:
        show_submission_interface()

    with tab2:
        show_submission_history()


def show_submission_interface():
    st.header("Submit Your Work")

    # Select submission type
    submission_type = st.selectbox(
        "Select Submission Type", ["Assignment", "Exam", "Test", "Project"]
    )

    # Course/Subject information
    course = st.text_input("Course/Subject Code")

    # Add title/description
    title = st.text_input(f"{submission_type} Title/Description")

    # File uploader for PDF
    uploaded_file = st.file_uploader("Upload your answer sheet (PDF)", type="pdf")

    if st.button("Submit"):
        if not uploaded_file:
            st.error("Please upload a PDF file.")
            return

        if not course or not title:
            st.error("Please fill in all the required fields.")
            return

        # Show a progress indicator
        with st.spinner(f"Processing your {submission_type.lower()}..."):
            # Process the submission
            success, message = process_submission(
                uploaded_file,
                submission_type.lower(),
                course,
                title,
                st.session_state.user_email,
            )

            # Create vector store for the document
            if success:
                vector_store_success = create_vector_store(
                    st.session_state.user_email, submission_type.lower(), course, title
                )

                if vector_store_success:
                    st.success(f"{message} Vector store created successfully!")
                else:
                    st.warning(
                        f"{message} However, there was an issue creating the vector store."
                    )
            else:
                st.error(message)


def show_submission_history():
    st.header("Your Submission History")

    # Get submission history
    submissions = get_submission_history(st.session_state.user_email)

    if not submissions:
        st.info("You haven't made any submissions yet.")
        return

    # Create a DataFrame from submission history
    df = pd.DataFrame(submissions)

    # Display the DataFrame with some styling
    st.dataframe(
        df.style.format({"Submission Date": lambda x: x.split(" ")[0]}),
        use_container_width=True,
    )

    # Allow filtering by submission type
    submission_type_filter = st.selectbox(
        "Filter by Type", ["All"] + sorted(df["Type"].unique().tolist())
    )

    if submission_type_filter != "All":
        filtered_df = df[df["Type"] == submission_type_filter]
        st.dataframe(
            filtered_df.style.format({"Submission Date": lambda x: x.split(" ")[0]}),
            use_container_width=True,
        )

    # Show evaluation results if available
    st.subheader("Evaluation Results")

    evaluated_submissions = [
        s for s in submissions if s.get("Evaluation Status") == "Completed"
    ]

    if not evaluated_submissions:
        st.info("None of your submissions have been evaluated yet.")
        return

    for submission in evaluated_submissions:
        with st.expander(
            f"{submission['Type']} - {submission['Title']} ({submission['Course']})"
        ):
            if "Score" in submission:
                st.metric("Score", f"{submission['Score']}/100")

            if "Feedback" in submission:
                st.markdown("### Feedback")
                st.write(submission["Feedback"])

            if "Detailed Analysis" in submission:
                st.markdown("### Detailed Analysis")
                st.write(submission["Detailed Analysis"])
