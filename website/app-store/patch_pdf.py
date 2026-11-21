from pathlib import Path

p = Path("app.py")
s = p.read_text()

start_admin = s.index('@app.route("/admin", methods=["GET", "POST"])')
end_admin = s.index('@app.route("/delete/', start_admin)

admin_code = r'''
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

'''

s = s[:start_admin] + admin_code + s[end_admin:]

start_upload = s.index('@app.route("/upload", methods=["POST"])')
end_upload = s.index('@app.route("/download/', start_upload)

upload_code = r'''
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

'''

s = s[:start_upload] + upload_code + s[end_upload:]

p.write_text(s)
print("APK + PDF Admin System updated successfully!")
