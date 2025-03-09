from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import openai
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# OpenAI API Key
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

def extract_text(soup, selector):
    """Extracts text content from a given selector."""
    try:
        return " ".join([tag.text.strip() for tag in soup.select(selector) if tag.text.strip()])
    except Exception as e:
        print(f"Error extracting {selector}: {e}")
        return ""

def scrape_leafly(url):
    """Scrapes Leafly strain data."""
    soup = fetch_html(url)
    if not soup:
        return None

    try:
        return {
            "name": soup.find(class_="text-secondary").text.strip() if soup.find(class_="text-secondary") else "Unknown",
            "description": extract_text(soup, '[data-testid="strain-description-container"]'),
            "thc_content": extract_text(soup, '[data-testid="THC"]').replace("%", ""),
            "cbd_content": extract_text(soup, '[data-testid="CBD"]').replace("%", ""),
            "aromas_raw": extract_text(soup, "#strain-aromas-section"),
            "flavors_raw": extract_text(soup, "#strain-flavors-section"),
            "terpenes_raw": extract_text(soup, "#strain-terpenes-section"),
            "effects_raw": extract_text(soup, "#strain-sensations-section"),
            "reviews_raw": extract_text(soup, "#strain-reviews-section")
        }
    except Exception as e:
        print(f"Leafly scraping error: {e}")
        return None

def scrape_allbud(url):
    """Scrapes AllBud strain data."""
    soup = fetch_html(url)
    if not soup:
        return None

    try:
        return {
            "name": soup.find("h1").text.strip() if soup.find("h1") else "Unknown",
            "description": extract_text(soup, ".panel-body.well.description"),
            "thc_content": extract_text(soup, ".percentage").replace("%", ""),
            "aromas_raw": extract_text(soup, "#aromas"),
            "flavors_raw": extract_text(soup, "#flavors"),
            "effects_raw": extract_text(soup, "#positive-effects"),
            "reviews_raw": extract_text(soup, "#collapse_reviews")
        }
    except Exception as e:
        print(f"AllBud scraping error: {e}")
        return None

def process_with_ai(leafly_data, allbud_data):
    """Uses AI to process and categorize scraped data properly."""
    prompt = f"""
    You are a data processor that extracts structured cannabis strain information.
    Take the raw data below and extract the following fields in a structured format:
    
    - **Aromas**: List of distinctive aromas.
    - **Flavors**: List of distinctive flavors.
    - **Terpenes**: Extract only the terpene names.
    - **Effects**: List of reported effects.
    - **Summarized User Reviews**: A short summary of what users reported about the strain.

    **Raw Data:**
    Leafly:
    - Aromas: {leafly_data.get("aromas_raw", "")}
    - Flavors: {leafly_data.get("flavors_raw", "")}
    - Terpenes: {leafly_data.get("terpenes_raw", "")}
    - Effects: {leafly_data.get("effects_raw", "")}
    - Reviews: {leafly_data.get("reviews_raw", "")}

    AllBud:
    - Aromas: {allbud_data.get("aromas_raw", "")}
    - Flavors: {allbud_data.get("flavors_raw", "")}
    - Effects: {allbud_data.get("effects_raw", "")}
    - Reviews: {allbud_data.get("reviews_raw", "")}

    Please return the response in JSON format like this:
    {{
        "aromas": ["...", "..."],
        "flavors": ["...", "..."],
        "terpenes": ["...", "..."],
        "effects": ["...", "..."],
        "user_reported_reviews": "..."
    }}
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a data extraction assistant."},
                  {"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()

@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    strain_name = request.args.get('name')
    leafly_url = f"https://www.leafly.com/strains/{'-'.join(strain_name.lower().split())}"
    allbud_url = f"https://www.allbud.com/marijuana-strains/hybrid/{'-'.join(strain_name.lower().split())}"

    if not strain_name:
        return jsonify({'error': 'Strain name is required'}), 400

    # Scrape both sites
    leafly_data = scrape_leafly(leafly_url)
    allbud_data = scrape_allbud(allbud_url)

    # Merge and process raw data
    processed_data = process_with_ai(leafly_data, allbud_data)

    # Prepare final response
    final_data = {
        "name": strain_name,
        "strain_subname": leafly_data["name"] if leafly_data else allbud_data["name"] if allbud_data else strain_name,
        "thc_content": leafly_data["thc_content"] if leafly_data else allbud_data["thc_content"] if allbud_data else None,
        "cbd_content": leafly_data["cbd_content"] if leafly_data else "1%",
        "description": process_with_ai(leafly_data, allbud_data),  # AI-Generated Description
        **eval(processed_data)  # Processed attributes from AI
    }

    return jsonify(final_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
