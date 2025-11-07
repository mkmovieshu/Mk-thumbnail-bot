from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Thumbnail Bot is running ✅"

def run():
    port = int(os.getenv("PORT", "8080"))
    # Flask built-in server (dev). Hosts like Replit / Railway can use this.
    app.run(host="0.0.0.0", port=port)
