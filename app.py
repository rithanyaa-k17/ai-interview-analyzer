import streamlit as st
import os
import whisper
import re
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

def analyze_transcript(transcript, duration_seconds):
    filler_words = [
        "um", "uh", "umm", "uhh",
        "actually", "basically", "literally",
        "you know", "i mean", "sort of", "kind of",
        "okay", "right", "yeah", "yeahh", "hmm"
    ]

    text = transcript.lower()
    words = re.findall(r"\b\w+\b", text)
    total_words = len(words)

    filler_count = 0
    detected_fillers = {}

    # Count direct filler words/phrases
    for filler in filler_words:
        pattern = r"\b" + re.escape(filler) + r"\b"
        count = len(re.findall(pattern, text))

        if count > 0:
            detected_fillers[filler] = count
            filler_count += count

    # Handle "like" carefully
    # Count "like" only when it is NOT used as "like to", "would like", "I'd like", etc.
    like_matches = re.findall(r"\blike\b", text)
    meaningful_like_patterns = [
        r"\blike to\b",
        r"\bwould like\b",
        r"\bi'd like\b",
        r"\bi would like\b",
        r"\blike working\b",
        r"\blike using\b"
    ]

    meaningful_like_count = 0
    for pattern in meaningful_like_patterns:
        meaningful_like_count += len(re.findall(pattern, text))

    like_filler_count = max(0, len(like_matches) - meaningful_like_count)

    if like_filler_count > 0:
        detected_fillers["like"] = like_filler_count
        filler_count += like_filler_count

    # Handle "so" carefully
    # Count only when it appears at the beginning or after punctuation-like pauses
    so_count = len(re.findall(r"(^|\.\s+|,\s+)\bso\b", text))
    if so_count > 0:
        detected_fillers["so"] = so_count
        filler_count += so_count

    # Handle "well" carefully
    # Avoid counting "as well"
    well_total = len(re.findall(r"\bwell\b", text))
    as_well_count = len(re.findall(r"\bas well\b", text))
    well_filler_count = max(0, well_total - as_well_count)

    if well_filler_count > 0:
        detected_fillers["well"] = well_filler_count
        filler_count += well_filler_count

    duration_minutes = duration_seconds / 60 if duration_seconds > 0 else 1

    filler_percentage = (filler_count / total_words) * 100 if total_words > 0 else 0
    fillers_per_minute = filler_count / duration_minutes

    return total_words, filler_count, filler_percentage, fillers_per_minute, detected_fillers
def get_filler_feedback(filler_count, fillers_per_minute, duration_seconds):
    if duration_seconds < 20:
        if filler_count == 0:
            return "Clean short response. No common filler words were detected."
        elif filler_count <= 2:
            return "A few fillers appeared in a short response. This is normal and not a major concern."
        else:
            return "Several fillers appeared in a short response. Try slowing down slightly."

    if filler_count == 0:
        return "Very clean response. No common filler words were detected, though natural speech may still contain pauses."
    elif fillers_per_minute <= 2:
        return "Very natural speech. A few fillers are normal and do not affect your clarity."
    elif fillers_per_minute <= 4:
        return "Good overall. Some fillers were present, but your speech still sounds controlled."
    elif fillers_per_minute <= 6:
        return "Slightly noticeable filler usage. Try replacing some fillers with short pauses."
    elif fillers_per_minute <= 8:
        return "Moderate filler usage. Your answer may sound a little hesitant in places."
    elif fillers_per_minute <= 12:
        return "High filler usage. Practicing slower, structured answers can improve confidence."
    else:
        return "Very high filler usage. Try pausing, breathing, and organizing your answer before speaking."

def get_pace_feedback(words_per_minute):
    if words_per_minute == 0:
        return "Could not calculate speaking pace."

    elif words_per_minute < 90:
        return "Your speaking pace is quite slow. This may sound hesitant, so try speaking with a little more flow."

    elif words_per_minute <= 150:
        return "Good speaking pace. This range usually sounds clear and comfortable for interviews."

    elif words_per_minute <= 180:
        return "Slightly fast pace. It is still understandable, but slow down a little for better clarity."

    else:
        return "Very fast pace. Try slowing down so your answer sounds more confident and easier to follow."
