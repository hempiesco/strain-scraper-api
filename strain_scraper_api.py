from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_strain_data_from_ai(strain_name):
    """Uses OpenAI GPT-4o to search for strain data and return structured JSON."""
    try:
        prompt = f"""
        Search for details about the cannabis strain "{strain_name}" on Leafly, AllBud, and other reliable sources.
        If the strain is not found, use your internal knowledge to generate the most accurate data.
        
        Extract and return structured JSON in the following format:
        {{
            "name": "{strain_name}",
            "strain_subname": "Alternative name if available",
            "thc_content": "THC percentage if available",
            "cbd_content": "CBD percentage if available",
            "aromas": ["List of aromas"],
            "flavors": ["List of flavors"],
            "effects": ["List of effects"],
            "terpenes": ["List of terpenes"],
            "description": "Detailed strain description without medical claims",
            "user_reported_reviews": "Summarized reviews from users"
        }}

        Do NOT include medical claims or any health benefits. Only provide factual information.
        """

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a cannabis strain expert and data researcher."},
                      {"role": "user", "content": prompt}]
        )

        # Extract JSON response
        strain_data = response.choices[0].message.content.strip()

        return eval(strain_data)  # Convert string response into JSON

    except openai.OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return {"error": "AI processing failed due to API error."}
    except Exception as e:
        print(f"Error processing AI response: {e}")
        return {"error": "AI returned malformed data."}

@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    strain_name = request.args.get('name')

    if not strain_name:
        return jsonify({"error": "Strain name is required"}), 400

    # Fetch strain data using OpenAI
    strain_data = get_strain_data_from_ai(strain_name)

    return jsonify(strain_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
