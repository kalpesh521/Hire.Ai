# Project Title

Django application to make evaluation of [Ai-interviewer-project](https://github.com/rasikaghadge/AI-Automated-Interview-Platform)

## Installation 

To install the project, follow these steps:

1. Clone the repository: `git clone https://github.com/kalpesh521/Hire.Ai.git`
2. Navigate to the project directory: `cd Hire.Ai`
3. Install the required packages: `pip install -r requirements.txt`

## Environment Variables

To run this project, you will need to add the following environment variables to your .env file:

`OPENAI_API_KEY` - Your OpenAI API key.

`VOICE_ID` - Your ElevenLabs voice ID.

`ELEVENLABS_MODEL_ID` - Your ElevenLabs model ID.

`ELEVENLABS_API_KEY` - Your ElevenLabs API key.

## Running the Project

To run the project:

1. Activate your virtual environment: `source venv/bin/activate`
2. Run the server: `python manage.py runserver`

## Features

- Converts text to speech using the ElevenLabs API
- Accepts an audio file, converts the audio to text, generates a response, and then converts the response back to speech

## API Reference

#### POST `/audio`

Converts text to speech using the ElevenLabs API.

| Parameter | Type     | Description                |
| :-------- | :------- | :------------------------- |
| `audio_file` | `file` | **Required**. The audio file to convert |

## Contributing

Contributions are always welcome!

See `CONTRIBUTING.md` for ways to get started.

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Contact
