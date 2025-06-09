import streamlit as st
import pandas as pd
import time
import json
import os
from datetime import datetime, timedelta
from utils import process_submission, create_vector_store, get_submission_history, get_published_question_papers, save_test_submission, get_test_submission, update_submission_record
import tempfile

def show_student_interface():
    st.title("Student Dashboard")

    # Create tabs for different student functionalities
    tab1, tab2, tab3 = st.tabs(["Submit Documents", "View Submissions", "Take Tests"])

    with tab1:
        show_submission_interface()

    with tab2:
        show_submission_history()
        
    with tab3:
        show_available_tests()



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


# Update the show_submission_history function to include test evaluations

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
        s for s in submissions if s.get("Evaluation Status") == "Evaluated"
    ]

    if not evaluated_submissions:
        st.info("None of your submissions have been evaluated yet.")
        return

    for submission in evaluated_submissions:
        with st.expander(
            f"{submission['Type']} - {submission['Title']} ({submission['Course']}) - {submission.get('Score', 'N/A')}/100"
        ):
            if "Score" in submission:
                st.metric("Score", f"{submission['Score']}/100")

            if "Marks" in submission:
                st.write(f"**Marks obtained:** {submission['Marks']}")

            if "Strengths" in submission:
                st.markdown("### Strengths")
                st.write(submission["Strengths"])

            if "Areas for Improvement" in submission:
                st.markdown("### Areas for Improvement")
                st.write(submission["Areas for Improvement"])

            if "Detailed Analysis" in submission:
                st.markdown("### Detailed Analysis")
                for analysis_item in submission["Detailed Analysis"].split("\n\n"):
                    st.write(analysis_item)
            
            # If it's a test, show the option to view questions and your answers
            if submission['Type'].lower() == 'test':
                if st.button(f"View Test Details for {submission['Title']}", key=f"view_test_{submission['Title']}"):
                    # Get the published paper for reference
                    papers = get_published_question_papers(st.session_state.user_email, course_code=submission['Course'])
                    
                    # Find the matching paper
                    paper_data = None
                    for paper in papers:
                        if paper['title'] == submission['Title']:
                            paper_data = paper
                            break
                    
                    if paper_data:
                        # Get the submission with answers
                        test_submission = get_test_submission(
                            st.session_state.user_email,
                            submission['Course'],
                            submission['Title']
                        )
                        
                        if test_submission and 'answers' in test_submission:
                            st.subheader("Your Answers")
                            
                            for q_idx, question in enumerate(paper_data["questions"]):
                                answer_key = f"q_{q_idx}"
                                student_answer = test_submission["answers"].get(answer_key, "No answer provided")
                                
                                # Extract feedback for this question from detailed analysis
                                question_feedback = ""
                                if "Detailed Analysis" in submission:
                                    for analysis_item in submission["Detailed Analysis"].split("\n\n"):
                                        if analysis_item.startswith(f"Q{q_idx+1}:"):
                                            question_feedback = analysis_item
                                            break
                                
                                # Show question, student answer, and feedback
                                with st.expander(f"Question {q_idx+1}: {question['question_text'][:50]}..."):
                                    st.write("**Question:**")
                                    st.write(question["question_text"])
                                    
                                    if "options" in question and question["options"]:
                                        st.write("**Options:**")
                                        for i, option in enumerate(question["options"]):
                                            st.write(f"{chr(65+i)}. {option}")
                                    
                                    st.write("**Your Answer:**")
                                    st.write(student_answer)
                                    
                                    if question_feedback:
                                        st.write("**Feedback:**")
                                        st.write(question_feedback)
                        else:
                            st.error("Could not retrieve your submission details.")
                    else:
                        st.error("Test details not available.")

