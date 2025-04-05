# Grade Flow: Teacher's Assitant
An advanced application for evaluating student submissions using AI. This tool helps teachers efficiently grade assignments, exams, tests, and projects.

## Features

- **Authentication**: Role-based access for students and teachers
- **Student Interface**: Upload submissions of different types
- **Teacher Interface**: Evaluate submissions based on custom criteria
- **AI-Powered Evaluation**: Automatic evaluation using Groq and Gemma-2 models
- **Robust Vector Storage**: Efficient document storage and retrieval
- **Detailed Reports**: Comprehensive feedback and analysis

## Setup Instructions

### Prerequisites

- Python 3.9+
- [Groq API Key](https://console.groq.com/)
- [Google API Key](https://console.cloud.google.com/)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ai-teachers-assistant
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with your API keys:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   GOOGLE_API_KEY=your_google_api_key_here
   ```

### Running the Application

Launch the Streamlit application:
```bash
streamlit run app.py
```

The application will be available at http://localhost:8501

## Usage

### For Students
1. Log in with your student email (format: name@students.college.ac.in)
2. Submit your assignments, exams, tests, or projects
3. View your submission history and evaluations

### For Teachers
1. Log in with your faculty email (format: name@faculty.college.ac.in)
2. Upload question papers and model answers
3. Define evaluation criteria
4. Evaluate student submissions
5. View and download reports

## Project Structure

- `app.py`: Main application entry point
- `auth.py`: Authentication functionality
- `student_interface.py`: Student-specific functionality
- `teacher_interface.py`: Teacher-specific functionality
- `evaluation.py`: Evaluation logic
- `utils.py`: Utility functions

## License

[MIT License](LICENSE)

