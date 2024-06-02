import os
import streamlit as st
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
from google.cloud import storage
from google.oauth2 import id_token
from google.auth.transport import requests
from google.oauth2 import service_account
from st_files_connection import FilesConnection
from httpx_oauth.clients.google import GoogleOAuth2
from google.api_core.retry import Retry


CLIENT_ID = st.secrets.gcs_connections.CLIENT_ID
CLIENT_SECRET = st.secrets.gcs_connections.CLIENT_SECRET
REDIRECT_URI = st.secrets.gcs_connections.REDIRECT_URI


# Initialize the Streamlit app
st.title("PDF Parser App")

# Create a file uploader
uploaded_pdf = st.file_uploader("Upload a PDF file", type=["pdf"])


# Create a button to trigger the parsing
parse_button = st.button("Parse PDF")

# Define the GCS bucket and credentials
GCS_BUCKET_NAME = "myfirstbucketof"
# GCS_CREDENTIALS = st.secrets.g_credentials
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GCS_CREDENTIALS

# # Create a GCS client
# client = storage.Client.from_service_account_json(GCS_CREDENTIALS)

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcs_connections"]
)
client = storage.Client(credentials=credentials)    

# Define the Vertex AI model and settings
vertexai.init(project="poised-climate-423605-k7", location="us-central1")
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
    #vertexai.init(project="poised-climate-423605-k7", location="us-central1",credentials=credentials)
    responses = model.generate_content(
        [document1, """Parse the given pdf"""],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    # Print the parsed text
    for response in responses:
        st.write(response.text)

# Trigger the parsing function when the button is clicked
if parse_button:
    parse_pdf(uploaded_pdf)