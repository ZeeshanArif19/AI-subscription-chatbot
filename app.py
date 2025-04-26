from flask import Flask, request, jsonify, render_template
import csv
import re
from google.generativeai import configure, GenerativeModel

# --- Configuration ---
app = Flask(__name__)
configure(api_key="AIzaSyC-NCBIh7ittFFFocHb5bpGNy41nxNkL_Q")  # Replace with your actual Gemini API key
model = GenerativeModel(model_name="models/gemini-1.5-flash-latest")

# --- Helper: Parse CSV to dictionary ---
def parse_csv(file_stream):
    subscriptions = []
    decoded = file_stream.read().decode("utf-8").splitlines()
    reader = csv.DictReader(decoded)
    for row in reader:
        subscriptions.append({
            "Service": row["Service"],
            "Cost": float(row["Cost"]),
            "Frequency": row.get("Frequency", "Monthly"),
            "LastUsed": row.get("LastUsed", "Unknown")
        })
    return subscriptions

# --- Helper: Extract subscriptions from text ---
def extract_subscriptions_from_text(text):
    subscriptions = []
    pattern = r"(?P<service>[A-Za-z0-9\s]+)\s+at\s+\$(?P<cost>\d+(\.\d+)?)\s+(?P<frequency>monthly|annually|yearly|year|month)"
    matches = re.finditer(pattern, text, re.IGNORECASE)

    for match in matches:
        service = match.group("service").strip()
        cost = float(match.group("cost"))
        frequency = match.group("frequency").lower()
        frequency = "Monthly" if "month" in frequency else "Annually"

        subscriptions.append({
            "Service": service,
            "Cost": cost,
            "Frequency": frequency,
            "LastUsed": "Unknown"
        })

    return subscriptions

# --- Helper: Create prompt for analyzing subscriptions ---
def create_analysis_prompt(subscriptions, user_query):
    prompt = """
You are 'Subscription Cost Analyzer Bot', a smart and helpful assistant.

Your goals:
- Analyze and summarize the user's subscription costs (monthly and annually).
- Categorize subscriptions into types (e.g., Entertainment, Productivity, Utilities).
- Highlight subscriptions that are expensive or rarely used.
- Suggest possible subscriptions to cancel, pause, or downgrade.
- Estimate costs for unknown subscriptions only if the user specifically asks.

Important Rules:
- Base your answers strictly on the user's provided subscription data (from file or chat).
- Use general market knowledge only when explicitly requested.
- Keep your answers clear, concise, structured, and friendly.

Here are the user's current subscriptions:
"""
    for sub in subscriptions:
        prompt += f"- {sub['Service']}: ${sub['Cost']} ({sub['Frequency']}), Last used: {sub['LastUsed']}\n"

    prompt += f"\nUser's Question: {user_query}\n\nPlease provide your detailed analysis based on the above."
    return prompt

# --- Helper: Create prompt for recommending subscriptions ---
def create_recommendation_prompt(user_query):
    prompt = f"""
You are 'Subscription Recommendation Bot', a smart and budget-friendly assistant.

The user has provided a budget and/or a specific interest area (e.g., sports, entertainment, daily soaps, education).
Your tasks are:
- Suggest **subscription services** that fit within the mentioned budget.
- Prefer services popular in India unless otherwise specified.
- Recommend 2-5 options depending on the budget.
- Mention the approximate monthly or yearly cost.
- If no budget is clearly mentioned, assume an affordable range (around 1000-3000 rupees).
- Answer only subscription related queries.

Important:
- Recommendations must match the **category or interest area** the user asks about.
- If the budget is tight, prioritize more affordable services or free trials.

Here is the user's request:
\"{user_query}\"

Respond clearly, politely, and with helpful explanations.
"""
    return prompt

# --- Route: Home Page ---
@app.route("/")
def index():
    return render_template("index.html")  # Make sure you have an 'index.html' in your templates folder

# --- Route: Handle user message and file upload ---
@app.route("/analyze", methods=["POST"])
def analyze():
    user_query = request.form.get("query")
    file = request.files.get("file")

    if not user_query:
        return jsonify({"error": "Query is required."}), 400

    subscriptions = []

    # Try parsing file
    if file:
        try:
            subscriptions = parse_csv(file)
        except Exception as e:
            return jsonify({"error": f"Failed to parse CSV: {str(e)}"}), 400

    # Try extracting from user chat
    if not subscriptions:
        subscriptions = extract_subscriptions_from_text(user_query)

    # Decide which prompt to create
    if subscriptions:
        prompt = create_analysis_prompt(subscriptions, user_query)
    else:
        prompt = create_recommendation_prompt(user_query)

    try:
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt)
        reply = response.text
    except Exception as e:
        return jsonify({"error": f"Failed to communicate with Gemini API: {str(e)}"}), 500

    return jsonify({"response": reply})

# --- Run app ---
if __name__ == "__main__":
    app.run(debug=True)
