import os
import json
import streamlit as st
import tempfile
from datetime import datetime
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from utils import get_published_question_papers
from plagiarism_detector import PlagiarismDetector, PlagiarismDatabase

def update_submission_status(student_email, submission_type, course, title, status, evaluation_result=None):
    """Update the status of a submission in the submission record"""
    try:
        # Path to the student's main submission record that student interface reads
        record_path = f"data/submission_records/{student_email.replace('@', '_at_')}.json"
        
        # Load existing submission records or create new ones
        if os.path.exists(record_path):
            with open(record_path, 'r') as f:
                records = json.load(f)
        else:
            # If no records exist yet, initialize empty list
            records = []
        
        # Check if this submission already exists in records
        submission_found = False
        for record in records:
            if (record.get('Type', '').lower() == submission_type.lower() and
                record.get('Course') == course and
                record.get('Title') == title):
                
                # Update existing record
                record['Evaluation Status'] = status
                record['Status'] = "Evaluated" if status == "Evaluated" else record.get('Status', 'Submitted')
                
                # Add evaluation results if provided
                if evaluation_result:
                    if 'Score' in evaluation_result:
                        record['Score'] = evaluation_result['Score']
                    if 'Marks' in evaluation_result:
                        record['Marks'] = evaluation_result['Marks']
                    if 'Strengths' in evaluation_result:
                        record['Strengths'] = evaluation_result['Strengths']
                    if 'Areas for Improvement' in evaluation_result:
                        record['Areas for Improvement'] = evaluation_result['Areas for Improvement']
                    if 'Detailed Analysis' in evaluation_result:
                        record['Detailed Analysis'] = evaluation_result['Detailed Analysis']
                
                submission_found = True
                break
        
        # If submission not found in records, add a new one (this happens for platform tests)
        if not submission_found and submission_type.lower() == 'test':
            # For test submissions taken on platform, need to create a record
            new_record = {
                'Type': 'Test',
                'Course': course,
                'Title': title,
                'Submission Date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'File Path': f"data/submissions/test/{course}/{title}/{student_email.replace('@', '_at_')}.json",
                'Status': "Evaluated" if status == "Evaluated" else "Submitted",
                'Evaluation Status': status
            }
            
            # Add evaluation results if provided
            if evaluation_result:
                if 'Score' in evaluation_result:
                    new_record['Score'] = evaluation_result['Score']
                if 'Marks' in evaluation_result:
                    new_record['Marks'] = evaluation_result['Marks']
                if 'Strengths' in evaluation_result:
                    new_record['Strengths'] = evaluation_result['Strengths']
                if 'Areas for Improvement' in evaluation_result:
                    new_record['Areas for Improvement'] = evaluation_result['Areas for Improvement']
                if 'Detailed Analysis' in evaluation_result:
                    new_record['Detailed Analysis'] = evaluation_result['Detailed Analysis']
            
            records.append(new_record)
        
        # Save updated records
        os.makedirs(os.path.dirname(record_path), exist_ok=True)
        with open(record_path, 'w') as f:
            json.dump(records, f, indent=2)
        
        # Also update the test submission file directly if it's a test
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
    
    except Exception as e:
        print(f"Error updating submission status: {e}")
        return False

