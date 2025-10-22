import streamlit as st
import boto3
import requests
import json
from datetime import datetime
import base64
import io

# AWS clients (S3 only for listing; region fixed to us-east-1 for security)
s3 = boto3.client('s3', region_name='us-east-1')

# Bucket name
BUCKET_NAME = 'traffic-sign-project-bucket'

# API Gateway URL (us-east-1 hardcoded; users can't change it)
API_URL = "https://6awdqqg9fl.execute-api.us-east-1.amazonaws.com/dev"

# Page config
st.set_page_config(page_title="Traffic Sign Indicator", layout="wide")

# Custom CSS for gradient background (red-orange-yellow like Whizlabs) and centering
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #FF0000 0%, #FF4500 25%, #FFA500 50%, #FFD700 75%, #FFFF00 100%);
        background-attachment: fixed;
    }
    .main .block-container {
        background: rgba(255, 255, 255, 0.9);
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        color: #333;  /* Dark grey for visibility */
        margin: 0 auto;
        max-width: 800px;
    }
    h1, h2, p {
        color: #333 !important;
    }
    .stSelectbox > div > div > div {
        text-align: center;
    }
    .stButton > button {
        width: 100%;
        background-color: #FF4500;
        color: white;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Whizlabs logo at top-middle
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("https://play-lh.googleusercontent.com/pUxNfrcwglo40Se238mGSMCQwBI-8niKDse6zdvgVnR4iCkQMckNqoE_WhcCSQVz9w", width=200, use_column_width=True)

# Title page
if 'page' not in st.session_state:
    st.session_state.page = 'home'

if st.session_state.page == 'home':
    st.title("🚦 Traffic Sign Indicator 🚦")
    st.write("Welcome to the Smart City Traffic Sign Recognition App!")
    
    if st.button("Go", use_container_width=True):
        st.session_state.page = 'analyzer'
        st.rerun()
    
    st.balloons()  # Fun effect

elif st.session_state.page == 'analyzer':
    st.title("🚦 Analyze Traffic Sign 🚦")
    
    # Dynamically fetch images from S3 inputs/ folder
    if 'image_options' not in st.session_state:
        try:
            response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix='inputs/', Delimiter='/')
            image_options = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.lower().endswith(('.jpg', '.jpeg', '.png')):
                        image_name = key.split('/')[-1]  # e.g., 'image-1.jpg'
                        image_options.append(image_name)
            st.session_state.image_options = sorted(image_options) if image_options else ['No images found']
        except Exception as e:
            st.session_state.image_options = ['Error loading images']
    
    # Image selection dropdown
    selected_image = st.selectbox("Select an image from S3 inputs/ folder:", st.session_state.image_options, help="Dynamically loaded from S3")
    
    # "Click me" button to trigger selection (optional, as selectbox auto-updates)
    if st.button("Click me to Select Image", use_container_width=True):
        st.rerun()  # Refresh to highlight selection
    
    context_info = st.text_input("Driving Context (optional, default: rainy, 60 km/h):", value="rainy, 60 km/h")
    
    if st.button("Analyze Sign", use_container_width=True):
        with st.spinner("Analyzing traffic sign via API..."):
            # Prepare payload for API Gateway (Lambda)
            payload = {
                "image_key": f"inputs/{selected_image}",
                "context": context_info
            }
            
            try:
                # POST to API Gateway (hardcoded us-east-1 endpoint; no user changes)
                response = requests.post(
                    API_URL,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                    timeout=60  # Allow time for Bedrock
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Display results (centered)
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col2:
                        st.subheader("📸 Selected Image:")
                        st.markdown(f"**{selected_image}**")
                        
                        st.subheader("📝 Sign Description:")
                        st.write(result.get("sign_description", "No description available"))
                        
                        st.subheader("⚠️ Precaution & Warning:")
                        st.markdown(f"**\"{result.get('precaution_warning', 'No warning available')}\"**")
                        
                        st.success("✅ Analysis complete! Stored in DynamoDB via Lambda.")
                else:
                    st.error(f"API Error: {response.status_code} - {response.text}")
                    
            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {str(e)}")
    
    # Back button
    if st.button("← Back to Home", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()
