import base64
from django.shortcuts import render
import json
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import  AudioFile ,UserDetail
import openai 
import os
import io
 
def index(request):
    return render(request, 'app/index.html')

# Set your OpenAI API key
openai.api_key = os.getenv("openai_secret") 

# for demo
# skills = ["Cloud Computing", "Azure"]
# experience = "fresher"
# role = "Cloud Engineer"

required_skills_for_job = ["AWS", "Azure", "Linux"]
topics = ["cloud Service Models","Cloud Deployment Models","Virtualization","Networking in the Cloud","IAM (Identity and Access Management),software development"]

question_history = []
 
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
 

@csrf_exempt
def save_user_details(request):
    if request.method == 'POST':
        json_data = json.loads(request.body)
        role = json_data.get("role")
        experience = json_data.get("experience")
        skills = json_data.get("skills")

        if role and experience and skills:
            user_details = UserDetail.objects.create(
                role=role,
                experience=experience,
                skills=skills
            )
            return JsonResponse({'message': 'User details saved successfully!'}, status=200)
        else:
            return JsonResponse({'error': 'Incomplete data provided!'}, status=400)
    elif request.method == 'OPTIONS':
        # Handle OPTIONS request
        response = JsonResponse({'message': 'This is an OPTIONS request'})
        # Set CORS headers
        response['Access-Control-Allow-Origin'] = '*'  # Update with your allowed origins
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE'  # Update with your allowed methods
        response['Access-Control-Allow-Headers'] = 'Content-Type'  # Update with your allowed headers
        return response
    else:
        return JsonResponse({'error': 'Only POST requests are allowed!'}, status=405)

def generate_prompt(user_response, skills, experience , role, skills_required):
    prompt = "Act as a interviewer and ask some technical question to the candidate based on this information.Just one question to the candidate not reply by the candidate , and question should be only one. "
    prompt += f"User Response: {user_response}\n"
    prompt += f"Skills: {', '.join(skills)}\n"
    prompt += f"Experience Level: {experience}\n"
    prompt += f"Role Interviewing For: {role}\n"
    # prompt += f"Skills Required for the Job: {', '.join(skills_required)}\n"
    # prompt += f"Question to be ask on topics : {', '.join(topics)}\n"
    return prompt


@csrf_exempt
def process_audio(request):
    openai.api_key = os.getenv("openai_secret") 

    if request.method == 'POST':
        json_data = json.loads(request.body)
        base64_audio_data = json_data.get("audioBase64")
        
        # base64_audio_data = request.POST.get("audioBase64")

        try:
            # Decode base64 data
            audio_binary_data = base64.b64decode(base64_audio_data)
           
            # Create an AudioFileModel instance and save the audio file
            audio_model = AudioFile()
            audio_model.audio_file.save('audio_file4.mp3', io.BytesIO(audio_binary_data), save=True)

            # Get the transcript of the audio
            transcript_response = transcribe_view(request, audio_model.id)
            transcript_content = transcript_response.content
            transcript_dict = json.loads(transcript_content)
            transcript = transcript_dict.get('transcript')
            
            user_details = UserDetail.objects.last()  # Assuming you want the latest user details
            if user_details:
                role = user_details.role
                experience = user_details.experience
                skills = user_details.skills
            prompt = generate_prompt(transcript, skills,experience, role, required_skills_for_job)

            # Include the history of asked questions in the prompt
            prompt += get_question_history_prompt()

            openai_response = get_openai_response(prompt)

            # Update the question history with the latest question
            update_question_history(openai_response)
            
            return JsonResponse({'status': 'success', 'audio_id': audio_model.id, 'transcript': transcript, 'openai-response': openai_response, 'prompt': prompt}, safe=False) 

        except Exception as e:
            # Handle any exceptions that may occur during decoding or saving
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    elif request.method == 'OPTIONS':
        # Handle OPTIONS request
        response = JsonResponse({'message': 'This is an OPTIONS request'})
        # Set CORS headers
        response['Access-Control-Allow-Origin'] = '*'  # Update with your allowed origins
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE'  # Update with your allowed methods
        response['Access-Control-Allow-Headers'] = 'Content-Type'  # Update with your allowed headers
        return response
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
    
    
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
            role = request.GET.getlist('role')
            experience = request.GET.getlist('experience')
            skills = request.GET.getlist('skills')
            prompt = generate_prompt(transcript, skills,  experience,  role, required_skills_for_job)

            # Include the history of asked questions in the prompt
            prompt += get_question_history_prompt()

            openai_response = get_openai_response(prompt)

            # Update the question history with the latest question
            update_question_history(openai_response)
            
            return JsonResponse({'transcript': transcript, 'openai-response': openai_response, 'prompt': prompt}, safe=False)
            # return JsonResponse({'transcript': transcript, 'openai-response': openai_response}, safe=False)
 
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)
