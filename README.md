# 🎓 Grade Flow: Teacher's Assistant

An advanced application for evaluating student submissions using AI. This tool helps teachers efficiently grade assignments, exams, tests, and projects.

---

## ✨ Features

- 🔐 **Authentication**: Role-based access for students and teachers  
- 📤 **Student Interface**: Upload different types of submissions  
- 🧑‍🏫 **Teacher Interface**: Evaluate submissions based on custom criteria  
- 🤖 **AI-Powered Evaluation**: Automatic grading powered by Groq and Gemma-2 models  
- 🗂️ **Robust Vector Storage**: Efficient document storage and retrieval  
- 📊 **Detailed Reports**: Comprehensive feedback and performance analysis  
- 🧬 **Plagiarism Check**: Check for plagiarism across the platform (submitted and ongoing tests)  
- ⚙️ **Custom Plagiarism Settings**: Configure plagiarism check criteria based on institution or instructor preferences  
- 📈 **Advanced Data Insights**: Gain better insights into student performance and feedback  
- 🛠️ **Admin Panel**: Full-featured admin panel with monitoring and management tools  
- 📝 **Automated Question Paper Generation**: Generate tests automatically based on predefined templates and subjects  
- ⏱️ **Timed Test Environment**: Students can take tests in a timed and controlled environment  
- 🧑‍⚖️ **Manual Evaluation**: Teachers can evaluate timed tests and provide personalized feedback  
- 💾 **Efficient Deployment**: Deployed with optimized storage and resource management  

---

## ⚙️ Setup Instructions

### ✅ Prerequisites

- 🐍 Python 3.9+  
- 🔑 [Groq API Key](https://console.groq.com/)  
- 🔑 [Google API Key](https://console.cloud.google.com/)

---

### 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ai-teachers-assistant
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file** in the project root with your API keys:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GOOGLE_API_KEY=your_google_api_key_here
   ```

---

### 🚀 Running the Application

Launch the Streamlit app:
```bash
streamlit run app.py
```

The application will be available at 👉 [http://localhost:8501](http://localhost:8501)

---

## 👩‍🏫 Usage

### 🎓 For Students

1. Log in using your student email (format: `name@students.<college_name>.ac.in`)  
2. Submit your assignments, exams, tests, or projects  
3. View submission history and AI-generated evaluations  

### 🧑‍🏫 For Teachers

1. Log in using your faculty email (format: `name@faculty.<college_name>.ac.in`)  
2. Upload question papers and model answers  
3. Define custom evaluation criteria  
4. Evaluate student submissions with AI support  
5. View and download comprehensive reports  

---

## 🗂️ Project Structure

```
app.py                # Main application entry point  
auth.py               # Authentication functionality  
student_interface.py  # Student-specific interface  
teacher_interface.py  # Teacher-specific interface  
evaluation.py         # Core evaluation logic  
utils.py              # Utility functions  
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE)

---