def format_time(seconds):
    """Format seconds into hours:minutes:seconds"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def show_available_tests():
    st.header("Available Tests")
    
    # Initialize session state variables for test timing
    if "test_in_progress" not in st.session_state:
        st.session_state.test_in_progress = False
    if "test_start_time" not in st.session_state:
        st.session_state.test_start_time = None
    if "test_end_time" not in st.session_state:
        st.session_state.test_end_time = None
    if "test_data" not in st.session_state:
        st.session_state.test_data = None
    if "current_answers" not in st.session_state:
        st.session_state.current_answers = {}
    
    # If test is in progress, show the test interface
    if st.session_state.test_in_progress:
        show_test_in_progress()
        return
    
    # Get all published papers for this student
    papers = get_published_question_papers(st.session_state.user_email)
    
    if not papers:
        st.info("There are no tests available for you at this time.")
        return
    
    # Filter only active tests
    active_papers = [p for p in papers if p.get("status", "active") == "active"]
    
    if not active_papers:
        st.info("There are no active tests available. All tests have expired.")
        return
    
    # Group by course
    papers_by_course = {}
    for paper in active_papers:
        course = paper["course"]
        if course not in papers_by_course:
            papers_by_course[course] = []
        papers_by_course[course].append(paper)
    
    # Course selection
    courses = list(papers_by_course.keys())
    selected_course = st.selectbox("Select Course", courses)
    
    if not selected_course:
        return
    
    # Test selection
    course_papers = papers_by_course[selected_course]
    paper_titles = [f"{p['title']} (Due: {p.get('deadline', 'No deadline')})" for p in course_papers]
    
    # Add submission status to title
    for i, paper in enumerate(course_papers):
        if paper.get("student_status") == "submitted":
            paper_titles[i] += " [SUBMITTED]"
        
        if paper.get("time_limit"):
            hours = paper["time_limit"] // 60
            minutes = paper["time_limit"] % 60
            time_display = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            paper_titles[i] += f" [Time: {time_display}]"
    
    selected_paper_idx = st.selectbox("Select Test", range(len(paper_titles)), format_func=lambda x: paper_titles[x])
    selected_paper = course_papers[selected_paper_idx]
    
    # Display test information
    st.subheader(selected_paper["title"])
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Course:** {selected_paper['course']}")
        st.write(f"**Created:** {selected_paper['created_date']}")
    
    with col2:
        st.write(f"**Deadline:** {selected_paper.get('deadline', 'Not specified')}")
        if selected_paper.get("student_status") == "submitted":
            st.write("**Status:** Already submitted")
        else:
            st.write("**Status:** Not submitted")
    
    # Display time limit information if available
    if selected_paper.get("time_limit"):
        hours = selected_paper["time_limit"] // 60
        minutes = selected_paper["time_limit"] % 60
        st.info(f"⏱️ This test has a time limit of {hours} hour(s) and {minutes} minute(s). Once you start, you must complete it within this time.")
    
    # Instructions
    if "instructions" in selected_paper:
        st.subheader("Instructions")
        st.write(selected_paper["instructions"])
    
    # Check if student has already submitted
    existing_submission = get_test_submission(
        st.session_state.user_email, 
        selected_paper["course"], 
        selected_paper["title"]
    )
    
    if existing_submission:
        st.success("You have already submitted this test.")
        
        # Option to view previous answers
        if st.button("View Your Submission"):
            st.subheader("Your Answers")
            
            for q_idx, question in enumerate(selected_paper["questions"]):
                answer_key = f"q_{q_idx}"
                student_answer = existing_submission["answers"].get(answer_key, "No answer provided")
                
                with st.expander(f"Question {q_idx+1}: {question['question_text'][:50]}..."):
                    st.write(question["question_text"])
                    
                    if "options" in question and question["options"]:
                        st.write("**Options:**")
                        for i, option in enumerate(question["options"]):
                            st.write(f"{chr(65+i)}. {option}")
                    
                    st.write("**Your Answer:**")
                    st.write(student_answer)
    else:
        # Start test button
        start_col1, start_col2 = st.columns([1, 2])
        with start_col1:
            if st.button("Start Test", key="start_test_button"):
                st.session_state.test_in_progress = True
                st.session_state.test_data = selected_paper
                
                # Calculate end time if there's a time limit
                if selected_paper.get("time_limit"):
                    st.session_state.test_start_time = datetime.now()
                    minutes_to_add = selected_paper["time_limit"]
                    st.session_state.test_end_time = st.session_state.test_start_time + timedelta(minutes=minutes_to_add)
                    
                    # Initialize empty answers
                    st.session_state.current_answers = {f"q_{i}": "" for i in range(len(selected_paper["questions"]))}
                
                st.rerun()
        
        with start_col2:
            if selected_paper.get("time_limit"):
                st.warning("⚠️ Once you start the test, the timer will begin and cannot be paused.")


def show_test_in_progress():
    """Display the test interface with timer for a test in progress"""
    
    # Get test data
    test_data = st.session_state.test_data
    
    if not test_data:
        st.error("Test data not found. Please try again.")
        if st.button("Return to Test Selection"):
            st.session_state.test_in_progress = False
            st.rerun()
        return
    
    # Display test title and timer
    st.header(test_data["title"])
    
    # Check if test has timed out
    timed_out = False
    if test_data.get("time_limit") and st.session_state.test_end_time:
        current_time = datetime.now()
        if current_time >= st.session_state.test_end_time:
            timed_out = True
    
    # Handle time out case
    if timed_out:
        st.error("⏰ Time's up! Your test is being submitted automatically.")
        
        # Submit the current answers
        success, message = save_test_submission(
            st.session_state.user_email,
            test_data["course"],
            test_data["title"],
            st.session_state.current_answers
        )
        
        if success:
            st.success("Your test has been automatically submitted due to time expiry.")
        else:
            st.error(f"Error submitting test: {message}")
        
        # Reset test session
        if st.button("Return to Test Selection"):
            st.session_state.test_in_progress = False
            st.session_state.test_data = None
            st.session_state.test_start_time = None
            st.session_state.test_end_time = None
            st.session_state.current_answers = {}
            st.rerun()
            
        return
    
    # Display timer if time limit is set
    if test_data.get("time_limit") and st.session_state.test_end_time:
        time_remaining = (st.session_state.test_end_time - datetime.now()).total_seconds()
        if time_remaining < 0:
            time_remaining = 0
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"### ⏱️ Time Remaining")
        with col2:
            # Format and display time
            formatted_time = format_time(int(time_remaining))
            
            # Style based on remaining time
            if time_remaining < 300:  # Less than 5 minutes
                st.markdown(f"<h3 style='color: red;'>{formatted_time}</h3>", unsafe_allow_html=True)
            elif time_remaining < 600:  # Less than 10 minutes
                st.markdown(f"<h3 style='color: orange;'>{formatted_time}</h3>", unsafe_allow_html=True)
            else:
                st.markdown(f"<h3>{formatted_time}</h3>", unsafe_allow_html=True)
            
            # Warning for low time
            if time_remaining < 300:
                st.warning("⚠️ Less than 5 minutes remaining!")
    
    # Add a progress bar
    if test_data.get("time_limit") and st.session_state.test_start_time and st.session_state.test_end_time:
        total_duration = test_data["time_limit"] * 60  # seconds
        elapsed = (datetime.now() - st.session_state.test_start_time).total_seconds()
        progress = min(elapsed / total_duration, 1.0)
        st.progress(progress)
    
    # Display questions
    with st.form(key=f"test_form_{test_data['title']}"):
        # Store answers
        answers = {}
        
        # Display each question
        for q_idx, question in enumerate(test_data["questions"]):
            st.write(f"**Question {q_idx+1}** ({question['marks']} marks)")
            st.write(question["question_text"])
            
            # If it's multiple choice, show options
            if question["question_type"].lower() in ["multiple choice", "multiple_choice"]:
                if "options" in question and question["options"]:
                    options = question["options"]
                    # Use the current answer from session state as default value
                    default_index = 0
                    if f"q_{q_idx}" in st.session_state.current_answers and st.session_state.current_answers[f"q_{q_idx}"] in options:
                        default_index = options.index(st.session_state.current_answers[f"q_{q_idx}"])
                    
                    selected_option = st.radio(
                        f"Select your answer for Q{q_idx+1}",
                        options,
                        index=default_index,
                        key=f"mc_{q_idx}"
                    )
                    answers[f"q_{q_idx}"] = selected_option
            elif question["question_type"].lower() in ["true/false", "true_false"]:
                # Use the current answer from session state as default value
                default_index = 0
                if f"q_{q_idx}" in st.session_state.current_answers:
                    if st.session_state.current_answers[f"q_{q_idx}"] == "True":
                        default_index = 0
                    elif st.session_state.current_answers[f"q_{q_idx}"] == "False":
                        default_index = 1
                
                selected_tf = st.radio(
                    f"Select your answer for Q{q_idx+1}",
                    ["True", "False"],
                    index=default_index,
                    key=f"tf_{q_idx}"
                )
                answers[f"q_{q_idx}"] = selected_tf
            else:
                # For other question types, show a text area
                default_value = ""
                if f"q_{q_idx}" in st.session_state.current_answers:
                    default_value = st.session_state.current_answers[f"q_{q_idx}"]
                
                answer_text = st.text_area(
                    f"Your answer for Q{q_idx+1}",
                    value=default_value,
                    height=150,
                    key=f"answer_{q_idx}"
                )
                answers[f"q_{q_idx}"] = answer_text
            
            st.markdown("---")
        
        # Add save progress button outside the form but before submit
        col1, col2 = st.columns(2)
        
        with col1:
            submit_button = st.form_submit_button("Submit Test")
            if submit_button:
                # Update current answers
                st.session_state.current_answers = answers
                
                # Save the submission
                success, message = save_test_submission(
                    st.session_state.user_email,
                    test_data["course"],
                    test_data["title"],
                    answers
                )
                
                if success:
                    st.success(message)
                    # End test session
                    st.session_state.test_in_progress = False
                    st.session_state.test_data = None
                    st.session_state.test_start_time = None
                    st.session_state.test_end_time = None
                    st.session_state.current_answers = {}
                    st.rerun()
                else:
                    st.error(message)
    
    # Save progress button outside the form
    if st.button("Save Progress (Without Submitting)"):
        # Update current answers in session state
        for q_idx in range(len(test_data["questions"])):
            if question["question_type"].lower() in ["multiple choice", "multiple_choice"]:
                if f"mc_{q_idx}" in st.session_state:
                    st.session_state.current_answers[f"q_{q_idx}"] = st.session_state[f"mc_{q_idx}"]
            elif question["question_type"].lower() in ["true/false", "true_false"]:
                if f"tf_{q_idx}" in st.session_state:
                    st.session_state.current_answers[f"q_{q_idx}"] = st.session_state[f"tf_{q_idx}"]
            else:
                if f"answer_{q_idx}" in st.session_state:
                    st.session_state.current_answers[f"q_{q_idx}"] = st.session_state[f"answer_{q_idx}"]
        
        st.success("Progress saved! Continue working on your test.")
    
    # Exit without submitting button
    if st.button("Exit Without Submitting", key="exit_test_button"):
        st.warning("Are you sure you want to exit without submitting? Your progress will be lost.")
        confirm_col1, confirm_col2 = st.columns(2)
        
        with confirm_col1:
            if st.button("Yes, Exit", key="confirm_exit"):
                st.session_state.test_in_progress = False
                st.session_state.test_data = None
                st.session_state.test_start_time = None
                st.session_state.test_end_time = None
                st.session_state.current_answers = {}
                st.rerun()
        
        with confirm_col2:
            if st.button("No, Continue Test", key="cancel_exit"):
                st.rerun()