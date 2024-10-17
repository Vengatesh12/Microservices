# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install necessary build tools and libraries for pyodbc
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc-dev

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .
EXPOSE 5000
# Command to run the application
CMD ["python", "app.py"]