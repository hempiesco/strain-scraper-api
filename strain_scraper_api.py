from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import openai

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

import os
import openai

# Load API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

def fetch_html(url):
    """Fetches the HTML content of a URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def scrape_leafly(url):
    """Scrapes Leafly strain data using known IDs and attributes."""
    soup = fetch_html(url)
    if not soup:
        return None

    try:
        name = soup.find(class_="text-secondary").text.strip() if soup.find(class_="text-secondary") else "Unknown"
        description = soup.find(attrs={"data-testid": "strain-description-container"}).text.strip() if soup.find(attrs={"data-testid": "strain-description-container"}) else "No description available"
        thc_content = soup.find(attrs={"data-testid": "THC"}).text.strip().replace("%", "") if soup.find(attrs={"data-testid": "THC"}) else None
        cbd_content = soup.find(attrs={"data-testid": "CBD"}).text.strip().replace("%", "") if soup.find(attrs={"data-testid": "CBD"}) else None
        aromas = [tag.text.strip() for tag in soup.select("#strain-aromas-section li")]
        flavors = [tag.text.strip() for tag in soup.select("#strain-flavors-section li")]
        effects = [tag.text.strip() for tag in soup.select("#strain-sensations-section li")]
        terpenes = [tag.text.strip() for tag in soup.select("#strain-terpenes-section li")]
        benefits = [tag.text.strip() for tag in soup.select("#helps-with-section li")]
        reviews = soup.find(id="strain-reviews-section").text.strip() if soup.find(id="strain-reviews-section") else ""

        return {
            "name": name,
            "description": description,
            "thc_content": thc_content,
            "cbd_content": cbd_content,
            "aromas": aromas,
            "flavors": flavors,
            "effects": effects,
            "terpenes": terpenes,
            "benefits": benefits,
            "reviews": reviews
        }
    except Exception as e:
        print(f"Leafly scraping error: {e}")
        return None

def scrape_allbud(url):
    """Scrapes AllBud strain data using known IDs and classes."""
    soup = fetch_html(url)
    if not soup:
        return None

    try:
        name = soup.find("h1").text.strip() if soup.find("h1") else "Unknown"
        description = soup.find(class_="panel-body well description").text.strip() if soup.find(class_="panel-body well description") else "No description available"
        thc_content = soup.find(class_="percentage").text.strip().replace("%", "") if soup.find(class_="percentage") else None
        aromas = [tag.text.strip() for tag in soup.select("#aromas li")]
        flavors = [tag.text.strip() for tag in soup.select("#flavors li")]
        effects = [tag.text.strip() for tag in soup.select("#positive-effects li")]
        benefits = [tag.text.strip() for tag in soup.select("#helps-with-section li")]
        reviews = soup.find(id="collapse_reviews").text.strip() if soup.find(id="collapse_reviews") else ""

        return {
            "name": name,
            "description": description,
            "thc_content": thc_content,
            "aromas": aromas,
            "flavors": flavors,
            "effects": effects,
            "benefits": benefits,
            "reviews": reviews
        }
    except Exception as e:
        print(f"AllBud scraping error: {e}")
        return None

def generate_ai_description(leafly_desc, allbud_desc, reviews):
    """Uses OpenAI to generate a refined description, avoiding medical claims and effects that are not approved by the fda."""
    prompt = f"""
    Combine the following strain descriptions and reviews into a single, refined description that is engaging and informative. 
    Avoid any medical claims or health benefits.

    Leafly Description:
    {leafly_desc}

    AllBud Description:
    {allbud_desc}

    User Reviews:
    {reviews}

    The final description should summarize key details while making it more engaging.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are an expert cannabis content writer."},
                  {"role": "user", "content": prompt}]
    )

    return response['choices'][0]['message']['content'].strip()

@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    strain_name = request.args.get('name')
    leafly_url = f"https://www.leafly.com/strains/{'-'.join(strain_name.lower().split())}"
    allbud_url = f"https://www.allbud.com/marijuana-strains/hybrid/{'-'.join(strain_name.lower().split())}"

    if not strain_name:
        return jsonify({'error': 'Strain name is required'}), 400

    # Scrape Leafly & AllBud
    leafly_data = scrape_leafly(leafly_url)
    allbud_data = scrape_allbud(allbud_url)

    # Merge Data, ensuring all attributes from both sources are included
    final_data = {
        "name": strain_name,
        "strain_subname": leafly_data["name"] if leafly_data else allbud_data["name"] if allbud_data else strain_name,
        "thc_content": leafly_data["thc_content"] if leafly_data else allbud_data["thc_content"] if allbud_data else None,
        "cbd_content": leafly_data["cbd_content"] if leafly_data else "1%",
        "aromas": list(set((leafly_data["aromas"] if leafly_data else []) + (allbud_data["aromas"] if allbud_data else []))),
        "flavors": list(set((leafly_data["flavors"] if leafly_data else []) + (allbud_data["flavors"] if allbud_data else []))),
        "effects": list(set((leafly_data["effects"] if leafly_data else []) + (allbud_data["effects"] if allbud_data else []))),
        "benefits": list(set((leafly_data["benefits"] if leafly_data else []) + (allbud_data["benefits"] if allbud_data else []))),
        "terpenes": leafly_data["terpenes"] if leafly_data else [],
        "reviews": leafly_data["reviews"] if leafly_data else allbud_data["reviews"] if allbud_data else ""
    }

    # Generate AI description
    final_data["description"] = generate_ai_description(
        leafly_data["description"] if leafly_data else "",
        allbud_data["description"] if allbud_data else "",
        final_data["reviews"]
    )

    return jsonify(final_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
