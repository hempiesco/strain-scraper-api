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
    """Fetch strain data using OpenAI with enforced JSON response format"""
    prompt = f"""
    Provide a JSON response with detailed information about the cannabis strain "{strain_name}".
    
    **Strict JSON Format:**  
    {{
      "name": "{strain_name}",
      "strain_subname": "Alternative name if available, otherwise 'Unknown'",
      "thc_content": "THC percentage (e.g., '24%' or 'Unknown')",
      "cbd_content": "CBD percentage (e.g., '1%' if unknown)",
      "aromas": ["Earthy", "Citrus"], 
      "flavors": ["Sweet", "Berry"], 
      "terpenes": ["Caryophyllene", "Limonene"], 
      "effects": ["Relaxed", "Happy"], 
      "user_reported_reviews": "Summarized user reviews in 2-3 sentences."
    }}

    **Rules:**  
    - **Return only valid JSON** (no extra text, no explanations).  
    - **Do not include medical claims.**  
    - **Use 'Unknown' for missing values.**  
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a cannabis expert providing structured strain data."},
                      {"role": "user", "content": prompt}],
            response_format="json",  # ✅ Forces JSON Output
            temperature=0
        )

        raw_ai_response = response.choices[0].message.content.strip()
        print(f"🔍 AI RAW RESPONSE: {raw_ai_response}")  # Debugging output

        # Ensure OpenAI returns valid JSON
        try:
            strain_data = json.loads(raw_ai_response)
            return strain_data
        except json.JSONDecodeError:
            print("❌ ERROR: JSON Decoding Failed.")
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
