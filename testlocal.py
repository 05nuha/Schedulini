
import os
import sys
import uuid
import json
import asyncio
import csv

import streamlit as st
from dotenv import load_dotenv
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
import google.generativeai as genai

from browser_use import Browser, Controller, Agent

from visuals import apply_custom_styles

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ✅ Load .env file
load_dotenv()

# ✅ Get API key
api_key = os.getenv("GOOGLE_API_KEY")

# ✅ Ensure API key is not None or empty
if not api_key:
    raise ValueError("GOOGLE_API_KEY is missing. Make sure it's in the .env file.")

# ✅ Configure API explicitly
genai.configure(api_key=api_key)

# ✅ Test API connection
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")  # or "gemini-2.5-pro-exp-03-25" for experimental

controller = Controller()

class Course:
    def __init__(self, course, course_name, credits, instructor, room, days, start_time, end_time, max_enrollment, total_enrollment):
        self.course = course
        self.course_name = course_name
        self.credits = credits
        self.instructor = instructor
        self.room = room
        self.days = days
        self.start_time = start_time
        self.end_time = end_time
        self.max_enrollment = max_enrollment
        self.total_enrollment = total_enrollment

    def __repr__(self):
        return f"{self.course} - {self.course_name} ({self.credits} Credits) by {self.instructor}"

class CourseNode:
    def __init__(self, course: Course):
        self.data = course
        self.next = None

class CourseLinkedList:
    def __init__(self):
        self.head = None

    def append(self, course: Course):
        new_node = CourseNode(course)
        if not self.head:
            self.head = new_node
        else:
            current = self.head
            while current.next:
                current = current.next
            current.next = new_node

    def to_list(self):
        result = []
        current = self.head
        while current:
            result.append(vars(current.data))
            current = current.next
        return result

    # def display_courses(self):
    #     courses = self.to_list()
    #     for index, course in enumerate(courses):
    #         print(f"{index + 1}. {course['course']} - {course['course_name']}")

    # def get_course_by_index(self, index: int):
    #     courses = self.to_list()
    #     if 0 <= index < len(courses):
    #         return courses[index]
    #     return None

    def to_text(self): #used for preview in streamlot
        """Convert linked list to formatted text for LLM context"""
        current = self.head
        courses_text = []
        while current:
            course = current.data
            courses_text.append(
                f"{course.course}: {course.course_name}\n"
                f"  • Instructor: {course.instructor}\n"
                f"  • Schedule: {course.days} {course.start_time}-{course.end_time}\n"
                f"  • Room: {course.room}\n"
                f"  • Enrollment: {course.total_enrollment}/{course.max_enrollment}"
            )
            current = current.next
        return "\n\n".join(courses_text)

def extract_json_from_history(raw_list):
    """Extracts the JSON portions from the agent's history result."""
    json_data_list = []
    for item in raw_list:
        if "json" in item:
            json_start = item.find("[")
            json_end = item.rfind("]") + 1
            if json_start != -1 and json_end != -1:
                json_data_list.append(item[json_start:json_end])
    return json_data_list

def parse_courses_to_linked_list(raw_list: str) -> CourseLinkedList:
    linked_list = CourseLinkedList()
    raw_json_list = extract_json_from_history(raw_list)

    if not raw_json_list:
        print("❌ No JSON found in extracted content.")
        return linked_list

    try:
        for raw_json in raw_json_list:
            try:
                json_data = json.loads(raw_json)
            except json.JSONDecodeError:
                print(f"❌ Failed to parse JSON: {raw_json}")
                continue

            if not isinstance(json_data, list):
                print("❌ JSON format is incorrect. Expected a list of courses.")
                continue

            for course in json_data:
                print(f"Processing course: {course.get('Course', 'Unknown Course')}")

                new_course = Course(
                    course=course.get("Course", ""),
                    course_name=course.get("Course Name", ""),
                    credits=course.get("Credits", ""),
                    instructor=course.get("Instructor", ""),
                    room=course.get("Room", ""),
                    days=course.get("Days", ""),
                    start_time=course.get("Start Time", ""),
                    end_time=course.get("End Time", ""),
                    max_enrollment=course.get("Max Enrollment", ""),
                    total_enrollment=course.get("Total Enrollment", ""),
                )
                linked_list.append(new_course)

        return linked_list

    except Exception as e:
        print(f"❌ Error processing courses: {e}")
        return linked_list

