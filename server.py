from flask import Flask
import subprocess
import os

app = Flask(__name__)

bot_directory = os.path.join(os.getcwd(), "bot")

bot_process = subprocess.Popen(
    ["python3", "app.py"], cwd=bot_directory
)

@app.route("/")
def home():
    return "hello"

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=7860)
    finally:
        bot_process.terminate()
