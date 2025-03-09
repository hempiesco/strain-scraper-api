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
        You are an expert cannabis researcher. Retrieve detailed strain information for '{strain_name}'. 
        Prioritize Leafly and AllBud, but use other reputable sources if needed. Extract and structure the data as JSON.

        Required fields:
        - **Description** (Engaging but no medical claims)
        - **Aromas** (List of aromas)
        - **Flavors** (List of flavors)
        - **Terpenes** (List of terpenes)
        - **THC Content** (Exact percentage if found)
        - **CBD Content** (Exact percentage if found, default to 1% if missing)
        - **Strain Subname** (e.g., "aka Apple Fritters")
        - **User-Reported Reviews** (Summarized user feedback)

        Output response as **valid JSON ONLY** with this format:
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
        Ensure there is no additional text, only JSON.
        """

        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        # Ensure response is valid JSON
        response_text = response['choices'][0]['message']['content'].strip()

        # Debugging - Log response from OpenAI
        print(f"AI Response: {response_text}")

        # Parse JSON
        strain_data = json.loads(response_text)

        return strain_data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        return {"error": "Invalid JSON response from OpenAI"}

    except openai.error.OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return {"error": "Issue with OpenAI API"}

    except Exception as e:
        print(f"Unexpected Error: {e}")
        return {"error": "AI processing failed."}


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
