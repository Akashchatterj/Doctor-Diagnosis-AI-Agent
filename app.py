import streamlit as st
import os
import io
from PIL import Image
from datetime import datetime
import json
import base64
# Import enhanced medical analysis functions
from utils_simple import (
    process_file, 
    analyze_image, 
    generate_heatmap, 
    save_analysis,
    get_latest_analyses, 
    generate_report,
    search_pubmed,
    generate_statistics_report
)
# Import chat system for collaboration
from chat_system import render_chat_interface, create_manual_chat_room

# Import QA system
from report_qa_chat import ReportQASystem, ReportQAChat

# Set page configuration
st.set_page_config(
    page_title="Medical Image Analysis Platform",
    page_icon="🏥",
    layout="wide"
)

# Initialize session states
if "openai_key" not in st.session_state:
    st.session_state.openai_key = ""
if "file_data" not in st.session_state:
    st.session_state.file_data = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "file_name" not in st.session_state:
    st.session_state.file_name = None
if "file_type" not in st.session_state:
    st.session_state.file_type = None
if "OPENAI_API_KEY" not in st.session_state:
    st.session_state.OPENAI_API_KEY = None
    
# Main app header
st.title("🏥 Advanced Medical Image Analysis")
st.markdown("Upload medical images for AI-powered analysis and collaborate with colleagues")

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    
    # API Key input
    api_key = st.text_input(
        "OpenAI API Key", 
        value=st.session_state.openai_key,
        type="password",
        help="Enter your OpenAI API key to enable image analysis"
    )
    
    if api_key:
        st.session_state.openai_key = api_key
        st.session_state.OPENAI_API_KEY = api_key
    
    # Explainable AI options
    st.subheader("Analysis Options")
    enable_xai = st.checkbox("Enable Explainable AI", value=True)
    include_references = st.checkbox("Include Medical References", value=True)
    
    # Recent analyses
    st.subheader("Recent Analyses")
    recent_analyses = get_latest_analyses(limit=5)
    for analysis in recent_analyses:
        st.caption(f"{analysis.get('filename', 'Unknown')} - {analysis.get('date', '')[:10]}")
    
    # Statistics report
    if st.button("Generate Statistics Report"):
        stats_report = generate_statistics_report()
        if stats_report:
            # Create download link
            b64_pdf = base64.b64encode(stats_report.read()).decode()
            href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="statistics_report.pdf">Download Statistics Report</a>'
            st.markdown(href, unsafe_allow_html=True)

# Navigation using radio buttons instead of tabs (to avoid st.chat_input() issues)
page = st.radio(
    "Navigation",
    ["Image Upload & Analysis", "Collaboration", "Report Q&A", "Reports"],
    horizontal=True,
    key="main_nav"
)

