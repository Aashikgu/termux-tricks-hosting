from flask import Flask, request, redirect, session, url_for, send_from_directory, jsonify
from pathlib import Path
from werkzeug.utils import secure_filename
import json, secrets, os

BASE = Path(__file__).resolve().parent
UPLOADS = BASE / "uploads"
CONFIG = BASE / "config"
DATA = BASE / "apps.json"

UPLOADS.mkdir(exist_ok=True)
CONFIG.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

PASSWORD_FILE = CONFIG / "admin_password.txt"

if not PASSWORD_FILE.exists():
    password = secrets.token_urlsafe(10)
    PASSWORD_FILE.write_text(password)
    print("\nYOUR ADMIN PASSWORD:", password)
    print("Save this password safely!\n")

ADMIN_PASSWORD = PASSWORD_FILE.read_text().strip()

def get_apps():
    if not DATA.exists():
        return []
    try:
        return json.loads(DATA.read_text())
    except Exception:
        return []

def save_apps(apps):
    DATA.write_text(json.dumps(apps, indent=2))


import re



def extract_apk_icon(apk_path, uid):
    import subprocess
    import zipfile
    import re

    try:
        result = subprocess.run(
            ["aapt", "dump", "badging", str(apk_path)],
            capture_output=True, text=True, timeout=30
        )

        candidates = []

        # APK metadata से घोषित आइकन खोजें
        matches = re.findall(
            r"application-icon(?:-\d+)?:\s*'([^']+)'",
            result.stdout
        )
        candidates.extend(matches)

        # APK के अंदर मौजूद launcher images खोजें
        with zipfile.ZipFile(apk_path) as z:
            files = z.namelist()

            for item in files:
                low = item.lower()

                if not low.startswith("res/"):
                    continue

                if not low.endswith((".png", ".webp", ".jpg", ".jpeg")):
                    continue

                base = low.rsplit("/", 1)[-1]

                if any(word in base for word in (
                    "ic_launcher", "launcher_icon",
                    "app_icon", "appicon"
                )):
                    candidates.append(item)

            # पहले घोषित आइकन, फिर अन्य launcher images
            seen = set()
            candidates = [
                x for x in candidates
                if not (x in seen or seen.add(x))
            ]

            # बड़े density वाले आइकन पहले
            def rank(name):
                n = name.lower()
                score = 0
                for word, value in (
                    ("xxxhdpi", 5), ("xxhdpi", 4),
                    ("xhdpi", 3), ("hdpi", 2), ("mdpi", 1)
                ):
                    if word in n:
                        score += value * 10
                if "ic_launcher" in n:
                    score += 100
                if "round" in n:
                    score -= 20
                return score

            candidates.sort(key=rank, reverse=True)

            for item in candidates:
                if item not in files:
                    continue

                ext = Path(item).suffix.lower()
                if ext not in (".png", ".webp", ".jpg", ".jpeg"):
                    continue

                folder = BASE / "icons"
                folder.mkdir(exist_ok=True)

                output = folder / (uid + ext)
                output.write_bytes(z.read(item))

                print("APK ICON FOUND:", item)
                return "/icons/" + output.name

        print("No compatible icon image found")
        return None

    except Exception as e:
        print("ICON EXTRACTION ERROR:", e)
        return None

@app.route("/")
def home():
    return send_from_directory(BASE, "index.html")

@app.route("/api/apps")
def api_apps():
    return jsonify(get_apps())



