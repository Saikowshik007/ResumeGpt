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
    """Clear all files in a specific folder"""
    try:
        folder = Path(folder_path)
        if folder.exists():
            for item in folder.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            return True
    except Exception as e:
        st.error(f"Error clearing folder {folder_path}: {str(e)}")
        return False

def clear_data_folder():
    """Clear the entire data directory"""
    try:
        data_dir = Path("data")
        if data_dir.exists():
            shutil.rmtree(data_dir)
            data_dir.mkdir(exist_ok=True)
            return True
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
    """Display PDF using PDF.js"""
    try:
        custom_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>PDF Viewer</title>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.11.338/pdf.min.js"></script>
                <style>
                    #pdf-container {
                        width: 100%;
                        height: 1200px;
                        overflow: auto;
                        background: #f8f9fa;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                    }
                    #pdf-canvas {
                        width: 100%;
                        height: auto;
                        display: block;
                    }
                </style>
            </head>
            <body>
                <div id="pdf-container">
                    <canvas id="pdf-canvas"></canvas>
                </div>
                <script>
                    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.11.338/pdf.worker.min.js';
                    
                    const pdfData = atob('PDFDATA');
                    
                    async function renderPDF() {
                        const pdf = await pdfjsLib.getDocument({data: pdfData}).promise;
                        const page = await pdf.getPage(1);
                        const canvas = document.getElementById('pdf-canvas');
                        const context = canvas.getContext('2d');
                        
                        // Get container width
                        const container = document.getElementById('pdf-container');
                        const desiredWidth = container.clientWidth - 20;
                        
                        // Calculate scale to fit width
                        const viewport = page.getViewport({scale: 1.0});
                        const scale = desiredWidth / viewport.width;
                        const scaledViewport = page.getViewport({scale: scale});
                        
                        // Set canvas dimensions
                        canvas.width = scaledViewport.width;
                        canvas.height = scaledViewport.height;
                        
                        await page.render({
                            canvasContext: context,
                            viewport: scaledViewport
                        }).promise;
                    }
                    
                    renderPDF();
                    window.addEventListener('resize', renderPDF);
                </script>
            </body>
            </html>
        """

        with open(pdf_path, "rb") as file:
            base64_pdf = base64.b64encode(file.read()).decode('utf-8')

        custom_html = custom_html.replace('PDFDATA', base64_pdf)
        st.components.v1.html(custom_html, height=1250)

        with open(pdf_path, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
            st.download_button(
                label="📥 Download PDF",
                data=PDFbyte,
                file_name="resume.pdf",
                mime='application/pdf'
            )

    except Exception as e:
        st.error(f"PDF display error: {str(e)}")

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

    # Add sidebar toggle button with adjusted position
    st.markdown("""
        <div class='sidebar-toggle' onclick='window.dispatchEvent(new KeyboardEvent("keydown", {key: ".", ctrlKey: true}))'>
            ☰
        </div>
    """, unsafe_allow_html=True)

    # Sidebar content
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

            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{indent}📁 {relative_path}")
            with col2:
                if st.button("❌", key=f"clear_{folder}"):
                    if clear_specific_folder(folder):
                        st.success(f"Cleared {relative_path}")
                        st.rerun()

    # Main content area
    if st.session_state.stage == 'input':
        # Create a container for the URL input to ensure proper spacing
        with st.container():
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
                        st.session_state.stage = 'review'
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                    finally:
                        logger.removeHandler(handler)
                else:
                    st.warning("Please enter a job URL")

    elif st.session_state.stage == 'review':
        container = st.container()
        with container:
            left_col, right_col = st.columns([1, 1])

            with left_col:
                edited_yaml = st.text_area(
                    "Review Resume YAML",
                    st.session_state.yaml_content,
                    height=800
                )
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
                        st.rerun()

            with right_col:
                if edited_yaml != st.session_state.last_yaml:
                    st.session_state.last_yaml = edited_yaml
                    pdf_path = generate_preview_pdf(
                        edited_yaml,
                        st.session_state.resume_improver
                    )
                    if pdf_path:
                        st.session_state.pdf_path = pdf_path
                        st.session_state.show_preview = True

                if hasattr(st.session_state, 'show_preview') and hasattr(st.session_state, 'pdf_path'):
                    st.subheader("PDF Preview")
                    display_pdf(st.session_state.pdf_path)

if __name__ == "__main__":
    main()