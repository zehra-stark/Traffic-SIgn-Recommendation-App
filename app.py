import streamlit as st
import boto3
import requests
import json

# AWS client
s3 = boto3.client('s3', region_name='us-east-1')

# Constants
BUCKET_NAME = 'traffic-sign-project-bucket'
API_URL = "https://6awdqqg9fl.execute-api.us-east-1.amazonaws.com/dev"

# Page setup
st.set_page_config(page_title="Traffic Sign Indicator", layout="wide")

# Custom CSS
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #FF0000 0%, #FF4500 25%, #FFA500 50%, #FFD700 75%, #FFFF00 100%);
        background-attachment: fixed;
        color: #333;
    }
    .main .block-container {
        background: rgba(255,255,255,0.95);
        padding: 2rem 3rem;
        border-radius: 20px;
        box-shadow: 0px 0px 10px rgba(0,0,0,0.2);
        max-width: 850px;
        margin: auto;
    }
    h1, h2, h3, p {
        color: #333 !important;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF4500 !important;
        color: white !important;
        font-weight: bold;
        border-radius: 10px;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #FF6347 !important;
        transform: scale(1.03);
    }
    .logo {
        display: block;
        margin-left: auto;
        margin-right: auto;
        width: 90px;
    }
    .dropdown-label {
        font-weight: 500;
        color: #444;
        margin-bottom: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# Whizlabs logo
st.markdown(
    '<img src="https://play-lh.googleusercontent.com/pUxNfrcwglo40Se238mGSMCQwBI-8niKDse6zdvgVnR4iCkQMckNqoE_WhcCSQVz9w" class="logo">',
    unsafe_allow_html=True
)

# Navigation
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# ---------- HOME PAGE ----------
if st.session_state.page == 'home':
    st.title("🚦 Traffic Sign Indicator 🚦")
    st.write("Welcome to the Smart City Traffic Sign Recognition System.")
    if st.button("Start Analysis", use_container_width=True):
        st.session_state.page = 'analyzer'
        st.rerun()
    st.balloons()

# ---------- ANALYZER PAGE ----------
elif st.session_state.page == 'analyzer':
    st.title("🧠 Analyze Traffic Sign")

    # Image options (load once)
    if 'image_options' not in st.session_state:
        try:
            response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix='inputs/', Delimiter='/')
            imgs = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    if key.lower().endswith(('.jpg', '.jpeg', '.png')):
                        imgs.append(key.split('/')[-1])
            st.session_state.image_options = sorted(imgs) if imgs else ['No images found']
        except Exception as e:
            st.session_state.image_options = [f"Error: {e}"]

    # Button to reveal dropdown
    if 'show_dropdown' not in st.session_state:
        st.session_state.show_dropdown = False

    if st.button("Choose Me 🖼️", use_container_width=True):
        st.session_state.show_dropdown = True

    selected_image = None
    if st.session_state.show_dropdown:
        st.markdown('<div class="dropdown-label">📁 Select a Traffic Sign Image:</div>', unsafe_allow_html=True)
        selected_image = st.selectbox(
            "",
            st.session_state.image_options,
            key="img_select",
            label_visibility="collapsed"
        )
        st.session_state.selected_image = selected_image
        st.info(f"✅ Selected: {selected_image}")

    # Driving context
    context_info = st.text_input("Driving Context (optional):", value="rainy, 60 km/h")

    # Analyze Sign button
    if st.button("Analyze Sign", use_container_width=True):
        if 'selected_image' not in st.session_state:
            st.warning("Please choose an image first using the 'Choose Me 🖼️' button.")
        else:
            with st.spinner("Analyzing traffic sign via AI..."):
                payload = {
                    "image_key": f"inputs/{st.session_state.selected_image}",
                    "context": context_info
                }
                try:
                    response = requests.post(
                        API_URL,
                        headers={"Content-Type": "application/json"},
                        data=json.dumps(payload),
                        timeout=60
                    )
                    if response.status_code == 200:
                        result = response.json()

                        # Output in a card-like container
                        st.markdown("---")
                        st.markdown("### 📸 Selected Image")
                        st.markdown(f"**{st.session_state.selected_image}**")

                        st.markdown("### 📝 Sign Description")
                        st.write(result.get("sign_description", "No description available."))

                        st.markdown("### ⚠️ Precaution & Warning")
                        st.markdown(f"**\"{result.get('precaution_warning', 'No warning available.')}\"**")

                        st.success("✅ Analysis complete!")
                    else:
                        st.error(f"API Error: {response.status_code} - {response.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {str(e)}")

    if st.button("← Back to Home", use_container_width=True):
        st.session_state.page = 'home'
        st.session_state.show_dropdown = False
        st.rerun()

