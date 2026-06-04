import os
import streamlit as st
import pymupdf
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_cerebras import ChatCerebras
from langchain_core.output_parsers import PydanticOutputParser
from typing import Optional
import pydantic
from DB import (insert_candidate, candidate_exsits, insert_projects, insert_skills)
from dotenv import load_dotenv


load_dotenv()


if not os.getenv("CEREBRAS_API_KEY"):
    st.error("❌ CEREBRAS_API_KEY not found in .env file. Please check your configuration.")
    st.stop()


st.set_page_config(page_title="RecruitAI", page_icon=":robot_face", layout="wide")
st.title("Recruit.AI")

st.markdown("""This is an Resume Assistant""")

# ======================================================
# FILE UPLOAD
# ======================================================

file_uploaded = st.file_uploader(
    "Upload CV/Resume",
    type=["pdf"],
    key="file_uploaded"
)

path = r"C:\GenAi\uploaded_files"


# Initialize session state to store extracted data
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'show_preview' not in st.session_state:
    st.session_state.show_preview = False
if 'text_extracted' not in st.session_state:
    st.session_state.text_extracted = None
if 'file_processed' not in st.session_state:
    st.session_state.file_processed = False

if file_uploaded and file_uploaded.type == "application/pdf":
    content = file_uploaded.read()

    file_path = os.path.join(path, file_uploaded.name)

    with open(file_path, 'wb') as file:
        file.write(content)

    # ======================================================
    # FILE TEXT EXTRACTED
    # ======================================================

    resume_doc = pymupdf.open(file_path)

    text_extracted = ""

    for i in resume_doc:
        text_extracted += i.get_text()

    # Close the document
    resume_doc.close()
    
    st.session_state.text_extracted = text_extracted

    # ======================================================
    # FILE TEXT VALIDATION
    # ======================================================

    def text_validator(text):
        
        sections = ["experience", "education", "skills", "email"]

        condition_1 = text is not None
        condition_2 = text.strip()
        condition_3 = any(section in text.lower() for section in sections)
        condition_4 = len(text) > 200

        if condition_1 and condition_2 and condition_3 and condition_4:
            return True
        else:
            return False

    if text_validator(text_extracted):
        st.session_state.file_processed = True
        
        # ======================================================
        # PREVIEW RESUME TEXT (optional)
        # ======================================================
        with st.expander("📄 Preview Resume Text (Optional)"):
            st.text_area("Extracted Text Preview", text_extracted[:1000] + "...", height=200, disabled=True)
        
        # ======================================================
        # ANALYZE RESUME BUTTON
        # ======================================================
        if st.button("🔍 Analyze Resume", type="primary", use_container_width=True):
            with st.spinner("Extracting information from resume..."):
                # ======================================================
                # PROMPT DESIGN
                # ======================================================
                
                # pydantic parser
                class Resume(pydantic.BaseModel):
                    first_name: str
                    last_name: str
                    mobile_no: str
                    email_id: str
                    nationality: Optional[str] = "NA"
                    highest_qualification: Optional[str] = "NA"
                    total_experience_years: Optional[float] = 0.0
                    projects_worked: Optional[int] = 0
                    projects_names: Optional[list] = None
                    projects_description: Optional[list] = None
                    project_duration: Optional[list] = None  
                    skills: Optional[list] = None

                template = """ Act as an Resume Extractor and Extract the required data from the document 
                {format_instructions}
                document: {resume}

                Required information:
                    First Name - This should be the First name of the candidate.
                    Last Name - This should be the Last name or sirname of the candidate.
                    Mobile Number - Every person maintains a mobile number which will be a 10 digit number.
                    Email id - This should be the email address of the candidate.
                    Nationality - The candidate belongs to a country. If no country or nation information available in given document, please return just "NA". 
                    Highest Qualification - The candiate can have multiple degrees. Just pick only the highest degree of the candidate. 
                    Total Number of Years of Experience - This is nothing but, how many years the candidate worked in different organizations in his/her career. if you find the experince, the extracted value should be an float.
                    Total Number of Project worked on
                    Project Names - The candidate may worked in multiple projects just pick latest 3 projects with project name and give them in a list. Make sure this field is must if the total projects worked count is more than 0 then this needs to be not NA if the total projects worked is 0 then this can be NA.  
                    Project Description - For the projects name that you have extracted add descption that is present for the respective project name and in same order add them in list and give me in a list. 
                    Projects Duration - For the project that we added in list we need the duration of the each project so please add the duration of the project into a list and give me the list of the project that he worked.
                    Skillsets - The candidate have skills in his resume we need all skills in a list format. 
                
                Instructions:
                        1) Strictly extract the above required information only. Do not extract any other extra information.
                        2) If any of the above infomration not found in the given document, return strictly "NA". Do not generate any other answers.

                """
                # llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
                # llm    = llm = ChatOllama(model="Qwen3:4B",temperature=0)
                llm = ChatCerebras(model="gpt-oss-120b",temperature=0)
                parser = PydanticOutputParser(pydantic_object=Resume)
                prompt = PromptTemplate(template=template, input_variables=['resume'], partial_variables={'format_instructions': parser.get_format_instructions()})

                chain = prompt | llm | parser

                response = chain.invoke({'resume': text_extracted})
                
                st.session_state.extracted_data = response
                
                # ======================================================
                # SHOW STRUCTURED DATA
                # ======================================================
                st.success("✅ Resume Analysis Complete!")
                
                with st.expander("📊 Extracted Information", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Personal Information**")
                        st.write(f"• **First Name:** {response.first_name}")
                        st.write(f"• **Last Name:** {response.last_name}")
                        st.write(f"• **Mobile:** {response.mobile_no}")
                        st.write(f"• **Email:** {response.email_id}")
                        st.write(f"• **Nationality:** {response.nationality}")
                        st.write(f"• **Highest Qualification:** {response.highest_qualification}")
                        st.write(f"• **Total Experience:** {response.total_experience_years} years")
                        st.write(f"• **Projects Worked:** {response.projects_worked}")
                    
                    with col2:
                        st.markdown("**Skills & Projects**")
                        st.markdown("**Skills:**")
                        if response.skills:
                            skills_str = ", ".join(response.skills[:10])
                            if len(response.skills) > 10:
                                skills_str += f" ... and {len(response.skills) - 10} more"
                            st.write(f"• {skills_str}")
                        else:
                            st.write("• No skills extracted")
                        
                        st.markdown("**Projects:**")
                        if response.projects_names:
                            for i, project in enumerate(response.projects_names[:3], 1):
                                st.write(f"• {i}. {project}")
                        else:
                            st.write("• No projects found")
                    
                    if response.projects_names and response.projects_description:
                        st.markdown("---")
                        st.markdown("### 📂 Project Details")
                        
                        for i, (name, desc) in enumerate(zip(response.projects_names, response.projects_description), 1):
                            st.markdown(f"**Project {i}: {name}**")
                            st.write(f"**Description:** {desc[:200]}..." if len(desc) > 200 else f"**Description:** {desc}")
                            
                            if response.project_duration:
                                if isinstance(response.project_duration, list) and i-1 < len(response.project_duration):
                                    st.write(f"**Duration:** {response.project_duration[i-1]}")
                                elif isinstance(response.project_duration, str):
                                    st.write(f"**Duration:** {response.project_duration}")
                            
                            if i < len(response.projects_names):
                                st.markdown("---")
                st.info("ℹ️ Please review the extracted information before saving to database.")
                
    else:
        st.error("❌ Please Upload a Valid PDF Document with proper resume content")
        st.session_state.file_processed = False

# ======================================================
# SAVE TO DATABASE BUTTON
# ======================================================
if st.session_state.extracted_data and st.session_state.file_processed:
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("💾 Save to Database", type="primary", use_container_width=True):
            try:
                with st.spinner("Saving to database..."):
                    response = st.session_state.extracted_data
                    
                    # Check if candidate exists
                    if candidate_exsits(response):
                        st.error("⚠️ Candidate already exists in our database!")
                    else:
                        # Insert into database
                        candidate_id = insert_candidate(response)
                        
                        if candidate_id:
                            # Insert projects if available
                            if response.projects_names and response.projects_names != "NA":
                                insert_projects(candidate_id, response.projects_names, response.projects_description)
                            
                            # Insert skills if available
                            if response.skills and response.skills != "NA":
                                insert_skills(candidate_id, response.skills)
                            
                            st.success(f"✅ Data inserted successfully! (Candidate ID: {candidate_id})")
                            
                            # Show success details
                            with st.expander("📋 Inserted Data Summary"):
                                st.write(f"**Candidate:** {response.first_name} {response.last_name}")
                                st.write(f"**Email:** {response.email_id}")
                                st.write(f"**Skills Count:** {len(response.skills) if response.skills else 0}")
                                st.write(f"**Projects Count:** {len(response.projects_names) if response.projects_names else 0}")
                        else:
                            st.error("❌ Failed to insert candidate data")
                            
            except Exception as e:
                st.error(f"❌ Error saving to database: {str(e)}")

# ======================================================
# FOOTER WITH INSTRUCTIONS
# ======================================================
st.divider()
st.markdown("""
### 📌 Instructions:
1. Upload a PDF resume
2. Preview the extracted text (optional)
3. Click **Analyze Resume** to extract information
4. Review the structured data
5. Click **Save to Database** to store the information
""")