import base64
import io
import json
import os
from itertools import chain

import openai
from django.http import HttpResponseBadRequest, JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain.memory import ChatMessageHistory


from .constants import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_MODEL_ID,
    ELEVENLABS_VOICE_ID,
    OPENAI_API_KEY,
)
from .models import AudioFile, UserDetail
from .utils import (
    audio_to_text,
    generate_prompt,
    get_chat_response,
    get_openai_response,
    get_question_history_prompt,
    text_to_audio,
    update_question_history,
)

openai.api_key = OPENAI_API_KEY


def index(request):
    return render(request, "app/index.html")


required_skills_for_job = ["AWS", "Azure", "Linux"]
topics = [
    "cloud Service Models",
    "Cloud Deployment Models",
    "Virtualization",
    "Networking in the Cloud",
    "IAM (Identity and Access Management),software development",
]


@csrf_exempt
def save_user_details(request):
    from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
    from langchain_openai import ChatOpenAI

    if request.method == "POST":
        json_data = json.loads(request.body)
        role = json_data.get("role")
        experience = json_data.get("experience")
        skills = json_data.get("skills")
        topics = json_data.get("topics", [])
        required_skills = json_data.get("requiredSkills", [])

        chat_message_history = MongoDBChatMessageHistory(
            session_id="test_session",
            connection_string="mongodb://mongo_user:password123@mongo:27017",
            database_name="my_db",
            collection_name="chat_histories",
        )
        promt = generate_prompt(
            skills=skills,
            experience=experience,
            role=role,
            skills_required=required_skills,
        )
        return JsonResponse({"message": "User details saved successfully!"}, status=201)
    else:
        return JsonResponse({"error": "Method not allwed"}, status=405)


@csrf_exempt
def process_audio(request):
    if request.method == "POST":
        json_data = json.loads(request.body)
        base64_audio_data = json_data.get("audioBase64")
        try:
            # Decode base64 data
            audio_binary_data = base64.b64decode(base64_audio_data)

            # Create an AudioFileModel instance and save the audio file
            audio_model = AudioFile()
            audio_model.audio_file.save(
                "audio_file4.mp3", io.BytesIO(audio_binary_data), save=True
            )

            # Get the transcript of the audio
            transcript_response = transcribe_view(request, audio_model.id)
            transcript_content = transcript_response.content
            transcript_dict = json.loads(transcript_content)
            transcript = transcript_dict.get("transcript")

            user_details = (
                UserDetail.objects.last()
            )  # Assuming you want the latest user details
            if user_details:
                role = user_details.role
                experience = user_details.experience
                skills = user_details.skills
            prompt = generate_prompt(
                transcript, skills, experience, role, required_skills_for_job
            )

            # Include the history of asked questions in the prompt
            prompt += get_question_history_prompt()

            openai_response = get_openai_response(prompt)

            # Update the question history with the latest question
            update_question_history(openai_response)

            return JsonResponse(
                {
                    "status": "success",
                    "audio_id": audio_model.id,
                    "transcript": transcript,
                    "openai-response": openai_response,
                    "prompt": prompt,
                },
                safe=False,
            )

        except Exception as e:
            # Handle any exceptions that may occur during decoding or saving
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    elif request.method == "OPTIONS":
        # Handle OPTIONS request
        response = JsonResponse({"message": "This is an OPTIONS request"})
        # Set CORS headers
        response["Access-Control-Allow-Origin"] = (
            "*"  # Update with your allowed origins
        )
        response["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE"  # Update with your allowed methods
        )
        response["Access-Control-Allow-Headers"] = (
            "Content-Type"  # Update with your allowed headers
        )
        return response
    else:
        return JsonResponse(
            {"status": "error", "message": "Invalid request method"}, status=400
        )


def transcribe_view(request, audio_file_id):
    try:
        audio_file_instance = AudioFile.objects.get(id=audio_file_id)
        audio_file_path = audio_file_instance.audio_file.path

        with open(audio_file_path, "rb") as file:
            transcript = openai.Audio.transcribe("whisper-1", file)
            return JsonResponse({"transcript": transcript.get("text")})
    except AudioFile.DoesNotExist:
        return JsonResponse({"details": "AudioFile with this ID does not exist"})
    except Exception:
        return JsonResponse({"details": "Unexpected Error"})


def process_audio_and_openai(request, audio_file_id):
    openai.api_key = os.getenv("openai_secret")

    if request.method == "GET":
        try:
            transcript_response = transcribe_view(request, audio_file_id)
            transcript_content = transcript_response.content
            transcript_dict = json.loads(transcript_content)
            transcript = transcript_dict.get("transcript")
            role = request.GET.getlist("role")
            experience = request.GET.getlist("experience")
            skills = request.GET.getlist("skills")
            prompt = generate_prompt(
                transcript, skills, experience, role, required_skills_for_job
            )

            # Include the history of asked questions in the prompt
            prompt += get_question_history_prompt()

            openai_response = get_openai_response(prompt)

            # Update the question history with the latest question
            update_question_history(openai_response)

            return JsonResponse(
                {
                    "transcript": transcript,
                    "openai-response": openai_response,
                    "prompt": prompt,
                },
                safe=False,
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)


