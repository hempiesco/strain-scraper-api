from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://hempesv2.staging.tempurl.host"]}})

# Load OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_openai(prompt):
    """Helper function to query OpenAI GPT-4o and return text response."""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are an expert cannabis strain researcher."},
                      {"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except openai.OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return None
    except Exception as e:
        print(f"Error querying OpenAI: {e}")
        return None

def get_strain_data_from_ai(strain_name):
    """Fetches structured strain data from OpenAI using multiple queries for JSON formatting accuracy."""

    sources = []

    # **1️⃣ Get Name & Alternative Name**
    name_prompt = f"Find strain '{strain_name}' on Leafly or AllBud. If it exists, return only:\n\nName: [Strain Name]\nAlternative Name: [Other names or blank]"
    name_response = ask_openai(name_prompt)

    if name_response:
        name_lines = name_response.split("\n")
        name = name_lines[0].replace("Name:", "").strip() if len(name_lines) > 0 else strain_name
        alternative_name = name_lines[1].replace("Alternative Name:", "").strip() if len(name_lines) > 1 else "Blank"
        sources.append("Leafly or AllBud")
    else:
        name, alternative_name = strain_name, "Blank"
        sources.append("OpenAI Knowledge")

    # **2️⃣ Get THC & CBD Content**
    thc_cbd_prompt = f"Find strain '{strain_name}' and return just THC and CBD percentages. Format:\nTHC: [number]\nCBD: [number]"
    thc_cbd_response = ask_openai(thc_cbd_prompt)

    thc_content, cbd_content = 0.0, 0.0  # Default values

    if thc_cbd_response:
        for line in thc_cbd_response.split("\n"):
            if "THC:" in line:
                try:
                    thc_content = float(line.split(":")[1].strip())
                except ValueError:
                    thc_content = 0.0
            if "CBD:" in line:
                try:
                    cbd_content = float(line.split(":")[1].strip())
                except ValueError:
                    cbd_content = 0.0
        sources.append("Leafly or AllBud")
    else:
        sources.append("OpenAI Knowledge")

    # **3️⃣ Get Aromas, Flavors, Terpenes, Effects, and Benefits**
    attributes_prompt = f"List the characteristics of strain '{strain_name}' as separate comma-separated values:\nAromas: [List]\nFlavors: [List]\nTerpenes: [List]\nEffects: [List]\nBenefits: [List]"
    attributes_response = ask_openai(attributes_prompt)

    attributes = {
        "aromas": [],
        "flavors": [],
        "terpenes": [],
        "effects": [],
        "benefits": []
    }

    if attributes_response:
        for line in attributes_response.split("\n"):
            key = line.split(":")[0].strip().lower()
            values = line.split(":")[1].strip().split(", ") if ":" in line else []
            if key in attributes:
                attributes[key] = values
        sources.append("Leafly or AllBud")
    else:
        sources.append("OpenAI Knowledge")

    # **4️⃣ Get Description**
    description_prompt = f"Write a **concise**, engaging, and **non-medical** description for '{strain_name}'. No medical claims."
    description = ask_openai(description_prompt) or "No description available."

    # **5️⃣ Get User-Reported Reviews Summary**
    reviews_prompt = f"Summarize **only user reviews** for '{strain_name}' in one paragraph without medical claims."
    user_reviews = ask_openai(reviews_prompt) or "No user reviews available."

    # **6️⃣ Build JSON Response**
    strain_data = {
        "name": name,
        "alternative_name": alternative_name if alternative_name else "",
        "thc_content": thc_content,
        "cbd_content": cbd_content,
        "aromas": attributes.get("aromas", []),
        "flavors": attributes.get("flavors", []),
        "terpenes": attributes.get("terpenes", []),
        "effects": attributes.get("effects", []),
        "benefits": attributes.get("benefits", []),
        "description": description,
        "user_reported_reviews": user_reviews,
        "sources": list(set(sources))  # Ensure unique sources
    }

    return strain_data

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