if page == "Image Upload & Analysis":
    # File uploader
    uploaded_file = st.file_uploader(
        "Upload a medical image (JPEG, PNG, DICOM, NIfTI)", 
        type=["jpg", "jpeg", "png", "dcm", "nii", "nii.gz"]
    )
    
    if uploaded_file:
        # Process the file
        try:
            file_data = process_file(uploaded_file)
            
            if file_data:
                st.session_state.file_data = file_data
                st.session_state.file_name = uploaded_file.name
                st.session_state.file_type = file_data["type"]
                
                # Display the image
                st.image(file_data["data"], caption=f"Uploaded {file_data['type']} image", use_column_width=True)
                
                # Analysis button
                if st.button("Analyze Image") and st.session_state.openai_key:
                    with st.spinner("Analyzing image..."):
                        # Run image analysis
                        analysis_results = analyze_image(
                            file_data["data"], 
                            st.session_state.openai_key,
                            enable_xai=enable_xai
                        )
                        
                        # Store the analysis
                        analysis_results = save_analysis(analysis_results, filename=uploaded_file.name)
                        
                        # Update session state
                        st.session_state.analysis_results = analysis_results
                        st.session_state.findings = analysis_results.get("findings", [])
                        
                        # Display results
                        st.subheader("Analysis Results")
                        st.markdown(analysis_results["analysis"])
                        
                        # Show findings if available
                        if analysis_results.get("findings"):
                            st.subheader("Key Findings")
                            for idx, finding in enumerate(analysis_results["findings"], 1):
                                st.markdown(f"{idx}. {finding}")
                        
                        # Show keywords if available
                        if analysis_results.get("keywords"):
                            st.subheader("Keywords")
                            st.markdown(f"*{', '.join(analysis_results['keywords'])}*")
                        
                        # Generate heatmap if XAI is enabled
                        if enable_xai:
                            st.subheader("Explainable AI Visualization")
                            overlay, heatmap = generate_heatmap(file_data["array"])
                            col1, col2 = st.columns(2)
                            with col1:
                                st.image(overlay, caption="Heatmap Overlay", use_column_width=True)
                            with col2:
                                st.image(heatmap, caption="Raw Heatmap", use_column_width=True)
                        
                        # Show medical references if enabled
                        if include_references and analysis_results.get("keywords"):
                            st.subheader("Relevant Medical Literature")
                            references = search_pubmed(analysis_results["keywords"], max_results=3)
                            for ref in references:
                                st.markdown(f"- **{ref['title']}**  \n{ref['journal']}, {ref['year']} (PMID: {ref['id']})")
                        
                        # Generate PDF report
                        st.subheader("Report Generation")
                        pdf_buffer = generate_report(analysis_results, include_references=include_references)
                        
                        # Create download link for the PDF
                        b64_pdf = base64.b64encode(pdf_buffer.read()).decode()
                        href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="medical_report_{datetime.now().strftime("%Y%m%d")}.pdf">Download PDF Report</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        
                        # Option to start a discussion
                        st.subheader("Collaborate")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("Start Case Discussion"):
                                case_description = f"{uploaded_file.name} analysis"
                                if "findings" in analysis_results and analysis_results["findings"]:
                                    case_description = analysis_results["findings"][0]
                                
                                case_id = f"{file_data['type'].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                                created_case_id = create_manual_chat_room("Dr. Anonymous", case_description)
                                st.session_state.current_case_id = created_case_id
                                st.rerun()
                        
                        with col2:
                            if st.button("Start Q&A Session"):
                                if "qa_chat" not in st.session_state:
                                    st.session_state.qa_chat = ReportQAChat()
                                
                                room_name = f"Q&A for {uploaded_file.name}"
                                created_qa_id = st.session_state.qa_chat.create_qa_room("Dr. Anonymous", room_name)
                                st.session_state.current_qa_id = created_qa_id
                                st.rerun()
                        
                elif not st.session_state.openai_key:
                    st.warning("Please enter your OpenAI API key in the sidebar to enable analysis")
            else:
                st.error("Unable to process the uploaded file")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    
    # Show previously analyzed results if available
    elif "analysis_results" in st.session_state and st.session_state.analysis_results:
        st.subheader("Previous Analysis Results")
        st.markdown(st.session_state.analysis_results["analysis"])
        
        if "findings" in st.session_state.analysis_results:
            st.subheader("Key Findings")
            for idx, finding in enumerate(st.session_state.analysis_results["findings"], 1):
                st.markdown(f"{idx}. {finding}")
        
        # Generate PDF report for previous analysis
        st.subheader("Report")
        if st.button("Generate PDF Report"):
            pdf_buffer = generate_report(st.session_state.analysis_results, include_references=include_references)
            
            b64_pdf = base64.b64encode(pdf_buffer.read()).decode()
            href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="medical_report_{datetime.now().strftime("%Y%m%d")}.pdf">Download PDF Report</a>'
            st.markdown(href, unsafe_allow_html=True)

elif page == "Collaboration":
    # Render the chat interface for collaboration
    try:
        render_chat_interface()
    except Exception as e:
        st.error(f"Error in chat interface: {str(e)}")
        st.info("If you're trying to create a new discussion, please upload and analyze an image first.")

        # Offer a direct way to create a discussion without an image
        st.subheader("Create Discussion Without Image")
        manual_creator = st.text_input("Your Name", value="Dr. Anonymous")
        manual_description = st.text_input("Case Description")
        
        if st.button("Create Manual Discussion") and manual_description:
            case_id = create_manual_chat_room(manual_creator, manual_description)
            st.session_state.current_case_id = case_id
            st.rerun()

