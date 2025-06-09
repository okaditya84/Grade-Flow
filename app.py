import os
import streamlit as st
from auth import authenticate_user, signup_user, is_student, is_teacher
from student_interface import show_student_interface
from teacher_interface import show_teacher_interface
from utils import setup_directories, load_css, update_active_tests
from dotenv import load_dotenv

# Set page config - must be the first Streamlit command
st.set_page_config(
    page_title="Grade Flow",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load environment variables
load_dotenv()


# Setup session state
def init_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "college_domain" not in st.session_state:
        st.session_state.college_domain = None


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
        if st.session_state.user_role == "student":
            show_student_interface()
        elif st.session_state.user_role == "teacher":
            show_teacher_interface()
        else:
            st.error("Unknown user role. Please log out and try again.")

        # Logout button in sidebar
        st.sidebar.title(f"Welcome, {st.session_state.user_email}")
        if st.sidebar.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


def show_auth_page():
    st.title("🏫 Grade Flow 🏫")
    st.markdown("### Namaste!")
    st.markdown("*You are the future of India, and we are here to help you succeed!*")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        st.subheader("Login")
        email = st.text_input("Email Address", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            if authenticate_user(email, password):
                st.session_state.authenticated = True
                st.session_state.user_email = email

                # Determine user role based on email
                if is_student(email):
                    st.session_state.user_role = "student"
                elif is_teacher(email):
                    st.session_state.user_role = "teacher"
                else:
                    st.error(
                        "Invalid email domain. Please use your institutional email."
                    )
                    st.session_state.authenticated = False
                    return

                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

    with tab2:
        st.subheader("Sign Up")
        new_email = st.text_input("Email Address", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input(
            "Confirm Password", type="password", key="confirm_password"
        )

        if st.button("Sign Up"):
            if new_password != confirm_password:
                st.error("Passwords do not match!")
                return

            if not (is_student(new_email) or is_teacher(new_email)):
                st.error("Please use your institutional email (student or faculty).")
                return

            if signup_user(new_email, new_password):
                st.success("Account created successfully! You can now login.")
            else:
                st.error("Email already registered or error creating account.")


if __name__ == "__main__":
    main()
