import os

import openai
import requests
from django.http import HttpResponseBadRequest
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory

from .constants import (
    DATABASE_URL,
    ELEVENLABS_API_KEY,
    ELEVENLABS_MODEL_ID,
    ELEVENLABS_VOICE_ID,
    OPENAI_API_KEY,
)

question_history = []
required_skills_for_job = ["JAVA", "C++"]

client = openai.OpenAI(api_key=OPENAI_API_KEY)


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


def generate_prompt(skills, experience, role, skills_required, user_response=""):
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
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=audio_file_path, response_format="text"
    )
    return transcription


def get_chat_response(session_id, history=[]):
    completion = openai.chat.completions.create(model="gpt-3.5-turbo", messages=history)
    response = completion["data"]["choices"][0]["message"]["content"]
    return response


def stream_audio(audio_output):
    yield audio_output


def handle_upload_file(audio_file):
    if not audio_file:
        return HttpResponseBadRequest({"details": "File Not Provided"})
    with open(os.getcwd() + f"/chat_audio/{audio_file.name}", "wb") as buffer:
        for chunks in audio_file.chunks():
            buffer.write(chunks)


def get_response_audio(file_path, session_id, initialize=False):
    with open(file_path, "rb") as buffer:
        message_decoded = audio_to_text(buffer)
    chat_response = get_chat_response(
        session_id, message_decoded, initialize=initialize
    )
    audio_output = text_to_audio(chat_response)
    return audio_output


def remove_upload_file(audio_file):
    if os.path.exists(audio_file):
        os.remove(audio_file)


def get_or_create_history(session_id):
    messages_in_history = MongoDBChatMessageHistory(
        session_id=session_id,
        connection_string=DATABASE_URL,
        database_name="AIInterviewer",
        collection_name="chat_histories",
    )
    return messages_in_history
