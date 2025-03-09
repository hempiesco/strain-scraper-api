from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_strain_data_from_ai(strain_name):
    """Uses OpenAI GPT-4o to search for strain data without enforcing JSON formatting."""
    try:
        prompt = f"""
        Search for details about the cannabis strain "{strain_name}" on Leafly, AllBud, and other reliable sources.
        If the strain is not found, use your internal knowledge to generate the most accurate data.

        Provide all the details you can find about the strain, including:
        - Name
        - Alternative name (if available)
        - THC & CBD content
        - Aromas, flavors, effects, and terpenes
        - A detailed strain description (without medical claims)
        - A summary of user-reported reviews.

        Do NOT format the response as JSON. Just return the full text in a readable way.
        """

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a cannabis strain expert and data researcher."},
                      {"role": "user", "content": prompt}]
        )

        # Get raw AI response
        strain_data = response.choices[0].message.content.strip()

        return strain_data  # Return raw text response

    except openai.OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return "AI processing failed due to API error."
    except Exception as e:
        print(f"Error processing AI response: {e}")
        return "AI returned malformed data."

@app.route('/fetch_strain', methods=['GET'])
def fetch_strain():
    strain_name = request.args.get('name')

    if not strain_name:
        return jsonify({"error": "Strain name is required"}), 400

    # Fetch strain data using OpenAI
    strain_data = get_strain_data_from_ai(strain_name)

    return jsonify({"response": strain_data})  # Return raw AI response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
