import streamlit as st
import pandas as pd
import json
import os
import pdfplumber
import docx

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="InternMatch Pro", layout="wide")

st.markdown(
"""
<style>
.stApp{
background-color:#FF8C00;
}

label{
color:white !important;
}

.stRadio label{
color:white !important;
}

.stButton button{
color:white !important;
background-color:#1f77b4;
}
</style>
""",
unsafe_allow_html=True
)

st.markdown(
"""
<h1 style='text-align:center;color:black;font-size:50px;'>
SkillMatch AI – Intelligent Internship Portal
</h1>
""",
unsafe_allow_html=True
)


# -----------------------------
# FILE PATHS
# -----------------------------
USER_FILE = "users.json"
PROFILE_FILE = "profiles.json"


# -----------------------------
# LOAD USERS SAFELY
# -----------------------------
if os.path.exists(USER_FILE):
    try:
        with open(USER_FILE,"r") as f:
            users = json.load(f)
    except:
        users = {}
else:
    users = {}

# -----------------------------
# LOAD PROFILES SAFELY
# -----------------------------
if os.path.exists(PROFILE_FILE):
    try:
        with open(PROFILE_FILE,"r") as f:
            profiles = json.load(f)
    except:
        profiles = {}
else:
    profiles = {}


# -----------------------------
# SESSION STATE
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# -----------------------------
# RESUME TEXT EXTRACTION
# -----------------------------
def extract_resume_text(uploaded_file):

    text = ""

    if uploaded_file.name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text()

    elif uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text

    return text


# -----------------------------
# LOAD DATASET
# -----------------------------
@st.cache_data
def load_data():
    return pd.read_csv("internship_dataset_500.csv")

df = load_data()


# -----------------------------
# LOGIN / REGISTER PAGE
# -----------------------------
if not st.session_state.logged_in:

    option = st.radio("Select Option",["Register","Login"])

    # REGISTER
    if option == "Register":

        st.subheader("Register")

        email = st.text_input("Email")
        password = st.text_input("Password",type="password")

        if st.button("Register"):

            if email in users:
                st.error("Email already registered")

            else:
                users[email] = password

                with open(USER_FILE,"w") as f:
                    json.dump(users,f)

                st.success("Registration successful! Please login.")


    # LOGIN
    if option == "Login":

        st.subheader("Login")

        email = st.text_input("Email")
        password = st.text_input("Password",type="password")

        if st.button("Login"):

            if email in users and users[email] == password:

                st.session_state.logged_in = True
                st.session_state.current_user = email

                st.success("Login successful")
                st.rerun()

            else:
                st.error("Invalid email or password")


# -----------------------------
# MAIN PORTAL
# -----------------------------
else:

    menu = st.sidebar.radio(
        "Navigation",
        ["Dashboard","My Profile","Search Internship","Logout"]
    )

    # DASHBOARD
    if menu == "Dashboard":

        st.header("Dashboard")

        col1,col2,col3 = st.columns(3)

        col1.metric("Total Internships",len(df))
        col2.metric("Companies",df["Company Name"].nunique())
        col3.metric("Locations",df["Location"].nunique())


    # PROFILE
    elif menu == "My Profile":

        st.header("Student Profile")

        email = st.session_state.current_user
        saved_profile = profiles.get(email,{})

        name = st.text_input("Name",saved_profile.get("name",""))
        college = st.text_input("College",saved_profile.get("college",""))
        skills = st.text_area("Skills",saved_profile.get("skills",""))
        interests = st.text_area("Interests",saved_profile.get("interests",""))
        cgpa = st.number_input(
            "CGPA",0.0,10.0,
            value=float(saved_profile.get("cgpa",0))
        )

        if st.button("Save Profile"):

            profiles[email] = {
                "name":name,
                "college":college,
                "skills":skills,
                "interests":interests,
                "cgpa":cgpa
            }

            with open(PROFILE_FILE,"w") as f:
                json.dump(profiles,f)

            st.success("Profile saved successfully")


    # SEARCH INTERNSHIP
    elif menu == "Search Internship":

        st.header("Find Internship Opportunities")

        email = st.session_state.current_user

        if email not in profiles:
            st.warning("Please complete your profile first")

        else:

            uploaded_file = st.file_uploader(
                "Upload Resume (PDF/DOCX)",
                type=["pdf","docx"]
            )

            role_input = st.text_input("Enter Internship Role")

            if st.button("Find Internships"):

                if uploaded_file is not None:
                    resume_text = extract_resume_text(uploaded_file)
                    skills_text = resume_text.lower()

                else:
                    skills_text = profiles[email]["skills"]

                filtered_df = df[
                    df["Internship Role"].str.contains(role_input,case=False)
                ]

                if filtered_df.empty:
                    st.warning("No exact match found. Showing all internships")
                    filtered_df = df

                roles = filtered_df["Internship Role"].astype(str).tolist()

                vectorizer = TfidfVectorizer()
                vectors = vectorizer.fit_transform(roles + [skills_text])

                similarity = cosine_similarity(vectors[-1],vectors[:-1])

                filtered_df["Match Score"] = similarity[0] * 100

                results = filtered_df.sort_values(
                    by="Match Score",
                    ascending=False
                )

                st.subheader("Recommended Internship Opportunities")

                st.dataframe(results[
                    ["Internship Role","Company Name","Location","Duration","Match Score"]
                ])


    # LOGOUT
    elif menu == "Logout":

        st.session_state.logged_in = False
        st.success("Logged out successfully")
        st.rerun()
