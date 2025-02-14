import json
import os
import base64
import streamlit as st
import logging
import config
import services
import yaml
import tempfile
import shutil
from pathlib import Path
from io import BytesIO

def load_job_details(yaml_content):
    """Extract job details from YAML content"""
    if not yaml_content:
        return None

    try:
        data = yaml.safe_load(yaml_content)
        if not data:
            return None

        # Filter for job-specific fields
        job_fields = ['company', 'job_title', 'team', 'is_fully_remote', 'job_summary',
                      'salary', 'duties', 'qualifications', 'technical_skills',
                      'non_technical_skills', 'ats_keywords']

        # Check if any job fields exist in the data
        if not any(field in data for field in job_fields):
            return None

        return {k: v for k, v in data.items() if k in job_fields}
    except Exception as e:
        st.error(f"Error parsing job details: {str(e)}")
        return None

def get_directory_contents(folder_path):
    """Return the YAML files and PDF in the given folder path"""
    path = Path(folder_path)
    contents = {
        'yaml': None,  # For resume.yaml
        'pdf_path': None,
        'job_yaml': None  # For job.yaml
    }

    if path.exists():
        for item in path.iterdir():
            if item.is_file():
                if item.name.lower() == 'job.yaml':
                    try:
                        with open(item, 'r') as f:
                            contents['job_yaml'] = f.read()
                    except Exception as e:
                        st.error(f"Error reading job.yaml: {str(e)}")
                elif item.suffix.lower() == '.yaml' and item.name.lower() != 'job.yaml':
                    try:
                        with open(item, 'r') as f:
                            contents['yaml'] = f.read()
                    except Exception as e:
                        st.error(f"Error reading resume YAML: {str(e)}")
                elif item.suffix.lower() == '.pdf':
                    contents['pdf_path'] = str(item)

    return contents

def get_directory_structure(path):
    """Return a list of all subfolders in the given path"""
    path = Path(path)
    folders = []
    if path.exists():
        for item in path.rglob("*"):
            if item.is_dir():
                folders.append(str(item))
    return sorted(folders)

def clear_specific_folder(folder_path):
    """Clear all files in a specific folder and remove the folder itself"""
    try:
        folder = Path(folder_path)
        if folder.exists():
            # First remove all contents
            for item in folder.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)

            # Then remove the folder itself if it's not the root data directory
            if folder.name != "data":
                try:
                    folder.rmdir()  # This will only work if the directory is empty
                    return True
                except Exception as e:
                    st.error(f"Error removing directory {folder_path}: {str(e)}")
                    return False
            return True
        return False
    except Exception as e:
        st.error(f"Error clearing folder {folder_path}: {str(e)}")
        return False

def clear_data_folder():
    """Clear the entire data directory but keep the root"""
    try:
        data_dir = Path("data")
        if data_dir.exists():
            # Clear all contents but keep the root directory
            for item in data_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            return True
        return False
    except Exception as e:
        st.error(f"Error clearing data folder: {str(e)}")
        return False

def generate_preview_pdf(yaml_content, resume_improver):
    """Generate a preview PDF from YAML content"""
    try:
        temp_dir = Path(tempfile.gettempdir()) / "resume_preview"
        temp_dir.mkdir(parents=True, exist_ok=True)

        yaml_path = temp_dir / "temp_resume.yaml"
        pdf_path = temp_dir / "preview_resume.pdf"

        yaml_dict = yaml.safe_load(yaml_content)
        yaml_dict["editing"] = False
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_dict, f)

        resume_improver.yaml_loc = str(yaml_path)
        resume_improver.pdf_loc = str(pdf_path)

        return resume_improver.create_pdf(auto_open=False)
    except Exception as e:
        st.error(f"Preview generation error: {str(e)}")
        return None

def generate_final_pdf(yaml_content, resume_improver, output_dir):
    """Generate the final PDF in the specified output directory"""
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        yaml_path = output_dir / "final_resume.yaml"
        pdf_path = output_dir / "final_resume.pdf"

        yaml_dict = yaml.safe_load(yaml_content)
        yaml_dict["editing"] = False
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_dict, f)

        resume_improver.yaml_loc = str(yaml_path)
        resume_improver.pdf_loc = str(pdf_path)

        return resume_improver.create_pdf(auto_open=False)
    except Exception as e:
        st.error(f"Final PDF generation error: {str(e)}")
        return None

