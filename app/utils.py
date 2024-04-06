import openai
import requests

from .constants import ELEVENLABS_API_KEY, ELEVENLABS_MODEL_ID, ELEVENLABS_VOICE_ID

question_history = []
required_skills_for_job = ["JAVA", "C++"]


def text_to_audio(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

    payload = {
        "model_id": ELEVENLABS_MODEL_ID,
        "text": text,
        "voice_settings": {"similarity_boost": 0.1, "stability": 0.2},
    }
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    response = requests.request("POST", url, json=payload, headers=headers)
    return response.content


def generate_prompt(skills, experience, role, skills_required, user_response = ""):
    prompt = "Act as a interviewer and ask some technical question to the candidate based on this information.Just one question to the candidate not reply by the candidate , and question should be only one. "
    prompt += f"User Response: {user_response}\n"
    prompt += f"Skills: {', '.join(skills)}\n"
    prompt += f"Experience Level: {experience}\n"
    prompt += f"Role Interviewing For: {role}\n"
    # prompt += f"Skills Required for the Job: {', '.join(skills_required)}\n"
    # prompt += f"Question to be ask on topics : {', '.join(topics)}\n"
    return prompt


def get_question_history_prompt():
    history_prompt = "History of Asked Questions:\n"
    for question in enumerate(question_history, start=1):
        history_prompt += f"{question}"
    return history_prompt


def update_question_history(openai_response):
    question_history.append(openai_response)
    max_history_length = 3
    if len(question_history) > max_history_length:
        question_history.pop(0)


def get_openai_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        assistant_reply = response["choices"][0]["message"]["content"].strip()
        return assistant_reply
    except Exception as e:
        raise Exception(str(e))


def audio_to_text(audio_file_path):
    transcript = openai.Audio.transcribe("whisper-1", audio_file_path)
    return transcript.get("text")
    # use this for testing
    # return "Hi, I am Virat and I have studied information technology from Oxford University and I have worked on data science and dot machine learning technology"


def get_chat_response(message):
    # get response from chatbot
    return "this is chat message for Hi, I am Virat and I have studied information technology from Oxford University and I have worked on data science and dot machine learning technology"