def calculate_confidence_score(filler_percentage, words_per_minute, total_words):
    score = 100

    # Penalize high filler usage
    if filler_percentage > 8:
        score -= 25
    elif filler_percentage > 5:
        score -= 15
    elif filler_percentage > 2:
        score -= 8

    # Penalize speaking too slow or too fast
    if words_per_minute < 90:
        score -= 15
    elif words_per_minute > 180:
        score -= 15
    elif words_per_minute > 150:
        score -= 8

    # Penalize very short answers
    if total_words < 20:
        score -= 10

    # Keep score between 0 and 100
    score = max(0, min(score, 100))

    return score

def get_confidence_feedback(score):
    if score >= 85:
        return "Strong communication confidence. Your response sounds clear, controlled, and well-paced."
    elif score >= 70:
        return "Good confidence level. A few small improvements can make your answer even stronger."
    elif score >= 50:
        return "Moderate confidence. Try reducing fillers, improving structure, and maintaining a steady pace."
    else:
        return "Low confidence score. Practice slower, structured answers with fewer fillers and clearer delivery."

def analyze_star_structure(transcript):
    text = transcript.lower()

    situation_keywords = [
        "during", "when", "while", "in my project", "in my internship",
        "there was", "we had", "i faced", "problem", "challenge"
    ]

    task_keywords = [
        "my responsibility", "my task", "i had to", "i needed to",
        "i was responsible", "goal", "objective"
    ]

    action_keywords = [
        "i did", "i worked", "i implemented", "i created", "i developed",
        "i solved", "i used", "i analyzed", "i designed", "i improved"
    ]

    result_keywords = [
    "as a result",
    "this resulted in",
    "this helped",
    "because of this",
    "the outcome was",
    "we achieved",
    "i achieved",
    "it improved",
    "improved by",
    "reduced by",
    "increased by",
    "successfully",
    "measurable outcome",
    "final result"
    ]

    def check_presence(keywords):
        return any(keyword in text for keyword in keywords)

    star_result = {
        "Situation": check_presence(situation_keywords),
        "Task": check_presence(task_keywords),
        "Action": check_presence(action_keywords),
        "Result": check_presence(result_keywords)
    }

    score = sum(star_result.values()) * 25

    missing_parts = [
        part for part, present in star_result.items()
        if not present
    ]

    return star_result, score, missing_parts

def extract_skills(transcript):
    skill_keywords = {
        "Python": ["python"],
        "Java": ["java"],
        "C++": ["c++", "cpp"],
        "C": [" c "],
        "JavaScript": ["javascript", "js"],
        "HTML": ["html"],
        "CSS": ["css"],
        "SQL": ["sql"],
        "DBMS": ["dbms", "database"],
        "Machine Learning": ["machine learning", "ml"],
        "Artificial Intelligence": ["artificial intelligence", "ai"],
        "Deep Learning": ["deep learning"],
        "NLP": ["nlp", "natural language processing"],
        "Speech-to-Text": ["speech to text", "speech-to-text", "transcription"],
        "Whisper": ["whisper"],
        "FFmpeg": ["ffmpeg"],
        "Streamlit": ["streamlit"],
        "Flask": ["flask"],
        "FastAPI": ["fastapi", "fast api"],
        "React": ["react"],
        "Git": ["git"],
        "GitHub": ["github"],
        "REST API": ["rest api", "api"],
        "Data Analysis": ["data analysis"],
        "Anomaly Detection": ["anomaly detection"]
    }

    text = transcript.lower()
    detected_skills = []

    for skill, keywords in skill_keywords.items():
        for keyword in keywords:
            if keyword in text:
                detected_skills.append(skill)
                break

    return detected_skills

st.title("AI Interview Analyzer")

