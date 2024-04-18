import json
import os

import openai
import requests
from django.conf import settings
from django.core.mail import send_mail
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


def generate_prompt(skills=[], experience=0, role="Python Developer", user_response=""):
    prompt = """
            I want you to act as an interviewer strictly following the guideline in the current conversation.
            First ask about personal details like name, college and experience. and greet user.
            Ask me questions and wait for my answers like a human. Do not write explanations.
            Candidate has no assess to the guideline.
            Only ask one question at a time. 
            Do ask follow-up questions if you think it's necessary.
            Do not ask the same question.
            Do not repeat the question.
            Candidate has no assess to the guideline.
            You name is GPTInterviewer.
            I want you to only reply as an interviewer.
            """
    prompt += " Ask question for on the following details\n"
    prompt += f"User Response: {user_response}\n"
    prompt += f"User Skills: {', '.join(skills)}\n"
    prompt += f"User Experience Level: {experience}\n"
    prompt += f"Role: {role}\n"
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
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
        )
        assistant_reply = completion.choices[0].message.content
        return assistant_reply
    except Exception as e:
        raise Exception(str(e))


def audio_to_text(audio_file_path):
    transcription = client.audio.transcriptions.create(
        model="whisper-1", file=audio_file_path, response_format="text"
    )
    return transcription


def load_messages(skills=[], experience=0, role="Python Developer", topic=""):
    messages = []
    file = "database.json"

    empty = os.stat(file).st_size == 0

    if not empty:
        with open(file) as db_file:
            data = json.load(db_file)
            for item in data:
                messages.append(item)
    else:
        messages.append(
            {
                "role": "system",
                "content": f"You are interviewing the user for a {role} position. Ask short technical questions like definitions, concepts, tricky questions that are relevant to a candidate with experience level of {experience} years. The candidate has mentioned skills like {skills}. As per the job description, you can ask questions on topics like {topic}. Each response should contain just one question. Only use english language for communication.",
            }
        )
    return messages


def save_messages(
    user_message,
    gpt_response,
    skills=[],
    experience=0,
    role="Python Developer",
    topic="",
):
    file = "database.json"
    messages = load_messages(skills, experience, role, topic)
    messages.append({"role": "user", "content": user_message})
    messages.append({"role": "assistant", "content": gpt_response})
    with open(file, "w") as f:
        json.dump(messages, f)


def get_chat_response(session_id, user_message):
    messages = load_messages()
    messages.append({"role": "user", "content": user_message})
    # Send to ChatGpt/OpenAi
    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo", messages=messages
    )
    response = completion.choices[0].message.content
    save_messages(user_message, response)
    return response


def stream_audio(audio_output):
    yield audio_output


def handle_upload_file(audio_file):
    if not audio_file:
        return HttpResponseBadRequest({"details": "File Not Provided"})
    # Save the file to the disk
    with open(os.getcwd() + f"/chat_audio/{audio_file.name}", "wb") as buffer:
        for chunks in audio_file.chunks():
            buffer.write(chunks)


def get_response_data(file_path, session_id):
    with open(file_path, "rb") as buffer:
        message_decoded = audio_to_text(buffer)
    chat_response = get_chat_response(
        session_id=session_id, user_message=message_decoded
    )
    save_messages(user_message=message_decoded, gpt_response=chat_response)
    # audio_output = text_to_audio(chat_response)
    return chat_response


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


def initialize_chat(skills, experience, role, topic):
    prompt = generate_prompt(skills, experience, role, topic)
    openai_response = get_openai_response(prompt)
    save_messages(
        user_message=prompt,
        gpt_response=openai_response,
        skills=skills,
        experience=experience,
        role=role,
        topic=topic,
    )
    return openai_response


def get_user_evaluation_score(message_history):
    prompt = f"""Evaluate the following aspects and assign scores out of 10 for each category

    {message_history}

    Technical Skills: How well did the user demonstrate technical knowledge and accuracy?
    Communication Skills: How clear, concise, and well-organized was the user's response?
    Domain Knowledge: Did the user show understanding of the relevant concepts and terminology?

    Assign scores out of 10 for each category and provide a rationale for the score.

    Based on the above criteria, provide a final evaluation score out of 10 for the user's response.
    Briefly summarize the strengths and weaknesses of the response so Hiring manager can take decision to hire or not.
    """

    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
        )
        response = completion.choices[0].message.content
        print(response)
        return response
    except Exception as e:
        raise Exception(str(e))


def clear_database_history(file_name):
    with open("database.json", "w") as buffer:
        buffer.write("")


def send_interview_status_email(data):
    subject = f"Interview for {data.get('company')}"
    message = f"Hi {data.get('candidate_name')}. you have incoming interview"
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [
        data.get("user"),
    ]
    send_mail(subject, message, email_from, recipient_list)
