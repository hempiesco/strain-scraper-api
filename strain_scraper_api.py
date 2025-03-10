from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# Load OpenAI API Key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

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

def get_strain_data_from_ai(strain_name):
    """Fetches strain details using AI knowledge and web searches."""
    
    # 1️⃣ Get General Strain Data
    prompt_general = f"""
    Find the cannabis strain '{strain_name}' on Leafly and AllBud. 
    If not found, use the most reliable sources available. 
    Provide a structured response with:
    - Name:
    - Alternative Name (if available, otherwise 'Blank'):
    - Description (No medical claims, just strain details):
    - Effects (comma-separated list):
    - Aromas (comma-separated list):
    - Flavors (comma-separated list):
    - Terpenes (comma-separated list):
    - Benefits (comma-separated list, no medical claims):
    - Sources (where the data came from, comma-separated):
    """
    general_response = ask_openai(prompt_general)

    # 2️⃣ Get THC & CBD Content
    thc_cbd_prompt = f"""
    Find the THC and CBD percentages for the strain '{strain_name}'. 
    If data is unavailable, return "THC: 0%" and "CBD: 0%".
    Format:
    THC: [number]%
    CBD: [number]%
    """
    thc_cbd_response = ask_openai(thc_cbd_prompt)

    # Extract THC & CBD values safely
    thc_content, cbd_content = 0.0, 0.0
    if thc_cbd_response:
        thc_match = re.search(r"THC:\s*([\d.]+)%?", thc_cbd_response)
        cbd_match = re.search(r"CBD:\s*([\d.]+)%?", thc_cbd_response)

        if thc_match:
            try:
                thc_content = float(thc_match.group(1))
            except ValueError:
                thc_content = 0.0

        if cbd_match:
            try:
                cbd_content = float(cbd_match.group(1))
            except ValueError:
                cbd_content = 0.0

    # 3️⃣ Get User Reviews Summary
    reviews_prompt = f"""
    Summarize the user-reported reviews for '{strain_name}' from sources like Leafly, AllBud, or trusted online communities.
    Format: Provide a short, unbiased summary in 2-3 sentences.
    """
    reviews_summary = ask_openai(reviews_prompt) or "No user reviews available."

    # Ensure AI returned valid data
    if not general_response:
        return {"error": "AI processing failed."}

    # Extract structured data
    structured_data = {
        "name": strain_name,
        "alternative_name": "Blank",
        "thc_content": thc_content,
        "cbd_content": cbd_content,
        "description": "No description available.",
        "effects": [],
        "aromas": [],
        "flavors": [],
        "terpenes": [],
        "benefits": [],
        "user_reported_reviews": reviews_summary,
        "sources": []
    }

    try:
        # Parse AI response
        lines = general_response.split("\n")
        for line in lines:
            if line.startswith("Name:"):
                structured_data["name"] = line.split(":")[1].strip()
            elif line.startswith("Alternative Name:"):
                structured_data["alternative_name"] = line.split(":")[1].strip()
            elif line.startswith("Description:"):
                structured_data["description"] = line.split(":", 1)[1].strip()
            elif line.startswith("Effects:"):
                structured_data["effects"] = [e.strip() for e in line.split(":", 1)[1].split(",") if e.strip()]
            elif line.startswith("Aromas:"):
                structured_data["aromas"] = [a.strip() for a in line.split(":", 1)[1].split(",") if a.strip()]
            elif line.startswith("Flavors:"):
                structured_data["flavors"] = [f.strip() for f in line.split(":", 1)[1].split(",") if f.strip()]
            elif line.startswith("Terpenes:"):
                structured_data["terpenes"] = [t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()]
            elif line.startswith("Benefits:"):
                structured_data["benefits"] = [b.strip() for b in line.split(":", 1)[1].split(",") if b.strip()]
            elif line.startswith("Sources:"):
                structured_data["sources"] = [s.strip() for s in line.split(":", 1)[1].split(",") if s.strip()]
    except Exception as e:
        print(f"Error parsing AI response: {e}")
        return {"error": "AI returned malformed data."}

    return structured_data

@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    """API endpoint to fetch strain details."""
    strain_name = request.args.get('name')

    if not strain_name:
        return jsonify({'error': 'Strain name is required'}), 400

    strain_data = get_strain_data_from_ai(strain_name)
    
    return jsonify(strain_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
