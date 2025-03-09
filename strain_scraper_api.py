from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# Load API Key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_strain_data_from_ai(strain_name):
    """Fetch strain data using OpenAI with improved error handling"""
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
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a cannabis expert providing accurate strain information."},
                      {"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        raw_ai_response = response.choices[0].message.content.strip()
        print(f"🔍 AI RAW RESPONSE: {raw_ai_response}")  # Debugging output

        # Try to parse as JSON
        strain_data = json.loads(raw_ai_response)
        return strain_data

    except json.JSONDecodeError:
        print("❌ ERROR: OpenAI returned invalid JSON format.")
        return {"error": "AI returned malformed data."}
    
    except openai.OpenAIError as e:
        print(f"❌ OpenAI API Error: {e}")
        return {"error": "AI processing failed due to API error."}
    
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
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
