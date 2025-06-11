import os
import json
import hashlib
import streamlit as st
from datetime import datetime, timedelta
import uuid
import re


# User data directory
USER_DATA_DIR = "data/users"


def hash_password(password):
    """Hash a password for secure storage"""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_user(email, password):
    """Authenticate a user with email and password"""
    if not email or not password:
        return False

    user_file = os.path.join(USER_DATA_DIR, f"{email.replace('@', '_at_')}.json")

    if not os.path.exists(user_file):
        return False

    try:
        with open(user_file, "r") as f:
            user_data = json.load(f)

        hashed_password = hash_password(password)
        return user_data.get("password") == hashed_password
    except Exception as e:
        print(f"Authentication error: {e}")
        return False


def signup_user(email, password):
    """Register a new user"""
    if not email or not password:
        return False

    # Create user directory if it doesn't exist
    os.makedirs(USER_DATA_DIR, exist_ok=True)

    user_file = os.path.join(USER_DATA_DIR, f"{email.replace('@', '_at_')}.json")

    # Check if user already exists
    if os.path.exists(user_file):
        return False

    try:
        # Extract domain for organization
        domain_match = re.search(r"@(.+?)\.", email)
        if domain_match:
            organization = domain_match.group(1)
        else:
            organization = "unknown"

        # Determine role from email
        role = (
            "student"
            if is_student(email)
            else "teacher" if is_teacher(email) else "unknown"
        )

        user_data = {
            "email": email,
            "password": hash_password(password),
            "role": role,
            "organization": organization,
        }

        with open(user_file, "w") as f:
            json.dump(user_data, f)

        return True
    except Exception as e:
        print(f"Signup error: {e}")
        return False


def is_student(email):
    """Check if email belongs to a student"""
    return bool(re.search(r"@students\..*\.ac\.in$", email))


def is_teacher(email):
    """Check if email belongs to a teacher"""
    return bool(re.search(r"@faculty\..*\.ac\.in$", email))


def get_college_domain(email):
    """Extract college domain from email"""
    match = re.search(r"@(?:students|faculty)\.(.+?)\.ac\.in$", email)
    if match:
        return match.group(1)
    return None

def is_admin(email):
    """Check if the user is an admin based on email domain"""
    return email.endswith("@admin.pdpu.ac.in") or email.endswith("@admin.pdpu.ac.in")

def get_user_role(email):
    """Get user role based on email domain"""
    if is_admin(email):
        return "admin"
    elif is_teacher(email):
        return "teacher"
    elif is_student(email):
        return "student"
    else:
        return None

def create_session_token(email):
    """Create a unique session token for the user"""
    timestamp = datetime.now().isoformat()
    unique_id = str(uuid.uuid4())
    token_data = f"{email}_{timestamp}_{unique_id}"
    token = hashlib.sha256(token_data.encode()).hexdigest()
    return token

def save_session(email, user_role, token):
    """Save session data to persistent storage"""
    try:
        session_dir = "data/sessions"
        os.makedirs(session_dir, exist_ok=True)
        
        session_data = {
            "email": email,
            "user_role": user_role,
            "token": token,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),  # 7 days expiry
            "last_activity": datetime.now().isoformat()
        }
        
        session_file = os.path.join(session_dir, f"{token}.json")
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving session: {e}")
        return False

def load_session(token):
    """Load session data from persistent storage"""
    try:
        session_dir = "data/sessions"
        session_file = os.path.join(session_dir, f"{token}.json")
        
        if not os.path.exists(session_file):
            return None
        
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        # Check if session has expired
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if datetime.now() > expires_at:
            # Session expired, delete it
            os.remove(session_file)
            return None
        
        # Update last activity
        session_data["last_activity"] = datetime.now().isoformat()
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return session_data
    except Exception as e:
        print(f"Error loading session: {e}")
        return None

def delete_session(token):
    """Delete session data"""
    try:
        session_dir = "data/sessions"
        session_file = os.path.join(session_dir, f"{token}.json")
        
        if os.path.exists(session_file):
            os.remove(session_file)
        return True
    except Exception as e:
        print(f"Error deleting session: {e}")
        return False

def clean_expired_sessions():
    """Clean up expired session files"""
    try:
        session_dir = "data/sessions"
        if not os.path.exists(session_dir):
            return
        
        current_time = datetime.now()
        for filename in os.listdir(session_dir):
            if filename.endswith('.json'):
                session_file = os.path.join(session_dir, filename)
                try:
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    expires_at = datetime.fromisoformat(session_data["expires_at"])
                    if current_time > expires_at:
                        os.remove(session_file)
                except:
                    # If we can't read the file, delete it
                    os.remove(session_file)
    except Exception as e:
        print(f"Error cleaning expired sessions: {e}")

def extend_session(token, days=7):
    """Extend session expiry"""
    try:
        session_dir = "data/sessions"
        session_file = os.path.join(session_dir, f"{token}.json")
        
        if not os.path.exists(session_file):
            return False
        
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        # Extend expiry
        session_data["expires_at"] = (datetime.now() + timedelta(days=days)).isoformat()
        session_data["last_activity"] = datetime.now().isoformat()
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error extending session: {e}")
        return False
