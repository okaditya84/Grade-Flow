import os
import json
import streamlit as st
from streamlit.components.v1 import html
import pandas as pd
from datetime import datetime
import time
from utils import process_submission, create_vector_store, get_submission_history

def show_student_interface():
    # Hide Streamlit UI elements completely
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
            background: #00171F !important;
        }
        header, [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, .stDecoration {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }
        /* Hide sidebar completely */
        .css-1d391kg, .css-1lcbmhc, .css-1cypcdb, .css-17eq0hr, .css-1rs6os, .css-17lntkn, 
        [data-testid="stSidebar"], .css-1oe5cao, .e1fqkh3o0, .css-6qob1r, .css-1lcbmhc {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
        }
        /* Ensure main content takes full width */
        .main .block-container {
            max-width: 100% !important;
            width: 100% !important;
        }
        /* Make iframe take full screen */
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
    
    # Load the HTML file
    with open("UI/student_interface.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Inject user data into the HTML
    html_content = html_content.replace("John Doe", st.session_state.user_email)
    
    # Add JavaScript to handle logout functionality
    logout_js = """
    <script>
        // Override the handleLogout function
        function handleLogout() {
            if (confirm("Are you sure you want to logout?")) {
                // Send logout message to Streamlit
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: { action: 'logout' }
                }, '*');
            }
        }
        
        // Listen for messages from Streamlit
        window.addEventListener('message', function(event) {
            if (event.data.type === 'streamlit:componentValue' && event.data.value) {
                const data = event.data.value;
                
                if (data.response) {
                    showMessage(data.response.type, data.response.message);
                    
                    if (data.response.type === 'success') {
                        // Reset form on success
                        document.getElementById('submission-form').reset();
                        const fileName = document.getElementById('file-name');
                        if (fileName) {
                            fileName.textContent = '';
                            fileName.classList.add('hidden');
                        }
                    }
                }
            }
        });
    </script>
    """
    
    # Inject the logout JavaScript before the closing body tag
    html_content = html_content.replace("</body>", logout_js + "</body>")
    
    # Render the HTML interface with full screen
    component_value = html(html_content, height=0, scrolling=True)
    st.session_state.last_component_value = component_value
    
    # Handle communication from the HTML interface
    # handle_html_events(component_value)
    handle_html_events(st.session_state.last_component_value)


# def handle_html_events(component_value):
#     """Handle events coming from the HTML/JS interface"""
    
#     if component_value:
#         # Convert component_value to dict if it's not already
#         data = component_value if isinstance(component_value, dict) else {}
        
#         # Handle logout
#         if data.get('action') == 'logout':
#             # Clear all session state
#             for key in list(st.session_state.keys()):
#                 del st.session_state[key]
#             # Reinitialize session state
#             st.session_state.authenticated = False
#             st.session_state.user_role = None
#             st.session_state.user_email = None
#             st.session_state.view = "landing"
#             st.session_state.ui_rendered = False
#             # Clear any URL parameters
#             st.query_params.clear()
#             st.rerun()
#             return
        
#         # Handle file submissions
#         if component_value.get('action') == 'submit':
#             data = component_value
            
#             # Process the submission
#             with st.spinner(f"Processing your {data['type'].lower()}..."):
#                 try:
#                     # Here you would use your actual processing functions
#                     # Note: You'll need to handle the base64 file content properly
#                     success, message = process_submission(
#                         data["file"],  # This contains name, type, and base64 content
#                         data["type"].lower(),
#                         data["course"],
#                         data["title"],
#                         st.session_state.user_email,
#                     )
                    
#                     # Create vector store for the document
#                     if success:
#                         vector_store_success = create_vector_store(
#                             st.session_state.user_email, 
#                             data["type"].lower(), 
#                             data["course"], 
#                             data["title"]
#                         )
                        
#                         # Send response back to the HTML interface
#                         if vector_store_success:
#                             response = {
#                                 "response": {
#                                     "type": "success",
#                                     "message": f"{message} Vector store created successfully!"
#                                 }
#                             }
#                         else:
#                             response = {
#                                 "response": {
#                                     "type": "warning",
#                                     "message": f"{message} However, there was an issue creating the vector store."
#                                 }
#                             }
#                     else:
#                         response = {
#                             "response": {
#                                 "type": "error",
#                                 "message": message
#                             }
#                         }
                    
#                     # Update the component with the response
#                     st.session_state.submission_response = response
                    
#                 except Exception as e:
#                     st.session_state.submission_response = {
#                         "response": {
#                             "type": "error",
#                             "message": f"Error processing submission: {str(e)}"
#                         }
#                     }

def handle_html_events(component_value):
    """Handle events coming from the HTML/JS interface"""
    
    if not isinstance(component_value, dict):
        return  # Ignore invalid messages

    action = component_value.get('action')

    if action == 'logout':
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        # Reinitialize session state
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.user_email = None
        st.session_state.view = "landing"
        st.session_state.ui_rendered = False
        # Clear any URL parameters
        st.query_params.clear()
        st.rerun()
        return

    if action == 'submit':
        # Process the submission
        with st.spinner(f"Processing your {component_value['type'].lower()}..."):
            try:
                success, message = process_submission(
                    component_value["file"],
                    component_value["type"].lower(),
                    component_value["course"],
                    component_value["title"],
                    st.session_state.user_email,
                )

                if success:
                    vector_store_success = create_vector_store(
                        st.session_state.user_email,
                        component_value["type"].lower(),
                        component_value["course"],
                        component_value["title"]
                    )
                    if vector_store_success:
                        response = {
                            "response": {
                                "type": "success",
                                "message": f"{message} Vector store created successfully!"
                            }
                        }
                    else:
                        response = {
                            "response": {
                                "type": "warning",
                                "message": f"{message} However, there was an issue creating the vector store."
                            }
                        }
                else:
                    response = {
                        "response": {
                            "type": "error",
                            "message": message
                        }
                    }

                st.session_state.submission_response = response

            except Exception as e:
                st.session_state.submission_response = {
                    "response": {
                        "type": "error",
                        "message": f"Error processing submission: {str(e)}"
                    }
                }


def show_submission_history():
    # This can remain similar to your original implementation
    st.header("Your Submission History")
    
    # Get submission history
    submissions = get_submission_history(st.session_state.user_email)
    
    if not submissions:
        st.info("You haven't made any submissions yet.")
        return
    
    # Create a DataFrame from submission history
    df = pd.DataFrame(submissions)
    
    # Display the DataFrame with some styling
    st.dataframe(
        df.style.format({"Submission Date": lambda x: x.split(" ")[0]}),
        use_container_width=True,
    )
    
    # Allow filtering by submission type
    submission_type_filter = st.selectbox(
        "Filter by Type", ["All"] + sorted(df["Type"].unique().tolist())
    )
    
    if submission_type_filter != "All":
        filtered_df = df[df["Type"] == submission_type_filter]
        st.dataframe(
            filtered_df.style.format({"Submission Date": lambda x: x.split(" ")[0]}),
            use_container_width=True,
        )
    
    # Show evaluation results if available
    st.subheader("Evaluation Results")
    
    evaluated_submissions = [
        s for s in submissions if s.get("Evaluation Status") == "Completed"
    ]
    
    if not evaluated_submissions:
        st.info("None of your submissions have been evaluated yet.")
        return
    
    for submission in evaluated_submissions:
        with st.expander(
            f"{submission['Type']} - {submission['Title']} ({submission['Course']})"
        ):
            if "Score" in submission:
                st.metric("Score", f"{submission['Score']}/100")
            
            if "Feedback" in submission:
                st.markdown("### Feedback")
                st.write(submission["Feedback"])
            
            if "Detailed Analysis" in submission:
                st.markdown("### Detailed Analysis")
                st.write(submission["Detailed Analysis"])