def evaluate_submissions(submission_type, course, question_paper, model_answer, evaluation_criteria, student_submissions):
    """Evaluate student submissions against question paper and model answers"""
    # Set up the LLM
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_key, model_name="Gemma2-9b-It")
    
    # Create temporary files for uploaded PDFs
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_q:
        temp_q.write(question_paper.read())
        question_path = temp_q.name
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_a:
        temp_a.write(model_answer.read())
        answer_path = temp_a.name
    
    try:
        # Load question paper and model answer
        question_loader = PyPDFLoader(question_path)
        question_docs = question_loader.load()
        
        answer_loader = PyPDFLoader(answer_path)
        answer_docs = answer_loader.load()
        
        # Process question and model answer
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        question_chunks = text_splitter.split_documents(question_docs)
        answer_chunks = text_splitter.split_documents(answer_docs)
        
        # Create embeddings and vector store for reference materials
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        reference_docs = question_chunks + answer_chunks
        reference_vectors = FAISS.from_documents(reference_docs, embeddings)
        
        # Create evaluation prompt template
        evaluation_prompt = ChatPromptTemplate.from_template(
            """You are an experienced educational evaluator tasked with grading student submissions.

### Reference Materials:
<question_paper>
{question_paper}
</question_paper>

<model_answer>
{model_answer}
</model_answer>

<evaluation_criteria>
{evaluation_criteria}
</evaluation_criteria>

### Student Submission:
<student_answer>
{student_answer}
</student_answer>

Please evaluate the student submission against the question paper, model answer, and given evaluation criteria.
Using confidence scoring: when a student shows excellence in difficult questions (worth more marks), be more lenient on minor mistakes in simpler questions.

Provide your evaluation in the following JSON format:

{{
"Score": <overall_score_out_of_100>,
"Strengths": "<summary_of_strengths>",
"Areas for Improvement": "<summary_of_weaknesses>",
"Detailed Analysis": "<paragraph_by_paragraph_or_question_by_question_analysis>",
"Confidence_Score": <a_number_from_0_to_10_indicating_your_confidence_in_this_evaluation>
}}
Ensure your evaluation is fair, constructive, and aligned with the evaluation criteria.
"""
        )
        # Evaluate each submission
        results = []
        
        for submission in student_submissions:
            student_email = submission.get('Student Email')
            title = submission.get('Title')
            submission_path = submission.get('File Path')
            
            # Skip if any required fields are missing
            if not student_email or not title or not submission_path:
                continue
            
            # Load student submission
            try:
                student_loader = PyPDFLoader(submission_path)
                student_docs = student_loader.load()
                student_chunks = text_splitter.split_documents(student_docs)
                
                # Combine all student chunks into a single text
                student_answer = "\n".join([doc.page_content for doc in student_chunks])
                
                # Extract just the content from question and answer documents for context
                question_paper_text = "\n".join([doc.page_content for doc in question_chunks])
                model_answer_text = "\n".join([doc.page_content for doc in answer_chunks])
                
                # Run the evaluation
                response = llm.invoke(
                    evaluation_prompt.format(
                        question_paper=question_paper_text,
                        model_answer=model_answer_text,
                        evaluation_criteria=evaluation_criteria,
                        student_answer=student_answer
                    )
                )
                
                # Extract JSON from response
                try:
                    # Find JSON content in response
                    response_text = response.content
                    json_start = response_text.find('```json') + 7 if '```json' in response_text else response_text.find('{')
                    json_end = response_text.rfind('```') if '```' in response_text else response_text.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_content = response_text[json_start:json_end].strip()
                        evaluation_result = json.loads(json_content)
                    else:
                        # Fallback if JSON parsing fails
                        evaluation_result = {
                            "Score": 0,
                            "Strengths": "Error parsing evaluation",
                            "Areas for Improvement": "Error parsing evaluation",
                            "Detailed Analysis": response_text,
                            "Confidence_Score": 0
                        }
                    
                    # Add student information
                    evaluation_result['Student'] = student_email.split('@')[0]
                    evaluation_result['Student Email'] = student_email
                    
                    # Store result
                    results.append(evaluation_result)
                    
                    # Save evaluation result
                    save_evaluation_result(
                        student_email, 
                        submission_type, 
                        course, 
                        title, 
                        evaluation_result
                    )
                    
                except Exception as e:
                    print(f"Error parsing evaluation for {student_email}: {e}")
                    results.append({
                        'Student': student_email.split('@')[0],
                        'Student Email': student_email,
                        'Score': 0,
                        'Strengths': "Error in evaluation",
                        'Areas for Improvement': "Error in evaluation",
                        'Detailed Analysis': f"An error occurred during evaluation: {str(e)}",
                        'Confidence_Score': 0
                    })
                
            except Exception as e:
                print(f"Error evaluating submission for {student_email}: {e}")
                results.append({
                    'Student': student_email.split('@')[0],
                    'Student Email': student_email,
                    'Score': 0,
                    'Strengths': "Error loading submission",
                    'Areas for Improvement': "Error loading submission",
                    'Detailed Analysis': f"An error occurred while loading the submission: {str(e)}",
                    'Confidence_Score': 0
                })
        
        return results
    
    finally:
        # Clean up temporary files
        try:
            os.unlink(question_path)
            os.unlink(answer_path)
        except:
            pass

