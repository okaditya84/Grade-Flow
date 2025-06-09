import os
import json
import tempfile
import base64
from datetime import datetime
from fpdf import FPDF
import streamlit as st
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings


def generate_questions_from_reference(reference_pdf, course, topics, difficulty_level, num_questions, question_types):
    """Generate questions based on a reference PDF"""
    
    # Set up the LLM
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_key, model_name="Gemma2-9b-It")
    
    # Create a temporary file for the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_ref:
        temp_ref.write(reference_pdf.read())
        reference_path = temp_ref.name
    
    try:
        # Load reference document
        reference_loader = PyPDFLoader(reference_path)
        reference_docs = reference_loader.load()
        
        # Process reference material
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        reference_chunks = text_splitter.split_documents(reference_docs)
        
        # Extract content from reference for context
        reference_text = "\n".join([doc.page_content for doc in reference_chunks[:10]])  # Limit to first 10 chunks
        
        # Create question generation prompt
        question_prompt = ChatPromptTemplate.from_template(
            """You are an experienced educational question paper creator for the course {course}.

I need you to create {num_questions} questions on the following topics:
{topics}

Reference material for context:
{reference_text}

Requirements:
- Difficulty level: {difficulty_level} (on a scale where Easy is for basic understanding, Medium requires application of concepts, and Hard requires deep analysis)
- Question types to include: {question_types}
- Each question should have a clear marking scheme
- For multiple choice questions, include 4 options with one correct answer
- For numerical problems, include step-by-step solutions
- For theoretical questions, provide model answer points

Output Format (respond with only the following JSON structure, no explanations or other text):
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Question statement here",
      "question_type": "Multiple Choice",
      "marks": 5,
      "difficulty": "easy",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "The correct answer",
      "solution_steps": ["Step 1", "Step 2", "Step 3"]
    }}
  ]
}}

Ensure the questions are relevant to the topics, appropriately challenging for the specified difficulty, and clearly formulated. Make sure your response is properly formatted JSON.
"""
        )
        
        # Generate questions
        response = llm.invoke(
            question_prompt.format(
                course=course,
                topics=topics,
                difficulty_level=difficulty_level,
                num_questions=num_questions,
                question_types=question_types,
                reference_text=reference_text[:3000]  # Limit context length
            )
        )
        
        # Extract JSON from response
        response_text = response.content
        
        # Remove any markdown formatting and non-JSON content
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_content = response_text[json_start:json_end].strip()
            
            # Handle potential JSON errors with a more robust approach
            try:
                questions_data = json.loads(json_content)
                return questions_data
            except json.JSONDecodeError as e:
                # Try to clean the JSON string further if parsing failed
                import re
                clean_json = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'', json_content)
                try:
                    questions_data = json.loads(clean_json)
                    return questions_data
                except:
                    # If still failing, return error
                    return {"questions": [], "error": f"Failed to parse JSON: {str(e)}"}
        else:
            return {"questions": [], "error": "Failed to extract JSON from response"}
        
    except Exception as e:
        return {"questions": [], "error": f"Error generating questions: {str(e)}"}
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(reference_path)
        except:
            pass


def generate_questions_from_prompt(course, topics, difficulty_level, num_questions, question_types, custom_prompt):
    """Generate questions based on custom prompt"""
    
    # Set up the LLM
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_key, model_name="Gemma2-9b-It")
    
    try:
        # Create question generation prompt
        question_prompt = ChatPromptTemplate.from_template(
            """You are an experienced educational question paper creator for the course {course}.

I need you to create {num_questions} questions on the following topics:
{topics}

Custom instructions:
{custom_prompt}

Requirements:
- Difficulty level: {difficulty_level} (on a scale where Easy is for basic understanding, Medium requires application of concepts, and Hard requires deep analysis)
- Question types to include: {question_types}
- Each question should have a clear marking scheme
- For multiple choice questions, include 4 options with one correct answer
- For numerical problems, include step-by-step solutions
- For theoretical questions, provide model answer points

Output Format:
```json
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Question statement here",
      "question_type": "multiple_choice/numerical/theoretical/etc",
      "marks": 5,
      "difficulty": "easy/medium/hard",
      "options": ["Option A", "Option B", "Option C", "Option D"],  // include only for MCQs
      "correct_answer": "Correct answer or solution",
      "solution_steps": ["Step 1", "Step 2", "Step 3"]  // include for numerical problems
    }},
    // more questions...
  ]
}}
```

Ensure the questions are relevant to the topics, appropriately challenging for the specified difficulty, and clearly formulated.
"""
        )
        
        # Generate questions
        response = llm.invoke(
            question_prompt.format(
                course=course,
                topics=topics,
                difficulty_level=difficulty_level,
                num_questions=num_questions,
                question_types=question_types,
                custom_prompt=custom_prompt
            )
        )
        
        # Extract JSON from response
        response_text = response.content
        json_start = response_text.find('```json') + 7 if '```json' in response_text else response_text.find('{')
        json_end = response_text.rfind('```') if '```' in response_text else response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_content = response_text[json_start:json_end].strip()
            questions_data = json.loads(json_content)
            return questions_data
        else:
            return {"questions": [], "error": "Failed to parse generated questions"}
        
    except Exception as e:
        return {"questions": [], "error": f"Error generating questions: {str(e)}"}


