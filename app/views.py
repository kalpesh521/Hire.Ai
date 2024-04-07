import base64
import io
import json
import os

import openai
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI

from .constants import OPENAI_API_KEY
from .models import AudioFile, UserDetail
from .utils import (
    audio_to_text,
    generate_prompt,
    get_chat_response,
    get_openai_response,
    get_or_create_history,
    get_question_history_prompt,
    get_response_audio,
    handle_upload_file,
    initialize_chat,
    remove_upload_file,
    stream_audio,
    text_to_audio,
    update_question_history,
)

openai.api_key = OPENAI_API_KEY


chat_history = []
client = OpenAI(api_key=OPENAI_API_KEY)


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
def initialize_session(request):
    if request.method == "POST":
        try:
            json_data = json.loads(request.body)
            role = json_data.get("role")
            experience = json_data.get("experience")
            skills = json_data.get("skills")
            topic = json_data.get("topic")

            response = initialize_chat(
                role=role, experience=experience, skills=skills, topic=topic
            )
            audio_output = text_to_audio(response)

            return StreamingHttpResponse(
                stream_audio(audio_output=audio_output),
                content_type="audio/mpeg",
            )
        except Exception as e:
            print(e)
            default_message = "I didn't get that. Can you please repeat?"
            audio_output = text_to_audio(default_message)
            return StreamingHttpResponse(
                stream_audio(audio_output=audio_output),
                content_type="audio/mpeg",
            )
    else:
        return JsonResponse({"details": "Method not allowed"}, status=405)


@csrf_exempt
def process_user_audio(request):
    if request.method == "POST":
        audio_file = request.FILES.get("audio_file")
        if not audio_file:
            default_message = "I didn't get that. Can you please repeat?"
            audio_output = text_to_audio(default_message)
            return StreamingHttpResponse(
                stream_audio(audio_output=audio_output),
                content_type="audio/mpeg",
            )
        session_id = request.headers.get("sessionId")
        handle_upload_file(audio_file=audio_file)
        file_path = os.path.join(os.getcwd(), "chat_audio", f"{audio_file.name}")
        audio_output = get_response_audio(file_path=file_path, session_id=session_id)
        remove_upload_file(file_path)
        return StreamingHttpResponse(
            stream_audio(audio_output=audio_output),
            content_type="audio/mpeg",
        )
    else:
        return JsonResponse({"details": "Method not allowed"}, status=405)


@csrf_exempt
def clear_history(request):
    with open("database.json", "w") as buffer:
        buffer.write("")
    return JsonResponse({"details": "Interview ended successfully"}, status=200)
