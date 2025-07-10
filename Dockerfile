# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container first
# This helps Docker cache the installed packages
COPY requirements-a2a.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements-a2a.txt

# Copy the rest of the application's code into the container
COPY . .

# The default command to run when the container launches.
# Note: This will be overridden by the 'command' directive
# in your docker-compose.yml for each specific service.
CMD ["python", "main.py"]
