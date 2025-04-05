import os
import json
import streamlit as st
import tempfile
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings

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

def update_submission_status(student_email, submission_type, course, title, status, evaluation_result=None):
    """Update the status of a submission in the submission record"""
    # Create a safe email identifier
    safe_email = student_email.replace('@', '_at_').replace('.', '_dot_')
    
    # Path to submission record
    record_path = f"data/submissions/{submission_type}/{safe_email}_{course}_submissions.json"
    
    if os.path.exists(record_path):
        try:
            with open(record_path, 'r') as f:
                submissions = json.load(f)
            
            # Find the submission and update its status
            for submission in submissions:
                if submission.get('Title') == title:
                    submission['Evaluation Status'] = status
                    
                    # Add evaluation details if provided
                    if evaluation_result:
                        submission['Score'] = evaluation_result.get('Score', 0)
                        submission['Feedback'] = {
                            'Strengths': evaluation_result.get('Strengths', ''),
                            'Areas for Improvement': evaluation_result.get('Areas for Improvement', '')
                        }
                        submission['Detailed Analysis'] = evaluation_result.get('Detailed Analysis', '')
            
            # Save updated submissions
            with open(record_path, 'w') as f:
                json.dump(submissions, f, indent=2)
                
        except Exception as e:
            print(f"Error updating submission status: {e}")