def create_question_paper_pdf(questions, course_code, title, exam_date, duration, instructions, include_answers=False):
    """Create a PDF of the question paper"""
    try:
        class QuestionPaperPDF(FPDF):
            def header(self):
                # Set font
                self.set_font('Arial', 'B', 15)
                # Title
                self.cell(0, 10, title, 0, 1, 'C')
                # Course code
                self.set_font('Arial', '', 12)
                self.cell(0, 10, f"Course: {course_code}", 0, 1, 'C')
                # Date and duration
                self.cell(0, 10, f"Date: {exam_date} | Duration: {duration}", 0, 1, 'C')
                # Line break
                self.ln(10)
                
            def footer(self):
                # Position at 1.5 cm from bottom
                self.set_y(-15)
                # Arial italic 8
                self.set_font('Arial', 'I', 8)
                # Page number
                self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')
        
        # Create PDF object
        pdf = QuestionPaperPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Instructions
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Instructions:", 0, 1)
        pdf.set_font('Arial', '', 10)
        
        # Split instructions into lines
        instructions_lines = instructions.split('\n')
        for line in instructions_lines:
            pdf.multi_cell(0, 5, line)
        
        pdf.ln(5)
        
        # Questions
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "Questions:", 0, 1)
        
        for q in questions["questions"]:
            # Question number and marks
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 10, f"Q{q['question_number']} ({q['marks']} marks) [{q['difficulty']}]", 0, 1)
            
            # Question text
            pdf.set_font('Arial', '', 11)
            pdf.multi_cell(0, 5, q['question_text'])
            
            # Options for MCQs
            if 'options' in q and q['options']:
                pdf.ln(2)
                for i, option in enumerate(q['options']):
                    pdf.multi_cell(0, 5, f"({chr(97+i)}) {option}")
            
            pdf.ln(5)
        
        # If answers are to be included
        if include_answers:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Answer Key", 0, 1, 'C')
            pdf.ln(5)
            
            for q in questions["questions"]:
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 10, f"Q{q['question_number']} ({q['marks']} marks)", 0, 1)
                
                pdf.set_font('Arial', '', 11)
                pdf.multi_cell(0, 5, f"Answer: {q['correct_answer']}")
                
                if 'solution_steps' in q and q['solution_steps']:
                    pdf.ln(2)
                    pdf.set_font('Arial', 'I', 10)
                    pdf.cell(0, 5, "Solution steps:", 0, 1)
                    pdf.set_font('Arial', '', 10)
                    for step in q['solution_steps']:
                        pdf.multi_cell(0, 5, f"• {step}")
                
                pdf.ln(5)
        
        # Save the PDF to a temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"question_paper_{course_code}_{timestamp}.pdf"
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        pdf.output(pdf_path)
        
        # Read the PDF as bytes for download
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Clean up
        os.unlink(pdf_path)
        
        return pdf_bytes, pdf_filename
    
    except Exception as e:
        raise Exception(f"Error creating PDF: {str(e)}")


def save_question_paper(course_code, title, questions_data, include_answers=False):
    """Save the question paper to disk"""
    try:
        # Create directory structure
        base_dir = f"data/question_papers/{course_code}"
        os.makedirs(base_dir, exist_ok=True)
        
        # Create safe filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in title)
        filename = f"{base_dir}/{safe_title}_{timestamp}.json"
        
        # Prepare data to save
        save_data = {
            "title": title,
            "course": course_code,
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "questions": questions_data["questions"],
            "include_answers": include_answers
        }
        
        # Save to disk
        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        return True
    
    except Exception as e:
        print(f"Error saving question paper: {e}")
        return False

def publish_question_paper(course_code, title, questions_data, deadline, instructions, include_answers=False, time_limit=None):
    """
    Publish a question paper for students to access
    
    Args:
        course_code: Course code
        title: Test title
        questions_data: Question paper data
        deadline: Submission deadline date string (YYYY-MM-DD)
        instructions: Test instructions
        include_answers: Whether to include answers (always False for students)
        time_limit: Time limit in minutes (optional)
    """
    try:
        # Create directory structure
        base_dir = f"data/published_papers/{course_code}"
        os.makedirs(base_dir, exist_ok=True)
        
        # Create safe filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in title)
        filename = f"{base_dir}/{safe_title}_{timestamp}.json"
        
        # Prepare data to save
        publish_data = {
            "title": title,
            "course": course_code,
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "deadline": deadline,
            "instructions": instructions,
            "questions": questions_data["questions"],
            "include_answers": False,  # Never show answers to students
            "status": "active",  # active or archived
            "time_limit": time_limit  # Time limit in minutes
        }
        
        # Save to disk
        with open(filename, 'w') as f:
            json.dump(publish_data, f, indent=2)
        
        print(f"Question paper published successfully to {filename}")
        return True
    
    except Exception as e:
        print(f"Error publishing question paper: {e}")
        return False