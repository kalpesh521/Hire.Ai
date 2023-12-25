
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
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Interview ,AudioFile
import openai
import os

def index(request):
    return render(request, 'app/index.html')


# Set your OpenAI API key
openai.api_key = os.getenv("openai_secret") 
# for demo
skills = ["Python", "Machine Learning"]
level = "Intermediate"
time_remaining = 30  # in minutes
role = "Data Scientist"
required_skills_for_job = ["Python", "Machine Learning", "Data Analysis"]

@csrf_exempt
def process_audio_and_openai(request, audio_file_id):
    # request should also contain the profile of user, so that in each request we can prompt the AI to ask questions accordingly 
   
    openai.api_key = os.getenv("openai_secret") 

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
    openai.api_key = os.getenv("openai_secret")
    
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