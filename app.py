from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

app = Flask(__name__)
CORS(app)# HERE it Allows frontend to send API requests to the backend

# Load and clean dataset
try:
    df = pd.read_csv("medical_ds.csv")
    df.dropna(subset=['Symptoms', 'Name', 'Treatments'], inplace=True)
    df['Symptoms'] = df['Symptoms'].apply(
        lambda x: ','.join(sorted([s.strip().lower() for s in str(x).split(',') if s.strip()])) )
    print("✅ CSV loaded.")
except Exception as e:
    print("❌ Error loading CSV:", e)
    df = pd.DataFrame(columns=["Name", "Symptoms", "Treatments"])

# Homepage route
@app.route('/')
def home():
    return render_template('index.html')

# Fuzzy matching helper
def fuzzy_match_symptom(input_symptom, all_symptoms):
    match = process.extractOne(input_symptom, all_symptoms, scorer=fuzz.partial_ratio)
    if match and match[1] > 70:# Uses fuzzy matching to find the closest known symptom if the user misspells a word.

      return match[0]
    return None

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get("query", "").lower().strip()

        if not user_input:
            return jsonify({"answer": "⚠️ Please provide a symptom or health-related question."})

        # Greeting, thanks, and bye checks
        greetings = {"hi", "hello", "hey", "hii", "good morning", "good afternoon", "good evening"}
        if any(greet in user_input for greet in greetings):
            return jsonify({"answer": "👋 Hello! Please tell me your symptoms, and I'll try to help you."})

        thanks = {"thanks", "thank you", "thx"}
        if any(thank in user_input for thank in thanks):
            return jsonify({"answer": "😊 You're welcome! Let me know if you need anything else."})

        bye = {"bye", "goodbye", "see you", "take care"}
        if any(bye in user_input for bye in bye):
            return jsonify({"answer": "👋 Take care! Wishing you good health. Bye!"})

        # Clean the input and extract symptoms
        cleaned_input = re.sub(r'[^\w\s]', '', user_input)  # Remove punctuation
        user_words = cleaned_input.split()

        # Gather all symptoms from dataset for matching
        all_symptoms = set()
        for sym_str in df['Symptoms']:
            all_symptoms.update([s.strip().lower() for s in sym_str.split(',')])

        extracted_symptoms = [word for word in user_words if word in all_symptoms]
        
        # If no exact match, use fuzzy matching
        if not extracted_symptoms:
            for word in user_words:
                matched_symptom = fuzzy_match_symptom(word, all_symptoms)
                if matched_symptom:
                    extracted_symptoms.append(matched_symptom)

        if not extracted_symptoms:
            return jsonify({"answer": "🤖 I couldn't identify any known symptoms in your message. Please try again."})

        # Find matching rows
        matched_rows = []
        for _, row in df.iterrows():
            dataset_symptoms = [s.strip().lower() for s in row['Symptoms'].split(',')]
            # Only consider rows where the extracted symptoms match at least some of the dataset's symptoms
            if any(sym in dataset_symptoms for sym in extracted_symptoms):
                matched_rows.append(row)

        if matched_rows:
            # Rank matches by number of symptoms matched
            matched_rows.sort(key=lambda row: sum(sym in row['Symptoms'].lower() for sym in extracted_symptoms), reverse=True)

            best_match = matched_rows[0]
            return jsonify({
                "answer": f"🩺 Condition: {best_match['Name']}\n💊 Treatment: {best_match['Treatments']}"
            })

        return jsonify({"answer": "🤖 No match found for the symptoms you entered. Please try again."})

    except Exception as e:
        print(f"🔥 Error: {e}")
        return jsonify({"answer": f"⚠️ An error occurred: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
