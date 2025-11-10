import streamlit as st
import sys
import os

# Add project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables BEFORE importing other modules
from utils.config.env_loader import load_env
load_env()

# Configure page
st.set_page_config(
    page_title="TalentMatch - 智能人才推荐",
    page_icon="👥"
)

# Import and run the recommendation page directly
from page.resume_recommendation import main as recommendation_main

# Run the recommendation system
recommendation_main()