question_type = st.selectbox(
    "Select Interview Question Type",
    [
        "General / Tell me about yourself",
        "Behavioral / Experience-based",
        "Project Explanation",
        "Technical Explanation",
        "Direct Factual Answer"
    ]
)

def analyze_direct_answer(transcript, detected_skills, total_words):
    if total_words <= 20:
        length_feedback = "Concise answer. Good for direct factual questions."
    elif total_words <= 45:
        length_feedback = "Good answer length. It gives enough detail without being too long."
    else:
        length_feedback = "This answer may be too long for a direct factual question. Try making it shorter and more specific."

    if detected_skills:
        skill_feedback = "Good. Your answer mentions specific tools or technologies."
    else:
        skill_feedback = "Your answer does not mention clear tools or technologies. Try naming the exact software, framework, model, database, or library used."

    if total_words <= 45 and detected_skills:
        overall_feedback = "Strong direct answer. It is specific, concise, and relevant."
    elif total_words > 45 and detected_skills:
        overall_feedback = "The answer includes useful technical details, but it can be made more concise."
    else:
        overall_feedback = "Try making the answer more specific by directly naming the tools or technologies used."

    return length_feedback, skill_feedback, overall_feedback

def detect_answer_type(transcript):
    text = transcript.lower()

    behavioral_keywords = [
        "challenge", "faced", "situation", "responsibility",
        "my task", "i had to", "i needed to", "as a result",
        "handled", "solved", "improved"
    ]

    project_keywords = [
        "project", "app", "application", "built", "developed",
        "implemented", "feature", "features", "upload",
        "transcribe", "analyze", "feedback", "helps", "users",
        "designed to", "created"
    ]

    technical_explanation_keywords = [
    "how", "why", "works", "working", "process", "pipeline",
    "because", "used for", "responsible for", "converts",
    "handles", "connects", "stores", "retrieves"
]

    technical_keywords = [
        "python", "java", "sql", "api", "database", "model",
        "algorithm", "whisper", "ffmpeg", "streamlit",
        "backend", "frontend", "deployment", "github",
        "machine learning", "artificial intelligence"
    ]

    project_connection_keywords = [
    "in my project", "in this project", "in my app", "in this app",
    "my project", "my app", "the app", "the system"
    ]

    direct_keywords = [
        "i used", "i use", "tools", "tool", "software",
        "technologies", "technology", "libraries", "library",
        "frameworks", "framework", "model", "database"
    ]

    behavioral_score = sum(1 for word in behavioral_keywords if word in text)
    project_score = sum(1 for word in project_keywords if word in text)
    technical_score = sum(1 for word in technical_keywords if word in text)
    direct_score = sum(1 for word in direct_keywords if word in text)
    project_connection_score = sum(1 for word in project_connection_keywords if word in text)
    technical_explanation_score = sum(1 for word in technical_explanation_keywords if word in text)
    if behavioral_score >= 2:
        return "Behavioral / Experience-based"

    elif project_score >= 2 and technical_score >= 1:
        return "Project Explanation"

    elif technical_explanation_score >= 1 and technical_score >= 1:
        return "Technical Explanation"

    elif technical_score >= 1 and project_connection_score >= 1:
        return "Technical Explanation"

    elif direct_score >= 1 and project_score < 2:
        return "Direct Factual Answer"

    elif technical_score >= 2:
        return "Technical Explanation"

    else:
        return "General / Tell me about yourself"
def analyze_project_explanation(transcript):
    text = transcript.lower()

    problem_keywords = [
        "problem", "purpose", "aim", "goal", "helps", "designed to",
        "built to", "used to", "solve"
    ]

    tech_stack_keywords = [
        "python", "streamlit", "flask", "sqlite", "whisper", "ffmpeg",
        "html", "css", "javascript", "api", "database", "github"
    ]

    feature_keywords = [
        "feature", "upload", "transcribe", "analyze", "detect",
        "score", "search", "store", "display", "dashboard"
    ]

    contribution_keywords = [
        "i built", "i developed", "i implemented", "i created",
        "i added", "i designed", "my role", "my contribution"
    ]

    outcome_keywords = [
        "as a result", "this helps", "this helped", "successfully",
        "improves", "improved", "useful", "benefit", "outcome"
    ]

    def check_presence(keywords):
        return any(keyword in text for keyword in keywords)

    project_result = {
        "Problem / Purpose": check_presence(problem_keywords),
        "Tech Stack": check_presence(tech_stack_keywords),
        "Features": check_presence(feature_keywords),
        "My Contribution": check_presence(contribution_keywords),
        "Outcome / Impact": check_presence(outcome_keywords)
    }

    score = sum(project_result.values()) * 20

    missing_parts = [
        part for part, present in project_result.items()
        if not present
    ]

    return project_result, score, missing_parts

