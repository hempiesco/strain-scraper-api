from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import re
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

def fetch_html(url):
    """Fetches HTML content from a given URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def scrape_leafly(strain_name):
    """Scrapes strain data from Leafly."""
    url = f"https://www.leafly.com/strains/{'-'.join(strain_name.lower().split())}"
    soup = fetch_html(url)
    if not soup:
        return None

    try:
        return {
            "name": soup.find(attrs={"data-testid": "strain-name"}).text.strip() if soup.find(attrs={"data-testid": "strain-name"}) else strain_name,
            "description": soup.find(attrs={"data-testid": "strain-description-container"}).text.strip() if soup.find(attrs={"data-testid": "strain-description-container"}) else "No description available.",
            "thc_content": soup.find(attrs={"data-testid": "THC"}).text.strip().replace("%", "") if soup.find(attrs={"data-testid": "THC"}) else None,
            "cbd_content": soup.find(attrs={"data-testid": "CBD"}).text.strip().replace("%", "") if soup.find(attrs={"data-testid": "CBD"}) else None,
            "aromas": [tag.text.strip() for tag in soup.select("#strain-aromas-section li")],
            "flavors": [tag.text.strip() for tag in soup.select("#strain-flavors-section li")],
            "effects": [tag.text.strip() for tag in soup.select("#strain-sensations-section li")],
            "terpenes": [tag.text.strip() for tag in soup.select("#strain-terpenes-section li")],
            "benefits": [tag.text.strip() for tag in soup.select("#helps-with-section li")],
            "reviews": soup.find(id="strain-reviews-section").text.strip() if soup.find(id="strain-reviews-section") else ""
        }
    except Exception as e:
        print(f"Leafly scraping error: {e}")
        return None

def scrape_allbud(strain_name):
    """Scrapes strain data from AllBud."""
    url = f"https://www.allbud.com/marijuana-strains/hybrid/{'-'.join(strain_name.lower().split())}"
    soup = fetch_html(url)
    if not soup:
        return None

    try:
        return {
            "name": soup.find("h1").text.strip() if soup.find("h1") else strain_name,
            "description": soup.find(class_="panel-body well description").text.strip() if soup.find(class_="panel-body well description") else "No description available.",
            "thc_content": soup.find(class_="percentage").text.strip().replace("%", "") if soup.find(class_="percentage") else None,
            "aromas": [tag.text.strip() for tag in soup.select("#aromas li")],
            "flavors": [tag.text.strip() for tag in soup.select("#flavors li")],
            "effects": [tag.text.strip() for tag in soup.select("#positive-effects li")],
            "benefits": [tag.text.strip() for tag in soup.select("#helps-with-section li")],
            "reviews": soup.find(id="collapse_reviews").text.strip() if soup.find(id="collapse_reviews") else ""
        }
    except Exception as e:
        print(f"AllBud scraping error: {e}")
        return None

def ask_openai(prompt):
    """Calls OpenAI API to fetch strain data."""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except openai.OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return None

def get_strain_data(strain_name):
    """Gets strain data from Leafly, AllBud, and OpenAI if needed."""
    
    # 1️⃣ Try Scraping Leafly First
    leafly_data = scrape_leafly(strain_name)

    # 2️⃣ If Leafly is Incomplete, Try Scraping AllBud
    allbud_data = scrape_allbud(strain_name)

    # 3️⃣ Merge Data & Use OpenAI for Missing Fields
    strain_data = {
        "name": leafly_data["name"] if leafly_data else allbud_data["name"] if allbud_data else strain_name,
        "alternative_name": "Blank",
        "thc_content": leafly_data["thc_content"] if leafly_data else allbud_data["thc_content"] if allbud_data else None,
        "cbd_content": leafly_data["cbd_content"] if leafly_data else None,
        "aromas": list(set((leafly_data["aromas"] if leafly_data else []) + (allbud_data["aromas"] if allbud_data else []))),
        "flavors": list(set((leafly_data["flavors"] if leafly_data else []) + (allbud_data["flavors"] if allbud_data else []))),
        "effects": list(set((leafly_data["effects"] if leafly_data else []) + (allbud_data["effects"] if allbud_data else []))),
        "terpenes": leafly_data["terpenes"] if leafly_data else [],
        "benefits": list(set((leafly_data["benefits"] if leafly_data else []) + (allbud_data["benefits"] if allbud_data else []))),
        "description": leafly_data["description"] if leafly_data else allbud_data["description"] if allbud_data else None,
        "user_reported_reviews": "",
        "sources": []
    }

    # 4️⃣ If Anything is Missing, Ask OpenAI
    if not strain_data["description"]:
        prompt = f"Provide a detailed description of the cannabis strain '{strain_name}', without medical claims."
        strain_data["description"] = ask_openai(prompt) or "No description available."

    if not strain_data["thc_content"] or not strain_data["cbd_content"]:
        prompt_thc_cbd = f"Find the THC and CBD percentages for the strain '{strain_name}'. Format: THC: [number]%, CBD: [number]%."
        thc_cbd_response = ask_openai(prompt_thc_cbd)
        if thc_cbd_response:
            thc_match = re.search(r"THC:\s*([\d.]+)%?", thc_cbd_response)
            cbd_match = re.search(r"CBD:\s*([\d.]+)%?", thc_cbd_response)
            strain_data["thc_content"] = float(thc_match.group(1)) if thc_match else 0.0
            strain_data["cbd_content"] = float(cbd_match.group(1)) if cbd_match else 0.0

    # 5️⃣ Get User Reviews Summary
    prompt_reviews = f"Summarize user reviews for the strain '{strain_name}' from Leafly and AllBud."
    strain_data["user_reported_reviews"] = ask_openai(prompt_reviews) or "No user reviews available."

    # 6️⃣ Track Sources
    if leafly_data:
        strain_data["sources"].append("Leafly")
    if allbud_data:
        strain_data["sources"].append("AllBud")
    if "OpenAI" in strain_data["description"]:
        strain_data["sources"].append("OpenAI")

    return strain_data

@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    """API endpoint to fetch strain details."""
    strain_name = request.args.get('name')

    if not strain_name:
        return jsonify({'error': 'Strain name is required'}), 400

    strain_data = get_strain_data(strain_name)
    
    return jsonify(strain_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
