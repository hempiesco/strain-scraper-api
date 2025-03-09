from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_strain_data_from_ai(strain_name):
    """Fetch strain details from OpenAI using browsing capabilities."""
    try:
        prompt = f"""
        You are a cannabis expert. Gather detailed strain information for '{strain_name}' from Leafly, AllBud, or other reputable sources.
        If sources are unavailable, use your own knowledge.

        Extract and structure the data in **JSON format** with these fields:
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
        Ensure **NO extra text**, just JSON.
        """

        response = openai.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        # Ensure AI returns JSON only
        response_text = response.choices[0].message.content.strip()
        print(f"AI Response: {response_text}")  # Debugging output

        # Convert response to JSON
        strain_data = json.loads(response_text)
        return strain_data

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        return {"error": "Invalid JSON response from AI"}

    except openai.OpenAIError as e:
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

    # Fetch AI-Generated Data
    strain_data = get_strain_data_from_ai(strain_name)

    # Final Response
    final_data = {
        "name": strain_name,
        **strain_data  # Merges AI-generated fields
    }

    return jsonify(final_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
