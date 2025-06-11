import os
import json
import hashlib
import numpy as np
from datetime import datetime
from collections import defaultdict
import difflib
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
import textstat
import spacy

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class PlagiarismDetector:
    def __init__(self):
        # Initialize the sentence transformer model for semantic similarity
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Load spaCy model for advanced text processing
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("SpaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Initialize stopwords
        self.stop_words = set(stopwords.words('english'))
        
        # Plagiarism thresholds
        self.EXACT_MATCH_THRESHOLD = 0.95  # 95% similarity for exact matches
        self.HIGH_SIMILARITY_THRESHOLD = 0.85  # 85% similarity for high plagiarism
        self.MODERATE_SIMILARITY_THRESHOLD = 0.70  # 70% similarity for moderate plagiarism
        self.MINIMUM_TEXT_LENGTH = 50  # Minimum characters to consider for plagiarism
        
    def preprocess_text(self, text):
        """Advanced text preprocessing for better comparison"""
        if not text or len(text.strip()) < self.MINIMUM_TEXT_LENGTH:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespaces and normalize
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common formatting patterns
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
        text = re.sub(r'\d+', '', text)  # Remove numbers (for text-based answers)
        
        # Remove stopwords for better semantic comparison
        words = word_tokenize(text)
        filtered_words = [word for word in words if word not in self.stop_words and len(word) > 2]
        
        return ' '.join(filtered_words)
    
    def calculate_similarity_scores(self, text1, text2):
        """Calculate multiple similarity scores using different algorithms"""
        if not text1 or not text2:
            return {
                'exact_similarity': 0.0,
                'tfidf_similarity': 0.0,
                'semantic_similarity': 0.0,
                'sequence_similarity': 0.0,
                'jaccard_similarity': 0.0
            }
        
        # Preprocess texts
        processed_text1 = self.preprocess_text(text1)
        processed_text2 = self.preprocess_text(text2)
        
        if not processed_text1 or not processed_text2:
            return {
                'exact_similarity': 0.0,
                'tfidf_similarity': 0.0,
                'semantic_similarity': 0.0,
                'sequence_similarity': 0.0,
                'jaccard_similarity': 0.0
            }
        
        scores = {}
        
        # 1. Exact string similarity (after preprocessing)
        scores['exact_similarity'] = difflib.SequenceMatcher(None, processed_text1, processed_text2).ratio()
        
        # 2. TF-IDF Cosine Similarity
        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 3), max_features=1000)
            tfidf_matrix = vectorizer.fit_transform([processed_text1, processed_text2])
            scores['tfidf_similarity'] = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except:
            scores['tfidf_similarity'] = 0.0
        
        # 3. Semantic Similarity using Sentence Transformers
        try:
            embeddings1 = self.sentence_model.encode([processed_text1])
            embeddings2 = self.sentence_model.encode([processed_text2])
            scores['semantic_similarity'] = cosine_similarity(embeddings1, embeddings2)[0][0]
        except:
            scores['semantic_similarity'] = 0.0
        
        # 4. Sequence-based similarity (for detecting rearranged content)
        scores['sequence_similarity'] = self.calculate_sequence_similarity(processed_text1, processed_text2)
        
        # 5. Jaccard Similarity (word-level overlap)
        scores['jaccard_similarity'] = self.calculate_jaccard_similarity(processed_text1, processed_text2)
        
        return scores
    
    def calculate_sequence_similarity(self, text1, text2):
        """Calculate similarity based on common subsequences"""
        words1 = text1.split()
        words2 = text2.split()
        
        if not words1 or not words2:
            return 0.0
        
        # Find longest common subsequence
        def lcs_length(X, Y):
            m, n = len(X), len(Y)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if X[i-1] == Y[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            
            return dp[m][n]
        
        lcs_len = lcs_length(words1, words2)
        max_len = max(len(words1), len(words2))
        
        return lcs_len / max_len if max_len > 0 else 0.0
    
    def calculate_jaccard_similarity(self, text1, text2):
        """Calculate Jaccard similarity coefficient"""
        set1 = set(text1.split())
        set2 = set(text2.split())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def detect_structural_similarity(self, text1, text2):
        """Detect structural similarities (sentence patterns, etc.)"""
        sentences1 = sent_tokenize(text1)
        sentences2 = sent_tokenize(text2)
        
        if len(sentences1) != len(sentences2):
            return 0.0
        
        sentence_similarities = []
        for s1, s2 in zip(sentences1, sentences2):
            similarity = difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
            sentence_similarities.append(similarity)
        
        return np.mean(sentence_similarities) if sentence_similarities else 0.0
    
    def analyze_writing_style(self, text):
        """Analyze writing style characteristics"""
        if not text or len(text) < 100:
            return {}
        
        return {
            'avg_sentence_length': textstat.avg_sentence_length(text),
            'flesch_reading_ease': textstat.flesch_reading_ease(text),
            'avg_syllables_per_word': textstat.avg_syllables_per_word(text),
            'sentence_count': textstat.sentence_count(text),
            'word_count': len(text.split())
        }
    
    def calculate_composite_score(self, similarity_scores, writing_style_similarity=0.0):
        """Calculate a weighted composite plagiarism score"""
        weights = {
            'exact_similarity': 0.25,
            'tfidf_similarity': 0.25,
            'semantic_similarity': 0.30,
            'sequence_similarity': 0.15,
            'jaccard_similarity': 0.05
        }
        
        composite_score = sum(
            similarity_scores.get(metric, 0.0) * weight 
            for metric, weight in weights.items()
        )
        
        # Add writing style similarity bonus
        composite_score += writing_style_similarity * 0.1
        
        return min(composite_score, 1.0)  # Cap at 1.0
    
    def determine_plagiarism_level(self, composite_score, similarity_scores):
        """Determine the level of plagiarism based on scores"""
        if composite_score >= self.EXACT_MATCH_THRESHOLD:
            return "CRITICAL", "Extremely high similarity - Likely exact copy or minimal changes"
        elif composite_score >= self.HIGH_SIMILARITY_THRESHOLD:
            return "HIGH", "High similarity detected - Significant plagiarism suspected"
        elif composite_score >= self.MODERATE_SIMILARITY_THRESHOLD:
            return "MODERATE", "Moderate similarity - Possible plagiarism or common source"
        elif composite_score >= 0.50:
            return "LOW", "Low similarity - May share common concepts or sources"
        else:
            return "NONE", "No significant similarity detected"
    
    def compare_submissions(self, submission1, submission2):
        """Compare two submissions and return detailed plagiarism analysis"""
        try:
            # Extract text content from submissions
            text1 = self.extract_text_from_submission(submission1)
            text2 = self.extract_text_from_submission(submission2)
            
            if not text1 or not text2:
                return None
            
            # Check minimum length requirement
            if len(text1) < self.MINIMUM_TEXT_LENGTH or len(text2) < self.MINIMUM_TEXT_LENGTH:
                return None
            
            # Calculate similarity scores
            similarity_scores = self.calculate_similarity_scores(text1, text2)
            
            # Analyze writing styles
            style1 = self.analyze_writing_style(text1)
            style2 = self.analyze_writing_style(text2)
            writing_style_similarity = self.compare_writing_styles(style1, style2)
            
            # Calculate composite score
            composite_score = self.calculate_composite_score(similarity_scores, writing_style_similarity)
            
            # Determine plagiarism level
            level, description = self.determine_plagiarism_level(composite_score, similarity_scores)
            
            # Calculate additional metrics
            structural_similarity = self.detect_structural_similarity(text1, text2)
            
            return {
                'submission1_info': self.get_submission_info(submission1),
                'submission2_info': self.get_submission_info(submission2),
                'plagiarism_level': level,
                'description': description,
                'composite_score': round(composite_score * 100, 2),
                'similarity_scores': {k: round(v * 100, 2) for k, v in similarity_scores.items()},
                'structural_similarity': round(structural_similarity * 100, 2),
                'writing_style_similarity': round(writing_style_similarity * 100, 2),
                'analysis_timestamp': datetime.now().isoformat(),
                'text_lengths': {
                    'submission1': len(text1),
                    'submission2': len(text2)
                },
                'common_phrases': self.find_common_phrases(text1, text2)
            }
            
        except Exception as e:
            print(f"Error comparing submissions: {e}")
            return None
    
    def compare_writing_styles(self, style1, style2):
        """Compare writing style characteristics"""
        if not style1 or not style2:
            return 0.0
        
        try:
            # Calculate normalized differences for each metric
            differences = []
            
            for metric in ['avg_sentence_length', 'flesch_reading_ease', 'avg_syllables_per_word']:
                if metric in style1 and metric in style2:
                    val1, val2 = style1[metric], style2[metric]
                    if val1 != 0 and val2 != 0:
                        diff = 1 - abs(val1 - val2) / max(val1, val2)
                        differences.append(max(0, diff))
            
            return np.mean(differences) if differences else 0.0
            
        except:
            return 0.0
    
    def find_common_phrases(self, text1, text2, min_length=5):
        """Find common phrases between two texts"""
        words1 = text1.split()
        words2 = text2.split()
        
        common_phrases = []
        
        # Look for common n-grams
        for n in range(min_length, min(len(words1), len(words2)) + 1):
            for i in range(len(words1) - n + 1):
                phrase1 = ' '.join(words1[i:i+n])
                for j in range(len(words2) - n + 1):
                    phrase2 = ' '.join(words2[j:j+n])
                    if phrase1 == phrase2:
                        common_phrases.append(phrase1)
                        break
        
        # Remove duplicates and return top matches
        unique_phrases = list(set(common_phrases))
        return sorted(unique_phrases, key=len, reverse=True)[:5]
    
    def extract_text_from_submission(self, submission):
        """Extract text content from submission based on type"""
        try:
            if isinstance(submission, dict):
                # For test submissions (JSON format)
                if 'answers' in submission:
                    answers = submission['answers']
                    if isinstance(answers, dict):
                        # Combine all answers into one text
                        return ' '.join(str(answer) for answer in answers.values() if answer)
                    return str(answers)
                
                # For other submission types
                if 'content' in submission:
                    return submission['content']
                if 'text' in submission:
                    return submission['text']
                
                # Try to find any text field
                for key, value in submission.items():
                    if isinstance(value, str) and len(value) > 50:
                        return value
            
            elif isinstance(submission, str):
                return submission
                
            return ""
            
        except Exception as e:
            print(f"Error extracting text from submission: {e}")
            return ""
    
    def get_submission_info(self, submission):
        """Extract submission metadata"""
        try:
            if isinstance(submission, dict):
                return {
                    'student_email': submission.get('student_email', 'Unknown'),
                    'course': submission.get('course', 'Unknown'),
                    'title': submission.get('title', 'Unknown'),
                    'submission_date': submission.get('submission_date', 'Unknown'),
                    'type': submission.get('type', 'Unknown')
                }
            return {
                'student_email': 'Unknown',
                'course': 'Unknown',
                'title': 'Unknown',
                'submission_date': 'Unknown',
                'type': 'Unknown'
            }
        except:
            return {}

class PlagiarismDatabase:
    """Database manager for plagiarism detection results"""
    
    def __init__(self):
        self.db_path = "data/plagiarism_results"
        os.makedirs(self.db_path, exist_ok=True)
    
    def save_plagiarism_result(self, result):
        """Save plagiarism detection result"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"plagiarism_result_{timestamp}.json"
            filepath = os.path.join(self.db_path, filename)
            
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving plagiarism result: {e}")
            return False
    
    def get_plagiarism_results(self, course=None, level=None, limit=None):
        """Retrieve plagiarism results with optional filtering"""
        results = []
        
        try:
            for filename in os.listdir(self.db_path):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.db_path, filename)
                    try:
                        with open(filepath, 'r') as f:
                            result = json.load(f)
                        
                        # Apply filters
                        if course and result.get('submission1_info', {}).get('course') != course:
                            continue
                        
                        if level and result.get('plagiarism_level') != level:
                            continue
                        
                        results.append(result)
                    except:
                        continue
            
            # Sort by composite score (highest first)
            results.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
            
            if limit:
                results = results[:limit]
            
            return results
            
        except Exception as e:
            print(f"Error retrieving plagiarism results: {e}")
            return []
    
    def get_student_plagiarism_history(self, student_email):
        """Get plagiarism history for a specific student"""
        results = []
        
        try:
            for filename in os.listdir(self.db_path):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.db_path, filename)
                    try:
                        with open(filepath, 'r') as f:
                            result = json.load(f)
                        
                        # Check if student is involved in this plagiarism case
                        student1 = result.get('submission1_info', {}).get('student_email', '')
                        student2 = result.get('submission2_info', {}).get('student_email', '')
                        
                        if student_email in [student1, student2]:
                            results.append(result)
                    except:
                        continue
            
            return sorted(results, key=lambda x: x.get('analysis_timestamp', ''), reverse=True)
            
        except Exception as e:
            print(f"Error retrieving student plagiarism history: {e}")
            return []

def run_plagiarism_detection_batch(course=None, submission_type=None):
    """Run plagiarism detection on all submissions"""
    detector = PlagiarismDetector()
    db = PlagiarismDatabase()
    
    # Collect all submissions
    submissions = collect_all_submissions(course, submission_type)
    
    results = []
    total_comparisons = len(submissions) * (len(submissions) - 1) // 2
    current_comparison = 0
    
    print(f"Starting plagiarism detection for {len(submissions)} submissions...")
    print(f"Total comparisons to perform: {total_comparisons}")
    
    # Compare each submission with every other submission
    for i in range(len(submissions)):
        for j in range(i + 1, len(submissions)):
            current_comparison += 1
            
            # Skip comparing submissions from the same student
            if submissions[i].get('student_email') == submissions[j].get('student_email'):
                continue
            
            print(f"Comparing {current_comparison}/{total_comparisons}...")
            
            result = detector.compare_submissions(submissions[i], submissions[j])
            
            if result and result['plagiarism_level'] in ['CRITICAL', 'HIGH', 'MODERATE']:
                # Save significant plagiarism cases
                db.save_plagiarism_result(result)
                results.append(result)
    
    print(f"Plagiarism detection completed. Found {len(results)} potential cases.")
    return results

def collect_all_submissions(course=None, submission_type=None):
    """Collect all submissions from the system"""
    submissions = []
    
    # Collect test submissions
    if not submission_type or submission_type == 'test':
        submissions.extend(collect_test_submissions(course))
    
    # Collect other submission types
    submission_types = ['assignment', 'exam', 'project']
    if submission_type and submission_type in submission_types:
        submission_types = [submission_type]
    
    for sub_type in submission_types:
        if not submission_type or submission_type == sub_type:
            submissions.extend(collect_regular_submissions(sub_type, course))
    
    return submissions

def collect_test_submissions(course=None):
    """Collect all test submissions"""
    submissions = []
    
    try:
        base_path = "data/submissions/test"
        if not os.path.exists(base_path):
            return submissions
        
        for course_dir in os.listdir(base_path):
            if course and course_dir != course:
                continue
                
            course_path = os.path.join(base_path, course_dir)
            if not os.path.isdir(course_path):
                continue
            
            for test_dir in os.listdir(course_path):
                test_path = os.path.join(course_path, test_dir)
                if not os.path.isdir(test_path):
                    continue
                
                for submission_file in os.listdir(test_path):
                    if submission_file.endswith('.json'):
                        submission_path = os.path.join(test_path, submission_file)
                        try:
                            with open(submission_path, 'r') as f:
                                submission = json.load(f)
                            
                            submission['course'] = course_dir
                            submission['title'] = test_dir
                            submission['type'] = 'test'
                            submission['file_path'] = submission_path
                            
                            submissions.append(submission)
                        except:
                            continue
    
    except Exception as e:
        print(f"Error collecting test submissions: {e}")
    
    return submissions

def collect_regular_submissions(submission_type, course=None):
    """Collect regular submissions (assignment, exam, project)"""
    submissions = []
    
    try:
        # Read from submission records
        if os.path.exists("data/submission_records"):
            for filename in os.listdir("data/submission_records"):
                if filename.endswith('.json'):
                    file_path = os.path.join("data/submission_records", filename)
                    try:
                        with open(file_path, 'r') as f:
                            records = json.load(f)
                        
                        student_email = filename.replace('_at_', '@').replace('.json', '')
                        
                        for record in records:
                            if record.get('Type', '').lower() == submission_type:
                                if course and record.get('Course') != course:
                                    continue
                                
                                # Try to read the actual submission content
                                submission_path = record.get('File Path', '')
                                content = ""
                                
                                if submission_path and os.path.exists(submission_path):
                                    # For PDF files, we'd need to extract text
                                    # For now, we'll use the evaluation content if available
                                    pass
                                
                                submission = {
                                    'student_email': student_email,
                                    'course': record.get('Course', ''),
                                    'title': record.get('Title', ''),
                                    'submission_date': record.get('Submission Date', ''),
                                    'type': submission_type,
                                    'content': content,
                                    'file_path': submission_path
                                }
                                
                                submissions.append(submission)
                    except:
                        continue
    
    except Exception as e:
        print(f"Error collecting {submission_type} submissions: {e}")
    
    return submissions