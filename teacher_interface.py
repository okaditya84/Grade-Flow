import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import tempfile
from datetime import datetime, timedelta
from fpdf import FPDF
from utils import (
    get_student_submissions, 
    save_evaluation_criteria, 
    get_published_question_papers, 
    get_test_submissions_for_course
)
from evaluation import evaluate_submissions, evaluate_test_submissions
from question_paper_generator import (
    generate_questions_from_reference, 
    generate_questions_from_prompt,
    create_question_paper_pdf,
    save_question_paper,
    publish_question_paper
)
from plagiarism_detector import PlagiarismDetector, PlagiarismDatabase, run_plagiarism_detection_batch

def show_teacher_interface():
    """Updated teacher interface with plagiarism detection"""
    st.title(f"👨‍🏫 Teacher Dashboard")
    st.write(f"Welcome, {st.session_state.user_email}")

    # Add custom CSS for better tab visibility in dark mode
    st.markdown("""
    <style>
    /* Improve tab visibility for dark mode */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px;
        font-weight: 600;
        color: #ffffff !important; /* White text for all tabs */
    }
    
    /* Active tab styling */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: #0e4b99 !important; /* Blue background for active tab */
        border-bottom: 3px solid #1f77b4 !important; /* Blue bottom border */
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] [data-testid="stMarkdownContainer"] p {
        color: #ffffff !important; /* White text for active tab */
    }
    
    /* Inactive tab styling */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="false"] {
        background-color: #2d3748 !important; /* Darker background for inactive tabs */
        border-bottom: 2px solid #4a5568 !important; /* Gray bottom border */
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="false"] [data-testid="stMarkdownContainer"] p {
        color: #e2e8f0 !important; /* Light gray text for inactive tabs */
    }
    
    /* Hover effect for inactive tabs */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="false"]:hover {
        background-color: #4a5568 !important; /* Lighter gray on hover */
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="false"]:hover [data-testid="stMarkdownContainer"] p {
        color: #ffffff !important; /* White text on hover */
    }
    
    /* Tab list container */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1a202c !important; /* Dark background for tab container */
        border-radius: 8px 8px 0 0;
        padding: 4px;
    }
    
    /* Individual tab buttons */
    .stTabs [data-baseweb="tab-list"] button {
        border-radius: 6px !important;
        margin: 0 2px;
        transition: all 0.2s ease-in-out;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create main tabs - ADD plagiarism detection tab
    tabs = st.tabs([
        "Evaluate Tests", 
        "Evaluate Assignments", 
        "Evaluate Exams", 
        "Evaluate Projects",
        "Generate Question Papers",
        "Manage Published Papers",
        "🔍 Plagiarism Detection"  # NEW TAB
    ])

    with tabs[0]:
        show_evaluation_interface("test")

    with tabs[1]:
        show_evaluation_interface("assignment")

    with tabs[2]:
        show_evaluation_interface("exam")

    with tabs[3]:
        show_evaluation_interface("project")

    with tabs[4]:
        show_question_paper_generation_interface()
    
    with tabs[5]:
        show_published_papers_interface()
    
    with tabs[6]:  
        show_plagiarism_detection_interface()


def show_evaluation_interface(submission_type):
    st.header(f"Evaluate {submission_type.title()}s")

    # Add unique key to the course input
    course = st.text_input(f"Course Code for {submission_type.title()}", 
                         key=f"course_code_{submission_type}")

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
    # Existing code - unchanged
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
    # Existing code - unchanged
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


def show_question_paper_generation_interface():
    """Interface for generating question papers"""
    st.header("Generate Question Papers")
    
    # Create directory if it doesn't exist
    os.makedirs("data/question_papers", exist_ok=True)
    
    # Add unique key to course code input
    course_code = st.text_input("Course Code", key="gen_course_code")
    title = st.text_input("Exam/Test Title", key="gen_title")
    
    # School Information Section
    with st.expander("📚 School Information (for PDF Header)", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            school_name = st.text_input(
                "School Name", 
                value="ABC International School",
                key="school_name"
            )
            grade = st.text_input(
                "Class/Grade", 
                value="Grade 10",
                key="grade"
            )
        
        with col2:
            academic_year = st.text_input(
                "Academic Year", 
                value="2024-2025",
                key="academic_year"
            )
        
        school_info = {
            "school_name": school_name,
            "academic_year": academic_year,
            "grade": grade
        }
    
    # Create tabs for different generation methods
    generation_tabs = st.tabs(["Generate from Reference PDF", "Generate from Custom Prompt"])
    
    with generation_tabs[0]:  # Generate from Reference PDF
        st.subheader("Generate from Reference Material")
        
        # Reference material upload
        reference_pdf = st.file_uploader(
            "Upload Reference Material (e.g., textbook chapter, lecture notes)",
            type="pdf",
            key="reference_pdf"
        )
        
        # Topic selection
        topics = st.text_area(
            "Enter Topics to Cover (one per line)",
            placeholder="Machine Learning\nNeural Networks\nDeep Learning",
            key="ref_topics"
        )
        
        # Question parameters
        col1, col2 = st.columns(2)
        
        with col1:
            difficulty = st.select_slider(
                "Difficulty Level",
                options=["Easy", "Medium", "Hard"],
                value="Medium",
                key="ref_difficulty"
            )
            
            num_questions = st.number_input(
                "Number of Questions",
                min_value=5,
                max_value=50,
                value=10,
                step=1,
                key="ref_num_questions"
            )
        
        with col2:
            question_types = st.multiselect(
                "Question Types",
                options=["Multiple Choice", "Short Answer", "Long Answer", "Numerical", "True/False"],
                default=["Multiple Choice", "Short Answer"],
                key="ref_question_types"
            )
            
        # Generate button
        if st.button("Generate Questions from Reference", key="gen_ref_btn"):
            if not reference_pdf:
                st.error("Please upload a reference PDF.")
                return
            
            if not topics or not question_types:
                st.error("Please provide topics and select at least one question type.")
                return
            
            # Generate questions
            with st.spinner("Generating questions... This may take a minute."):
                questions_data = generate_questions_from_reference(
                    reference_pdf,
                    course_code,
                    topics,
                    difficulty,
                    num_questions,
                    ", ".join(question_types)
                )
                
                # Store in session state for preview
                if "questions" in questions_data and questions_data["questions"]:
                    st.session_state.generated_questions = questions_data
                    st.session_state.question_paper_title = title
                    st.session_state.question_paper_course = course_code
                    st.success(f"Successfully generated {len(questions_data['questions'])} questions!")
                else:
                    if "error" in questions_data:
                        st.error(f"Failed to generate questions: {questions_data['error']}")
                    else:
                        st.error("Failed to generate questions. Please try again.")
    
    with generation_tabs[1]:  # Generate from Custom Prompt
        st.subheader("Generate from Custom Prompt")
        
        # Topic selection
        topics = st.text_area(
            "Enter Topics to Cover (one per line)",
            placeholder="Machine Learning\nNeural Networks\nDeep Learning",
            key="prompt_topics"
        )
        
        # Custom prompt
        custom_prompt = st.text_area(
            "Custom Instructions",
            placeholder="Create questions that test the student's understanding of neural network architectures and their applications.",
            height=150,
            key="custom_prompt"
        )
        
        # Question parameters
        col1, col2 = st.columns(2)
        
        with col1:
            difficulty = st.select_slider(
                "Difficulty Level",
                options=["Easy", "Medium", "Hard"],
                value="Medium",
                key="prompt_difficulty"
            )
            
            num_questions = st.number_input(
                "Number of Questions",
                min_value=5,
                max_value=50,
                value=10,
                step=1,
                key="prompt_num_questions"
            )
        
        with col2:
            question_types = st.multiselect(
                "Question Types",
                options=["Multiple Choice", "Short Answer", "Long Answer", "Numerical", "True/False"],
                default=["Multiple Choice", "Short Answer"],
                key="prompt_question_types"
            )
        
        # Generate button
        if st.button("Generate Questions from Prompt", key="gen_prompt_btn"):
            if not topics or not question_types or not custom_prompt:
                st.error("Please provide topics, question types, and custom instructions.")
                return
            
            # Generate questions
            with st.spinner("Generating questions... This may take a minute."):
                questions_data = generate_questions_from_prompt(
                    course_code,
                    topics,
                    difficulty,
                    num_questions,
                    ", ".join(question_types),
                    custom_prompt
                )
                
                # Store in session state for preview
                if "questions" in questions_data and questions_data["questions"]:
                    st.session_state.generated_questions = questions_data
                    st.session_state.question_paper_title = title
                    st.session_state.question_paper_course = course_code
                    st.success(f"Successfully generated {len(questions_data['questions'])} questions!")
                else:
                    if "error" in questions_data:
                        st.error(f"Failed to generate questions: {questions_data['error']}")
                    else:
                        st.error("Failed to generate questions. Please try again.")
    
    # Question preview and refinement section
    if "generated_questions" in st.session_state:
        st.header("Question Paper Preview")
        
        # Paper metadata
        col1, col2, col3 = st.columns(3)
        
        with col1:
            exam_date = st.date_input("Exam Date", key="exam_date")
        
        with col2:
            duration = st.text_input("Duration (e.g., '3 hours')", value="3 hours", key="duration")
        
        with col3:
            include_answers = st.checkbox("Include Answer Key in PDF", value=False, key="include_answers")
        
        # Instructions
        instructions = st.text_area(
            "Instructions for Students",
            value="1. Attempt all questions.\n2. Each question carries marks as indicated.\n3. Write clear and concise answers.\n4. Time management is crucial.",
            height=100,
            key="instructions"
        )
        
        # Display and allow editing of questions
        st.subheader("Questions")
        
        questions_data = st.session_state.generated_questions
        edited_questions = []
        
        for i, question in enumerate(questions_data["questions"]):
            with st.expander(f"Question {i+1} - Section {question.get('section', 'A')} ({question['marks']} marks)"):
                # Question metadata
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    section = st.selectbox(
                        "Section",
                        options=["A", "B", "C"],
                        index=["A", "B", "C"].index(question.get("section", "A")),
                        key=f"q_section_{i}"
                    )
                
                with col2:
                    question_type = st.selectbox(
                        "Question Type",
                        options=["Multiple Choice", "True/False", "Fill in Blanks", "Short Answer", "Long Answer", "Numerical"],
                        index=0,
                        key=f"q_type_{i}"
                    )
                
                with col3:
                    marks = st.number_input(
                        "Marks",
                        min_value=1,
                        max_value=20,
                        value=int(question["marks"]),
                        key=f"q_marks_{i}"
                    )
                
                with col4:
                    difficulty = st.select_slider(
                        "Difficulty",
                        options=["Easy", "Medium", "Hard"],
                        value=question["difficulty"].capitalize() if question["difficulty"] in ["easy", "medium", "hard"] else "Medium",
                        key=f"q_diff_{i}"
                    )
                
                # Question text
                question_text = st.text_area(
                    "Question Text", 
                    value=question["question_text"],
                    key=f"q_text_{i}"
                )
                
                # Chapter/Unit information
                chapter_unit = st.text_input(
                    "Chapter/Unit Reference",
                    value=question.get("chapter_unit", ""),
                    key=f"q_chapter_{i}"
                )
                
                # Cognitive level
                cognitive_level = st.selectbox(
                    "Cognitive Level",
                    options=["Knowledge", "Understanding", "Application", "Analysis", "Synthesis", "Evaluation"],
                    index=0,
                    key=f"q_cognitive_{i}"
                )
                
                # Options for multiple choice
                options = []
                if question_type == "Multiple Choice":
                    st.subheader("Options")
                    
                    for j in range(4):
                        option_value = ""
                        if "options" in question and len(question["options"]) > j:
                            option_value = question["options"][j]
                        
                        option = st.text_input(
                            f"Option {chr(65+j)}",
                            value=option_value,
                            key=f"q_opt_{i}_{j}"
                        )
                        options.append(option)
                
                # Correct answer
                correct_answer = st.text_area(
                    "Correct Answer",
                    value=question.get("correct_answer", ""),
                    key=f"q_ans_{i}"
                )
                
                # Solution steps
                solution_steps = []
                if question_type == "Numerical":
                    st.subheader("Solution Steps")
                    
                    existing_steps = question.get("solution_steps", [""])
                    num_steps = st.number_input(
                        "Number of Steps",
                        min_value=1,
                        max_value=10,
                        value=len(existing_steps),
                        key=f"q_step_count_{i}"
                    )
                    
                    for j in range(num_steps):
                        step_value = ""
                        if j < len(existing_steps):
                            step_value = existing_steps[j]
                            
                        step = st.text_input(
                            f"Step {j+1}",
                            value=step_value,
                            key=f"q_step_{i}_{j}"
                        )
                        solution_steps.append(step)
                
                # Collect edited question
                edited_question = {
                    "question_number": i + 1,
                    "question_text": question_text,
                    "question_type": question_type,
                    "marks": marks,
                    "difficulty": difficulty.lower(),
                    "correct_answer": correct_answer,
                    "section": section,
                    "chapter_unit": chapter_unit
                }
                
                if question_type == "Multiple Choice":
                    edited_question["options"] = options
                
                if question_type == "Numerical" and solution_steps:
                    edited_question["solution_steps"] = solution_steps
                
                edited_questions.append(edited_question)
        
        # Update the questions data
        questions_data["questions"] = edited_questions
        st.session_state.generated_questions = questions_data
        
        # ADD THIS PREVIEW SECTION HERE:
        st.markdown("---")
        st.subheader("📋 Question Paper Preview")
        
        # Show formatted preview
        if st.button("📋 Show Formatted Preview", key="show_preview"):
            show_question_paper_preview(questions_data, course_code, title, school_info)
        
        st.markdown("---")
        
        # Generate PDF button
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Generate PDF", key="gen_pdf_btn"):
                try:
                    # Create PDF with school information
                    pdf_bytes, pdf_filename = create_question_paper_pdf(
                        questions_data,
                        course_code,
                        title,
                        exam_date.strftime("%Y-%m-%d"),
                        duration,
                        instructions,
                        include_answers,
                        school_info  # Add school info parameter
                    )
                    
                    # Provide download button
                    st.session_state.pdf_bytes = pdf_bytes
                    st.session_state.pdf_filename = pdf_filename
                    
                    # Save to disk
                    save_question_paper(
                        course_code,
                        title,
                        questions_data,
                        include_answers
                    )
                    
                    st.success("Question paper generated successfully!")
                    
                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")
        
        with col2:
            # Download button will appear after PDF is generated
            if "pdf_bytes" in st.session_state and "pdf_filename" in st.session_state:
                st.download_button(
                    label="Download Question Paper",
                    data=st.session_state.pdf_bytes,
                    file_name=st.session_state.pdf_filename,
                    mime="application/pdf"
                )
        
         # Publication section
        st.subheader("Publish to Students")
        
        # Initialize session state variables if they don't exist
        if "publishing_mode" not in st.session_state:
            st.session_state.publishing_mode = False
        
        # Set up the publication form
        publication_col1, publication_col2 = st.columns(2)
        
        with publication_col1:
            deadline_date = st.date_input(
                "Submission Deadline", 
                value=datetime.now() + timedelta(days=7),
                key="publish_deadline_date"
            )
        
        with publication_col2:
            publish_instructions = st.checkbox(
                "Use same instructions for students", 
                value=True,
                key="use_same_instructions"
            )
        
        # Time limit option
        time_limit_enabled = st.checkbox("Enable time limit for test", key="enable_time_limit")
        
        time_limit = None
        if time_limit_enabled:
            time_limit_col1, time_limit_col2 = st.columns(2)
            
            with time_limit_col1:
                time_limit_hours = st.number_input("Hours", min_value=0, max_value=24, value=1, key="time_limit_hours")
            
            with time_limit_col2:
                time_limit_minutes = st.number_input("Minutes", min_value=0, max_value=59, value=30, key="time_limit_minutes")
            
            time_limit = time_limit_hours * 60 + time_limit_minutes  # Convert to minutes
            
            st.info(f"Students will have {time_limit_hours} hour(s) and {time_limit_minutes} minute(s) to complete this test once they start.")
        
        if not publish_instructions:
            publish_instruction_text = st.text_area(
                "Instructions for Students (when published)",
                value=instructions,
                height=100,
                key="publish_instructions"
            )
        else:
            publish_instruction_text = instructions
            
        # Publish button with confirmation
        if st.button("Publish to Students", key="publish_final_btn"):
            if not title or not course_code:
                st.error("Please enter a course code and title for the question paper.")
            elif len(questions_data["questions"]) == 0:
                st.error("Cannot publish a question paper with no questions.")
            else:
                try:
                    # Create directories if they don't exist
                    os.makedirs("data/published_papers", exist_ok=True)
                    os.makedirs(f"data/published_papers/{course_code}", exist_ok=True)
                    
                    # Publish the question paper
                    success = publish_question_paper(
                        course_code,
                        title,
                        questions_data,
                        deadline_date.strftime("%Y-%m-%d"),
                        publish_instruction_text,
                        include_answers=False,  # Never publish answers to students
                        time_limit=time_limit   # Add time limit
                    )
                    
                    if success:
                        st.success(f"Question paper '{title}' published successfully for course {course_code}.")
                        if time_limit_enabled:
                            st.success(f"Time limit set: {time_limit_hours} hour(s) and {time_limit_minutes} minute(s).")
                        st.info("Students can now access this paper in their interface.")
                        
                        # Option to view published papers
                        if st.button("Manage Published Papers"):
                            # Switch to the Manage Published Papers tab
                            st.session_state.active_tab = 5  # Index of the Manage Published Papers tab
                            st.rerun()
                    else:
                        st.error("Failed to publish question paper. Please try again.")
                        
                except Exception as e:
                    st.error(f"Error publishing question paper: {str(e)}")
                    st.error("Please check that all required data is provided and try again.")

# Update the show_published_papers_interface function to fix the evaluation process
def show_published_papers_interface():
    """Interface for managing published question papers"""
    st.header("Manage Published Question Papers")
    
    # Add unique key to the course input
    course_code = st.text_input("Course Code", key="published_course_code")
    
    if not course_code:
        st.info("Please enter a course code to view published question papers.")
        return
    
    # Get published papers
    published_papers = get_published_question_papers(course_code=course_code)
    
    if not published_papers:
        st.info(f"No question papers have been published for {course_code}.")
        return
    
    # Display papers in a selection box
    paper_titles = [f"{paper['title']} (Published: {paper['created_date']})" for paper in published_papers]
    selected_paper_idx = st.selectbox("Select Paper", range(len(paper_titles)), format_func=lambda x: paper_titles[x])
    
    # Get the selected paper
    selected_paper = published_papers[selected_paper_idx]
    
    # Display paper details
    st.subheader(f"Paper Details: {selected_paper['title']}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Course:** {selected_paper['course']}")
        st.write(f"**Published:** {selected_paper['created_date']}")
    
    with col2:
        st.write(f"**Deadline:** {selected_paper.get('deadline', 'Not specified')}")
        st.write(f"**Status:** {selected_paper.get('status', 'Active')}")
        
    with col3:
        if selected_paper.get('time_limit'):
            hours = selected_paper['time_limit'] // 60
            minutes = selected_paper['time_limit'] % 60
            time_display = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            st.write(f"**Time Limit:** {time_display}")
        else:
            st.write("**Time Limit:** None")
    
    # Option to view paper content
    if st.button("View Paper Content"):
        st.subheader("Questions")
        
        for i, question in enumerate(selected_paper["questions"]):
            with st.expander(f"Q{i+1}: {question['question_text'][:50]}... ({question['marks']} marks)"):
                st.write(question["question_text"])
                
                if "options" in question and question["options"]:
                    st.write("**Options:**")
                    for j, option in enumerate(question["options"]):
                        st.write(f"{chr(65+j)}. {option}")
                
                st.write(f"**Correct Answer:** {question['correct_answer']}")
    
    # View student submissions
    st.subheader("Student Submissions")
    
    # Get submissions for this paper
    submissions = get_test_submissions_for_course(course_code, selected_paper["title"])
    
    if not submissions:
        st.info("No student submissions yet.")
    else:
        # Create DataFrame for submissions
        submissions_df = pd.DataFrame([
            {
                "Student": sub["student_email"].split("@")[0],
                "Submission Date": sub["submission_date"],
                "Status": sub.get("evaluation_status", "Pending")
            }
            for sub in submissions
        ])
        
        st.dataframe(submissions_df, use_container_width=True)
        
        # Option to evaluate submissions
        if st.button("Evaluate Submissions"):
            with st.spinner("Evaluating submissions... This may take some time."):
                # Use our new evaluation function that handles JSON submissions directly
                results, message = evaluate_test_submissions(
                    course_code,
                    selected_paper["title"],
                    submissions
                )
                
                if results:
                    # Display results
                    display_evaluation_results(results, "test", course_code)
                else:
                    st.error(f"Evaluation failed: {message}")

# Add this function to show a preview of the formatted question paper

def show_question_paper_preview(questions_data, course_code, title, school_info):
    """Show a preview of how the question paper will look"""
    st.subheader("📋 Question Paper Preview")
    
    # Header preview
    st.markdown("---")
    st.markdown(f"<h2 style='text-align: center'>{school_info.get('school_name', 'SCHOOL NAME')}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center'>Academic Year: {school_info.get('academic_year', '2024-2025')}</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Paper details table
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Class/Grade:** {school_info.get('grade', 'Grade X')}")
        st.write(f"**Time:** 3 hours")
        st.write(f"**Date:** {datetime.now().strftime('%d/%m/%Y')}")
    
    with col2:
        st.write(f"**Subject:** {course_code}")
        st.write(f"**Total Marks:** {questions_data.get('paper_info', {}).get('total_marks', 'XX')}")
        st.write(f"**Paper Code:** {title}-SET-A")
    
    st.markdown("---")
    
    # Questions by section
    questions = questions_data.get("questions", [])
    sections = {"A": [], "B": [], "C": []}
    
    for q in questions:
        section = q.get("section", "A").upper()
        sections[section].append(q)
    
    section_titles = {
        "A": "Section A: Objective Questions (1 Mark each)",
        "B": "Section B: Short Answer Questions (3-5 Marks each)",
        "C": "Section C: Long Answer Questions (6-10 Marks each)"
    }
    
    for section_key in ["A", "B", "C"]:
        if sections[section_key]:
            st.markdown(f"### {section_titles[section_key]}")
            
            for q in sections[section_key]:
                with st.container():
                    # Question header
                    marks_text = f"({q.get('marks', 1)} Mark{'s' if q.get('marks', 1) > 1 else ''})"
                    st.markdown(f"**Q{q.get('question_number', '')}. {marks_text}**")
                    
                    # Chapter reference
                    if q.get('chapter_unit'):
                        st.markdown(f"*[{q.get('chapter_unit')}]*")
                    
                    # Question text
                    st.write(q.get('question_text', ''))
                    
                    # Options for MCQs
                    if q.get('question_type', '').lower() in ['multiple choice', 'mcq'] and q.get('options'):
                        for i, option in enumerate(q['options']):
                            st.write(f"({chr(97+i)}) {option}")
                    
                    st.write("")  # Space between questions
            
            st.markdown("---")
    
    # Paper analysis
    st.subheader("📊 Question Paper Analysis")
    
    paper_info = questions_data.get('paper_info', {})
    sections_info = paper_info.get('sections', {})
    
    analysis_data = {
        "Section": ["A", "B", "C", "Total"],
        "Type of Questions": [
            "Objective (MCQ, T/F, Fill)", 
            "Short Answer", 
            "Long Answer", 
            "ALL"
        ],
        "No. of Questions": [
            sections_info.get('section_a', {}).get('questions', 0),
            sections_info.get('section_b', {}).get('questions', 0),
            sections_info.get('section_c', {}).get('questions', 0),
            sum([sections_info.get(f'section_{s}', {}).get('questions', 0) for s in ['a', 'b', 'c']])
        ],
        "Marks per Question": ["1", "3-5", "6-10", "-"],
        "Total Marks": [
            sections_info.get('section_a', {}).get('total_marks', 0),
            sections_info.get('section_b', {}).get('total_marks', 0),
            sections_info.get('section_c', {}).get('total_marks', 0),
            paper_info.get('total_marks', 0)
        ]
    }
    
    analysis_df = pd.DataFrame(analysis_data)
    st.table(analysis_df)

def show_plagiarism_detection_interface():
    """Interface for plagiarism detection and management"""
    st.header("🔍 Plagiarism Detection System")
    
    # Create tabs for different plagiarism functions
    plag_tabs = st.tabs([
        "🔎 Run Detection", 
        "📊 View Results", 
        "📈 Analytics",
        "⚙️ Settings"
    ])
    
    with plag_tabs[0]:
        show_run_plagiarism_detection()
    
    with plag_tabs[1]:
        show_plagiarism_results()
    
    with plag_tabs[2]:
        show_plagiarism_analytics()
    
    with plag_tabs[3]:
        show_plagiarism_settings()

def show_run_plagiarism_detection():
    """Interface to run plagiarism detection"""
    st.subheader("🔎 Run Plagiarism Detection")
    
    # Detection scope options
    col1, col2 = st.columns(2)
    
    with col1:
        detection_scope = st.selectbox(
            "Detection Scope",
            ["All Submissions", "Specific Course", "Specific Type", "Recent Submissions"]
        )
    
    with col2:
        if detection_scope == "Specific Course":
            course_filter = st.text_input("Course Code")
        elif detection_scope == "Specific Type":
            type_filter = st.selectbox(
                "Submission Type",
                ["test", "assignment", "exam", "project"]
            )
        elif detection_scope == "Recent Submissions":
            days_filter = st.number_input("Days back", min_value=1, max_value=365, value=30)
    
    # Detection sensitivity
    st.subheader("Detection Settings")
    
    sensitivity = st.select_slider(
        "Detection Sensitivity",
        options=["Low", "Medium", "High", "Maximum"],
        value="High",
        help="Higher sensitivity may catch more cases but could increase false positives"
    )
    
    # Include specific checks
    check_options = st.multiselect(
        "Include Additional Checks",
        [
            "Cross-batch comparison",
            "Writing style analysis", 
            "Structural similarity",
            "Common phrase detection",
            "Time-based patterns"
        ],
        default=["Cross-batch comparison", "Writing style analysis"]
    )
    
    # Run detection button
    st.markdown("---")
    
    if st.button("🚀 Start Plagiarism Detection", type="primary"):
        if detection_scope == "All Submissions":
            course_param = None
            type_param = None
        elif detection_scope == "Specific Course":
            course_param = course_filter if 'course_filter' in locals() else None
            type_param = None
        elif detection_scope == "Specific Type":
            course_param = None
            type_param = type_filter if 'type_filter' in locals() else None
        else:
            course_param = None
            type_param = None
        
        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("Initializing plagiarism detection...")
            progress_bar.progress(10)
            
            status_text.text("Collecting submissions...")
            progress_bar.progress(30)
            
            # Run detection
            results = run_plagiarism_detection_batch(course_param, type_param)
            progress_bar.progress(80)
            
            status_text.text("Analyzing results...")
            progress_bar.progress(100)
            
            # Display results summary
            st.success(f"✅ Detection completed! Found {len(results)} potential plagiarism cases.")
            
            if results:
                # Quick summary
                critical_cases = len([r for r in results if r['plagiarism_level'] == 'CRITICAL'])
                high_cases = len([r for r in results if r['plagiarism_level'] == 'HIGH'])
                moderate_cases = len([r for r in results if r['plagiarism_level'] == 'MODERATE'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🚨 Critical Cases", critical_cases)
                with col2:
                    st.metric("⚠️ High Risk Cases", high_cases)
                with col3:
                    st.metric("⚡ Moderate Cases", moderate_cases)
                
                # Show top cases
                st.subheader("Top Plagiarism Cases")
                for i, result in enumerate(results[:5]):
                    with st.expander(
                        f"Case {i+1}: {result['plagiarism_level']} - "
                        f"{result['submission1_info']['student_email'].split('@')[0]} vs "
                        f"{result['submission2_info']['student_email'].split('@')[0]} "
                        f"({result['composite_score']}% similarity)"
                    ):
                        display_plagiarism_case(result)
            
        except Exception as e:
            st.error(f"Error during plagiarism detection: {e}")
        finally:
            progress_bar.empty()
            status_text.empty()

def show_plagiarism_results():
    """Display plagiarism detection results"""
    st.subheader("📊 Plagiarism Detection Results")
    
    db = PlagiarismDatabase()
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        level_filter = st.selectbox(
            "Filter by Level",
            ["All", "CRITICAL", "HIGH", "MODERATE", "LOW"]
        )
    
    with col2:
        course_filter = st.text_input("Filter by Course")
    
    with col3:
        limit = st.number_input("Max Results", min_value=10, max_value=100, value=50)
    
    # Get results
    level_param = None if level_filter == "All" else level_filter
    course_param = course_filter if course_filter else None
    
    results = db.get_plagiarism_results(
        course=course_param,
        level=level_param,
        limit=limit
    )
    
    if not results:
        st.info("No plagiarism results found. Run detection first.")
        return
    
    # Display results
    st.write(f"Found {len(results)} plagiarism cases")
    
    # Results summary
    level_counts = {}
    for result in results:
        level = result.get('plagiarism_level', 'UNKNOWN')
        level_counts[level] = level_counts.get(level, 0) + 1
    
    if level_counts:
        st.bar_chart(level_counts)
    
    # Detailed results
    for i, result in enumerate(results):
        severity_color = {
            'CRITICAL': '🚨',
            'HIGH': '⚠️', 
            'MODERATE': '⚡',
            'LOW': 'ℹ️',
            'NONE': '✅'
        }
        
        icon = severity_color.get(result['plagiarism_level'], '❓')
        
        with st.expander(
            f"{icon} Case {i+1}: {result['plagiarism_level']} Similarity "
            f"({result['composite_score']}%) - "
            f"{result['submission1_info']['student_email'].split('@')[0]} vs "
            f"{result['submission2_info']['student_email'].split('@')[0]}"
        ):
            display_plagiarism_case(result)

def display_plagiarism_case(result):
    """Display detailed information about a plagiarism case"""
    
    # Case overview
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Student 1:**")
        st.write(f"Email: {result['submission1_info']['student_email']}")
        st.write(f"Course: {result['submission1_info']['course']}")
        st.write(f"Assignment: {result['submission1_info']['title']}")
        st.write(f"Date: {result['submission1_info']['submission_date']}")
    
    with col2:
        st.write("**Student 2:**")
        st.write(f"Email: {result['submission2_info']['student_email']}")
        st.write(f"Course: {result['submission2_info']['course']}")
        st.write(f"Assignment: {result['submission2_info']['title']}")
        st.write(f"Date: {result['submission2_info']['submission_date']}")
    
    # Similarity metrics
    st.subheader("Similarity Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Composite Score", f"{result['composite_score']}%")
        st.metric("Exact Similarity", f"{result['similarity_scores']['exact_similarity']}%")
    
    with col2:
        st.metric("Semantic Similarity", f"{result['similarity_scores']['semantic_similarity']}%")
        st.metric("TF-IDF Similarity", f"{result['similarity_scores']['tfidf_similarity']}%")
    
    with col3:
        st.metric("Structural Similarity", f"{result['structural_similarity']}%")
        st.metric("Writing Style", f"{result['writing_style_similarity']}%")
    
    # Common phrases
    if result.get('common_phrases'):
        st.subheader("Common Phrases Found")
        for phrase in result['common_phrases']:
            st.code(phrase)
    
    # Analysis details
    st.subheader("Analysis Details")
    st.write(f"**Level:** {result['plagiarism_level']}")
    st.write(f"**Description:** {result['description']}")
    st.write(f"**Analysis Date:** {result['analysis_timestamp']}")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📧 Notify Students", key=f"notify_{hash(str(result))}"):
            st.warning("Student notification feature would be implemented here")
    
    with col2:
        if st.button("📝 Generate Report", key=f"report_{hash(str(result))}"):
            generate_plagiarism_report(result)
    
    with col3:
        if st.button("❌ Mark as False Positive", key=f"false_{hash(str(result))}"):
            st.info("False positive marking feature would be implemented here")

def show_plagiarism_analytics():
    """Show plagiarism analytics and trends"""
    st.subheader("📈 Plagiarism Analytics")
    
    db = PlagiarismDatabase()
    all_results = db.get_plagiarism_results()
    
    if not all_results:
        st.info("No data available for analytics. Run detection first.")
        return
    
    # Overall statistics
    col1, col2, col3, col4 = st.columns(4)
    
    total_cases = len(all_results)
    critical_cases = len([r for r in all_results if r['plagiarism_level'] == 'CRITICAL'])
    high_cases = len([r for r in all_results if r['plagiarism_level'] == 'HIGH'])
    avg_similarity = np.mean([r['composite_score'] for r in all_results])
    
    with col1:
        st.metric("Total Cases", total_cases)
    with col2:
        st.metric("Critical Cases", critical_cases)
    with col3:
        st.metric("High Risk Cases", high_cases)
    with col4:
        st.metric("Avg Similarity", f"{avg_similarity:.1f}%")
    
    # Trends over time
    st.subheader("Detection Trends")
    
    # Group by date
    from collections import defaultdict
    daily_counts = defaultdict(int)
    
    for result in all_results:
        date = result['analysis_timestamp'][:10]  # Extract date part
        daily_counts[date] += 1
    
    if daily_counts:
        dates = sorted(daily_counts.keys())
        counts = [daily_counts[date] for date in dates]
        
        import plotly.express as px
        import pandas as pd
        
        df = pd.DataFrame({'Date': dates, 'Cases': counts})
        fig = px.line(df, x='Date', y='Cases', title='Plagiarism Cases Over Time')
        st.plotly_chart(fig, use_container_width=True)
    
    # Course-wise analysis
    st.subheader("Course-wise Analysis")
    
    course_stats = defaultdict(lambda: {'total': 0, 'critical': 0, 'high': 0})
    
    for result in all_results:
        course1 = result['submission1_info']['course']
        course2 = result['submission2_info']['course']
        level = result['plagiarism_level']
        
        course_stats[course1]['total'] += 1
        course_stats[course2]['total'] += 1
        
        if level == 'CRITICAL':
            course_stats[course1]['critical'] += 1
            course_stats[course2]['critical'] += 1
        elif level == 'HIGH':
            course_stats[course1]['high'] += 1
            course_stats[course2]['high'] += 1
    
    if course_stats:
        course_df = pd.DataFrame([
            {
                'Course': course,
                'Total Cases': stats['total'],
                'Critical': stats['critical'],
                'High Risk': stats['high']
            }
            for course, stats in course_stats.items()
        ])
        
        st.dataframe(course_df, use_container_width=True)

def show_plagiarism_settings():
    """Plagiarism detection settings and configuration"""
    st.subheader("⚙️ Plagiarism Detection Settings")
    
    # Detection thresholds
    st.write("**Detection Thresholds**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        exact_threshold = st.slider(
            "Exact Match Threshold (%)",
            min_value=80,
            max_value=100,
            value=95,
            help="Threshold for considering submissions as exact matches"
        )
        
        high_threshold = st.slider(
            "High Similarity Threshold (%)",
            min_value=70,
            max_value=90,
            value=85,
            help="Threshold for high plagiarism detection"
        )
    
    with col2:
        moderate_threshold = st.slider(
            "Moderate Similarity Threshold (%)",
            min_value=50,
            max_value=80,
            value=70,
            help="Threshold for moderate plagiarism detection"
        )
        
        min_text_length = st.number_input(
            "Minimum Text Length (characters)",
            min_value=10,
            max_value=500,
            value=50,
            help="Minimum text length to consider for plagiarism"
        )
    
    # Algorithm weights
    st.write("**Algorithm Weights**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        exact_weight = st.slider("Exact Similarity Weight", 0.0, 1.0, 0.25, 0.05)
        tfidf_weight = st.slider("TF-IDF Weight", 0.0, 1.0, 0.25, 0.05)
    
    with col2:
        semantic_weight = st.slider("Semantic Weight", 0.0, 1.0, 0.30, 0.05)
        sequence_weight = st.slider("Sequence Weight", 0.0, 1.0, 0.15, 0.05)
    
    with col3:
        jaccard_weight = st.slider("Jaccard Weight", 0.0, 1.0, 0.05, 0.05)
        style_weight = st.slider("Writing Style Weight", 0.0, 1.0, 0.10, 0.05)
    
    # Save settings
    if st.button("💾 Save Settings"):
        settings = {
            'exact_threshold': exact_threshold,
            'high_threshold': high_threshold,
            'moderate_threshold': moderate_threshold,
            'min_text_length': min_text_length,
            'weights': {
                'exact_similarity': exact_weight,
                'tfidf_similarity': tfidf_weight,
                'semantic_similarity': semantic_weight,
                'sequence_similarity': sequence_weight,
                'jaccard_similarity': jaccard_weight,
                'writing_style': style_weight
            }
        }
        
        # Save to file
        os.makedirs("data/plagiarism_settings", exist_ok=True)
        with open("data/plagiarism_settings/config.json", 'w') as f:
            json.dump(settings, f, indent=2)
        
        st.success("Settings saved successfully!")

def generate_plagiarism_report(result):
    """Generate a detailed plagiarism report"""
    try:
        report_content = f"""
# Plagiarism Detection Report

## Case Summary
- **Detection Date**: {result['analysis_timestamp']}
- **Plagiarism Level**: {result['plagiarism_level']}
- **Overall Similarity Score**: {result['composite_score']}%

## Students Involved

### Student 1
- **Email**: {result['submission1_info']['student_email']}
- **Course**: {result['submission1_info']['course']}
- **Assignment**: {result['submission1_info']['title']}
- **Submission Date**: {result['submission1_info']['submission_date']}

### Student 2
- **Email**: {result['submission2_info']['student_email']}
- **Course**: {result['submission2_info']['course']}
- **Assignment**: {result['submission2_info']['title']}
- **Submission Date**: {result['submission2_info']['submission_date']}

## Similarity Analysis

### Detailed Scores
- **Exact Similarity**: {result['similarity_scores']['exact_similarity']}%
- **TF-IDF Similarity**: {result['similarity_scores']['tfidf_similarity']}%
- **Semantic Similarity**: {result['similarity_scores']['semantic_similarity']}%
- **Sequence Similarity**: {result['similarity_scores']['sequence_similarity']}%
- **Jaccard Similarity**: {result['similarity_scores']['jaccard_similarity']}%
- **Structural Similarity**: {result['structural_similarity']}%
- **Writing Style Similarity**: {result['writing_style_similarity']}%

## Common Phrases
{chr(10).join(f"- {phrase}" for phrase in result.get('common_phrases', []))}

## Recommendation
{result['description']}

---
*This report was generated automatically by the Grade-Flow Plagiarism Detection System*
        """
        
        # Provide download
        st.download_button(
            label="📥 Download Report",
            data=report_content,
            file_name=f"plagiarism_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
        
    except Exception as e:
        st.error(f"Error generating report: {e}")