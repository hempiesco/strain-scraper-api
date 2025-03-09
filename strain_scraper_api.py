from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# Load API Key for OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


def get_strain_data_from_ai(strain_name):
    """Uses OpenAI Browsing to find and structure strain data."""
    try:
        prompt = f"""
        Find accurate and up-to-date strain information for '{strain_name}'. Prioritize data from sources like Leafly and AllBud, 
        but if unavailable, use another reputable source or your internal knowledge. Extract the following:

        - A clean, well-formatted **description** (avoiding medical claims).
        - **Aromas** (if available).
        - **Flavors** (if available).
        - **Terpenes** (if available).
        - **THC Content** (if available).
        - **CBD Content** (if available, default to 1% if missing).
        - **Strain Subname** (if known, e.g., "aka Apple Fritters").
        - **User-reported review summary** (summarize themes, avoid medical claims).
        
        Return the response in **valid JSON format**, structured like this:
        {{
            "description": "...",
            "aromas": ["..."],
            "flavors": ["..."],
            "terpenes": ["..."],
            "thc_content": "...",
            "cbd_content": "...",
            "strain_subname": "...",
            "user_reported_reviews": "..."
        }}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are an expert cannabis researcher."},
                      {"role": "user", "content": prompt}],
            temperature=0.7
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
            "thc_content": "Unknown",
            "cbd_content": "1%",
            "strain_subname": "Unknown",
            "user_reported_reviews": "No summary available."
        }


@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    strain_name = request.args.get('name')

    if not strain_name:
        return jsonify({'error': 'Strain name is required'}), 400

    # Get AI-Generated Data from OpenAI's Browsing and Knowledge Base
    strain_data = get_strain_data_from_ai(strain_name)

    # Final Response
    final_data = {
        "name": strain_name,
        **strain_data  # Merges all AI-generated fields
    }

    return jsonify(final_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
