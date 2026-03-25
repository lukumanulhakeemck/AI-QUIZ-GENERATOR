import streamlit as st
import fitz  # PyMuPDF
import os
import google.generativeai as genai
import re

# Configuration & SetUp
st.set_page_config(page_title="AI Quiz Master", layout="wide")

# Configure Gemini with your API key
genai.configure(api_key="[Import your API Key her]") 

def extract_text_from_pdf(uploaded_file):
    """extract text from uploaded PDF file"""
    doc = fitz.open(stream=uploaded_file.read(),filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text
def parse_quiz_data(quiz_text):
    """Parse quiz text into structured questions with options and correct answers"""
    questions = []
    
    # Split by Q1, Q2, Q3, etc.
    q_pattern = r'Q\d+:\s*(.*?)(?=Q\d+:|$)'
    q_matches = re.findall(q_pattern, quiz_text, re.DOTALL)
    
    for q_text in q_matches:
        lines = q_text.strip().split('\n')
        if not lines:
            continue
            
        question = lines[0].strip()
        options = {}
        correct_answer = None
        
        for line in lines[1:]:
            line = line.strip()
            if line.startswith(('A.', 'B.', 'C.', 'D.')):
                option_key = line[0]
                option_text = line[3:].strip()
                options[option_key] = option_text
            elif 'Correct Answer' in line:
                # Extract the letter (A, B, C, or D)
                correct_answer = re.search(r'([A-D])', line).group(1) if re.search(r'([A-D])', line) else None
        
        if question and options and correct_answer:
            questions.append({
                'question': question,
                'options': options,
                'correct_answer': correct_answer
            })
    
    return questions

#Brain of the AI
def generate_quiz_chain(context, difficulty):
    # 1 = Question Generation
    quiz_prompt = f"""Create a 5-question multiple choice quiz based only
    on the following context.
    Difficulty Level: {difficulty}
    Format:
    Q1:[Question]
    A. [Option A]
    B. [Option B]   
    C. [Option C]
    D. [Option D]
    Correct Answer : [Letter]
    Context:{context[:4000]}"""

    model = genai.GenerativeModel("gemini-3-flash-preview")
    response = model.generate_content("Generate 5 MCQ questions on Python")
    print(response.text)
    for m in genai.list_models():
        print(m.name, "→", m.supported_generation_methods)
    quiz_data = model.generate_content(quiz_prompt).text    

    # 2 = Explainable AI
    explain_prompt = f"""For the following quiz questions and answers,
    provide a deep logical explanation for WHY the correct answer is right
    and WHY the others are distractors.
    Quiz:{quiz_data}"""

    xai_response = model.generate_content(explain_prompt)

    return quiz_data, xai_response.text

st.title("🎓 Smart AI Quiz Generator")
st.markdown("Upload a textbook PDF to generate an interactive XAI-powered quiz.")

with st.sidebar:
    st.header("Settings")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    difficulty = st.select_slider(
        "Select Difficulty",
        options=["Beginner", "Intermediate", "Advanced", "PhD Level"]
    )
    generate_btn = st.button("Generate Quiz")

if generate_btn and uploaded_file:
    with st.spinner("Analyzing text and generating explanations..."):
        # Process
        raw_text = extract_text_from_pdf(uploaded_file)
        quiz_text, explanation = generate_quiz_chain(raw_text, difficulty)
        
        # Parse quiz into structured format
        questions = parse_quiz_data(quiz_text)
        
        # Store in session state
        st.session_state.questions = questions
        st.session_state.explanation = explanation
        st.session_state.quiz_generated = True

# Display quiz if generated
if st.session_state.get('quiz_generated', False):
    questions = st.session_state.questions
    explanation = st.session_state.explanation
    
    st.header("📝 Quiz Questions")
    st.markdown("---")
    
    # Initialize session state for user answers
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    if 'submitted' not in st.session_state:
        st.session_state.submitted = False
    
    # Display questions with interactive selection
    for idx, q_data in enumerate(questions, 1):
        st.subheader(f"Question {idx}")
        st.write(f"**{q_data['question']}**")
        
        # Radio buttons for answer selection
        selected_answer = st.radio(
            label=f"Your answer for Question {idx}:",
            options=list(q_data['options'].keys()),
            format_func=lambda x: f"{x}. {q_data['options'][x]}",
            key=f"q_{idx}",
            label_visibility="collapsed"
        )
        
        st.session_state.user_answers[idx] = selected_answer
        st.markdown("---")
    
    # Submit button
    col1, col2 = st.columns([1, 5])
    with col1:
        submit_btn = st.button("📊 Submit Answers", key="submit")
    
    if submit_btn:
        st.session_state.submitted = True
    
    # Show results if submitted
    if st.session_state.submitted:
        st.header("✅ Results & Explanations")
        st.markdown("---")
        
        score = 0
        total = len(questions)
        
        for idx, q_data in enumerate(questions, 1):
            user_ans = st.session_state.user_answers.get(idx)
            correct_ans = q_data['correct_answer']
            is_correct = user_ans == correct_ans
            
            if is_correct:
                score += 1
                st.success(f"✅ **Question {idx}: CORRECT!**")
            else:
                st.error(f"❌ **Question {idx}: INCORRECT**")
            
            st.write(f"**Question:** {q_data['question']}")
            st.write(f"**Your Answer:** {user_ans}. {q_data['options'][user_ans]}")
            st.write(f"**Correct Answer:** {correct_ans}. {q_data['options'][correct_ans]}")
            
            # Show explanation from XAI
            with st.expander(f"📚 See Explanation for Question {idx}"):
                st.info(explanation)
            
            st.markdown("---")
        
        # Show final score
        percentage = (score / total) * 100
        st.header(f"🎯 Final Score: {score}/{total} ({percentage:.1f}%)")
        
        # Feedback based on score
        if percentage == 100:
            st.balloons()
            st.success("🌟 Perfect Score! Excellent work!")
        elif percentage >= 70:
            st.info("👍 Great job! Keep it up!")
        elif percentage >= 50:
            st.warning("⚠️ Good effort! Review the explanations to improve.")
        else:
            st.error("📖 Keep practicing! Review the material and try again.")
        
        # Reset button
        if st.button("🔄 Try Another Quiz"):
            st.session_state.submitted = False
            st.session_state.user_answers = {}
            st.session_state.quiz_generated = False
            st.rerun()

else:
    st.info("📤 Upload a PDF and click 'Generate Quiz' to start!")
