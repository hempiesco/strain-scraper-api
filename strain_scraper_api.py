from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import openai
import os
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# Load API Key for OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


def fetch_html(url):
    """Fetches and parses HTML content from a URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None


def scrape_leafly(url):
    """Scrapes Leafly strain data."""
    soup = fetch_html(url)
    if not soup:
        return None

    try:
        name = soup.find(class_="text-secondary").text.strip() if soup.find(class_="text-secondary") else "Unknown"
        description = soup.find(attrs={"data-testid": "strain-description-container"}).text.strip() if soup.find(attrs={"data-testid": "strain-description-container"}) else "No description available"
        thc_content = soup.find(attrs={"data-testid": "THC"}).text.strip().replace("%", "") if soup.find(attrs={"data-testid": "THC"}) else None
        cbd_content = soup.find(attrs={"data-testid": "CBD"}).text.strip().replace("%", "") if soup.find(attrs={"data-testid": "CBD"}) else None
        
        # Extract Aromas, Flavors, Terpenes
        aromas = [tag.text.strip() for tag in soup.select("#strain-aromas-section a")]
        flavors = [tag.text.strip() for tag in soup.select("#strain-flavors-section a")]
        terpenes = [tag.text.strip() for tag in soup.select("#strain-terpenes-section a")]
        
        # Extract Reviews
        reviews = soup.find(id="strain-reviews-section").text.strip() if soup.find(id="strain-reviews-section") else ""

        return {
            "name": name,
            "description": description,
            "thc_content": thc_content,
            "cbd_content": cbd_content,
            "aromas": aromas,
            "flavors": flavors,
            "terpenes": terpenes,
            "reviews": reviews
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
        name = soup.find("h1").text.strip() if soup.find("h1") else "Unknown"
        description = soup.find(class_="panel-body well description").text.strip() if soup.find(class_="panel-body well description") else "No description available"
        thc_content = soup.find(class_="percentage").text.strip().replace("%", "") if soup.find(class_="percentage") else None
        
        # Extract Aromas, Flavors, Effects
        aromas = [tag.text.strip() for tag in soup.select("#aromas a")]
        flavors = [tag.text.strip() for tag in soup.select("#flavors a")]
        effects = [tag.text.strip() for tag in soup.select("#positive-effects a")]
        
        # Extract Reviews
        reviews = soup.find(id="collapse_reviews").text.strip() if soup.find(id="collapse_reviews") else ""

        return {
            "name": name,
            "description": description,
            "thc_content": thc_content,
            "aromas": aromas,
            "flavors": flavors,
            "effects": effects,
            "reviews": reviews
        }
    except Exception as e:
        print(f"AllBud scraping error: {e}")
        return None


def process_with_ai(leafly_data, allbud_data):
    """Uses OpenAI to process and categorize strain attributes."""
    try:
        prompt = f"""
        Extract relevant information from the given strain descriptions and reviews.
        Ensure the final data includes: 
        - A clean and formatted description (avoiding medical claims).
        - Categorized attributes for aromas, flavors, and terpenes.
        - A user-reported review summary.
        
        Leafly Data:
        {json.dumps(leafly_data, indent=2)}

        AllBud Data:
        {json.dumps(allbud_data, indent=2)}

        Return the response in **valid JSON format**, structured like this:
        {{
            "description": "...",
            "aromas": ["..."],
            "flavors": ["..."],
            "terpenes": ["..."],
            "user_reported_reviews": "..."
        }}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are an expert cannabis data processor."},
                      {"role": "user", "content": prompt}]
        )

        # Ensure response is valid JSON
        processed_data = json.loads(response['choices'][0]['message']['content'].strip())

        return processed_data
    except Exception as e:
        print(f"AI Processing Error: {e}")
        return {
            "description": "AI processing failed.",
            "aromas": [],
            "flavors": [],
            "terpenes": [],
            "user_reported_reviews": "No summary available."
        }


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

    # Merge Data
    final_data = {
        "name": strain_name,
        "strain_subname": leafly_data["name"] if leafly_data else allbud_data["name"] if allbud_data else strain_name,
        "thc_content": leafly_data["thc_content"] if leafly_data else allbud_data["thc_content"] if allbud_data else None,
        "cbd_content": leafly_data["cbd_content"] if leafly_data else "1%",
        "aromas": list(set((leafly_data["aromas"] if leafly_data else []) + (allbud_data["aromas"] if allbud_data else []))),
        "flavors": list(set((leafly_data["flavors"] if leafly_data else []) + (allbud_data["flavors"] if allbud_data else []))),
        "effects": list(set((leafly_data["effects"] if leafly_data else []) + (allbud_data["effects"] if allbud_data else []))),
        "terpenes": list(set((leafly_data["terpenes"] if leafly_data else [])))
    }

    # AI Processing
    ai_data = process_with_ai(leafly_data, allbud_data)

    # Merge AI Data into Final Output
    final_data.update(ai_data)

    return jsonify(final_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