def analyze_technical_explanation(transcript):
    text = transcript.lower()

    concept_keywords = [
        "is used", "it is", "it helps", "it allows", "it means",
        "used for", "responsible for", "works as"
    ]

    reason_keywords = [
        "because", "why", "needed", "required", "so that",
        "in order to", "helps to", "useful for"
    ]

    flow_keywords = [
        "first", "then", "after that", "finally", "step",
        "process", "flow", "pipeline", "input", "output"
    ]

    project_connection_keywords = [
        "in my project", "in this project", "in my app", "in this app",
        "the app", "the system", "uploaded audio", "transcript",
        "user", "file"
    ]

    technical_terms = [
        "python", "streamlit", "whisper", "ffmpeg", "sqlite",
        "database", "api", "model", "audio", "transcription",
        "backend", "frontend", "flask", "request", "response"
    ]

    def check_presence(keywords):
        return any(keyword in text for keyword in keywords)

    technical_result = {
        "Concept Explanation": check_presence(concept_keywords),
        "Reason / Purpose": check_presence(reason_keywords),
        "Step-by-step Flow": check_presence(flow_keywords),
        "Project Connection": check_presence(project_connection_keywords),
        "Technical Terms": check_presence(technical_terms)
    }

    score = sum(technical_result.values()) * 20

    missing_parts = [
        part for part, present in technical_result.items()
        if not present
    ]

    return technical_result, score, missing_parts

def analyze_self_intro(transcript):
    text = transcript.lower()

    background_keywords = [
        "i am", "i'm", "my name", "student", "studying",
        "computer science", "cse", "engineering", "college"
    ]

    skills_keywords = [
        "python", "java", "sql", "machine learning", "ai",
        "web development", "full stack", "frontend", "backend",
        "problem solving", "communication"
    ]

    project_keywords = [
        "project", "built", "developed", "worked on",
        "implemented", "created", "interview analyzer",
        "anomaly detection", "skillswap"
    ]

    interest_keywords = [
        "interested in", "passionate about", "i enjoy",
        "i would like", "i want to", "career", "domain",
        "software", "ai", "machine learning"
    ]

    closing_keywords = [
        "looking forward", "opportunity", "contribute",
        "grow", "learn", "improve", "develop my skills"
    ]

    def check_presence(keywords):
        return any(keyword in text for keyword in keywords)

    intro_result = {
        "Background / Education": check_presence(background_keywords),
        "Skills": check_presence(skills_keywords),
        "Projects": check_presence(project_keywords),
        "Career Interest": check_presence(interest_keywords),
        "Closing / Goal": check_presence(closing_keywords)
    }

    score = sum(intro_result.values()) * 20

    missing_parts = [
        part for part, present in intro_result.items()
        if not present
    ]

    return intro_result, score, missing_parts

