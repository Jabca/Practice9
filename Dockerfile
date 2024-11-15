# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get -y update  && apt-get -y upgrade 
RUN apt-get install -y ffmpeg

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run app.py when the container launches
CMD ["python", "lib/main.py"]

