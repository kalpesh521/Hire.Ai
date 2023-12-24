# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from .models import Interview ,AudioFile
# import openai
# import os
 

# def transcribe_view(request, audio_file_id):
#     openai.api_key = os.getenv("openai_key")
# 
#     try:
#         audio_file_instance = AudioFile.objects.get(id=audio_file_id)
#         audio_file_path = audio_file_instance.audio_file.path   

#         with open(audio_file_path, "rb") as file:
#             transcript = openai.Audio.transcribe("whisper-1", file)
#             return JsonResponse({'transcript': transcript})
#     except AudioFile.DoesNotExist:
#         return JsonResponse({'error': 'AudioFile with this ID does not exist'})

# @csrf_exempt
# def get_openai_response(request):
#     if request.method == 'POST':
#         try:
#             # Get the user's input from the POST request
#             user_input = request.POST.get('user_input')

#             # Construct the prompt with conversation history
#             conversation_history = request.POST.get('conversation_history', '')
#             prompt = f"{conversation_history}\nUser: {user_input}"

#             # Make a call to the OpenAI API
#             response = openai.Completion.create(
#                 engine="text-davinci-002",
#                 prompt=prompt,
#                 max_tokens=150
#             )

#             # Extract the assistant's reply from the API response
#             assistant_reply = response['choices'][0]['text'].strip()

#             # Update conversation history for the next turn
#             conversation_history += f"\nUser: {user_input}\nAI: {assistant_reply}"

#             # Respond with the assistant's reply
#             return JsonResponse({'assistant_reply': assistant_reply, 'conversation_history': conversation_history})

#         except Exception as e:
#             # Handle errors
#             return JsonResponse({'error': str(e)}, status=500)

#     return JsonResponse({'error': 'Invalid request method'}, status=400)
 




 



























# @csrf_exempt
# def transcribe_audio(request):
#     if request.method == 'POST':
#         try:
#             audio_file = request.FILES['./audio.mp3']
#             print(audio_file)
#             prompt = request.POST.get('prompt')
#             #Backend\Interview\audio_files
#             # Save audio file to Interview model (if needed)
#             new_interview = Interview.objects.create(prompt=prompt, audio_file=audio_file)
#             new_interview.save()

#             # Perform transcription using the Whisper model (example)
#             # Replace this with your Whisper model logic
#             # Simulated transcription for example
#             transcript = openai.Audio.transcribe("whisper-1", audio_file)
#             print(transcript)
#             # Update transcript in Interview model
#             new_interview.transcript = transcript
#             new_interview.save()

#             return JsonResponse({'transcript': transcript})  # Return transcript as JSON response
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)  # Return error response if any
#     else:
#         return JsonResponse({'error': 'Invalid method'}, status=405)  # Return error for unsupported methods

# # views.py

 


# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from .models import AudioFile

# @csrf_exempt
# def upload_audio(request):
#     if request.method == 'POST' and request.FILES.get('audio'):
#         audio_file = request.FILES['audio']
#         new_audio = AudioFile.objects.create(audio_file=audio_file)
#         return JsonResponse({'message': 'Audio file uploaded successfully'})
#     return JsonResponse({'error': 'Invalid request'}, status=400)

from django.shortcuts import render


def index(request):
    return render(request, 'app/index.html')

# views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Interview ,AudioFile
import openai
import os

# Set your OpenAI API key
openai.api_key = os.getenv("openai_key") 
# for demo
skills = ["Python", "Machine Learning"]
level = "Intermediate"
time_remaining = 30  # in minutes
role = "Data Scientist"
required_skills_for_job = ["Python", "Machine Learning", "Data Analysis"]

@csrf_exempt
def process_audio_and_openai(request, audio_file_id):
    # request should also contain the profile of user, so that in each request we can prompt the AI to ask questions accordingly 

    # Also the AI should have the context of the previous questions and the usre's responses, that will be an overhead to store as well as send in the request to model (it'll increase the token count)
    if request.method == 'GET':
        try:
            # Get the audio file and its ID from the request
            # audio_file_id = request.POST.get('audio_file_id')
            print(audio_file_id)

            transcript_response = transcribe_view(request, audio_file_id)
           
            transcript_content = transcript_response.content
            transcript_dict = json.loads(transcript_content)
 
            transcript = transcript_dict.get('transcript')

            # demo user answer
            # transcript = "Hi i am xyz and i have studied data science from abc university and i have worked on python and machine learning"

            # get response from AI
            prompt = generate_prompt(transcript, skills, level, time_remaining, role, required_skills_for_job)

            openai_response = get_openai_response(prompt)
        
            return JsonResponse({'transcript': transcript, 'openai-response': openai_response, 'prompt': prompt}, safe=False)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

def transcribe_view(request, audio_file_id):
    openai.api_key = os.getenv("openai_key")

    try:
        audio_file_instance = AudioFile.objects.get(id=audio_file_id)
        audio_file_path = audio_file_instance.audio_file.path   

        with open(audio_file_path, "rb") as file:
            transcript = openai.Audio.transcribe("whisper-1", file)
            print(transcript)
            return JsonResponse({'transcript': transcript.get('text')})
    except AudioFile.DoesNotExist:
        return JsonResponse({'error': 'AudioFile with this ID does not exist'})

def get_openai_response(prompt):
    try:
        # Call the OpenAI API function and get the response
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=prompt,
            max_tokens=150
        )

        # Extract the assistant's reply from the API response
        assistant_reply = response['choices'][0]['text'].strip()
        
        # return {'assistant_reply': assistant_reply}
        return assistant_reply

    except Exception as e:
        raise Exception(str(e))

def generate_prompt(user_response, skills, experience_level, time_remaining, role, skills_required):
    # Customize the prompt based on user details and interview context
    prompt = "Act as a interviewer and ask some technical question to the candidate based on this information.Just one question"
    prompt += f"User Response: {user_response}\n"
    prompt += f"Skills: {', '.join(skills)}\n"
    prompt += f"Experience Level: {experience_level}\n"
    prompt += f"Time Remaining: {time_remaining} minutes\n"
    prompt += f"Role Interviewing For: {role}\n"
    prompt += f"Skills Required for the Job: {', '.join(skills_required)}\n"

    return prompt