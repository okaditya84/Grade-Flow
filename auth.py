import os
import json
import hashlib
import re
import streamlit as st

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
