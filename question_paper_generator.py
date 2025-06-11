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
    """Generate questions based on a reference PDF with proper school format"""
    
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
        reference_text = "\n".join([doc.page_content for doc in reference_chunks[:10]])
        
        # Create enhanced question generation prompt for school format
        question_prompt = ChatPromptTemplate.from_template(
            """You are an experienced school question paper creator for {course}.

Create a well-structured question paper with {num_questions} questions on these topics:
{topics}

Reference material for context:
{reference_text}

IMPORTANT REQUIREMENTS:
1. Create questions in THREE sections following school format:
   - Section A: Objective Questions (MCQs, True/False, Fill in blanks) - 1 mark each
   - Section B: Short Answer Questions - 3-5 marks each  
   - Section C: Long Answer Questions - 6-10 marks each

2. Distribute questions across sections based on difficulty:
   - Easy questions: Section A
   - Medium questions: Section B
   - Hard questions: Section C

3. Question types to include: {question_types}
4. Overall difficulty level: {difficulty_level}

5. For each question include:
   - Clear question text
   - Appropriate marks allocation
   - Chapter/unit reference if possible
   - For MCQs: 4 options with one correct answer
   - For descriptive questions: key points for model answer

6. Ensure questions test different cognitive levels:
   - Knowledge/Recall (Section A)
   - Understanding/Application (Section B)
   - Analysis/Synthesis (Section C)

Output Format (JSON only, no explanations):
{{
  "paper_info": {{
    "subject": "{course}",
    "total_marks": 0,
    "sections": {{
      "section_a": {{"questions": 0, "marks_per_question": 1, "total_marks": 0}},
      "section_b": {{"questions": 0, "marks_per_question": 4, "total_marks": 0}},
      "section_c": {{"questions": 0, "marks_per_question": 8, "total_marks": 0}}
    }}
  }},
  "questions": [
    {{
      "question_number": 1,
      "section": "A",
      "question_text": "Question statement here",
      "question_type": "Multiple Choice",
      "marks": 1,
      "difficulty": "easy",
      "chapter_unit": "Chapter 1: Introduction",
      "cognitive_level": "Knowledge",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Brief explanation why this is correct"
    }}
  ]
}}

Create a balanced question paper that properly evaluates student understanding across all cognitive levels.
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
                reference_text=reference_text[:3000]
            )
        )
        
        # Extract JSON from response
        response_text = response.content
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_content = response_text[json_start:json_end].strip()
            
            try:
                questions_data = json.loads(json_content)
                
                # Calculate paper info if not provided
                if "paper_info" not in questions_data:
                    questions_data["paper_info"] = calculate_paper_info(questions_data["questions"])
                
                return questions_data
            except json.JSONDecodeError as e:
                import re
                clean_json = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'', json_content)
                try:
                    questions_data = json.loads(clean_json)
                    if "paper_info" not in questions_data:
                        questions_data["paper_info"] = calculate_paper_info(questions_data["questions"])
                    return questions_data
                except:
                    return {"questions": [], "error": f"Failed to parse JSON: {str(e)}"}
        else:
            return {"questions": [], "error": "Failed to extract JSON from response"}
        
    except Exception as e:
        return {"questions": [], "error": f"Error generating questions: {str(e)}"}
    
    finally:
        try:
            os.unlink(reference_path)
        except:
            pass

def generate_questions_from_prompt(course, topics, difficulty_level, num_questions, question_types, custom_prompt):
    """Generate questions based on custom prompt with proper school format"""
    
    # Set up the LLM
    groq_api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(groq_api_key=groq_api_key, model_name="Gemma2-9b-It")
    
    try:
        # Enhanced question generation prompt
        question_prompt = ChatPromptTemplate.from_template(
            """You are an experienced school question paper creator for {course}.

Create a well-structured question paper with {num_questions} questions on these topics:
{topics}

Custom Instructions: {custom_prompt}

IMPORTANT REQUIREMENTS:
1. Create questions in THREE sections following school format:
   - Section A: Objective Questions (MCQs, True/False, Fill in blanks) - 1 mark each
   - Section B: Short Answer Questions - 3-5 marks each  
   - Section C: Long Answer Questions - 6-10 marks each

2. Distribute questions across sections based on difficulty:
   - Easy questions: Section A
   - Medium questions: Section B
   - Hard questions: Section C

3. Question types to include: {question_types}
4. Overall difficulty level: {difficulty_level}

5. For each question include:
   - Clear question text
   - Appropriate marks allocation
   - Chapter/unit reference if possible
   - For MCQs: 4 options with one correct answer
   - For descriptive questions: key points for model answer

Output Format (JSON only):
{{
  "paper_info": {{
    "subject": "{course}",
    "total_marks": 0,
    "sections": {{
      "section_a": {{"questions": 0, "marks_per_question": 1, "total_marks": 0}},
      "section_b": {{"questions": 0, "marks_per_question": 4, "total_marks": 0}},
      "section_c": {{"questions": 0, "marks_per_question": 8, "total_marks": 0}}
    }}
  }},
  "questions": [
    {{
      "question_number": 1,
      "section": "A",
      "question_text": "Question statement here",
      "question_type": "Multiple Choice",
      "marks": 1,
      "difficulty": "easy",
      "chapter_unit": "Chapter 1: Introduction",
      "cognitive_level": "Knowledge",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Brief explanation"
    }}
  ]
}}
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
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_content = response_text[json_start:json_end].strip()
            questions_data = json.loads(json_content)
            
            # Calculate paper info if not provided
            if "paper_info" not in questions_data:
                questions_data["paper_info"] = calculate_paper_info(questions_data["questions"])
            
            return questions_data
        else:
            return {"questions": [], "error": "Failed to parse generated questions"}
        
    except Exception as e:
        return {"questions": [], "error": f"Error generating questions: {str(e)}"}

def calculate_paper_info(questions):
    """Calculate paper information from questions"""
    sections = {"section_a": {"questions": 0, "marks_per_question": 1, "total_marks": 0},
                "section_b": {"questions": 0, "marks_per_question": 4, "total_marks": 0},
                "section_c": {"questions": 0, "marks_per_question": 8, "total_marks": 0}}
    
    total_marks = 0
    
    for q in questions:
        section = q.get("section", "A").lower()
        marks = int(q.get("marks", 1))
        total_marks += marks
        
        if section == "a":
            sections["section_a"]["questions"] += 1
            sections["section_a"]["total_marks"] += marks
        elif section == "b":
            sections["section_b"]["questions"] += 1
            sections["section_b"]["total_marks"] += marks
        elif section == "c":
            sections["section_c"]["questions"] += 1
            sections["section_c"]["total_marks"] += marks
    
    return {
        "total_marks": total_marks,
        "sections": sections
    }

def create_question_paper_pdf(questions_data, course_code, title, exam_date, duration, instructions, include_answers=False, school_info=None):
    """Create a properly formatted school question paper PDF"""
    try:
        class SchoolQuestionPaperPDF(FPDF):
            def header(self):
                # School header
                self.set_font('Arial', 'B', 16)
                school_name = school_info.get('school_name', 'SCHOOL NAME') if school_info else 'SCHOOL NAME'
                self.cell(0, 10, school_name, 0, 1, 'C')
                
                # Academic year
                self.set_font('Arial', '', 12)
                academic_year = school_info.get('academic_year', '2024-2025') if school_info else '2024-2025'
                self.cell(0, 8, f"Academic Year: {academic_year}", 0, 1, 'C')
                
                # Horizontal line
                self.ln(5)
                self.line(10, self.get_y(), 200, self.get_y())
                self.ln(5)
                
                # Paper details
                self.set_font('Arial', 'B', 12)
                
                # Create a table-like structure for paper details
                paper_details = [
                    [f"Class/Grade: {school_info.get('grade', 'Grade X') if school_info else 'Grade X'}", f"Subject: {course_code}"],
                    [f"Time: {duration}", f"Total Marks: {questions_data.get('paper_info', {}).get('total_marks', 'XX')}"],
                    [f"Date: {exam_date}", f"Paper Code: {title}-SET-A"]
                ]
                
                for row in paper_details:
                    self.cell(95, 8, row[0], 1, 0, 'L')
                    self.cell(95, 8, row[1], 1, 1, 'L')
                
                self.ln(5)
            
            def footer(self):
                self.set_y(-15)
                self.set_font('Arial', 'I', 8)
                self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')
        
        # Create PDF object
        pdf = SchoolQuestionPaperPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Instructions section
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, "General Instructions:", 0, 1)
        pdf.set_font('Arial', '', 10)
        
        # Default instructions if not provided
        if not instructions:
            instructions = """1. All questions are compulsory unless stated otherwise.
2. Marks for each question are indicated on the right.
3. Write your answers neatly and clearly.
4. Draw diagrams wherever necessary and label them properly.
5. Read all questions carefully before answering.
6. Maintain the order of questions in your answer sheet."""
        
        instructions_lines = instructions.split('\n')
        for line in instructions_lines:
            if line.strip():
                pdf.multi_cell(0, 5, line.strip())
        
        pdf.ln(5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Section-wise questions
        questions = questions_data.get("questions", [])
        current_section = None
        
        # Group questions by section
        sections = {"A": [], "B": [], "C": []}
        for q in questions:
            section = q.get("section", "A").upper()
            sections[section].append(q)
        
        section_info = {
            "A": {"title": "Section A: Objective Questions", "subtitle": "(1 Mark each)"},
            "B": {"title": "Section B: Short Answer Questions", "subtitle": "(3-5 Marks each)"},
            "C": {"title": "Section C: Long Answer Questions", "subtitle": "(6-10 Marks each)"}
        }
        
        for section_key in ["A", "B", "C"]:
            if sections[section_key]:
                # Section header
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, section_info[section_key]["title"], 0, 1)
                pdf.set_font('Arial', 'I', 10)
                pdf.cell(0, 6, section_info[section_key]["subtitle"], 0, 1)
                pdf.ln(3)
                
                # Questions in this section
                for q in sections[section_key]:
                    pdf.set_font('Arial', 'B', 11)
                    
                    # Question number and marks
                    marks_text = f"({q.get('marks', 1)} Mark{'s' if q.get('marks', 1) > 1 else ''})"
                    question_header = f"Q{q.get('question_number', '')}. "
                    
                    # Chapter/Unit info if available
                    if q.get('chapter_unit'):
                        question_header += f"[{q.get('chapter_unit')}] "
                    
                    pdf.cell(0, 8, f"{question_header}{marks_text}", 0, 1)
                    
                    # Question text
                    pdf.set_font('Arial', '', 11)
                    pdf.multi_cell(0, 6, q.get('question_text', ''))
                    
                    # Options for MCQs
                    if q.get('question_type', '').lower() in ['multiple choice', 'mcq'] and q.get('options'):
                        pdf.ln(2)
                        for i, option in enumerate(q['options']):
                            pdf.cell(0, 5, f"({chr(97+i)}) {option}", 0, 1)
                    
                    # Space for answer (more space for higher mark questions)
                    if section_key == "A":
                        pdf.ln(3)
                    elif section_key == "B":
                        pdf.ln(8)
                        pdf.set_font('Arial', 'I', 9)
                        pdf.cell(0, 4, f"(Answer in about {q.get('marks', 4) * 20} words)", 0, 1)
                    else:  # Section C
                        pdf.ln(12)
                        pdf.set_font('Arial', 'I', 9)
                        pdf.cell(0, 4, f"(Answer in about {q.get('marks', 8) * 25} words)", 0, 1)
                    
                    pdf.ln(2)
                
                # Section separator
                pdf.ln(5)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(5)
        
        # Evaluation table
        pdf.add_page()
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, "Question Paper Analysis", 0, 1, 'C')
        pdf.ln(5)
        
        # Create evaluation table
        paper_info = questions_data.get('paper_info', {})
        sections_info = paper_info.get('sections', {})
        
        pdf.set_font('Arial', 'B', 10)
        # Table headers
        pdf.cell(40, 8, "Section", 1, 0, 'C')
        pdf.cell(60, 8, "Type of Questions", 1, 0, 'C')
        pdf.cell(30, 8, "No. of Questions", 1, 0, 'C')
        pdf.cell(30, 8, "Marks per Q", 1, 0, 'C')
        pdf.cell(30, 8, "Total Marks", 1, 1, 'C')
        
        # Table data
        pdf.set_font('Arial', '', 10)
        section_data = [
            ["A", "Objective (MCQ, T/F, Fill)", str(sections_info.get('section_a', {}).get('questions', 0)), "1", str(sections_info.get('section_a', {}).get('total_marks', 0))],
            ["B", "Short Answer", str(sections_info.get('section_b', {}).get('questions', 0)), "3-5", str(sections_info.get('section_b', {}).get('total_marks', 0))],
            ["C", "Long Answer", str(sections_info.get('section_c', {}).get('questions', 0)), "6-10", str(sections_info.get('section_c', {}).get('total_marks', 0))],
            ["", "TOTAL", str(sum([sections_info.get(f'section_{s}', {}).get('questions', 0) for s in ['a', 'b', 'c']])), "", str(paper_info.get('total_marks', 0))]
        ]
        
        for row in section_data:
            for i, cell in enumerate(row):
                if i == 0:
                    pdf.cell(40, 8, cell, 1, 0, 'C')
                elif i == 1:
                    pdf.cell(60, 8, cell, 1, 0, 'C')
                else:
                    pdf.cell(30, 8, cell, 1, 0, 'C')
            pdf.ln()
        
        # Answer key section
        if include_answers:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, "Answer Key & Marking Scheme", 0, 1, 'C')
            pdf.ln(5)
            
            for q in questions:
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 8, f"Q{q.get('question_number', '')}. Answer: ({q.get('marks', 1)} Mark{'s' if q.get('marks', 1) > 1 else ''})", 0, 1)
                
                pdf.set_font('Arial', '', 11)
                pdf.multi_cell(0, 6, q.get('correct_answer', ''))
                
                if q.get('explanation'):
                    pdf.set_font('Arial', 'I', 10)
                    pdf.multi_cell(0, 5, f"Explanation: {q.get('explanation', '')}")
                
                pdf.ln(3)
        
        # Save the PDF
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
            "paper_info": questions_data.get("paper_info", {}),
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
    """Publish a question paper for students to access"""
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
            "paper_info": questions_data.get("paper_info", {}),
            "include_answers": False,
            "status": "active",
            "time_limit": time_limit
        }
        
        # Save to disk
        with open(filename, 'w') as f:
            json.dump(publish_data, f, indent=2)
        
        print(f"Question paper published successfully to {filename}")
        return True
    
    except Exception as e:
        print(f"Error publishing question paper: {e}")
        return False