# Python image use karenge
FROM python:3.9

# User setup
WORKDIR /app

# Requirements copy karke install karein
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Main code copy karein
COPY main.py .

# Bot run karein
CMD ["python", "main.py"]
