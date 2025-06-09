import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from utils import get_student_submissions, save_evaluation_criteria
from evaluation import evaluate_submissions
from question_paper_generator import (
    generate_questions_from_reference, 
    generate_questions_from_prompt,
    create_question_paper_pdf,
    save_question_paper
)


def show_teacher_interface():
    st.title("Teacher Dashboard")

    # Create tabs for different teacher functionalities
    tabs = st.tabs(
        [
            "Evaluate Tests",
            "Evaluate Assignments",
            "Evaluate Exams",
            "Evaluate Projects",
            "Generate Question Papers",  # New tab
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
        
    with tabs[4]:  # New tab for question paper generation
        show_question_paper_generation_interface()


def show_evaluation_interface(submission_type):
    # Existing code - unchanged
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
    
    # Course information
    course_code = st.text_input("Course Code")
    title = st.text_input("Exam/Test Title")
    
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
            with st.expander(f"Question {i+1} ({question['marks']} marks)"):
                # Question text
                question_text = st.text_area(
                    "Question Text", 
                    value=question["question_text"],
                    key=f"q_text_{i}"
                )
                
                # Question metadata
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    question_type = st.selectbox(
                        "Question Type",
                        options=["Multiple Choice", "Short Answer", "Long Answer", "Numerical", "True/False"],
                        index=["Multiple Choice", "Short Answer", "Long Answer", "Numerical", "True/False"].index(
                            question["question_type"] if question["question_type"] in ["Multiple Choice", "Short Answer", "Long Answer", "Numerical", "True/False"] else "Short Answer"
                        ),
                        key=f"q_type_{i}"
                    )
                
                with col2:
                    marks = st.number_input(
                        "Marks",
                        min_value=1,
                        max_value=20,
                        value=int(question["marks"]),
                        key=f"q_marks_{i}"
                    )
                
                with col3:
                    difficulty = st.select_slider(
                        "Difficulty",
                        options=["Easy", "Medium", "Hard"],
                        value=question["difficulty"].capitalize() if question["difficulty"] in ["easy", "medium", "hard"] else "Medium",
                        key=f"q_diff_{i}"
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
                    "correct_answer": correct_answer
                }
                
                if question_type == "Multiple Choice":
                    edited_question["options"] = options
                
                if question_type == "Numerical" and solution_steps:
                    edited_question["solution_steps"] = solution_steps
                
                edited_questions.append(edited_question)
        
        # Update the questions data
        questions_data["questions"] = edited_questions
        st.session_state.generated_questions = questions_data
        
        # Generate PDF button
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Generate PDF", key="gen_pdf_btn"):
                try:
                    # Create PDF
                    pdf_bytes, pdf_filename = create_question_paper_pdf(
                        questions_data,
                        course_code,
                        title,
                        exam_date.strftime("%Y-%m-%d"),
                        duration,
                        instructions,
                        include_answers
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
        
        # Reset button
        if st.button("Clear and Start Over", key="reset_btn"):
            if "generated_questions" in st.session_state:
                del st.session_state.generated_questions
            if "pdf_bytes" in st.session_state:
                del st.session_state.pdf_bytes
            if "pdf_filename" in st.session_state:
                del st.session_state.pdf_filename
            st.rerun()
