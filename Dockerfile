# Use Python 3.10
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy required files
COPY requirements.txt requirements.txt
COPY strain_scraper_api.py strain_scraper_api.py

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose API port
EXPOSE 5000

# Run the API
CMD ["python", "strain_scraper_api.py"]