@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        return "Wrong password. <a href='/admin'>Try again</a>"

    if not session.get("admin"):
        return """
        <body style="background:#151124;color:white;padding:30px;font-family:Arial">
        <h2>TERMUX TRICKS STORE - Admin Login</h2>
        <form method="post">
        <input name="password" type="password" placeholder="Admin Password" required>
        <button>Login</button>
        </form></body>
        """

    import html
    all_items = get_apps()
    total_downloads = sum(int(x.get("downloads", 0) or 0) for x in all_items)
    apk_count = sum(1 for x in all_items if x.get("file_type", "apk") != "pdf")
    pdf_count = sum(1 for x in all_items if x.get("file_type") == "pdf" or x.get("category") == "PDF Books")
    total_ratings = sum(int(x.get("reviews", 0) or 0) for x in all_items)
    stats_html = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:15px 0">
      <div style="background:#29213d;padding:15px;border-radius:10px">📥 Total Downloads<br><b>{total_downloads}</b></div>
      <div style="background:#29213d;padding:15px;border-radius:10px">📱 APK Apps<br><b>{apk_count}</b></div>
      <div style="background:#29213d;padding:15px;border-radius:10px">📚 PDF Books<br><b>{pdf_count}</b></div>
      <div style="background:#29213d;padding:15px;border-radius:10px">⭐ Total Ratings<br><b>{total_ratings}</b></div>
    </div>
    """
    rows = ""
    for i, item in enumerate(get_apps()):
        name = html.escape(str(item.get("name", "Unnamed")))
        category = html.escape(str(item.get("category", "Other")))
        kind = html.escape(str(item.get("file_type", "APK")).upper())
        rows += f"""
        <div style="background:#29213d;padding:12px;margin:10px 0;border-radius:10px">
        <b>{name}</b><br>Category: {category}<br>File: {kind}
        <form method="post" action="/delete/{i}"
        onsubmit="return confirm('Delete this item?')">
        <button style="background:#e53935;color:white;padding:9px;border:0">Delete</button>
        </form></div>
        """

    return """
    <body style="background:#151124;color:white;padding:20px;font-family:Arial">
    <h2>⚡ TERMUX TRICKS STORE</h2>
    """ + stats_html + """
    <h3>Upload New Content</h3>
    <form method="post" action="/upload" enctype="multipart/form-data">
    <p>Name</p><input name="name" maxlength="80" required>
    <p>Category</p>
    <select name="category" id="category" onchange="setFileType()" required>
    <option>Apps</option><option>Games</option><option>Top Apps</option>
    <option>Terminal</option><option>Books (APK)</option><option>PDF Books</option>
    </select>
    <p>Description</p><textarea name="description" maxlength="1000" required></textarea>
    <p id="file-label">APK File</p>
    <input type="file" name="content_file" id="content-file" accept=".apk" required>
    <p>Cover Photo / App Icon (Optional)</p>
    <input type="file" name="app_image" accept=".png,.jpg,.jpeg,.webp">
    <p><button type="submit">Upload</button></p>
    </form>
    <script>
    function setFileType(){
      const pdf = document.getElementById('category').value === 'PDF Books';
      document.getElementById('file-label').textContent = pdf ? 'PDF Book File' : 'APK File';
      document.getElementById('content-file').accept = pdf ? '.pdf' : '.apk';
    }
    </script>
    <hr><h3>Manage Uploaded Content</h3>
    """ + rows + """
    <p><a href="/api/apps" style="color:#b99aff">View App List</a></p>
    <p><a href="/logout" style="color:#ff9999">Logout</a></p>
    </body>
    """

@app.route("/delete/<int:index>", methods=["POST"])
def delete_app(index):
    if not session.get("admin"):
        return "Login required", 401

    apps = get_apps()

    if index < 0 or index >= len(apps):
        return "App not found", 404

    item = apps[index]

    # Delete APK only from the uploads folder
    filename = Path(str(item.get("file", ""))).name
    if filename:
        apk_path = (UPLOADS / filename).resolve()
        if apk_path.parent == UPLOADS.resolve() and apk_path.is_file():
            apk_path.unlink()

    # Delete icon only from the icons folder
    icon_url = str(item.get("icon_url", ""))
    if icon_url.startswith("/icons/"):
        icon_name = Path(icon_url).name
        icon_path = (BASE / "icons" / icon_name).resolve()
        if icon_path.parent == (BASE / "icons").resolve() and icon_path.is_file():
            icon_path.unlink()

    deleted_name = item.get("name", "App")
    apps.pop(index)
    save_apps(apps)

    return f"App deleted successfully: {deleted_name} <br><a href='/admin'>Back to Admin</a>"


@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("admin"):
        return "Login required", 401

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    file = request.files.get("content_file")
    image_file = request.files.get("app_image")

    categories = {
        "Apps", "Games", "Top Apps", "Terminal",
        "Books (APK)", "PDF Books"
    }

    if not name or category not in categories or not file or not file.filename:
        return "Name, category and file are required", 400

    is_pdf = category == "PDF Books"
    ext = ".pdf" if is_pdf else ".apk"

    if Path(file.filename).suffix.lower() != ext:
        return "Selected category requires a " + ext + " file", 400

    if len(name) > 80 or len(description) > 1000:
        return "Text too long", 400

    filename = secure_filename(file.filename)
    if not filename:
        return "Invalid filename", 400

    path = UPLOADS / filename
    if path.exists():
        return "Filename already exists. Rename the file.", 409

    allowed = {".png", ".jpg", ".jpeg", ".webp"}
    image_ext = None
    if image_file and image_file.filename:
        image_ext = Path(secure_filename(image_file.filename)).suffix.lower()
        if image_ext not in allowed:
            return "Invalid cover photo format", 400

    import uuid
    uid = uuid.uuid4().hex
    icon_url = None
    file.save(path)

    try:
        if image_file and image_file.filename:
            icons_dir = BASE / "icons"
            icons_dir.mkdir(exist_ok=True)
            image_name = uid + image_ext
            image_file.save(icons_dir / image_name)
            icon_url = "/icons/" + image_name
        elif not is_pdf:
            icon_url = extract_apk_icon(path, uid)

        apps = get_apps()
        apps.append({
            "name": name,
            "category": category,
            "file_type": "pdf" if is_pdf else "apk",
            "icon": "📚" if is_pdf else "📱",
            "icon_url": icon_url,
            "description": description,
            "file": "/download/" + filename,
            "rating": 0,
            "downloads": 0,
            "reviews": 0
        })
        save_apps(apps)

        notes = read_notifications()
        notes.insert(0, {
            "title": "🔔 नया कंटेंट उपलब्ध है!",
            "message": name + " अब TERMUX TRICKS STORE पर उपलब्ध है।",
            "icon_url": icon_url,
            "icon": "📚" if is_pdf else "📱",
            "time": __import__("datetime").datetime.now().strftime("%d-%m-%Y %H:%M")
        })
        (BASE / "notifications.json").write_text(
            json.dumps(notes[:50], indent=2, ensure_ascii=False)
        )
    except Exception:
        if path.exists():
            path.unlink()
        raise

    return "Upload सफल हुआ! <a href='/admin'>Back to Admin</a>"

@app.route("/api/rate/<int:index>", methods=["POST"])
def rate_item(index):
    data = request.get_json(silent=True) or {}
    try:
        rating = int(data.get("rating", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid rating"}), 400

    if rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be between 1 and 5"}), 400

    apps = get_apps()
    if index < 0 or index >= len(apps):
        return jsonify({"error": "Item not found"}), 404

    item = apps[index]
    old_reviews = int(item.get("reviews", 0) or 0)
    old_average = float(item.get("rating", 0) or 0)
    new_reviews = old_reviews + 1
    new_average = ((old_average * old_reviews) + rating) / new_reviews

    item["reviews"] = new_reviews
    item["rating"] = round(new_average, 2)
    save_apps(apps)

    return jsonify({
        "rating": item["rating"],
        "reviews": item["reviews"]
    })


@app.route("/download/<filename>")
def download(filename):
    filename = secure_filename(filename)
    apps = get_apps()

    for item in apps:
        if item.get("file") == "/download/" + filename:
            item["downloads"] = item.get("downloads", 0) + 1
            save_apps(apps)
            return send_from_directory(UPLOADS, filename, as_attachment=True)

    return "App not found", 404

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")

# TERMUX TRICKS STORE ADD-ON
@app.route("/api/store-info")
def store_info():
    return jsonify({
        "name": "TERMUX TRICKS STORE",
        "notifications": "/api/notifications",
        "admin": "/admin"
    })


@app.route("/admin/icons")
def admin_icons():
    if not session.get("admin"):
        return redirect("/admin")
    return """
    <body style="background:#100d19;color:white;font-family:Arial;padding:20px">
    <h2>⚡ TERMUX TRICKS - App Upload</h2>
    <form action="/upload-with-icon" method="post" enctype="multipart/form-data">
    <p>App Name</p><input name="name" required>
    <p>Category</p><select name="category">
    <option>Apps</option><option>Games</option>
    <option>Books</option><option>Terminal</option></select>
    <p>Description</p><textarea name="description" required></textarea>
    <p>App Icon</p><input type="file" name="icon_file" accept="image/png,image/jpeg,image/webp" required>
    <p>APK File</p><input type="file" name="apk" accept=".apk" required>
    <p><button>Upload App</button></p></form>
    </body>
    """

@app.route("/icons/<filename>")
def serve_app_icon(filename):
    filename = secure_filename(filename)
    return send_from_directory(BASE / "icons", filename)

@app.route("/api/notifications")
def api_notifications():
    return jsonify(read_notifications())

def read_notifications():
    path = BASE / "notifications.json"
    try:
        return json.loads(path.read_text()) if path.exists() else []
    except Exception:
        return []

@app.route("/upload-with-icon", methods=["POST"])
def upload_with_icon():
    if not session.get("admin"):
        return "Login required", 401

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    apk = request.files.get("apk")
    icon = request.files.get("icon_file")

    if not name or not category or not description or not apk or not icon:
        return "All fields are required", 400
    if len(name) > 80 or len(description) > 1000:
        return "Text too long", 400
    if not apk.filename.lower().endswith(".apk"):
        return "Only APK files are allowed", 400

    ext = Path(icon.filename).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        return "Icon must be PNG, JPG or WEBP", 400

    import uuid
    uid = uuid.uuid4().hex
    (BASE / "icons").mkdir(exist_ok=True)
    apk_name = uid + ".apk"
    icon_name = uid + ext
    apk.save(UPLOADS / apk_name)
    icon.save(BASE / "icons" / icon_name)

    apps = get_apps()
    app_item = {
        "id": uid, "name": name, "category": category,
        "description": description, "icon": "📱",
        "icon_url": "/icons/" + icon_name,
        "file": "/download/" + apk_name,
        "rating": 0, "downloads": 0, "reviews": 0
    }
    apps.insert(0, app_item)
    save_apps(apps)

    notes = read_notifications()
    notes.insert(0, {
        "title": "New App Added!",
        "message": name + " is now available.",
        "icon_url": app_item["icon_url"]
    })
    (BASE / "notifications.json").write_text(
        json.dumps(notes[:50], indent=2, ensure_ascii=False)
    )
    return "App uploaded! <a href='/admin/icons'>Upload another</a> | <a href='/'>Open Store</a>"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
