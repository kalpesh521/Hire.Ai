import base64
import io
import json
import os
from ast import mod

import openai
from django.http import HttpResponseBadRequest, JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain_openai import ChatOpenAI
from openai import OpenAI

from .constants import (
    DATABASE_URL,
    OPENAI_API_KEY,
)
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
    remove_upload_file,
    stream_audio,
    text_to_audio,
    update_question_history,
)

openai.api_key = OPENAI_API_KEY

chat_history = []
client = OpenAI()


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
def process_user_audio(request):
    if request.method == "POST":
        audio_file = request.FILES.get("audio_file")
        session_id = request.headers.get("sessionId")
        handle_upload_file(audio_file=audio_file)
        file_path = os.path.join(os.getcwd(), "chat_audio", f"{audio_file.name}")
        audio_output = get_response_audio(file_path=file_path, session_id=session_id)
        remove_upload_file(audio_file)
        return StreamingHttpResponse(
            stream_audio(audio_output=audio_output),
            content_type="audio/mpeg",
        )
    else:
        return JsonResponse({"details": "Method not allowed"}, status=405)


@csrf_exempt
def start(request):
    if request.method == "POST":
        audio_file = request.FILES.get("audio_file")
        session_id = request.headers.get("sessionId")
        subject = json.loads(request.body).get("subject")
        handle_upload_file(audio_file=audio_file)
        messages_in_history = get_or_create_history(session_id=session_id)
        messages_in_history.add_user_message(
            f"Act as an interviewer and ask me exactly one question from the below topics. {subject}"
        )
        response = get_chat_response(
            session_id=session_id, history=messages_in_history.messages
        )
        messages_in_history.add_ai_message(response)
        audio_output = text_to_audio(response)

        return StreamingHttpResponse(
            stream_audio(audio_output=audio_output),
            content_type="audio/mpeg",
        )
    else:
        return JsonResponse({"details": "Method not allowed"}, status=405)


@csrf_exempt
def end(request):
    if request.method == "POST":
        audio_file = request.FILES.get("audio_file")
        session_id = request.headers.get("sessionId")
        end_feedback_prompt = {
            "role": "user",
            "content": """
                    Based on the above questions and answers give a feedback using the following rubrics
                    Technical Knowledge: The interviewer will gauge your understanding of core technical concepts related to the field you're being interviewed for. This could include knowledge of programming languages, algorithms, data structures, specific frameworks, or relevant technologies.
                    Problem-Solving Skills: You might be presented with hypothetical scenarios or theoretical problems to solve. The interviewer will assess your ability to approach problems logically, break them down into smaller parts, and devise solutions using your technical knowledge.
                    Critical Thinking: Your capacity to analyze information critically will be examined. This involves evaluating various options, considering pros and cons, and selecting the most appropriate solution or approach.
                    Communication Skills: It's not just about knowing the answers; you should be able to articulate your thoughts effectively. Clear and concise communication is vital in a technical role, as you may need to collaborate with teammates or explain complex concepts to non-technical stakeholders.
                    Understanding of Fundamentals: A solid grasp of the foundational principles is crucial. The interviewer may ask questions about basic concepts in the field to assess whether you have a strong understanding of the fundamentals.
                    Rate each key out of 10 and  and give the response in json format and calculate the average `,
                """,
        }
        handle_upload_file(audio_file=audio_file)
        messages_in_history = get_or_create_history(session_id=session_id).messages

        messages_in_history.append(end_feedback_prompt)
        response = get_chat_response(
            session_id=session_id, history=messages_in_history.messages
        )
        messages_in_history.add_ai_message(response)
        audio_output = text_to_audio(response)

        return StreamingHttpResponse(
            stream_audio(audio_output=audio_output),
            content_type="audio/mpeg",
        )
    else:
        return JsonResponse({"details": "Method not allowed"}, status=405)


@csrf_exempt
def next(request):
    if request.method == "POST":
        audio_file = request.FILES.get("audio_file")
        session_id = request.headers.get("sessionId")
        handle_upload_file(audio_file=audio_file)
        messages_in_history = get_or_create_history(session_id=session_id)
        messages_in_history.add_user_message("Ask the next question")
        try:
            response = get_chat_response(
                session_id=session_id, history=messages_in_history.messages
            )
            messages_in_history.add_ai_message(response)
            audio_output = text_to_audio(response)

            return StreamingHttpResponse(
                stream_audio(audio_output=audio_output),
                content_type="audio/mpeg",
            )
        except Exception:
            response = "Sorry I didn't understand? Can you please repeat?"
            return StreamingHttpResponse(
                stream_audio(text_to_audio(response)), content_type="audio/mpeg"
            )
    else:
        return JsonResponse({"details": "Method not allowed"}, status=405)


@csrf_exempt
def submit(request):
    if request.method == "POST":
        audio_file = request.FILES.get("audio_file")
        session_id = request.headers.get("sessionId")
        data = json.loads(request.body)
        answer = data.get("answer", "")
        feedback = request.GET.get("feedback", "")
        feedback = "do" if feedback == "1" else "Don't"
        handle_upload_file(audio_file=audio_file)
        messages_in_history = get_or_create_history(session_id=session_id)
        messages_in_history.add_user_message(
            f"{answer}. this is my response to the above question keep a note of it  and {feedback} provide a feed back and ask the next question in the interview."
        )
        try:
            response = get_chat_response(
                session_id=session_id, history=messages_in_history.messages
            )
            messages_in_history.add_ai_message(response)
            audio_output = text_to_audio(response)

            return StreamingHttpResponse(
                stream_audio(audio_output=audio_output),
                content_type="audio/mpeg",
            )
        except Exception as e:
            print(e)
            response = "Sorry I didn't understand? Can you please repeat?"
            return StreamingHttpResponse(
                stream_audio(text_to_audio(response)), content_type="audio/mpeg"
            )
    else:
        return JsonResponse({"details": "Method not allowed"}, status=405)