elif page == "Report Q&A":
    # Render QA interface - NOW AT ROOT LEVEL, NOT IN TABS!
    st.subheader("🩺 Medical Report Q&A System")
    
    # Initialize QA system and chat if not present
    if "qa_system" not in st.session_state:
        api_key_qa = st.session_state.get("OPENAI_API_KEY", st.session_state.get("openai_key", None))
        st.session_state.qa_system = ReportQASystem(api_key=api_key_qa)
    
    if "qa_chat" not in st.session_state:
        st.session_state.qa_chat = ReportQAChat()
    
    # User information
    if "qa_user_name" not in st.session_state:
        st.session_state.qa_user_name = "Dr. User"
    
    user_name = st.text_input("Your Name", value=st.session_state.qa_user_name, key="qa_name_input")
    if user_name != st.session_state.qa_user_name:
        st.session_state.qa_user_name = user_name
    
    # Room selection - using columns instead of tabs
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Join Existing Q&A")
        qa_rooms = st.session_state.qa_chat.get_qa_rooms()
        if qa_rooms:
            room_options = {f"{room['name']} (by {room['creator']})": room["id"] for room in qa_rooms}
            selected_room = st.selectbox("Select Q&A Room", options=list(room_options.keys()), key="qa_room_select")
            
            if st.button("Join Q&A Room", key="join_qa_btn"):
                selected_qa_id = room_options[selected_room]
                st.session_state.current_qa_id = selected_qa_id
                st.rerun()
        else:
            st.info("No active Q&A rooms. Create a new one!")
    
    with col2:
        st.markdown("### Create New Q&A Room")
        room_name = st.text_input("Q&A Room Name", key="qa_room_name_input")
        
        if st.button("Create Q&A Room", key="create_qa_btn"):
            if room_name:
                created_qa_id = st.session_state.qa_chat.create_qa_room(user_name, room_name)
                st.session_state.current_qa_id = created_qa_id
                st.rerun()
            else:
                st.error("Please provide a room name")
    
    # Active Q&A chat display
    if "current_qa_id" in st.session_state:
        qa_id = st.session_state.current_qa_id
        qa_rooms = st.session_state.qa_chat.get_qa_rooms()
        
        current_room = None
        for room in qa_rooms:
            if room["id"] == qa_id:
                current_room = room
                break
        
        if current_room:
            st.divider()
            st.subheader(f"Q&A Room: {current_room['name']}")
            st.caption(f"Created by {current_room['creator']} on {current_room['created_at'][:10]}")
            
            if st.button("Clear Conversation History", key="clear_qa_hist"):
                st.session_state.qa_system.clear_history()
                st.info("Conversation history has been cleared.")
            
            messages = st.session_state.qa_chat.get_messages(qa_id)
            
            for msg in messages:
                is_ai = msg["user"] == "Report QA System"
                with st.chat_message(name=msg["user"], avatar="🤖" if is_ai else "👨‍⚕️"):
                    st.write(msg["content"])
            
            with st.expander("Room Settings"):
                if st.button("Delete Q&A Room", key="del_qa_room"):
                    if st.session_state.qa_chat.delete_qa_room(qa_id):
                        st.success("Room deleted successfully.")
                        del st.session_state.current_qa_id
                        st.rerun()
                    else:
                        st.error("Failed to delete room.")
        else:
            st.error("This Q&A room no longer exists")
            if st.button("Return to Room Selection", key="back_qa_btn"):
                del st.session_state.current_qa_id
                st.rerun()
    
    # CHAT INPUT AT ROOT LEVEL - CRITICAL!
    if "current_qa_id" in st.session_state:
        qa_message = st.chat_input("Ask a question about your medical reports", key="qa_msg_input")
        
        if qa_message:
            qa_id = st.session_state.current_qa_id
            st.session_state.qa_chat.add_message(qa_id, user_name, qa_message)
            
            api_key_qa = st.session_state.get("OPENAI_API_KEY", st.session_state.get("openai_key", None))
            
            if api_key_qa != st.session_state.qa_system.api_key:
                st.session_state.qa_system.api_key = api_key_qa
            
            with st.spinner("Analyzing medical reports..."):
                import time
                time.sleep(0.5)
                ai_response = st.session_state.qa_system.answer_question(qa_message)
            
            st.session_state.qa_chat.add_message(qa_id, "Report QA System", ai_response)
            st.rerun()

elif page == "Reports":
    # Reports and Analytics section
    st.subheader("Medical Reports & Analytics")
    
    st.markdown("### Analysis History")
    recent_analyses = get_latest_analyses(limit=10)
    
    if recent_analyses:
        for idx, analysis in enumerate(recent_analyses, 1):
            with st.expander(f"{idx}. {analysis.get('filename', 'Unknown')} - {analysis.get('date', '')[:10]}"):
                st.markdown(analysis.get("analysis", "No analysis available"))
                
                if analysis.get("findings"):
                    st.markdown("**Key Findings:**")
                    for finding_idx, finding in enumerate(analysis["findings"], 1):
                        st.markdown(f"{finding_idx}. {finding}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"Generate Report #{idx}"):
                        pdf_buffer = generate_report(analysis, include_references=include_references)
                        
                        b64_pdf = base64.b64encode(pdf_buffer.read()).decode()
                        report_name = f"report_{analysis.get('id', 'unknown')[:8]}.pdf"
                        href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{report_name}">Download Report</a>'
                        st.markdown(href, unsafe_allow_html=True)
                
                with col2:
                    if st.button(f"Q&A on Report #{idx}"):
                        if "qa_chat" not in st.session_state:
                            st.session_state.qa_chat = ReportQAChat()
                        
                        report_name = f"Q&A for {analysis.get('filename', 'Unknown')}"
                        created_qa_id = st.session_state.qa_chat.create_qa_room("Dr. Anonymous", report_name)
                        st.session_state.current_qa_id = created_qa_id
                        st.rerun()
    else:
        st.info("No previous analyses found. Upload and analyze an image to get started.")
    
    st.markdown("### Statistics")
    
    if st.button("Generate Comprehensive Statistics"):
        stats_report = generate_statistics_report()
        if stats_report:
            b64_pdf = base64.b64encode(stats_report.read()).decode()
            href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="statistics_report.pdf">Download Statistics Report</a>'
            st.markdown(href, unsafe_allow_html=True)