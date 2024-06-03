import os
import streamlit as st
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
from google.cloud import storage
from google.oauth2 import service_account
from google.api_core.retry import Retry

# Initialize the Streamlit app
st.title("PDF Parser App")

# Initialize session state
if "is_parsing" not in st.session_state:
    st.session_state.is_parsing = False

if "parse_another" not in st.session_state:
    st.session_state.parse_another = False

# Define the GCS bucket and credentials
GCS_BUCKET_NAME = "myfirstbucketof"

# Create API client
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcs_connections"]
)
client = storage.Client(credentials=credentials)

# Define the Vertex AI model and settings
vertexai.init(project="poised-climate-423605-k7", location="us-central1", credentials=credentials)
model = GenerativeModel("gemini-1.5-flash-preview-0514")
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 1,
    "top_p": 0.95,
}
safety_settings = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# Define the parsing function
def parse_pdf(uploaded_pdf):
    # Upload the PDF file to GCS
    bucket = client.get_bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(uploaded_pdf.name)

    retry = Retry(deadline=300)  # 5 minutes timeout
    blob.upload_from_file(uploaded_pdf, retry=retry, timeout=300)  # Set appropriate timeout

    # Create a Part object from the GCS URI
    document1 = Part.from_uri(f"gs://{GCS_BUCKET_NAME}/{uploaded_pdf.name}", mime_type="application/pdf")

    responses = model.generate_content(
        [document1, """Parse the given pdf"""],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    # Collect all response texts
    parsed_text = ""
    for response in responses:
        parsed_text += response.text + "\n"

    return parsed_text

# Create a file uploader and disable it when parsing
uploaded_pdf = st.file_uploader("Upload a PDF file", type=["pdf"], disabled=st.session_state.is_parsing)

# UI layout for buttons
col1, col2 = st.columns([1, 1])

with col1:
    parse_button = st.button("Parse PDF", disabled=(uploaded_pdf is None or st.session_state.is_parsing))

with col2:
    if st.session_state.parse_another:
        parse_another_button = st.button("Parse Another Document")
    else:
        parse_another_button = None

# Trigger the parsing function when the button is clicked
if parse_button:
    st.session_state.is_parsing = True
    with st.spinner('Parsing the document...'):
        parsed_text = parse_pdf(uploaded_pdf)
        
    # Save the parsed text to a .doc file
    doc_file_name = uploaded_pdf.name.split(".pdf")[0] + "_parsed_text.doc"
    doc_file_path = os.path.join("/tmp", doc_file_name)
    with open(doc_file_path, "w") as doc_file:
        doc_file.write(parsed_text)
    
    # Provide the download link
    with open(doc_file_path, "rb") as doc_file:
        st.download_button(
            label="📄 Download Parsed Text",
            data=doc_file,
            file_name=doc_file_name,
            mime="application/msword",
            key="download-button",
            help="Click to download the parsed document as a .doc file.",
        )

    st.success("Parsing complete. You can download the parsed text.")
    st.session_state.parse_another = True
    st.session_state.is_parsing = False

# Show Parse Another Document button if the document was parsed
if parse_another_button:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_rerun()
