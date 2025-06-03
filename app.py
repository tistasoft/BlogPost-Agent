import csv
import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime
from werkzeug.utils import secure_filename
from utils import get_post_id_from_url, optimize_content, update_wordpress

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SESSION_FILE = None  # Stores current file path
SESSION_ROWS = []    # Stores current rows in memory

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_csv():
    global SESSION_FILE, SESSION_ROWS

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    SESSION_FILE = path

    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Status", "").strip().lower() == "done":
                continue
            rows.append({
                "url": row["URL"].strip(),
                "keywords": [k.strip() for k in row["Keywords"].split(",")],
                "status": row.get("Status", ""),
                "last_updated": row.get("Last updated", "")
            })
    SESSION_ROWS = rows
    return jsonify({"rows": rows})

@app.route("/process-row", methods=["POST"])
def process_row():
    global SESSION_FILE

    data = request.get_json()
    url = data.get("url")
    keywords = data.get("keywords", [])

    try:
        post_id, post_content = get_post_id_from_url(url)
        optimized = optimize_content(post_content, keywords)
        update_wordpress(post_id, optimized)
        # update_wordpress(post_id, post_content)
        # Update CSV row
        update_csv_status(SESSION_FILE, url)
        return jsonify({"success": True, "message": "Updated and marked as done"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

def update_csv_status(filepath, url):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated_rows = []

    print("Updating file:", filepath)

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        
        # Normalize header keys
        required_fields = ["URL", "Keywords", "Status", "Last updated"]
        for field in required_fields:
            if field not in fieldnames:
                fieldnames.append(field)

        for row in reader:
            # Ensure row has all keys
            for field in required_fields:
                if field not in row:
                    row[field] = ""

            if row["URL"].strip() == url.strip():
                row["Status"] = "Done"
                row["Last updated"] = now
            updated_rows.append(row)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)


if __name__ == "__main__":
    app.run(debug=True)