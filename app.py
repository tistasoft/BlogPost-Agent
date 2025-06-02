from flask import Flask, render_template, request, jsonify
from utils import get_post_id_from_url, optimize_content, update_wordpress
import os, csv
from io import StringIO
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_csv():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    content = file.read().decode("utf-8")
    reader = csv.reader(StringIO(content))
    next(reader, None)  # skip header

    rows = []
    for row in reader:
        if len(row) < 2:
            continue
        url = row[0].strip()
        keywords = [k.strip() for k in row[1].split(",")]
        rows.append({
            "url": url,
            "keywords": keywords,
            "status": "",
            "message": ""
        })
    return jsonify({"rows": rows})

@app.route("/process-row", methods=["POST"])
def process_row():
    data = request.get_json()
    url = data.get("url")
    keywords = data.get("keywords", [])

    try:
        if not url or not url.startswith("http"):
            return jsonify({"success": False, "message": "Invalid URL"})
        post_id, post_content = get_post_id_from_url(url)
        # optimized = optimize_content(post_content, keywords)
        # update_wordpress(post_id, optimized)
        update_wordpress(post_id, post_content)
        return jsonify({"success": True, "message": "Updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

if __name__ == "__main__":
    app.run(debug=True)