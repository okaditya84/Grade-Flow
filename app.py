import os
import streamlit as st
import streamlit.components.v1 as components
# from streamlit_javascript import st_javascript
from auth import authenticate_user, signup_user, is_student, is_teacher
from student_interface import show_student_interface
from teacher_interface import show_teacher_interface
from utils import setup_directories, load_css
from dotenv import load_dotenv
import time
import json
import urllib.parse

st.set_page_config(
    page_title="Grade Flow",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()

def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "college_domain" not in st.session_state:
        st.session_state.college_domain = None
    if "view" not in st.session_state:
        st.session_state.view = "landing"
    if "auth_result" not in st.session_state:
        st.session_state.auth_result = None
    if "auth_message" not in st.session_state:
        st.session_state.auth_message = None

def handle_auth_request(auth_data):
    """Handle authentication requests from the HTML frontend"""
    action = auth_data.get('action')
    data = auth_data.get('data', {})
    
    if action == 'login':
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return {"success": False, "message": "Please fill in all fields"}
        
        if authenticate_user(email, password):
            st.session_state.authenticated = True
            st.session_state.user_email = email
            
            if is_student(email):
                st.session_state.user_role = "student"
            elif is_teacher(email):
                st.session_state.user_role = "teacher"
            else:
                return {"success": False, "message": "Invalid institutional email."}
            
            return {"success": True, "message": "Login successful! Redirecting...", "role": st.session_state.user_role}
        else:
            return {"success": False, "message": "Invalid credentials. Please try again."}
    
    elif action == 'signup':
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirmPassword', '')
        
        if not all([email, password, confirm_password]):
            return {"success": False, "message": "Please fill in all fields"}
        
        if password != confirm_password:
            return {"success": False, "message": "Passwords do not match!"}
        
        if not (is_student(email) or is_teacher(email)):
            return {"success": False, "message": "Please use your institutional email."}
        
        if signup_user(email, password):
            return {"success": True, "message": "Account created successfully! You can now login."}
        else:
            return {"success": False, "message": "Email already registered or error creating account."}
    
    return {"success": False, "message": "Invalid request"}

# def main():
#     setup_directories()
#     load_css()
#     init_session_state()
    
#     if not st.session_state.authenticated:
#         if st.session_state.view == "landing":
#             show_enhanced_landing_page()
#         elif st.session_state.view == "auth":
#             show_auth_page()  # Keep the old auth page as fallback
#     else:
#         # Prevent enhanced landing from rendering again
#         if st.session_state.view == "landing":
#             st.session_state.view = "main"
#             st.session_state.ui_rendered = False
#         # Show the appropriate interface based on user role
#         if st.session_state.user_role == "student":
#             show_student_interface()
#         elif st.session_state.user_role == "teacher":
#             show_teacher_interface()
#         else:
#             st.error("Unknown user role. Please log out and try again.")

#         st.sidebar.title(f"Welcome, {st.session_state.user_email}")
#         if st.sidebar.button("Logout"):
#             # Clear all session state
#             for key in list(st.session_state.keys()):
#                 del st.session_state[key]
#             # Reinitialize session state
#             init_session_state()
#             # Clear any URL parameters
#             st.query_params.clear()
#             # Reset UI rendered flag
#             st.session_state.ui_rendered = False
#             st.rerun()

def main():
    setup_directories()
    load_css()
    init_session_state()
    
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
        
        # Hide sidebar and streamlit elements for authenticated users
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
        
        # Show the appropriate interface based on user role
        if st.session_state.user_role == "student":
            show_student_interface()
        elif st.session_state.user_role == "teacher":
            show_teacher_interface()
        else:
            st.error("Unknown user role. Please log out and try again.")

        # Note: Sidebar is now hidden, logout is handled within the HTML interface

# def show_enhanced_landing_page():
#     # Prevent multiple renderings of the landing page
#     if st.session_state.get("ui_rendered", False):
#         return
#     st.session_state.ui_rendered = True
#     # Hide Streamlit UI elements
#     st.markdown("""
#     <style>
#         .block-container {
#         padding-top: 0rem !important;
#         padding-bottom: 0rem !important;
#         padding-left: 0rem !important;
#         padding-right: 0rem !important;
#     }
#     .main {
#         padding-left: 0rem !important;
#         padding-right: 0rem !important;
#         padding-top: 0rem !important;
#         padding-bottom: 0rem !important;
#     }
#     .stApp {
#         background: #00171F !important; /* match your UI background */
#     }
#     header, [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, .stDecoration {
#         display: none !important;
#         visibility: hidden !important;
#         height: 0 !important;
#     }
#     </style>
#     """, unsafe_allow_html=True)
    
#     # Check for simple auth parameters
#     query_params = st.query_params
#     auth_action = query_params.get("auth_action")
#     auth_data_str = query_params.get("auth_data")
    
#     if auth_action and auth_data_str:
#         try:
#             # Parse the auth data
#             auth_data = json.loads(auth_data_str)
            
#             # Process the authentication
#             if auth_action == 'login':
#                 email = auth_data.get('email', '').strip()
#                 password = auth_data.get('password', '')
                
#                 if authenticate_user(email, password):
#                     st.session_state.authenticated = True
#                     st.session_state.user_email = email
                    
#                     if is_student(email):
#                         st.session_state.user_role = "student"
#                     elif is_teacher(email):
#                         st.session_state.user_role = "teacher"
#                     else:
#                         # Redirect with error
#                         st.query_params.clear()
#                         st.query_params["auth_result"] = "error"
#                         st.query_params["auth_message"] = "Invalid institutional email."
#                         st.rerun()
#                         return
                    
#                     # Clear auth params and redirect to authenticated state
#                     st.query_params.clear()
#                     st.rerun()
#                     return
#                 else:
#                     # Redirect with error
#                     st.query_params.clear()
#                     st.query_params["auth_result"] = "error"
#                     st.query_params["auth_message"] = "Invalid credentials. Please try again."
#                     st.rerun()
#                     return
            
#             elif auth_action == 'signup':
#                 email = auth_data.get('email', '').strip()
#                 password = auth_data.get('password', '')
#                 confirm_password = auth_data.get('confirmPassword', '')
                
#                 if password != confirm_password:
#                     st.query_params.clear()
#                     st.query_params["auth_result"] = "error"
#                     st.query_params["auth_message"] = "Passwords do not match!"
#                     st.rerun()
#                     return
                
#                 if not (is_student(email) or is_teacher(email)):
#                     st.query_params.clear()
#                     st.query_params["auth_result"] = "error"
#                     st.query_params["auth_message"] = "Please use your institutional email."
#                     st.rerun()
#                     return
                
#                 if signup_user(email, password):
#                     st.query_params.clear()
#                     st.query_params["auth_result"] = "success"
#                     st.query_params["auth_message"] = "Account created successfully! You can now login."
#                     st.rerun()
#                     return
#                 else:
#                     st.query_params.clear()
#                     st.query_params["auth_result"] = "error"
#                     st.query_params["auth_message"] = "Email already registered or error creating account."
#                     st.rerun()
#                     return
                    
#         except Exception as e:
#             st.query_params.clear()
#             st.query_params["auth_result"] = "error"
#             st.query_params["auth_message"] = f"Error processing request: {str(e)}"
#             st.rerun()
#             return
    
#     # Only render HTML if we're not processing authentication
#     # This prevents the HTML from being rendered multiple times
#     if not st.session_state.authenticated:
#         try:
#             with open("UI/index.html", "r", encoding="utf-8") as f:
#                 html = f.read()
                
#             components.html(html, height=800, scrolling=False)
                
#         except FileNotFoundError:
#             st.error("Could not find UI/index.html file")
#             if st.button("Go to Login Page"):
#                 st.session_state.view = "auth"
#                 st.rerun()

def show_enhanced_landing_page():
    # Clear any existing components first
    components.html("", height=0)
    
    # Prevent multiple renderings of the landing page
    if st.session_state.get("ui_rendered", False):
        return
    
    st.session_state.ui_rendered = True
    
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
    
    # Check for simple auth parameters
    query_params = st.query_params
    auth_action = query_params.get("auth_action")
    auth_data_str = query_params.get("auth_data")
    
    if auth_action and auth_data_str:
        try:
            # Parse the auth data
            auth_data = json.loads(auth_data_str)
            
            # Process the authentication
            if auth_action == 'login':
                email = auth_data.get('email', '').strip()
                password = auth_data.get('password', '')
                
                if authenticate_user(email, password):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    
                    if is_student(email):
                        st.session_state.user_role = "student"
                    elif is_teacher(email):
                        st.session_state.user_role = "teacher"
                    else:
                        # Redirect with error
                        st.query_params.clear()
                        st.query_params["auth_result"] = "error"
                        st.query_params["auth_message"] = "Invalid institutional email."
                        st.rerun()
                        return
                    
                    # Clear auth params and redirect to authenticated state
                    st.query_params.clear()
                    st.rerun()
                    return
                else:
                    # Redirect with error
                    st.query_params.clear()
                    st.query_params["auth_result"] = "error"
                    st.query_params["auth_message"] = "Invalid credentials. Please try again."
                    st.rerun()
                    return
            
            elif auth_action == 'signup':
                email = auth_data.get('email', '').strip()
                password = auth_data.get('password', '')
                confirm_password = auth_data.get('confirmPassword', '')
                
                if password != confirm_password:
                    st.query_params.clear()
                    st.query_params["auth_result"] = "error"
                    st.query_params["auth_message"] = "Passwords do not match!"
                    st.rerun()
                    return
                
                if not (is_student(email) or is_teacher(email)):
                    st.query_params.clear()
                    st.query_params["auth_result"] = "error"
                    st.query_params["auth_message"] = "Please use your institutional email."
                    st.rerun()
                    return
                
                if signup_user(email, password):
                    st.query_params.clear()
                    st.query_params["auth_result"] = "success"
                    st.query_params["auth_message"] = "Account created successfully! You can now login."
                    st.rerun()
                    return
                else:
                    st.query_params.clear()
                    st.query_params["auth_result"] = "error"
                    st.query_params["auth_message"] = "Email already registered or error creating account."
                    st.rerun()
                    return
                    
        except Exception as e:
            st.query_params.clear()
            st.query_params["auth_result"] = "error"
            st.query_params["auth_message"] = f"Error processing request: {str(e)}"
            st.rerun()
            return
    
    # Only render HTML if we're not processing authentication
    if not st.session_state.authenticated:
        try:
            with open("UI/landing.html", "r", encoding="utf-8") as f:
                html = f.read()
                
            # Render the HTML in a full-screen iframe
            components.html(html, height=0, scrolling=True)
                
        except FileNotFoundError:
            st.error("Could not find UI/index.html file")
            if st.button("Go to Login Page"):
                st.session_state.view = "auth"
                st.rerun()

def show_auth_page():
    """Fallback authentication page with basic Streamlit UI"""
    # Add a back button
    if st.button("← Back to Home"):
        st.session_state.view = "landing"
        st.rerun()
    
    st.title("🏫 Grade Flow 🏫")
    st.markdown("### Namaste!")
    st.markdown("*You are the future of India, and we are here to help you succeed!*")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            
            if submitted:
                if not email or not password:
                    st.error("Please fill in all fields")
                elif authenticate_user(email, password):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email

                    if is_student(email):
                        st.session_state.user_role = "student"
                    elif is_teacher(email):
                        st.session_state.user_role = "teacher"
                    else:
                        st.error("Invalid institutional email.")
                        st.session_state.authenticated = False
                        return

                    st.success("Login successful!")
                    time.sleep(1)  # Brief pause to show success message
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")

    with tab2:
        st.subheader("Sign Up")
        with st.form("signup_form"):
            new_email = st.text_input("Email Address")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Sign Up")
            
            if submitted:
                if not all([new_email, new_password, confirm_password]):
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("Passwords do not match!")
                elif not (is_student(new_email) or is_teacher(new_email)):
                    st.error("Please use your institutional email.")
                elif signup_user(new_email, new_password):
                    st.success("Account created successfully! You can now login.")
                else:
                    st.error("Email already registered or error creating account.")

if __name__ == "__main__":
    main()