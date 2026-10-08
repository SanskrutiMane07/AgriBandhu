from flask import Flask, render_template, request, session, send_file, redirect,jsonify
import json
import sqlite3
import io
import pickle
import requests
from datetime import date
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

#print("JSON LOADED:", crop_data.keys())

import os
API_KEY2 = os.getenv("API_KEY2")
API_KEY = os.getenv("API_KEY")
app = Flask(__name__)
app.secret_key = os.getenv("secret123")
with open('crops.json') as f:
    crop_data = json.load(f)
with open('roadmap_data.json') as f:
    roadmap_data = json.load(f)  
with open("chatbot_data.json", "r", encoding="utf-8") as f:
    chatbot_data = json.load(f)
# Create database
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            username TEXT UNIQUE,
            email TEXT,
            password TEXT
        )
    ''')

    # ✅ ADDED (crop comparison table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crop_comparison(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            crop1 TEXT,
            crop2 TEXT,
            crop3 TEXT,
            best_crop TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# Load crop recommendation model
crop_model = pickle.load(open('crop_model.pkl', 'rb'))


# Home
@app.route('/')
def home():
    return render_template("index.html")

 #chatbot backend
# @app.route('/chat', methods=['POST'])
# def chat():
#    user_msg = request.json['message'].lower()

#    if "crop" in user_msg:
#      reply = "You can grow rice, wheat or maize depending on season."
#    elif "fertilizer" in user_msg:
#      reply = "Use NPK or organic compost."
#    elif "weather" in user_msg:
#      reply = "Check weather alerts section for updates."
#    elif "scheme" in user_msg:
#      reply = "Government schemes include PM-Kisan and crop insurance."
#    elif "hello" in user_msg:
#      reply = "Hello Farmer! 👋 How can I help you?"
#    else:
#     reply = "Sorry, I didn't understand."
#    return jsonify({"reply": reply})   

@app.route('/chatbot')
def chatbot_page():
    if 'user' not in session:
        return redirect('/login')
    return render_template("chatbot.html")
@app.route('/chat', methods=['POST'])
def chat_api():
    # force=True bypasses the strict Content-Type check
    data = request.get_json(force=True) 
    
    if not data:
        return jsonify({"reply": "Error: No data received"}), 400

    user_msg = data.get('message', '').lower().strip()

    best_match = None
    max_score = 0

    for intent, intent_data in chatbot_data.items():
        score = 0

        for keyword in intent_data.get("keywords", []):
            if keyword in user_msg:
                score += 1

        if score > max_score:
            max_score = score
            best_match = intent_data["response"]

    if best_match:
        return jsonify({"reply": best_match})

    return jsonify({
        "reply": "🤖 I can help with crops 🌾, fertilizer 🧪, weather 🌦, schemes 🏛, irrigation 💧 and profit 💰."
    })
# Profit Estimation
crop_mapping = {
    "rice": "Rice",
    "wheat": "Wheat",
    "maize": "Maize",
    "cotton": "Cotton",
    "sugarcane": "Sugarcane",
    "banana": "Banana",
    "mango": "Mango",
    "pomegranate": "Pomegranate",
    "grapes": "Grapes"
}
def get_market_price(crop):
    try:
        api_crop = crop_mapping.get(crop, crop.capitalize())
        url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={API_KEY2}&format=json&filters[commodity]={api_crop}"
        response = requests.get(url)
        data = response.json()

        if 'records' in data and len(data['records']) > 0:
            record_crop = data['records'][0]['commodity'].lower()

            if record_crop != crop:
                print("⚠️ MISMATCH! API returned:", record_crop)
                raise Exception("Wrong crop data")

        price = float(data['records'][0]['modal_price'])
        print("✅ API PRICE USED:", price)
        return price

    except Exception as e:
        print("❌ API FAILED:", e)

    fallback_prices = {
        "rice": 2200,
        "wheat": 2100,
        "maize": 1800,
        "cotton": 6000,
        "sugarcane": 350,
        "banana": 1500,
        "mango": 3000,
        "pomegranate": 5000,
        "grapes": 4000
    }

    print("⚠️ FALLBACK PRICE USED")
    return fallback_prices.get(crop.lower(), 2000)
    
def estimate_yield(crop, temp, humidity):
    base_yield = {
        "rice": 25,
        "wheat": 20,
        "maize": 30,
        "cotton": 10,
        "sugarcane": 100,
        "banana": 40,
        "mango": 15,
        "pomegranate": 12,
        "grapes": 18
    }

    y = base_yield.get(crop.lower(), 20)

    # Smart adjustments
    if temp > 35:
        y *= 0.85
    if humidity < 40:
        y *= 0.9

    return y  
#profit prediction
@app.route('/profit', methods=['GET', 'POST'])
def profit():
    if 'user' not in session:
        return redirect('/login')

    result = None

    if request.method == 'POST':
        crop = request.form.get('crop').lower()
        print("CROP SELECTED:", crop)
        land = float(request.form.get('land'))
        location = request.form.get('location')
        user_yield = request.form.get('yield')

        # 🌦 Get weather
        weather = fetch_weather(location)
        temp = weather["temperature"]
        humidity = weather["humidity"]

        # 💰 Market price
        price = get_market_price(crop)

        # 🤖 Yield logic
        if user_yield and user_yield.strip() != "":
            yield_per_acre = float(user_yield)
        else:
            yield_per_acre = estimate_yield(crop, temp, humidity)

        # 📊 Calculations
        total_yield = land * yield_per_acre
        revenue = total_yield * price
        cost = land * 20000
        profit_val = revenue - cost

        # ✅ THIS WAS MISSING
        result = {
            "crop": crop,
            "price": round(price, 2),
            "revenue": round(revenue, 2),
            "cost": round(cost, 2),
            "profit": round(profit_val, 2)
            #"source": "Live API"  # or "Estimated"
        }

    return render_template("profit_prediction.html", result=result)

# Step-by-Step Farming
@app.route('/roadmap', methods=['GET', 'POST'])
def roadmap():
    roadmap = None
    selected_crop = None

    if request.method == 'POST':
        selected_crop = request.form['crop']
        roadmap = roadmap_data.get(selected_crop)

    return render_template('farming_roadmap.html',
                           roadmap=roadmap,
                           selected_crop=selected_crop)

# 📄 Download PDF
@app.route('/download-roadmap', methods=['POST'])
def download_roadmap():
    crop = request.form['crop']

    # 🔹 Get logged-in user
    username = session.get('user')

    # 🔹 Fetch farmer name from DB
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute("SELECT fullname FROM users WHERE username=?", (username,))
    result = cursor.fetchone()

    farmer_name = result[0] if result else "Farmer"

    conn.close()

    # 🔹 Get roadmap steps
    steps = roadmap_data.get(crop)

    # 🔹 Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("AgriBandhu Farming Roadmap", styles['Title']))
    content.append(Spacer(1, 20))

    content.append(Paragraph(f"<b>Farmer Name:</b> {farmer_name}", styles['Normal']))
    content.append(Paragraph(f"<b>Crop:</b> {crop.capitalize()}", styles['Normal']))
    content.append(Paragraph(f"<b>Date:</b> {date.today()}", styles['Normal']))
    content.append(Spacer(1, 20))

    for i, step in enumerate(steps, 1):
        content.append(Paragraph(f"<b>Step {i}: {step['title']}</b>", styles['Heading3']))
        content.append(Paragraph(step['desc'], styles['BodyText']))
        content.append(Spacer(1, 12))

    doc.build(content)

    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name=f"{farmer_name}_{crop}_roadmap.pdf",
                     mimetype='application/pdf')
# Weather Alerts
@app.route('/weather')
def weather():
    if 'user' not in session:
        return redirect('/login')
    return render_template("weather_alerts.html")


# Government Schemes
@app.route('/schemes')
def schemes():
    if 'user' not in session:
        return redirect('/login')
    return render_template("government_schemes.html")



# Register Logic
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form

        if data['password'] != data['confirm_password']:
            return render_template("register.html", error="Passwords do not match")

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (fullname, username, email, password) VALUES (?, ?, ?, ?)",
                (data['fullname'], data['username'], data['email'], data['password'])
            )
            conn.commit()
        except:
            return render_template("register.html", error="Username already exists")

        conn.close()
        return redirect('/login')

    return render_template("register.html")


# Login Logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (data['username'], data['password'])
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = data['username']
            return redirect('/')
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


# auto fill temp humidity
@app.route('/get_weather')
def get_weather():
    city = request.args.get('city')

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={API_KEY}&units=metric"

    response = requests.get(url)
    data = response.json()

    if data["cod"] != 200:
        return {"error": "City not found"}

    temp = data["main"]["temp"]
    humidity = data["main"]["humidity"]

    return {"temperature": temp, "humidity": humidity}
def fetch_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        if data["cod"] != 200:
            return {"temperature": 30, "humidity": 70}

        return {
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"]
        }
    except:
        return {"temperature": 30, "humidity": 70}


# Crop Recommendation
@app.route('/crop', methods=['GET', 'POST'])
def recommend_crop():
    if 'user' not in session:
        return redirect('/login')

    recommended_crop = None
    top_crops = []

    if request.method == 'POST':
        try:
            N = float(request.form['N'])
            P = float(request.form['P'])
            K = float(request.form['K'])
            temperature = float(request.form['temperature'])
            humidity = float(request.form['humidity'])
            ph = float(request.form['ph'])
            rainfall = float(request.form['rainfall'])

            features = [[N, P, K, temperature, humidity, ph, rainfall]]

            probs = crop_model.predict_proba(features)[0]
            crops = crop_model.classes_

            sorted_crops = sorted(zip(crops, probs), key=lambda x: x[1], reverse=True)

            top_crops = [crop[0] for crop in sorted_crops[:3]]
            recommended_crop = top_crops[0]

        except:
            recommended_crop = "Invalid Input"

    return render_template(
        "crop_recommendation.html",
        recommended_crop=recommended_crop,
        top_crops=top_crops
    )

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    if 'user' not in session:
        return redirect('/login')
    

    crops = []
    best_crop = None
    

    if request.method == 'POST':
        crop1 = request.form.get('crop1')
        crop2 = request.form.get('crop2')
        crop3 = request.form.get('crop3')

        selected_crops = [crop1, crop2, crop3]

        for crop in selected_crops:
            if not crop:
                continue

            clean_crop = crop.strip().lower()

            print("MATCHING:", clean_crop)

            data = crop_data.get(clean_crop, {
                "cost": 0,
                "profit": 0,
                "duration": "N/A",
                "water": "N/A",
                "season": "N/A"
            })

            print("DATA FOUND:", data)

            crops.append({
                "name": crop,
                "cost": data["cost"],
                "profit": data["profit"],
                "duration": data["duration"],
                "water": data["water"],
                "season": data["season"]
            })

        # 🔥 Find best crop
        if crops:
            best_crop = max(crops, key=lambda x: x["profit"])["name"]

            # Save to DB
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO crop_comparison (user, crop1, crop2, crop3, best_crop) VALUES (?, ?, ?, ?, ?)",
                (session['user'], crop1, crop2, crop3, best_crop)
            )

            conn.commit()
            conn.close()

    return render_template(
        "crop_comparison.html",
        crops=crops,
        best_crop=best_crop
    )


# Run
if __name__ == "__main__":
    app.run(debug=True)