def write_courses_to_csv(course_list: CourseLinkedList, filename="courses.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Course", "Course Name", "Credits", "Instructor", "Room", "Days", "Start Time", "End Time", "Max Enrollment", "Total Enrollment"])

        current = course_list.head
        while current:
            course = current.data
            writer.writerow([course.course, course.course_name, course.credits, course.instructor, course.room, course.days, course.start_time, course.end_time, course.max_enrollment, course.total_enrollment])
            current = current.next

def login_successful(history_output):
    """Check if the agent output indicates a successful login."""
    # You can adjust this logic based on how failure is shown in history
    content = "".join(history_output).lower()
    failure_keywords = ["login failed", "invalid", "incorrect", "error"]
    return not any(keyword in content for keyword in failure_keywords)


async def main():
    st.title("🍁 CUD Course Extractor & Query System")

    apply_custom_styles()

    if 'course_linked_list' not in st.session_state:
        st.session_state.course_linked_list = None
    if 'courses_extracted' not in st.session_state:
        st.session_state.courses_extracted = False
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Welcome! Please extract courses first by clicking 'Run Agent'"}
        ]

    # LLM Selection
    choice = st.selectbox("Choose LLM Type:", ["Cloud (Gemini)", "Local (Ollama)"])

    if "llm_choice_key" not in st.session_state:
        st.session_state["llm_choice_key"] = f"llm_choice_{uuid.uuid4()}"

    llm_choice = st.radio(
        "Select an option:",
        ["Cloud (Gemini)", "Local (Ollama)"],
        key=st.session_state["llm_choice_key"]
    )

    if llm_choice == "Cloud (Gemini)":
        st.write("✅ Using Gemini (Cloud)")
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            st.error("❌ GOOGLE_API_KEY is missing. Make sure it's in the .env file.")
            st.stop()
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    else:
        st.write("✅ Using Local Ollama LLM")
        llm = ChatOllama(model="qwen2.5:3b")

    # Credentials Input
    username = st.text_input("Username", value="")
    password = st.text_input("Password", type='password', value="")

    if not username:
        username = os.getenv("CUD_USERNAME")
    if not password:
        password = os.getenv("CUD_PASSWORD")

    # Term Selection
    terms = [
        "FA 2020-21", "SP 2020-21", "SU 1 2020-21", "SU 2 2020-21",
        "FA 2021-22", "SP 2021-22", "SU 1 2021-22", "SU 2 2021-22",
        "FA 2022-23", "SP 2022-23", "SU 1 2022-23", "SU 2 2022-23",
        "FA 2023-24", "SP 2023-24", "SU 1 2023-24", "SU 2 2023-24",
        "FA 2024-25", "SP 2024-25", "SU 1 2024-25"
    ]
    selected_term = st.selectbox("Select a Term", terms)
    st.write(f"✅ You selected: {selected_term}")

    sensitive_data = {
        'username': username,
        'password': password,
        'selected_term': selected_term
    }

    initial_actions = [{'open_tab': {'url': "https://cudportal.cud.ac.ae/student/login.asp"}}]

    task = f'''
        
        1. Go to CUD portal login page
        2. Log in with username: {username} and password: {password}
        3. Select term: {selected_term} from the dropdown menu
        4. Navigate to "Course Offerings", IF ITS NOT THERE DONT DO ANYTHING ELSE MOVE ON TO STEP 5 PLEASE
        5. If you CANT navigate to Course offerings, this means the login information was wrong, clearly output 'login invalid, PLEASE RE-ENTER USER CREDENTIALS'.
        6. Click on "Show Filter"
        7. Select "SEAST" from divisions
        8. Click on "Apply filter" and WAIT for full load.
        9. After the filter is applied and courses are visible:
            a. Extract all course details in the "Course Offering List" ONLY
            b. Return data in EXACTLY this format as a JSON array:
               [
                 {{"Course": "...", "Course Name": "...", "Credits": "...", "Instructor": "...", "Room": "...", "Days": "...", "Start Time": "...", "End Time": "...", "Max Enrollment": "...", "Total Enrollment": "..."}},
                 {{...}},
                 ...
               ]

            c. EXTRACT ALL THE PAGES AVAILABLE, IF THERES 8 PAGES, EXTRACT ALL 8 PAGES AND ETC. *FOCUS*

        Important Notes:
        - Must extract all courses on each page. If there are multiple pages, navigate through them and extract all courses.
        - Ensure the term "{selected_term}" is actually selected before proceeding.
        - Return the extracted data as a single JSON array containing all courses.

        VERY IMPORTANT STEP TO LOOK AT AFTER EXTRACTING AND DOING EVERYTHING YOU'RE SUPPOSED TO DO:
        1. Confirm whether the courses have been successfully extracted from the webpage.
        2. Verify if the extracted data has been correctly parsed and stored in the `course_linked_list`.
        3. Display a preview of the first few courses in the linked list to show that the parsing was successful.
        4. Explain the steps taken to write the data from the linked list into the "courses.csv" file, including opening the file in write mode, writing the header row, and iterating through the linked list to write each course as a row in the CSV.
        '''

    if st.button("Run Agent"):
        while True:
            with st.spinner("🧠 Running the agent..."):
                agent = Agent(task=task, llm=llm, initial_actions=initial_actions, sensitive_data=sensitive_data)
                history = await agent.run()
                raw_list = history.extracted_content()

                course_list = parse_courses_to_linked_list(raw_list)

                if course_list and course_list.head is not None:
                    st.info("⚠️ Partial data may have been extracted. Proceeding with available course data.")
                    break  # ✅ Proceed even if only partial data is available
                else:
                    st.warning("❌ No course data could be extracted. This might be due to invalid credentials *or* no access to Course Offerings. Please try again.")
                    st.stop()


        if course_list.head is not None:
            write_courses_to_csv(course_list)
            st.success("✅ Courses successfully extracted and saved to courses.csv!")

            # Store the linked list in session state
            st.session_state.course_linked_list = course_list
            st.session_state.courses_extracted = True
            # Format the linked list as display text
            linked_list_preview = course_list.to_text()
            preview_text = f"✅ Courses successfully parsed into a linked list. Here's a preview:\n\n{linked_list_preview[:1500]}..."  # limit to avoid overflow
            st.info(preview_text)

            # Initialize chat history
            st.session_state.messages = [
                {"role": "assistant", "content": "I've loaded the course data. Ask me anything about the courses!"}
            ]
        else:
            st.error("❌ No courses were extracted or parsed. Please check the agent's output and the website.")

    # Chat interface - only show if courses are extracted
    if st.session_state.courses_extracted and st.session_state.course_linked_list:
        st.subheader("Course query chat")

        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Get new user prompt
        if prompt := st.chat_input("Ask anything about courses..."):
            # Show user message instantly
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Prepare prompt for LLM
            course_data = st.session_state.course_linked_list.to_text()
            system_prompt = f"""
    You are a university course assistant. Below is the extracted course schedule from the university system.

    Each course has this format:
    Course Code: Course Name
    • Instructor: Name
    • Schedule: Days Start-End Time
    • Room: Location
    • Enrollment: Current/Max

    {course_data}

    Now, answer the following user question using ONLY the data above. Be concise and specific.
    User question: "{prompt}"
    """

            # Call LLM and display response in real time
            with st.chat_message("assistant"):
                with st.spinner("🤖 Thinking..."):
                    try:
                        response = await llm.ainvoke(system_prompt)
                        st.markdown(response.content)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": response.content}
                        )
                    except Exception as e:
                        error_msg = f"❌ Error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": error_msg}
                        )

if __name__ == '__main__':
    asyncio.run(main())