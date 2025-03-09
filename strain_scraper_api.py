from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# Allow CORS for your WordPress domain
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host", "https://your-main-wordpress-site.com"]}})

# Function to scrape Leafly
def scrape_leafly(url):
    try:
        logging.debug(f"Scraping Leafly: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logging.error(f"Leafly request failed with status code: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        name = soup.find('h1').text.strip() if soup.find('h1') else "Unknown"
        description = soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else "No description available"
        
        logging.debug(f"Leafly Data: Name: {name}, Description: {description[:50]}")
        return {'name': name, 'description': description}
    
    except Exception as e:
        logging.error(f"Leafly scraping error: {str(e)}")
        return None

# Function to scrape AllBud
def scrape_allbud(url):
    try:
        logging.debug(f"Scraping AllBud: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logging.error(f"AllBud request failed with status code: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        name = soup.find('h1').text.strip() if soup.find('h1') else "Unknown"
        description = soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else "No description available"
        
        logging.debug(f"AllBud Data: Name: {name}, Description: {description[:50]}")
        return {'name': name, 'description': description}
    
    except Exception as e:
        logging.error(f"AllBud scraping error: {str(e)}")
        return None

# API Route to Fetch Strain Data
@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    strain_name = request.args.get('name')
    leafly_url = request.args.get('leafly_url')
    allbud_url = request.args.get('allbud_url')

    if not strain_name:
        return jsonify({'error': 'Strain name is required'}), 400

    logging.info(f"Fetching strain: {strain_name}")
    
    strain_data = {'name': strain_name, 'description': "Generated AI description here."}

    if leafly_url:
        logging.info(f"Fetching Leafly data for {strain_name}")
        leafly_data = scrape_leafly(leafly_url)
        if leafly_data:
            strain_data.update(leafly_data)

    if allbud_url:
        logging.info(f"Fetching AllBud data for {strain_name}")
        allbud_data = scrape_allbud(allbud_url)
        if allbud_data:
            strain_data.update(allbud_data)

    logging.info(f"Final strain data: {strain_data}")
    return jsonify(strain_data)

# Run Flask with Gunicorn for Production
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
