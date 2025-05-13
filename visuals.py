
import streamlit as st

def apply_custom_styles():
    st.markdown(
        """
        <style>
        /* Custom Background Image */
        body {
            background-image: url('https://www.cud.ac.ae/sites/default/files/general/2024/open_jan_1_desk.png');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }
        .stApp {
            background-color: rgba(0, 0, 0, 0.8); /* Dark overlay */
            color: #FFFFFF;
        }
        
        /* Red-themed elements */
        h1, h2, h3, h4 {
            color: #FF0000;  /* Red headers */
        }
        .stButton > button {
            background-color: #FF0000;  /* Red button background */
            color: #FFFFFF;  /* White text */
        }
        .stButton > button:hover {
            background-color: #CC0000;  /* Darker red on hover */
        }
        .stTextInput input {
            background-color: #333333;  /* Dark input box */
            color: #FFFFFF;  /* White text */
            border-color: #FF0000;  /* Red border */
        }
        .css-18ni7ap, .css-1d391kg {
            background-color: rgba(30, 30, 30, 0.9) !important;
            color: #FFFFFF !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div style="position: fixed; bottom: 10px; right: 10px; z-index: 100;">
            <img src="https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExYnpuajEwcnRzbGpwand2NDk1b2I0NnI1eG00NGJocGoxM3lkc2xqZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/x5wC9Udx9eUdeao5oE/giphy.gif" width="100">
        </div>
        """,
        unsafe_allow_html=True
    )
    

def show_custom_button(label="Run Agent", key="run_button"):
    return st.button(label, key=key)


#https://www.cud.ac.ae/sites/default/files/general/2024/open_jan_1_desk.png