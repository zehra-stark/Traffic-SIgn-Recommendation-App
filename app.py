import streamlit as st
import boto3
import json
from datetime import datetime
import base64
import io

# AWS clients (assumes AWS credentials are configured)
s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('TrafficSignRecommendations')

# Bucket name
BUCKET_NAME = 'traffic-sign-project-bucket'

# Page config
st.set_page_config(page_title="Traffic Sign Indicator", layout="wide")

# Custom CSS for gradient background (red-orange-yellow like Whizlabs)
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
    }
    h1, h2, p {
        color: #333 !important;
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
    
    # Image selection dropdown
    image_options = ['image-1.jpg', 'image-2.jpg', 'image-3.jpg', 'image-4.jpg']
    selected_image = st.selectbox("Select an image from S3:", image_options, help="Choose image-*.jpg from inputs folder")
    
    context_info = st.text_input("Driving Context (optional, default: rainy, 60 km/h):", value="rainy, 60 km/h")
    
    if st.button("Analyze Sign", use_container_width=True):
        with st.spinner("Analyzing traffic sign..."):
            key = f"inputs/{selected_image}"
            
            # Step 1: Get image bytes from S3
            image_response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            image_bytes = image_response['Body'].read()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Step 2: Describe traffic sign with Bedrock
            describe_prompt = (
                "Describe the main traffic sign in this image precisely "
                "(e.g., 'No Right Turn', 'Stop', or 'Speed Limit 60'). "
                "Include shape, color, and symbols. Ignore the background."
            )
            
            describe_body = json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": describe_prompt},
                            {
                                "image": {
                                    "format": "jpeg" if key.lower().endswith('.jpg') else "png",
                                    "source": {"bytes": base64_image}
                                }
                            }
                        ]
                    }
                ],
                "inferenceConfig": {"maxTokens": 50, "temperature": 0.3}
            })
            
            describe_response = bedrock.invoke_model(
                modelId="amazon.nova-lite-v1:0",
                body=describe_body,
                contentType="application/json",
                accept="application/json"
            )
            
            describe_output = json.loads(describe_response["body"].read())
            sign_description = (
                describe_output.get("output", {})
                .get("message", {})
                .get("content", [{}])[0]
                .get("text", "")
                .strip()
            )
            
            if not sign_description or "no sign" in sign_description.lower():
                sign_description = "No clear traffic sign detected"
            
            # Step 3: Generate precaution/warning
            precaution_prompt = (
                f"You are a driving assistant. The detected traffic sign is '{sign_description}'. "
                f"Given the driving context '{context_info}', provide one concise precaution or safety warning."
            )
            
            precaution_body = json.dumps({
                "messages": [{"role": "user", "content": [{"text": precaution_prompt}]}],
                "inferenceConfig": {"maxTokens": 100, "temperature": 0.7}
            })
            
            precaution_response = bedrock.invoke_model(
                modelId="amazon.nova-lite-v1:0",
                body=precaution_body,
                contentType="application/json",
                accept="application/json"
            )
            
            precaution_output = json.loads(precaution_response["body"].read())
            precaution = (
                precaution_output.get("output", {})
                .get("message", {})
                .get("content", [{}])[0]
                .get("text", "")
                .strip()
            )
            
            # Step 4: Store in DynamoDB
            timestamp = datetime.utcnow().isoformat() + "Z"
            item = {
                "image_key": key,
                "sign_description": sign_description,
                "context": context_info,
                "precaution_warning": precaution,
                "timestamp": timestamp
            }
            table.put_item(Item=item)
            
            # Display results (centered)
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                st.subheader("📸 Selected Image:")
                st.write(f"**{selected_image}**")
                
                st.subheader("📝 Sign Description:")
                st.write(sign_description)
                
                st.subheader("⚠️ Precaution & Warning:")
                st.markdown(f"**\"{precaution}\"**")
                
                st.success("✅ Analysis complete! Stored in DynamoDB.")
    
    # Back button
    if st.button("← Back to Home", use_container_width=True):
        st.session_state.page = 'home'
        st.rerun()