@csrf_exempt
def process_user_audio(request):
    if request.method == "POST":
        audio_file = request.FILES.get("audio_file")
        if not audio_file:
            return HttpResponseBadRequest({"details": "File Not Provided"})
        with open(os.getcwd() + f"/chat_audio/{audio_file.name}", "wb") as buffer:
            for chunks in audio_file.chunks():
                buffer.write(chunks)

        file_path = os.path.join(os.getcwd(), "chat_audio", f"{audio_file.name}")
        with open(file_path, "rb") as buffer:
            message_decoded = audio_to_text(buffer)
        chat_response = get_chat_response(message_decoded)
        audio_output = text_to_audio(chat_response)

        if os.path.exists(file_path):
            # remove the stored files
            os.remove(file_path)

        # function to return genrator for audio
        def stream_audio():
            yield audio_output

        return StreamingHttpResponse(
            stream_audio(),
            content_type="audio/mpeg",
        )
    else:
        return JsonResponse({"details": "Method not allowed"}, status=405)

sessions = {}

def process_user_question(user_question, session_id=None):
    from langchain_openai import ChatOpenAI
    if session_id not in sessions:
        pass 
    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: MongoDBChatMessageHistory(
            session_id=session_id,
            connection_string="mongodb+srv://ghadgerasika16:Rasika123@cluster0.0fnjyu2.mongodb.net/AIInterviewer?retryWrites=true&w=majority",
            database_name="AIInterviewer",
            collection_name="chat_histories",
        ),
        input_messages_key="question",
        history_messages_key="history",
    )
    
    config = {"configurable": {"session_id": session_id}}
    return chain_with_history.invoke({"question": user_question}, config=config)
    
    
@csrf_exempt
def process_user_chat(request):
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{question}"),
        ]
    )
    chain = prompt | ChatOpenAI()

    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: MongoDBChatMessageHistory(
            session_id=session_id,
            connection_string="mongodb+srv://ghadgerasika16:Rasika123@cluster0.0fnjyu2.mongodb.net/AIInterviewer?retryWrites=true&w=majority",
            database_name="AIInterviewer",
            collection_name="chat_histories",
        ),
        input_messages_key="question",
        history_messages_key="history",
    )
    session_id = request.headers.get("Sessionid")
    question = json.loads(request.body).get('question')
    config = {"configurable": {"session_id": session_id}}
    response = chain_with_history.invoke({"question": question}, config=config)
    print(response.content)
    return JsonResponse({"data": response.content})



def save_user_details(request):
    if request.method == "POST":
        json_data = json.loads(request.body)
        role = json_data.get("role")
        experience = json_data.get("experience")
        skills = json_data.get("skills")
        topics = json_data.get("topics", [])
        required_skills = json_data.get("requiredSkills", [])
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a helpful interviewer Your name is Rachel. ask questions to the user based on his skills."),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}"),
            ]
        )
        chain = prompt | ChatOpenAI()
        data = MongoDBChatMessageHistory()
        chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: MongoDBChatMessageHistory(
                session_id=session_id,
                connection_string="mongodb+srv://ghadgerasika16:Rasika123@cluster0.0fnjyu2.mongodb.net/AIInterviewer?retryWrites=true&w=majority",
                database_name="AIInterviewer",
                collection_name="chat_histories",
            ),
            input_messages_key="question",
            history_messages_key="history",
        )
        session_id = request.headers.get("Sessionid")
        question = json.loads(request.body).get('question')
        config = {"configurable": {"session_id": session_id}}
        response = chain_with_history.invoke({"question": question}, config=config)
        print(response.content)
        return JsonResponse({"data": response.content})


def evaluate_user_answer_and_ask_question(request):
    if request.method == "POST":
        json_data = json.loads(request.body)
        user_answer = json_data.get("answer")
        
        chat = ChatOpenAI(model="gpt-3.5-turbo-1106")
        
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "You are a helpful interviewer Your name is Rachel. ask questions to the user based on his skills."),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}"),
            ]
        )
        chain = prompt | ChatOpenAI()
        data = MongoDBChatMessageHistory()
        chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: MongoDBChatMessageHistory(
                session_id=session_id,
                connection_string="mongodb+srv://ghadgerasika16:Rasika123@cluster0.0fnjyu2.mongodb.net/AIInterviewer?retryWrites=true&w=majority",
                database_name="AIInterviewer",
                collection_name="chat_histories",
            ),
            input_messages_key="question",
            history_messages_key="history",
        )
        session_id = request.headers.get("Sessionid")
        question = json.loads(request.body).get('question')
        config = {"configurable": {"session_id": session_id}}
        response = chain_with_history.invoke({"question": question}, config=config)

