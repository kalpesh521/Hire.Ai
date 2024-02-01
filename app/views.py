 
import base64
from django.shortcuts import render
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import  AudioFile  
import openai 
import os
import io
 
def index(request):
    return render(request, 'app/index.html')

# Set your OpenAI API key
openai.api_key = os.getenv("openai_secret") 
# for demo
skills = ["Cloud Computing", "Azure"]
level = "fresher"
time_remaining = 30  # in minutes
role = "Cloud Engineer"
required_skills_for_job = ["AWS", "Azure", "Linux"]
topics = ["cloud Service Models","Cloud Deployment Models","Virtualization","Networking in the Cloud","IAM (Identity and Access Management),software development"]
question_history = []

@csrf_exempt
def process_audio_and_openai(request, audio_file_id):
    
    openai.api_key = os.getenv("openai_secret") 

    if request.method == 'GET':
        try:
            # Get the audio file and its ID from the request
            # audio_file_id = request.POST.get('audio_file_id')
            # print(audio_file_id)

            transcript_response = transcribe_view(request, audio_file_id)
            transcript_content = transcript_response.content
            transcript_dict = json.loads(transcript_content)
            transcript = transcript_dict.get('transcript')
           
            prompt = generate_prompt(transcript, skills, level, time_remaining, role, required_skills_for_job)

            # Include the history of asked questions in the prompt
            prompt += get_question_history_prompt()

            openai_response = get_openai_response(prompt)

            # Update the question history with the latest question
            update_question_history(openai_response)
            
            # return JsonResponse({'transcript': transcript, 'openai-response': openai_response, 'prompt': prompt}, safe=False)
            return JsonResponse({'transcript': transcript, 'openai-response': openai_response}, safe=False)
 
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
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
               
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )

        # Extract the assistant's reply from the API response
        assistant_reply = response['choices'][0]['message']['content'].strip()

        return assistant_reply

    except Exception as e:
   
        raise Exception(str(e))
    
    # Customize the prompt based on user details and interview context
def generate_prompt(user_response, skills, experience_level, time_remaining, role, skills_required):
    prompt = "Act as a interviewer and ask some technical question to the candidate based on this information.Just one question to the candidate not reply by the candidate , and question should be only one. "
    prompt += f"User Response: {user_response}\n"
    prompt += f"Skills: {', '.join(skills)}\n"
    prompt += f"Experience Level: {experience_level}\n"
    prompt += f"Time Remaining: {time_remaining} minutes\n"
    prompt += f"Role Interviewing For: {role}\n"
    prompt += f"Skills Required for the Job: {', '.join(skills_required)}\n"
    prompt += f"Question to be ask on topics : {', '.join(topics)}\n"
    return prompt

   
    # Generate a prompt based on the history of asked questions
def get_question_history_prompt():  
    history_prompt = "History of Asked Questions:\n"
    for  question in enumerate(question_history, start=1):
        history_prompt += f"{question}"
    return history_prompt
 
 
    # Update the question history with the latest question
def update_question_history(openai_response):
    question_history.append(openai_response)
     
    max_history_length = 3
    if len(question_history) > max_history_length:
        question_history.pop(0)

 
def convertAudio(request):
    if request.method == 'POST':
        try:

            request_data = json.loads(request.body)
            print("request ", request_data)
            
            # Extract audio data from JSON
            audio_base64 = request_data.get('audioBase64')
            print("audio ", audio_base64)
            
            if audio_base64:
                # Decode the Base64 audio data
                audio_data = base64.b64decode(audio_base64)  # Assuming 'audio_data' is the key in the POST data

            wav_file = open("temp.wav", "wb")
            wav_file.write(audio_data)

            return JsonResponse({'status': 'success', 'message': 'Conversion successful'})
            # return response
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
def receive_and_save_audio(request):
    if request.method == 'POST':
        base64_audio_data = request.POST.get("audioBase64")

        try:
            # Decode base64 data
            audio_binary_data = base64.b64decode(base64_audio_data)

            # Create an AudioFileModel instance and save the audio file
            audio_model = AudioFile()
            audio_model.audio_file.save('audio_file4.mp3', io.BytesIO(audio_binary_data), save=True)

            # get id
            audio_id = audio_model.id

            # In this example, let's just return a success response
            return JsonResponse({'status': 'success', 'audio_id': audio_id})

        except Exception as e:
            # Handle any exceptions that may occur during decoding or saving
            return JsonResponse({'status': 'error', 'message': str(e)})

    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})