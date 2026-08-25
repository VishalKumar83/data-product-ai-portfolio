import sys
import os
import streamlit as st

# Tell Python where to find your AI agents
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from vc_firm.crew import VcFirmCrew

# --- 1. SET UP THE WEB PAGE ---
st.set_page_config(page_title="AI Venture Capitalist", page_icon="💼", layout="wide")
st.title("💼 Autonomous VC Firm")
st.markdown("Paste a startup pitch below. Our 7-agent AI team will conduct full due diligence and return a final verdict.")

# --- 2. THE INPUT BOX ---
pitch_text = st.text_area(
    "Startup Pitch:", 
    height=200, 
    placeholder="e.g., AeroDrive is raising $2M at a $10M valuation to build flying cars. We have zero revenue..."
)

# --- 3. THE MAGIC BUTTON ---
if st.button("Run Due Diligence 🚀"):
    if not pitch_text.strip():
        st.error("Please enter a startup pitch first!")
    else:
        # Show a loading spinner while the AI thinks
        with st.spinner("The AI team is analyzing the pitch... This will take a few minutes."):
            
            # Feed the website text directly to your agents!
            inputs = {'pitch_data': pitch_text}
            VcFirmCrew().crew().kickoff(inputs=inputs)
            
            st.success("Analysis Complete!")
            
            # --- 4. DISPLAY THE RESULTS SIDE-BY-SIDE ---
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("📄 Due Diligence Report")
                if os.path.exists('due_diligence_report.md'):
                    with open('due_diligence_report.md', 'r') as f:
                        st.markdown(f.read())
                else:
                    st.error("Report failed to generate.")
                    
            with col2:
                st.subheader("⚖️ Managing Partner Verdict")
                if os.path.exists('partner_verdict.md'):
                    with open('partner_verdict.md', 'r') as f:
                        # Displaying the verdict in a highlighted box
                        st.info(f.read())
                else:
                    st.error("Verdict failed to generate.")