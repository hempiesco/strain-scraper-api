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

        Return the response **strictly** in JSON format with the following structure:
        {{
            "name": "Apple Fritter",
            "alternative_name": "",  # Leave blank if none found
            "thc_content": 24.0,  # Number only, no text
            "cbd_content": 1.0,  # Number only, no text
            "aromas": ["Sweet", "Earthy", "Apple"],  # Array of words
            "flavors": ["Apple", "Vanilla", "Pastry"],  # Array of words
            "terpenes": ["Caryophyllene", "Limonene", "Pinene"],  # Array of words
            "effects": ["Relaxing", "Euphoric", "Uplifting"],  # Array of words
            "description": "A well-balanced hybrid...",
            "user_reported_reviews": "Users describe the experience as..."
        }}

        Important:
        - Do NOT include any medical claims or FDA-sensitive language.
        - Keep all numeric values as pure numbers (e.g., 24.0, 1.0).
        - Ensure JSON is **valid and properly structured**.
        """

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a cannabis strain expert and data researcher."},
                      {"role": "user", "content": prompt}]
        )

        # Convert AI response to JSON
        strain_data = response.choices[0].message.content.strip()

        # Ensure response is valid JSON
        import json
        try:
            strain_json = json.loads(strain_data)
            return strain_json  # Return as JSON object
        except json.JSONDecodeError:
            print("AI returned malformed JSON.")
            return {"error": "AI returned malformed data."}

    except openai.OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return {"error": "AI processing failed due to API error."}
    except Exception as e:
        print(f"Error processing AI response: {e}")
        return {"error": "Unexpected processing error."}

@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    strain_name = request.args.get('name')

    if not strain_name:
        return jsonify({"error": "Strain name is required"}), 400

    # Fetch structured strain data using OpenAI
    strain_data = get_strain_data_from_ai(strain_name)

    return jsonify(strain_data)  # Return JSON response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
