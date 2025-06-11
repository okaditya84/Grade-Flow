import os
import streamlit as st
from auth import (
    authenticate_user, signup_user, is_student, is_teacher, is_admin, get_user_role,
    create_session_token, save_session, load_session, delete_session, 
    clean_expired_sessions, extend_session
)
from student_interface import show_student_interface
from teacher_interface import show_teacher_interface
from admin_interface import show_admin_interface
from utils import setup_directories, load_css, update_active_tests
from dotenv import load_dotenv
import time

# Set page config - must be the first Streamlit command
st.set_page_config(
    page_title="Grade Flow",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load environment variables
load_dotenv()

# Setup session state with persistence
def init_session_state():
    """Initialize session state with persistence check"""
    
    # Clean up expired sessions on app start
    clean_expired_sessions()
    
    # Initialize basic session state variables
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "session_token" not in st.session_state:
        st.session_state.session_token = None
    if "last_activity_check" not in st.session_state:
        st.session_state.last_activity_check = time.time()
    
    # Check for existing session token in query params or cookies
    query_params = st.query_params
    stored_token = None
    
    # Try to get token from query params (fallback method)
    if "session_token" in query_params:
        stored_token = query_params["session_token"]
    
    # Try to get token from session state if not authenticated
    elif not st.session_state.authenticated and st.session_state.session_token:
        stored_token = st.session_state.session_token
    
    # If we have a stored token and user is not authenticated, try to restore session
    if stored_token and not st.session_state.authenticated:
        restore_session(stored_token)
    
    # Periodic session validation (every 5 minutes)
    current_time = time.time()
    if current_time - st.session_state.last_activity_check > 300:  # 5 minutes
        if st.session_state.authenticated and st.session_state.session_token:
            validate_and_extend_session()
        st.session_state.last_activity_check = current_time

def restore_session(token):
    """Restore user session from stored token"""
    try:
        session_data = load_session(token)
        if session_data:
            st.session_state.authenticated = True
            st.session_state.user_email = session_data["email"]
            st.session_state.user_role = session_data["user_role"]
            st.session_state.session_token = token
            
            # Update query params to maintain session
            st.query_params["session_token"] = token
            return True
        else:
            # Invalid or expired session
            clear_session_state()
            return False
    except Exception as e:
        st.error(f"Error restoring session: {e}")
        clear_session_state()
        return False

def validate_and_extend_session():
    """Validate current session and extend if valid"""
    try:
        if st.session_state.session_token:
            session_data = load_session(st.session_state.session_token)
            if session_data:
                # Session is valid, extend it
                extend_session(st.session_state.session_token)
                return True
            else:
                # Session is invalid or expired
                clear_session_state()
                st.rerun()
                return False
    except Exception as e:
        st.error(f"Error validating session: {e}")
        clear_session_state()
        return False

def clear_session_state():
    """Clear all session state variables"""
    if st.session_state.session_token:
        delete_session(st.session_state.session_token)
    
    # Clear query params
    st.query_params.clear()
    
    # Reset session state
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.user_email = None
    st.session_state.session_token = None

def create_persistent_session(email, user_role):
    """Create a persistent session for the user"""
    try:
        # Generate session token
        token = create_session_token(email)
        
        # Save session data
        if save_session(email, user_role, token):
            # Update session state
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.session_state.user_role = user_role
            st.session_state.session_token = token
            
            # Add token to query params for persistence
            st.query_params["session_token"] = token
            
            return True
        return False
    except Exception as e:
        st.error(f"Error creating session: {e}")
        return False

def main():
    # Initialize the application
    setup_directories()
    update_active_tests()
    load_css()
    init_session_state()

    # Display authentication page if not authenticated
    if not st.session_state.authenticated:
        show_auth_page()
    else:
        # Show appropriate interface based on user role
        show_main_interface()

def show_main_interface():
    """Show the main interface based on user role"""
    try:
        # Display session info in sidebar
        with st.sidebar:
            st.title(f"Welcome!")
            st.write(f"**Email:** {st.session_state.user_email}")
            st.write(f"**Role:** {st.session_state.user_role.title()}")
            
            # Session management
            st.markdown("---")
            st.subheader("Session Info")
            if st.session_state.session_token:
                session_data = load_session(st.session_state.session_token)
                if session_data:
                    from datetime import datetime
                    last_activity = datetime.fromisoformat(session_data["last_activity"])
                    expires_at = datetime.fromisoformat(session_data["expires_at"])
                    
                    st.write(f"**Last Activity:** {last_activity.strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**Session Expires:** {expires_at.strftime('%Y-%m-%d %H:%M')}")
            
            # Logout button
            st.markdown("---")
            if st.button("🚪 Logout", key="main_logout_btn"):
                logout_user()

            # Extend session button
            if st.button("🔄 Extend Session", key="extend_session_btn"):
                if extend_session(st.session_state.session_token, days=7):
                    st.success("Session extended by 7 days!")
                    st.rerun()
                else:
                    st.error("Failed to extend session")

        # Show appropriate interface
        if st.session_state.user_role == "student":
            show_student_interface()
        elif st.session_state.user_role == "teacher":
            show_teacher_interface()
        elif st.session_state.user_role == "admin":
            show_admin_interface()
        else:
            st.error("Unknown user role. Please log out and try again.")
            
    except Exception as e:
        st.error(f"Error loading interface: {e}")
        st.error("Please try logging out and logging in again.")

def logout_user():
    """Logout user and clear session"""
    clear_session_state()
    st.success("Logged out successfully!")
    st.rerun()

def show_auth_page():
    """Show authentication page"""
    st.title("🏫 Grade Flow 🏫")
    st.markdown("### Namaste!")
    st.markdown("*You are the future of India, and we are here to help you succeed!*")
    
    # Add session restoration notice
    if "session_token" in st.query_params:
        st.info("🔄 Attempting to restore your session...")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.subheader("Login")
        
        with st.form("login_form"):
            email = st.text_input("Email Address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            remember_me = st.checkbox("Remember me for 7 days", value=True)
            
            login_submitted = st.form_submit_button("Login")
            
            if login_submitted:
                if not email or not password:
                    st.error("Please enter both email and password.")
                elif authenticate_user(email, password):
                    # Determine user role
                    user_role = get_user_role(email)
                    if user_role:
                        # Create persistent session
                        if create_persistent_session(email, user_role):
                            st.success("Login successful! Session created.")
                            st.rerun()
                        else:
                            st.error("Login successful but failed to create session.")
                    else:
                        st.error("Invalid email domain. Please use your institutional email.")
                else:
                    st.error("Invalid email or password.")

    with tab2:
        st.subheader("Sign Up")
        
        with st.form("signup_form"):
            new_email = st.text_input("Email Address", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            
            signup_submitted = st.form_submit_button("Sign Up")
            
            if signup_submitted:
                if not new_email or not new_password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    # Validate email domain
                    user_role = get_user_role(new_email)
                    if not user_role:
                        st.error("Please use a valid institutional email address.")
                    elif signup_user(new_email, new_password):
                        st.success("Account created successfully! You can now log in.")
                    else:
                        st.error("Email already exists or signup failed.")

if __name__ == "__main__":
    main()