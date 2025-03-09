# Use official Python image
FROM python:3.9

# Set working directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Expose port
EXPOSE 5000

# Use Gunicorn for production
CMD sh -c "gunicorn -w 4 -b 0.0.0.0:${PORT} strain_scraper_api:app"