def generate_final_summary(
    filler_percentage,
    words_per_minute,
    confidence_score,
    detected_skills,
    question_type
):
    strengths = []
    improvements = []

    # Filler-based feedback
    if filler_percentage <= 2:
        strengths.append("Low filler usage, which makes the answer sound clean and controlled.")
    elif filler_percentage <= 5:
        strengths.append("Filler usage is reasonable and does not strongly affect clarity.")
    else:
        improvements.append("Reduce filler words by pausing briefly instead of using repeated fillers.")

    # Pace-based feedback
    if 90 <= words_per_minute <= 150:
        strengths.append("Speaking pace is comfortable and suitable for interviews.")
    elif words_per_minute < 90:
        improvements.append("Try speaking with slightly more flow, as the pace may sound slow or hesitant.")
    else:
        improvements.append("Slow down slightly so the answer sounds clearer and easier to follow.")

    # Confidence score feedback
    if confidence_score >= 85:
        strengths.append("Overall communication confidence is strong.")
    elif confidence_score >= 70:
        strengths.append("Overall confidence is good, with only minor improvements needed.")
    else:
        improvements.append("Improve confidence by giving more structured, steady, and specific answers.")

    # Skill extraction feedback
    if detected_skills:
        strengths.append("Relevant technical skills or tools were mentioned in the answer.")
    else:
        improvements.append("Mention specific tools, technologies, or skills where relevant.")

    # Question-type feedback
    if question_type == "Behavioral / Experience-based":
        improvements.append("For behavioral answers, make sure the response clearly covers Situation, Task, Action, and Result.")
    elif question_type == "Project Explanation":
        improvements.append("For project explanations, clearly mention the problem, tech stack, features, your contribution, and outcome.")
    elif question_type == "Technical Explanation":
        improvements.append("For technical explanations, include what it is, why it is used, and how it works in your project.")
    elif question_type == "Direct Factual Answer":
        improvements.append("For direct factual answers, keep the response concise and name exact tools or technologies.")
    elif question_type == "General / Tell me about yourself":
        improvements.append("For self-introductions, include background, skills, projects, interests, and a clear closing goal.")

    # Avoid too many suggestions
    strengths = strengths[:3]
    improvements = improvements[:3]

    return strengths, improvements

def create_pdf_report(
    transcript,
    question_type,
    detected_answer_type,
    total_words,
    duration_seconds,
    filler_count,
    filler_percentage,
    fillers_per_minute,
    words_per_minute,
    confidence_score,
    detected_skills,
    strengths,
    improvements
):
    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 50

    def add_line(text, font="Helvetica", size=11, gap=18):
        nonlocal y

        if y < 60:
            pdf.showPage()
            y = height - 50

        pdf.setFont(font, size)
        pdf.drawString(50, y, str(text))
        y -= gap

    def add_wrapped_text(text, font="Helvetica", size=10, max_chars=90, gap=14):
        nonlocal y

        words = str(text).split()
        line = ""

        for word in words:
            if len(line) + len(word) + 1 <= max_chars:
                line += word + " "
            else:
                add_line(line.strip(), font, size, gap)
                line = word + " "

        if line:
            add_line(line.strip(), font, size, gap)

    add_line("AI Interview Analyzer Report", "Helvetica-Bold", 16, 26)
    add_line("=" * 70, "Helvetica", 10, 18)

    add_line("Question Type Selected:", "Helvetica-Bold", 12)
    add_line(question_type)

    add_line("Detected Answer Type:", "Helvetica-Bold", 12)
    add_line(detected_answer_type)

    add_line("Transcript:", "Helvetica-Bold", 12)
    add_wrapped_text(transcript)

    y -= 10
    add_line("Universal Communication Analysis", "Helvetica-Bold", 13, 22)
    add_line(f"Total Words: {total_words}")
    add_line(f"Approx Duration: {round(duration_seconds, 2)} seconds")
    add_line(f"Filler Words Count: {filler_count}")
    add_line(f"Filler Percentage: {round(filler_percentage, 2)}%")
    add_line(f"Fillers Per Minute: {round(fillers_per_minute, 2)}")
    add_line(f"Words Per Minute: {round(words_per_minute, 2)}")
    add_line(f"Confidence Score: {confidence_score}/100")

    y -= 10
    add_line("Detected Skills", "Helvetica-Bold", 13, 22)
    if detected_skills:
        add_wrapped_text(", ".join(detected_skills))
    else:
        add_line("No major technical skills detected.")

    y -= 10
    add_line("Strengths", "Helvetica-Bold", 13, 22)
    if strengths:
        for strength in strengths:
            add_wrapped_text("- " + strength)
    else:
        add_line("No major strengths detected.")

    y -= 10
    add_line("Areas to Improve", "Helvetica-Bold", 13, 22)
    if improvements:
        for improvement in improvements:
            add_wrapped_text("- " + improvement)
    else:
        add_line("No major improvements suggested.")

    y -= 10
    add_line("Note", "Helvetica-Bold", 13, 22)
    add_wrapped_text(
        "This report is generated using speech-to-text transcription and rule-based analysis. "
        "Results may vary depending on audio clarity, speaking style, and transcription accuracy."
    )

    pdf.save()

    buffer.seek(0)
    return buffer

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base", device="cpu")

