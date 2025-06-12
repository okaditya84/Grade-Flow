import os
import streamlit as st
import streamlit.components.v1 as components
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
import json

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
    if "view" not in st.session_state:
        st.session_state.view = "landing"
    if "ui_rendered" not in st.session_state:
        st.session_state.ui_rendered = False
    
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
    st.session_state.view = "landing"
    st.session_state.ui_rendered = False

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

def logout_user():
    """Logout user and clear session"""
    clear_session_state()
    st.success("Logged out successfully!")
    st.rerun()

def show_enhanced_landing_page():
    """Show the enhanced HTML landing page with authentication"""
    
    # Clear any existing components first
    components.html("", height=0)
    
    # Prevent multiple renderings of the landing page
    if st.session_state.get("ui_rendered", False) and not st.query_params.get("auth_action"):
        return
    
    st.session_state.ui_rendered = True
    
    # If we have a session token in query params but not in URL, redirect to include it
    if st.session_state.session_token and "session_token" not in st.query_params:
        st.query_params["session_token"] = st.session_state.session_token
        st.rerun()
    # Hide Streamlit UI elements
    st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
        }
        .main {
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        .stApp {
            background: #00171F !important; /* match your UI background */
        }
        header, [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, .stDecoration {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }
        iframe {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100% !important;
            border: none !important;
            z-index: 9999 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Check for authentication parameters from HTML form
    # Check for authentication parameters from HTML form
    query_params = st.query_params
    auth_action = query_params.get("auth_action")
    auth_data_str = query_params.get("auth_data")
    
    # Check for auth results to display
    auth_result = query_params.get("auth_result")
    auth_message = query_params.get("auth_message")
    
    if auth_action and auth_data_str:
        try:
            # Parse the auth data
            auth_data = json.loads(auth_data_str)
            
            # Process the authentication
            if auth_action == 'login':
                email = auth_data.get('email', '').strip()
                password = auth_data.get('password', '')
                
                if not email or not password:
                    st.query_params.clear()
                    st.query_params["auth_result"] = "error"
                    st.query_params["auth_message"] = "Please fill in all fields"
                    st.session_state.ui_rendered = False  # Force re-render
                    st.rerun()
                    return
                
                if authenticate_user(email, password):
                    # Determine user role
                    user_role = get_user_role(email)
                    if user_role:
                        # Create persistent session
                        if create_persistent_session(email, user_role):
                            # Clear auth params and redirect to authenticated state
                            st.query_params.clear()
                            st.rerun()
                            return
                        else:
                            st.query_params.clear()
                            st.query_params["auth_result"] = "error"
                            st.query_params["auth_message"] = "Login successful but failed to create session."
                            st.session_state.ui_rendered = False  # Force re-render
                            st.rerun()
                            return
                    else:
                        st.query_params.clear()
                        st.query_params["auth_result"] = "error"
                        st.query_params["auth_message"] = "Invalid email domain. Please use your institutional email."
                        st.session_state.ui_rendered = False  # Force re-render
                        st.rerun()
                        return
                else:
                    st.query_params.clear()
                    st.query_params["auth_result"] = "error"
                    st.query_params["auth_message"] = "Invalid email or password."
                    st.session_state.ui_rendered = False  # Force re-render
                    st.rerun()
                    return
            
            elif auth_action == 'signup':
                email = auth_data.get('email', '').strip()
                password = auth_data.get('password', '')
                confirm_password = auth_data.get('confirmPassword', '')
                
                if not all([email, password, confirm_password]):
                    st.query_params.clear()
                    st.query_params["auth_result"] = "error"
                    st.query_params["auth_message"] = "Please fill in all fields"
                    st.session_state.ui_rendered = False  # Force re-render
                    st.rerun()
                    return
                
                if password != confirm_password:
                    st.query_params.clear()
                    st.query_params["auth_result"] = "error"
                    st.query_params["auth_message"] = "Passwords do not match!"
                    st.session_state.ui_rendered = False  # Force re-render
                    st.rerun()
                    return
                
                # Validate email domain
                user_role = get_user_role(email)
                if not user_role:
                    st.query_params.clear()
                    st.query_params["auth_result"] = "error"
                    st.query_params["auth_message"] = "Please use a valid institutional email address."
                    st.session_state.ui_rendered = False  # Force re-render
                    st.rerun()
                    return
                
                if signup_user(email, password):
                    st.query_params.clear()
                    st.query_params["auth_result"] = "success"
                    st.query_params["auth_message"] = "Account created successfully! You can now login."
                    st.session_state.ui_rendered = False  # Force re-render
                    st.rerun()
                    return
                else:
                    st.query_params.clear()
                    st.query_params["auth_result"] = "error"
                    st.query_params["auth_message"] = "Email already exists or signup failed."
                    st.session_state.ui_rendered = False  # Force re-render
                    st.rerun()
                    return
                    
        except Exception as e:
            st.query_params.clear()
            st.query_params["auth_result"] = "error"
            st.query_params["auth_message"] = f"Error processing request: {str(e)}"
            st.session_state.ui_rendered = False  # Force re-render
            st.rerun()
            return
    
    # Only render HTML if we're not processing authentication
    if not st.session_state.authenticated:
        try:
            with open("UI/landing2.html", "r", encoding="utf-8") as f:
                html = f.read()
            
            # Inject auth result messages into HTML if they exist
            if auth_result and auth_message:
                # Add JavaScript to show the message
                message_script = f"""
                <script>
                window.addEventListener('load', function() {{
                    const messageType = '{auth_result}';
                    const messageText = {json.dumps(auth_message)};
                    
                    // Create or update message element
                    let messageEl = document.getElementById('auth-message');
                    if (!messageEl) {{
                        messageEl = document.createElement('div');
                        messageEl.id = 'auth-message';
                        messageEl.style.position = 'fixed';
                        messageEl.style.top = '20px';
                        messageEl.style.left = '50%';
                        messageEl.style.transform = 'translateX(-50%)';
                        messageEl.style.padding = '15px 20px';
                        messageEl.style.borderRadius = '8px';
                        messageEl.style.fontWeight = 'bold';
                        messageEl.style.zIndex = '10000';
                        messageEl.style.maxWidth = '400px';
                        messageEl.style.textAlign = 'center';
                        document.body.appendChild(messageEl);
                    }}
                    
                    if (messageType === 'error') {{
                        messageEl.style.backgroundColor = '#fee2e2';
                        messageEl.style.color = '#dc2626';
                        messageEl.style.border = '1px solid #fecaca';
                    }} else if (messageType === 'success') {{
                        messageEl.style.backgroundColor = '#dcfce7';
                        messageEl.style.color = '#16a34a';
                        messageEl.style.border = '1px solid #bbf7d0';
                    }}
                    
                    messageEl.textContent = messageText;
                    messageEl.style.display = 'block';
                    
                    // Hide message after 5 seconds
                    setTimeout(function() {{
                        if (messageEl) {{
                            messageEl.style.display = 'none';
                        }}
                    }}, 5000);
                }});
                </script>
                """
                # Inject the script before closing body tag
                html = html.replace('</body>', message_script + '</body>')
                
                # Clear the message params after injecting
                st.query_params.clear()
                
            # Render the HTML in a full-screen iframe
            components.html(html, height=0, scrolling=True)
                
        except FileNotFoundError:
            st.error("Could not find UI/landing2.html file")
            if st.button("Go to Login Page"):
                st.session_state.view = "auth"
                st.rerun()
                
def show_auth_page():
    """Fallback authentication page with basic Streamlit UI"""
    # Add a back button
    if st.button("← Back to Home"):
        st.session_state.view = "landing"
        st.session_state.ui_rendered = False
        st.rerun()
    
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

def show_main_interface():
    """Show the main interface based on user role"""
    try:
        # Hide sidebar and streamlit elements for authenticated users using HTML interface
        if st.session_state.view == "landing":
            st.markdown("""
            <style>
                /* Hide sidebar completely */
                .css-1d391kg, .css-1lcbmhc, .css-1cypcdb, .css-17eq0hr, .css-1rs6os, .css-17lntkn, 
                [data-testid="stSidebar"], .css-1oe5cao, .e1fqkh3o0, .css-6qob1r, .css-1lcbmhc {
                    display: none !important;
                    visibility: hidden !important;
                    width: 0 !important;
                }
                /* Hide header elements */
                header, [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, .stDecoration {
                    display: none !important;
                    visibility: hidden !important;
                    height: 0 !important;
                }
                /* Ensure main content takes full width */
                .main .block-container {
                    max-width: 100% !important;
                    width: 100% !important;
                    padding: 0 !important;
                }
                .main {
                    padding: 0 !important;
                }
            </style>
            """, unsafe_allow_html=True)
        else:
            # Display session info in sidebar for fallback auth
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

def main():
    # Initialize the application
    setup_directories()
    update_active_tests()
    load_css()
    init_session_state()

    # Display authentication page if not authenticated
    if not st.session_state.authenticated:
        if st.session_state.view == "landing":
            show_enhanced_landing_page()
        elif st.session_state.view == "auth":
            show_auth_page()  # Keep the old auth page as fallback
    else:
        # Prevent enhanced landing from rendering again
        if st.session_state.view == "landing":
            st.session_state.view = "main"
            st.session_state.ui_rendered = False
        
        # Show the appropriate interface based on user role
        show_main_interface()

if __name__ == "__main__":
    main()