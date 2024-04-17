# Use the official Python image from the Docker Hub
FROM python:3.8-alpine

# Set environment variables for Python to run in unbuffered mode
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /code

# Copy the requirements file to the container
COPY requirements.txt /code/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files to the container
COPY . /code/

# Expose the port the app runs on
EXPOSE 8000

# Run the Django application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "Interview.wsgi:application"]
