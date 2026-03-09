# cv_builder_ollama_unicode.py

import os
import json
from datetime import datetime
import streamlit as st
from paddleocr import PaddleOCR
from PIL import Image
import numpy as np
from fpdf import FPDF
import ollama

# ==============================
# CONFIG
# ==============================
MODEL_NAME = "phi"  # Ollama local model
CHAT_FILE = "cv_chats_ollama.json"

# ==============================
# LOAD & SAVE CHAT FUNCTIONS
# ==============================
def load_chats():
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_chats(chats):
    with open(CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, indent=4, ensure_ascii=False)

# ==============================
# SESSION STATE
# ==============================
if "chats" not in st.session_state:
    st.session_state.chats = load_chats()
if "current_chat" not in st.session_state:
    st.session_state.current_chat = None

# ==============================
# OCR
# ==============================
@st.cache_resource
def load_ocr():
    return PaddleOCR(use_angle_cls=True, lang='en')

ocr = load_ocr()

# ==============================
# SIDEBAR CHAT HISTORY
# ==============================
st.sidebar.title("💬 Chat History")
if st.sidebar.button("➕ New Chat"):
    chat_id = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.chats[chat_id] = []
    st.session_state.current_chat = chat_id
    save_chats(st.session_state.chats)
    st.rerun()

for chat_id in list(st.session_state.chats.keys()):
    col1, col2 = st.sidebar.columns([4, 1])
    if col1.button(chat_id):
        st.session_state.current_chat = chat_id
        st.rerun()
    if col2.button("❌", key=chat_id):
        del st.session_state.chats[chat_id]
        save_chats(st.session_state.chats)
        st.session_state.current_chat = None
        st.rerun()

# ==============================
# MAIN UI
# ==============================

st.set_page_config(
    page_title="Personalized CV",
    page_icon="🤖",initial_sidebar_state="collapsed"
)

st.title("📝 Personalized Cover Letter Generator")

if not st.session_state.current_chat:
    st.info("👈 Click 'New Chat' to start")
    st.stop()

messages = st.session_state.chats[st.session_state.current_chat]

# Display chat messages
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==============================
# FILE UPLOAD + OCR
# ==============================
uploaded_files = st.file_uploader(
    "📂 Upload Resume/Certificates/Marksheets",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

cv_output = None

if uploaded_files:
    combined_text = ""
    with st.spinner("🔍 Extracting text from documents..."):
        for uploaded_file in uploaded_files:
            image = Image.open(uploaded_file)
            img_array = np.array(image)
            try:
                result = ocr.ocr(img_array)
            except Exception as e:
                result = []
                st.warning(f"⚠️ OCR failed for {uploaded_file.name}: {str(e)}")
            if result and result[0]:
                for line in result[0]:
                    combined_text += line[1][0] + "\n"

    if combined_text.strip():
        st.success("✅ Documents processed successfully!")

        system_prompt = """
You are an expert professional CV writer.
Using the extracted text, generate a clean,
modern, ATS-friendly CV with the following sections:
Respected Hiring Mnager,

- Full Name
- Contact Information
- Professional Summary
- Education
- Experience
- Skills
- Certifications
- Projects
- Achievements (if available)

Format professionally with proper headings, bullet points,
and clear structure suitable for recruiters.
"""

        with st.spinner("🧠 Generating Professional CV..."):
            try:
                response = ollama.chat(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": combined_text}
                    ],
                    options={"temperature":0.7}
                )
                cv_output = response["message"]["content"]
            except Exception as e:
                cv_output = f"⚠️ Ollama Error: {str(e)}"

        messages.append({"role": "assistant", "content": cv_output})
        save_chats(st.session_state.chats)

        with st.chat_message("assistant"):
            st.markdown(cv_output)

# ==============================
# CHAT INPUT
# ==============================
if prompt := st.chat_input("Ask anything or edit your CV..."):
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    system_prompt = "You are a highly intelligent and professional AI assistant. Provide structured, clear, and useful responses."

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": system_prompt}] +
                     messages,
            options={"temperature":0.7}
        )
        reply = response["message"]["content"]
    except Exception as e:
        reply = f"⚠️ Ollama Error: {str(e)}"

    messages.append({"role": "assistant", "content": reply})
    save_chats(st.session_state.chats)
    with st.chat_message("assistant"):
        st.markdown(reply)

# ==============================
# PDF DOWNLOAD (Unicode-safe)
# ==============================
if cv_output:
    def generate_pdf(text):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Unicode-safe font
        font_path = "DejaVuSansCondensed.ttf"  # Place this TTF file in same folder
        pdf.add_font("DejaVu", "", font_path, uni=True)
        pdf.set_font("DejaVu", size=12)

        for line in text.split("\n"):
            pdf.multi_cell(0, 8, line)
        pdf_file = "generated_cv.pdf"
        pdf.output(pdf_file)
        return pdf_file

    pdf_file = generate_pdf(cv_output)
    with open(pdf_file, "rb") as f:
        st.download_button(
            label="📄 Download CV as PDF",
            data=f,
            file_name="My_CV.pdf",
            mime="application/pdf"
        )