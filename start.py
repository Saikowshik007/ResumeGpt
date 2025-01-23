import streamlit as st
import logging
import services
import yaml

class StreamlitHandler(logging.Handler):
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
    st.title("Resume Tailoring Tool")

    if 'stage' not in st.session_state:
        st.session_state.stage = 'input'
        st.session_state.resume_improver = None
        st.session_state.yaml_content = None

    if st.session_state.stage == 'input':
        url = st.text_input("Enter Job URL:", placeholder="https://example.com/job/...")

        if st.button("Analyze Job", key="analyze_btn"):
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
        edited_yaml = st.text_area("Review Resume", st.session_state.yaml_content, height=400)

        if st.button("Confirm and Generate PDF", key="download_btn"):
            try:
                yaml_dict = yaml.safe_load(edited_yaml)
                yaml_dict["editing"] = False

                with open(st.session_state.resume_improver.yaml_loc, 'w') as f:
                    yaml.dump(yaml_dict, f)
                st.session_state.resume_improver.create_pdf(auto_open=False)
                st.success("PDF generated successfully!")
                st.session_state.stage = 'input'
            except Exception as e:
                st.error(f"Error saving changes: {str(e)}")

        if st.button("Open PDF", key="open_pdf"):
            pdf_path = os.path.join(st.session_state.resume_improver.yaml_loc, "Sai_Ananthula_resume.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name="SAI_ANANTHULA_resume.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("PDF not found. Please generate it first.")

        if st.button("Cancel", key="cancel_btn"):
            st.session_state.stage = 'input'
            st.rerun()

if __name__ == "__main__":
    main()