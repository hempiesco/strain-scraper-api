from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Allow requests from WordPress site
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host", "https://your-main-wordpress-site.com"]}})

# Function to scrape Leafly
def scrape_leafly(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        name = soup.find('h1').text.strip() if soup.find('h1') else "Unknown"
        description = soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else "No description available"
        return {'name': name, 'description': description}
    except Exception as e:
        return None

# Function to scrape AllBud
def scrape_allbud(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        name = soup.find('h1').text.strip() if soup.find('h1') else "Unknown"
        description = soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else "No description available"
        return {'name': name, 'description': description}
    except Exception as e:
        return None

# Route to Fetch Strain Data
@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    strain_name = request.args.get('name')
    leafly_url = request.args.get('leafly_url')
    allbud_url = request.args.get('allbud_url')

    if not strain_name:
        return jsonify({'error': 'Strain name is required'}), 400

    strain_data = {'name': strain_name, 'description': "Generated AI description here."}

    if leafly_url:
        leafly_data = scrape_leafly(leafly_url)
        if leafly_data:
            strain_data.update(leafly_data)

    if allbud_url:
        allbud_data = scrape_allbud(allbud_url)
        if allbud_data:
            strain_data.update(allbud_data)

    return jsonify(strain_data)

# Run Flask with Gunicorn for Production
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
