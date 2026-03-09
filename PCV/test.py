import numpy
print(numpy.__version__)

import streamlit as st
import openai

openai.api_key = st.secrets.get("OPENAI_API_KEY")