def display_pdf(pdf_path):
    """Display PDF using PDF.js with page count and provide ATS-friendly download"""
    try:
        # First, verify the PDF exists and is readable
        if not os.path.exists(pdf_path):
            st.error("PDF file not found")
            return

        # Read the PDF file
        with open(pdf_path, "rb") as pdf_file:
            # Create base64 version for display
            base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')

            # Store original PDF bytes for download
            pdf_file.seek(0)
            pdf_bytes = pdf_file.read()

        # Use a simpler PDF.js viewer setup that's more reliable
        pdf_display = f'''
            <iframe
                src="data:application/pdf;base64,{base64_pdf}"
                width="100%"
                height="800px"
                type="application/pdf"
            ></iframe>
        '''

        st.markdown(pdf_display, unsafe_allow_html=True)

        # Add download functionality
        import PyPDF2
        with open(pdf_path, "rb") as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)

            # Verify PDF is readable and contains text
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text()

            if text_content.strip():
                st.success(f"✅ PDF is valid and contains {page_count} page{'s' if page_count != 1 else ''}")
            else:
                st.warning("⚠️ PDF appears to be empty or unreadable")

        col1, col2 = st.columns([3, 1])
        with col1:
            st.download_button(
                label=f"📥 Download ATS-Friendly PDF ({page_count} pages)",
                data=pdf_bytes,
                file_name="resume.pdf",
                mime='application/pdf',
                use_container_width=True
            )

    except Exception as e:
        st.error(f"PDF display error: {str(e)}")
        import traceback
        st.error(traceback.format_exc())

class StreamlitHandler(logging.Handler):
    """Custom logging handler for Streamlit"""
    def __init__(self, placeholder):
        super().__init__()
        self.placeholder = placeholder
        self.logs = []
        self.counter = 0

    def emit(self, record):
        log_entry = self.format(record)
        self.logs.append(log_entry)
        log_text = "\n".join(self.logs)
        self.counter += 1
        self.placeholder.text_area("Logs", log_text, height=300, key=f"log_area_{self.counter}")