def save_evaluation_result(student_email, submission_type, course, title, evaluation_result):
    """Save evaluation result to disk"""
    # Create directory structure
    base_dir = f"data/evaluations/{submission_type}/{course}"
    os.makedirs(base_dir, exist_ok=True)
    
    # Create a safe filename from title
    safe_title = "".join(c if c.isalnum() else "_" for c in title)
    
    # Create a safe email identifier
    safe_email = student_email.replace('@', '_at_').replace('.', '_dot_')
    
    # Save the evaluation result
    filename = f"{base_dir}/{safe_email}_{safe_title}_evaluation.json"
    
    with open(filename, 'w') as f:
        json.dump(evaluation_result, f, indent=2)
    
    # Update submission status to mark as evaluated
    update_submission_status(student_email, submission_type, course, title, "Completed", evaluation_result)


def evaluate_test_submissions(course_code, paper_title, submissions):
    """Evaluate test submissions against the published question paper with plagiarism detection"""
    # Set up the LLM
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_key, model_name="Gemma2-9b-It")
    
    # Initialize plagiarism detector
    plagiarism_detector = PlagiarismDetector()
    plagiarism_db = PlagiarismDatabase()
    
    try:
        # Get the published paper (with correct answers)
        published_papers = get_published_question_papers(course_code=course_code)
        paper_data = None
        
        for paper in published_papers:
            if paper["title"] == paper_title:
                paper_data = paper
                break
        
        if not paper_data:
            return [], "Question paper not found"
        
        # First, run plagiarism detection on all submissions
        st.info("🔍 Running plagiarism detection...")
        plagiarism_cases = []
        
        for i in range(len(submissions)):
            for j in range(i + 1, len(submissions)):
                # Skip same student comparisons
                if submissions[i].get('student_email') == submissions[j].get('student_email'):
                    continue
                
                result = plagiarism_detector.compare_submissions(submissions[i], submissions[j])
                
                if result and result['plagiarism_level'] in ['CRITICAL', 'HIGH', 'MODERATE']:
                    plagiarism_cases.append(result)
                    plagiarism_db.save_plagiarism_result(result)
        
        if plagiarism_cases:
            st.warning(f"⚠️ Found {len(plagiarism_cases)} potential plagiarism cases!")
            
            # Show plagiarism alert
            with st.expander("🚨 Plagiarism Alert - Click to view details"):
                for case in plagiarism_cases:
                    st.error(
                        f"**{case['plagiarism_level']} Similarity ({case['composite_score']}%)**: "
                        f"{case['submission1_info']['student_email'].split('@')[0]} vs "
                        f"{case['submission2_info']['student_email'].split('@')[0]}"
                    )
        
        # Evaluate each submission
        results = []
        
        for submission in submissions:
            student_email = submission.get('student_email')
            submission_date = submission.get('submission_date', 'Unknown')
            answers = submission.get('answers', {})
            
            if not student_email or not answers:
                continue
                
            # Calculate score based on correct answers
            total_marks = 0
            earned_marks = 0
            correct_count = 0
            incorrect_count = 0
            unanswered_count = 0
            
            # Analysis of each question/answer
            detailed_analysis = []
            
            # Check if this student is involved in plagiarism
            plagiarism_flag = any(
                student_email in [case['submission1_info']['student_email'], 
                                case['submission2_info']['student_email']]
                for case in plagiarism_cases
            )
            
            # Process each question
            for i, question in enumerate(paper_data["questions"]):
                q_key = f"q_{i}"
                student_answer = answers.get(q_key, "")
                correct_answer = question.get("correct_answer", "")
                max_marks = int(question.get("marks", 1))
                total_marks += max_marks
                
                # For unanswered questions
                if not student_answer or student_answer.strip() == "":
                    unanswered_count += 1
                    detailed_analysis.append(
                        f"Q{i+1}: No answer provided. (0/{max_marks} marks)"
                    )
                    continue
                
                # For multiple choice questions
                if question.get("question_type", "").lower() in ["multiple choice", "multiple_choice"]:
                    if student_answer == correct_answer:
                        earned_marks += max_marks
                        correct_count += 1
                        detailed_analysis.append(
                            f"Q{i+1}: Correct. Your answer matches the expected solution. ({max_marks}/{max_marks} marks)"
                        )
                    else:
                        incorrect_count += 1
                        detailed_analysis.append(
                            f"Q{i+1}: Incorrect. You selected '{student_answer}' but the correct answer is '{correct_answer}'. (0/{max_marks} marks)"
                        )
                
                # For true/false questions
                elif question.get("question_type", "").lower() in ["true/false", "true_false"]:
                    if student_answer.lower() == correct_answer.lower():
                        earned_marks += max_marks
                        correct_count += 1
                        detailed_analysis.append(
                            f"Q{i+1}: Correct. Your answer '{student_answer}' is correct. ({max_marks}/{max_marks} marks)"
                        )
                    else:
                        incorrect_count += 1
                        detailed_analysis.append(
                            f"Q{i+1}: Incorrect. You selected '{student_answer}' but the correct answer is '{correct_answer}'. (0/{max_marks} marks)"
                        )
                
                # For other question types, use LLM to evaluate
                else:
                    # Prepare prompt for evaluation
                    eval_prompt = f"""
                    Evaluate this student answer for a {question.get('question_type', 'short answer')} question.
                    
                    Question: {question.get('question_text', '')}
                    Correct Answer: {correct_answer}
                    Student Answer: {student_answer}
                    Max Marks: {max_marks}
                    
                    Evaluate how well the student answer matches the correct answer.
                    Return a JSON object with:
                    1. "marks_awarded": number between 0 and {max_marks} (integer)
                    2. "feedback": brief explanation of why these marks were awarded
                    """
                    
                    try:
                        response = llm.invoke(eval_prompt)
                        
                        # Extract marks and feedback from response
                        response_text = response.content
                        
                        # Try to find JSON in the response
                        import re
                        import json
                        
                        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                        if json_match:
                            try:
                                eval_result = json.loads(json_match.group(0))
                                marks_awarded = int(eval_result.get("marks_awarded", 0))
                                feedback = eval_result.get("feedback", "")
                                
                                # Cap marks at maximum possible
                                marks_awarded = min(marks_awarded, max_marks)
                                earned_marks += marks_awarded
                                
                                if marks_awarded == max_marks:
                                    correct_count += 1
                                elif marks_awarded > 0:
                                    # Partially correct
                                    pass
                                else:
                                    incorrect_count += 1
                                    
                                detailed_analysis.append(
                                    f"Q{i+1}: {feedback} ({marks_awarded}/{max_marks} marks)"
                                )
                            except:
                                # If JSON parsing fails, make a simple assessment
                                similarity_score = 0
                                if student_answer.lower() == correct_answer.lower():
                                    earned_marks += max_marks
                                    correct_count += 1
                                    detailed_analysis.append(
                                        f"Q{i+1}: Answer matches expected solution. ({max_marks}/{max_marks} marks)"
                                    )
                                else:
                                    # Give partial credit for non-empty answers
                                    partial_marks = max(1, max_marks // 2) if len(student_answer) > 20 else 0
                                    earned_marks += partial_marks
                                    if partial_marks > 0:
                                        detailed_analysis.append(
                                            f"Q{i+1}: Partial answer provided. ({partial_marks}/{max_marks} marks)"
                                        )
                                    else:
                                        incorrect_count += 1
                                        detailed_analysis.append(
                                            f"Q{i+1}: Answer does not match expected solution. (0/{max_marks} marks)"
                                        )
                        else:
                            # Simple evaluation if no JSON found
                            if student_answer.lower() == correct_answer.lower():
                                earned_marks += max_marks
                                correct_count += 1
                                detailed_analysis.append(
                                    f"Q{i+1}: Answer matches expected solution. ({max_marks}/{max_marks} marks)"
                                )
                            else:
                                incorrect_count += 1
                                detailed_analysis.append(
                                    f"Q{i+1}: Answer does not match expected solution. (0/{max_marks} marks)"
                                )
                                
                    except Exception as e:
                        # Fallback if LLM evaluation fails
                        print(f"Error in LLM evaluation: {e}")
                        # Simple evaluation
                        if student_answer.lower() == correct_answer.lower():
                            earned_marks += max_marks
                            correct_count += 1
                            detailed_analysis.append(
                                f"Q{i+1}: Answer matches expected solution. ({max_marks}/{max_marks} marks)"
                            )
                        else:
                            incorrect_count += 1
                            detailed_analysis.append(
                                f"Q{i+1}: Answer does not match expected solution. (0/{max_marks} marks)"
                            )
            
            # Calculate final score as percentage
            score = round((earned_marks / total_marks) * 100) if total_marks > 0 else 0
            
            # Generate overall feedback
            strengths = []
            areas_for_improvement = []
            
            if correct_count > 0:
                strengths.append(f"Correctly answered {correct_count} question(s).")
            
            if incorrect_count > 0:
                areas_for_improvement.append(f"Incorrectly answered {incorrect_count} question(s).")
            
            if unanswered_count > 0:
                areas_for_improvement.append(f"Did not attempt {unanswered_count} question(s).")
            
            # Add plagiarism warning to areas for improvement
            if plagiarism_flag:
                areas_for_improvement.insert(0, 
                    "⚠️ PLAGIARISM DETECTED: Significant similarity found with other submission(s). "
                    "This may affect your final grade."
                )
            
            # Prepare evaluation result
            evaluation_result = {
                'Student': student_email.split('@')[0],
                'Student Email': student_email,
                'Score': score,
                'Marks': f"{earned_marks}/{total_marks}",
                'Strengths': "; ".join(strengths),
                'Areas for Improvement': "; ".join(areas_for_improvement),
                'Detailed Analysis': "\n\n".join(detailed_analysis),
                'Confidence_Score': 10,  # High confidence since we're using exact matching for most cases
                'Plagiarism_Flag': plagiarism_flag,  # New field
                'Plagiarism_Cases': len([c for c in plagiarism_cases 
                                       if student_email in [c['submission1_info']['student_email'], 
                                                           c['submission2_info']['student_email']]])
            }
            
            # Save evaluation result
            save_evaluation_result(
                student_email, 
                "test", 
                course_code, 
                paper_title, 
                evaluation_result
            )
            
            # Update submission status
            update_submission_status(
                student_email,
                "test",
                course_code,
                paper_title,
                "Evaluated",
                evaluation_result
            )
            
            results.append(evaluation_result)
        
        return results, f"Evaluation completed successfully. Found {len(plagiarism_cases)} plagiarism cases."
    
    except Exception as e:
        print(f"Error evaluating test submissions: {e}")
        return [], f"Error: {str(e)}"

def save_evaluation_result(student_email, submission_type, course, title, evaluation_result):
    """Save evaluation result to disk"""
    try:
        # Create directory structure
        result_dir = f"data/evaluations/results/{submission_type}/{course}/{title}"
        os.makedirs(result_dir, exist_ok=True)
        
        # Save evaluation result
        filename = f"{result_dir}/{student_email.replace('@', '_at_')}.json"
        
        with open(filename, 'w') as f:
            json.dump(evaluation_result, f, indent=2)
        
        print(f"Evaluation result saved to {filename}")
        return True
    
    except Exception as e:
        print(f"Error saving evaluation result: {e}")
        return False    