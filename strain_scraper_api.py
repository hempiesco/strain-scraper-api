from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# Load API Key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_strain_data_from_ai(strain_name):
    """Fetch strain data using OpenAI, ensuring correct API calls"""
    prompt = f"""
    Gather the most accurate and up-to-date information about the cannabis strain "{strain_name}". 
    Include:
    - Description (No medical claims)
    - THC Content
    - CBD Content (Default to 1% if unknown)
    - Aromas
    - Flavors
    - Terpenes
    - Effects
    - User-Reported Reviews Summary

    Sources: First check Leafly and AllBud. If no data is found, summarize from OpenAI knowledge.
    Provide a structured JSON response.
    """

    try:
        response = openai.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a cannabis expert providing accurate strain information."},
                      {"role": "user", "content": prompt}],
            temperature=0.7
        )
        ai_data = response.choices[0].message.content.strip()
        return eval(ai_data)  # Convert JSON response
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return {"error": "AI processing failed."}

@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    strain_name = request.args.get('name')
    if not strain_name:
        return jsonify({"error": "Strain name is required"}), 400

    strain_data = get_strain_data_from_ai(strain_name)

    return jsonify(strain_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