def main():
    # Updated Custom CSS for layout control
    st.markdown("""
        <style>
        /* Add padding to the top to accommodate the header */
        .block-container {
            padding-top: 3rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-bottom: 1rem !important;
            max-width: 100%;
        }
        
        /* Style for the title */
        h1 {
            padding-top: 1rem;
            padding-left: 1rem;
            margin-bottom: 2rem;
        }
        
        /* Style for URL input container */
        .stTextInput {
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        /* Remove extra padding from columns */
        div.row-widget.stHorizontal {
            padding: 0;
            margin: 0;
            max-width: 100%;
        }
        
        /* Make text area expand fully */
        .stTextArea textarea {
             font-family: monospace;
            width: 100% !important;
            max-width: none !important;
            background-color: #1E1E1E !important;  /* Dark background */
            color: #FFFFFF !important;  /* Light text */
        }
        
        /* Ensure columns take full width */
        div.column-widget {
            width: 100% !important;
            max-width: none !important;
        }
        
        /* Make PDF viewer responsive */
        iframe {
            width: 100% !important;
            max-width: none !important;
        }
        
        /* Hide default Streamlit menu */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Adjust column gaps */
        div.row-widget.stHorizontal > div {
            min-width: 0;
            flex: 1;
            padding: 0 10px;
        }
        
        /* Ensure content stretches in columns */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 50% !important;
            min-width: 0;
        }
        
        /* Add scrolling for overflow */
        [data-testid="stHorizontalBlock"] {
            width: 100%;
            overflow-x: auto;
        }
        
        /* Style for sidebar toggle button */
        .sidebar-toggle {
            position: fixed;
            top: 1rem;
            left: 1rem;
            z-index: 99999;
            padding: 0.5rem;
            background: #ffffff;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
        }

        /* Add spacing between title and content */
        .main .block-container {
            margin-top: 2rem;
        }

        /* Ensure input field is fully visible */
        .stTextInput > div > div > input {
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    # Create a container for the title and URL input
    with st.container():
        st.title("Resume Tailoring Tool")

    # Initialize session state
    if 'stage' not in st.session_state:
        st.session_state.stage = 'input'
        st.session_state.resume_improver = None
        st.session_state.yaml_content = None
        st.session_state.last_yaml = None
        st.session_state.sidebar_state = 'collapsed'
        st.session_state.current_pdf_path = None
        st.session_state.preview_mode = None  # Can be 'folder' or 'job'

    # Add sidebar toggle button with adjusted position
    st.markdown("""
        <div class='sidebar-toggle' onclick='window.dispatchEvent(new KeyboardEvent("keydown", {key: ".", ctrlKey: true}))'>
            ☰
        </div>
    """, unsafe_allow_html=True)

    # Sidebar content
    if 'preview_states' not in st.session_state:
        st.session_state.preview_states = {}

    with st.sidebar:
        st.subheader("Folder Management")

        data_dir = Path(config.DATA_PATH)
        data_dir.mkdir(exist_ok=True)

        folders = get_directory_structure(config.DATA_PATH)

        col1, col2 = st.columns([4, 1])
        with col1:
            st.write("📁 data")
        with col2:
            if st.button("❌", key="main_clear"):
                if clear_data_folder():
                    st.success("Data folder cleared!")
                    st.rerun()

        for folder in folders:
            folder_path = Path(folder)
            relative_path = folder_path.relative_to(data_dir)
            indent = "    " * (len(folder_path.parts) - 1)

            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"{indent}📁 {relative_path}")
            with col2:
                if st.button("👁️", key=f"preview_{folder}"):
                    contents = get_directory_contents(folder_path)
                    st.session_state.yaml_content = contents['yaml']
                    st.session_state.yaml_content = contents['job_yaml']
                    st.session_state.current_pdf_path = contents['pdf_path']
                    st.session_state.preview_mode = 'folder'
                    st.session_state.stage = 'review'
                    st.rerun()
            with col3:
                if st.button("❌", key=f"clear_{folder}"):
                    if clear_specific_folder(folder):
                        st.success(f"Cleared {relative_path}")
                        st.rerun()

    container = st.container()
    with container:
        # URL input section is always visible
        url = st.text_input("Enter Job URL:", placeholder="https://example.com/job/...")
        if st.button("Analyze Job", use_container_width=True):
            if url:
                progress_bar = st.progress(0)
                log_placeholder = st.empty()
                logger = logging.getLogger()
                logger.setLevel(logging.INFO)
                handler = StreamlitHandler(log_placeholder)
                formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)

                try:
                    st.session_state.resume_improver = services.ResumeImprover(url)
                    progress_bar.progress(25)
                    st.session_state.resume_improver.create_draft_tailored_resume(
                        auto_open=False,
                        manual_review=False,
                        skip_pdf_create=True
                    )
                    with open(st.session_state.resume_improver.yaml_loc, 'r') as f:
                        st.session_state.yaml_content = f.read()
                    progress_bar.progress(100)
                    st.session_state.preview_mode = 'job'
                    st.session_state.stage = 'review'
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                finally:
                    logger.removeHandler(handler)
            else:
                st.warning("Please enter a job URL")

        # Show review section if we're in review stage (either from folder preview or job analysis)
        if st.session_state.stage == 'review':
            tabs = st.tabs(["Resume Editor", "Job Details"])
            with tabs[0]:
                left_col, right_col = st.columns([1, 1])

                with left_col:
                    edited_yaml = st.text_area(
                        "Review Resume YAML",
                        st.session_state.yaml_content,
                        height=800
                    )

                    # Only show output directory and save options for job analysis mode
                    if st.session_state.preview_mode == 'job':
                        output_dir = st.text_input(
                            "Output Directory:",
                            placeholder="/path/to/save/resume"
                        )

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Save Final PDF", use_container_width=True):
                                if output_dir:
                                    pdf_path = generate_final_pdf(
                                        edited_yaml,
                                        st.session_state.resume_improver,
                                        output_dir
                                    )
                                    if pdf_path and os.path.exists(pdf_path):
                                        st.success(f"PDF saved to: {pdf_path}")
                                        with open(pdf_path, "rb") as f:
                                            pdf_bytes = f.read()
                                        st.download_button(
                                            label="Download PDF",
                                            data=pdf_bytes,
                                            file_name="resume.pdf",
                                            mime="application/pdf",
                                            use_container_width=True
                                        )
                                else:
                                    st.warning("Please specify an output directory")

                        with col2:
                            if st.button("Start Over", use_container_width=True):
                                st.session_state.stage = 'input'
                                st.session_state.preview_mode = None
                                st.rerun()

                with right_col:
                    if st.session_state.preview_mode == 'job':
                        # For job analysis, generate preview PDF from YAML
                        if edited_yaml != st.session_state.last_yaml:
                            st.session_state.last_yaml = edited_yaml
                            pdf_path = generate_preview_pdf(
                                edited_yaml,
                                st.session_state.resume_improver
                            )
                            if pdf_path:
                                st.session_state.current_pdf_path = pdf_path

                    # Display PDF (whether from folder preview or job analysis)
                    if st.session_state.current_pdf_path:
                        st.subheader("PDF Preview")
                        display_pdf(st.session_state.current_pdf_path)
            with tabs[1]:
                # Initialize job_details to None at the start
                job_details = None

                try:
                    if st.session_state.preview_mode == 'folder':
                        job_details = load_job_details(st.session_state.yaml_content)
                        if not job_details:
                            st.warning("job.yaml found but contains no valid job details")
                    elif st.session_state.preview_mode == 'job':
                        # For job analysis mode, check if we have a job.yaml in the output directory
                        if hasattr(st.session_state, 'resume_improver') and st.session_state.resume_improver and st.session_state.resume_improver.job_data_location:
                            output_dir = Path(st.session_state.resume_improver.job_data_location)
                            contents = get_directory_contents(output_dir)
                            if contents['job_yaml']:
                                job_details = load_job_details(contents['job_yaml'])
                except Exception as e:
                    st.error(f"Error loading job details: {str(e)}")
                    job_details = None

                # Display job details if available
                if job_details:
                    # Display company info
                    st.markdown(f"## {job_details.get('company', 'Company Not Specified')}")
                    st.markdown(f"### {job_details.get('job_title', 'Title Not Specified')} - {job_details.get('team', 'Team Not Specified')}")

                    # Status badges
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if job_details.get('is_fully_remote'):
                            st.success("🌐 Fully Remote")
                    with col2:
                        if job_details.get('salary'):
                            st.info(f"💰 {job_details['salary']}")

                    # Job Summary
                    if job_details.get('job_summary'):
                        st.markdown("### Summary")
                        st.info(job_details['job_summary'])

                    # Two-column layout for duties and qualifications
                    col1, col2 = st.columns(2)

                    with col1:
                        if job_details.get('duties'):
                            st.markdown("### Key Responsibilities")
                            for duty in job_details['duties']:
                                st.markdown(f"- {duty}")

                    with col2:
                        if job_details.get('qualifications'):
                            st.markdown("### Qualifications")
                            for qual in job_details['qualifications']:
                                st.markdown(f"- {qual}")

                    # Skills section
                    st.markdown("### Skills")
                    col1, col2 = st.columns(2)

                    with col1:
                        if job_details.get('technical_skills'):
                            st.markdown("#### Technical Skills")
                            skills_html = ' '.join([
                                f'<span style="background-color: #e3f2fd; color: #1976d2; padding: 5px 10px; margin: 5px; border-radius: 15px; display: inline-block;">{skill}</span>'
                                for skill in job_details['technical_skills']
                            ])
                            st.markdown(skills_html, unsafe_allow_html=True)

                    with col2:
                        if job_details.get('non_technical_skills'):
                            st.markdown("#### Non-Technical Skills")
                            skills_html = ' '.join([
                                f'<span style="background-color: #f5f5f5; color: #616161; padding: 5px 10px; margin: 5px; border-radius: 15px; display: inline-block;">{skill}</span>'
                                for skill in job_details['non_technical_skills']
                            ])
                            st.markdown(skills_html, unsafe_allow_html=True)

                    # ATS Keywords section
                    if job_details.get('ats_keywords'):
                        st.markdown("### ATS Keywords")
                        keywords_html = ' '.join([
                            f'<span style="background-color: #f3e5f5; color: #7b1fa2; padding: 5px 10px; margin: 5px; border-radius: 15px; display: inline-block;">{keyword}</span>'
                            for keyword in job_details['ats_keywords']
                        ])
                        st.markdown(keywords_html, unsafe_allow_html=True)
                else:
                    st.warning("No valid job details available. Make sure job.yaml exists in the same directory as the resume files and contains valid job information.")



if __name__ == "__main__":
    main()