uploaded_file = st.file_uploader(
    "Upload Interview Audio",
    type=["mp3", "wav", "m4a", "mp4"]
)

if uploaded_file:
    os.makedirs("audio", exist_ok=True)

    file_path = os.path.join("audio", uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("Audio uploaded successfully!")
    st.write("File Name:", uploaded_file.name)
    st.write("Saved To:", file_path)

    if st.button("Transcribe Audio"):
        with st.spinner("Transcribing audio... Please wait."):
            model = load_whisper_model()
            result = model.transcribe(file_path, initial_prompt="Transcribe the speech exactly as spoken, including filler words like um, uh, like, actually, and pauses if spoken.")
            transcript = result["text"]
            duration_seconds = 0
            if result.get("segments"):
                duration_seconds = result["segments"][-1]["end"]
            detected_answer_type = detect_answer_type(transcript)
            st.subheader("Transcript")
            st.write(transcript)
            total_words, filler_count, filler_percentage, fillers_per_minute, detected_fillers = analyze_transcript(transcript,duration_seconds)
            duration_minutes = duration_seconds / 60 if duration_seconds > 0 else 1
            words_per_minute = total_words / duration_minutes
            st.subheader("Universal Communication Analysis")

            st.write("Total Words:", total_words)
            st.write("Approx Duration:", round(duration_seconds, 2), "seconds")
            st.write("Filler Words Count:", filler_count)
            st.write("Filler Percentage:", round(filler_percentage, 2), "%")
            st.write("Fillers Per Minute:", round(fillers_per_minute, 2))

            if detected_fillers:
                st.write("Detected Fillers:", detected_fillers)
            else:
                st.success("No common filler words detected in the transcript.")
            feedback = get_filler_feedback(filler_count, fillers_per_minute, duration_seconds)
            st.info(feedback)
            st.subheader("Speaking Pace Analysis")

            st.write("Words Per Minute:", round(words_per_minute, 2))

            pace_feedback = get_pace_feedback(words_per_minute)
            st.info(pace_feedback)
            confidence_score = calculate_confidence_score(filler_percentage,words_per_minute,total_words)

            st.subheader("Confidence Score")

            st.metric("Score", f"{confidence_score}/100")

            confidence_feedback = get_confidence_feedback(confidence_score)
            st.info(confidence_feedback)
            st.subheader("Answer Type Check")
            st.write("Selected Question Type:", question_type)
            st.write("Detected Answer Type:", detected_answer_type)

            if question_type != detected_answer_type:
                st.warning(
                    "The selected question type and detected answer type may not match. "
                    "Some feedback sections may be less suitable for this answer."
                )
            else:
                st.success("The selected question type seems suitable for this answer.")
            detected_skills = extract_skills(transcript)

            st.subheader("Question-Specific Analysis")

            if question_type == "Behavioral / Experience-based":
                st.write("Behavioral answers are evaluated using the STAR framework.")

                star_result, star_score, missing_parts = analyze_star_structure(transcript)

                st.write("STAR Score:", f"{star_score}/100")

                for part, present in star_result.items():
                    if present:
                        st.success(f"{part}: Present")
                    else:
                        st.warning(f"{part}: Missing")

                if missing_parts:
                    st.info(
                        "Suggestion: Try adding " +
                        ", ".join(missing_parts) +
                        " to make your answer more structured."
                    )
                else:
                    st.success("Great structure! Your answer covers Situation, Task, Action, and Result.")

            elif question_type == "Direct Factual Answer":
                st.write("Direct factual answers are evaluated for conciseness, specificity, and relevance.")

                length_feedback, skill_feedback, overall_feedback = analyze_direct_answer(
                    transcript,
                    detected_skills,
                    total_words
                )

                st.write("Answer Length:", total_words, "words")
                st.info(length_feedback)
                st.info(skill_feedback)
                st.success(overall_feedback)

            elif question_type == "Project Explanation":
                st.write("Project explanations are evaluated for problem clarity, tech stack, features, contribution, and outcome.")

                project_result, project_score, missing_project_parts = analyze_project_explanation(transcript)

                st.write("Project Explanation Score:", f"{project_score}/100")

                for part, present in project_result.items():
                    if present:
                        st.success(f"{part}: Present")
                    else:
                        st.warning(f"{part}: Missing")

                if missing_project_parts:
                    st.info(
                        "Suggestion: Try adding " +
                        ", ".join(missing_project_parts) +
                        " to make your project explanation stronger."
                    )
                else:
                    st.success("Great project explanation! It covers purpose, tools, features, contribution, and outcome.")
            elif question_type == "Technical Explanation":
                st.write(
                    "Technical explanations are evaluated for concept clarity, purpose, flow, "
                    "project connection, and use of technical terms."
                )

                technical_result, technical_score, missing_technical_parts = analyze_technical_explanation(transcript)

                st.write("Technical Explanation Score:", f"{technical_score}/100")

                for part, present in technical_result.items():
                    if present:
                        st.success(f"{part}: Present")
                    else:
                        st.warning(f"{part}: Missing")

                if missing_technical_parts:
                    st.info(
                        "Suggestion: Try adding " +
                        ", ".join(missing_technical_parts) +
                        " to make your technical explanation clearer."
                    )
                else:
                    st.success(
                        "Strong technical explanation! Your answer explains the concept, purpose, flow, "
                        "and project relevance clearly."
                    )
            elif question_type == "General / Tell me about yourself":
                st.write(
                    "Self-introduction answers are evaluated for background, skills, projects, "
                    "career interest, and a clear closing goal."
                )

                intro_result, intro_score, missing_intro_parts = analyze_self_intro(transcript)

                st.write("Self Introduction Score:", f"{intro_score}/100")

                for part, present in intro_result.items():
                    if present:
                        st.success(f"{part}: Present")
                    else:
                        st.warning(f"{part}: Missing")

                if missing_intro_parts:
                    st.info(
                        "Suggestion: Try adding " +
                        ", ".join(missing_intro_parts) +
                        " to make your self-introduction stronger."
                    )
                else:
                    st.success(
                        "Strong self-introduction! Your answer covers your background, skills, projects, interests, and goal."
                    )
            else:
                st.info(
                    "No specialized analysis is applied for this question type yet. "
                    "Universal communication analysis and skill extraction are still shown."
                )

            st.subheader("Skill Extraction")

            
            if detected_skills:
                st.write("Detected Skills:")
                for skill in detected_skills:
                    st.success(skill)
            else:
                st.info("No major technical skills detected in the transcript.") 
            st.subheader("Final Summary")

            strengths, improvements = generate_final_summary(
                filler_percentage,
                words_per_minute,
                confidence_score,
                detected_skills,
                question_type
            )

            st.write("Strengths")

            for strength in strengths:
                st.success(strength)

            st.write("Areas to Improve")

            for improvement in improvements:
                st.warning(improvement)
            pdf_report = create_pdf_report(
                transcript,
                question_type,
                detected_answer_type,
                total_words,
                duration_seconds,
                filler_count,
                filler_percentage,
                fillers_per_minute,
                words_per_minute,
                confidence_score,
                detected_skills,
                strengths,
                improvements
            )

            st.download_button(
                label="Download PDF Report",
                data=pdf_report,
                file_name="interview_analysis_report.pdf",
                mime="application/pdf"
            )