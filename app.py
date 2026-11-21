from flask import Flask, request, redirect, render_template_string
from pathlib import Path
from werkzeug.utils import secure_filename
import zipfile

app = Flask(__name__)

BASE = Path.home() / "termux-tricks-host"
SITES = BASE / "website"
UPLOADS = BASE / "uploads"

SITES.mkdir(exist_ok=True)
UPLOADS.mkdir(exist_ok=True)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Termux Tricks Hosting</title>
<style>
body {
 background:#101827;
 color:white;
 font-family:Arial;
 text-align:center;
 padding:30px;
}
.box {
 background:#1e293b;
 padding:25px;
 border-radius:15px;
 max-width:500px;
 margin:auto;
}
button {
 background:#00c878;
 padding:12px 25px;
 border:0;
 border-radius:8px;
}
input {margin:15px;}
a {color:#00e6a0;}
</style>
</head>
<body>
<div class="box">
<h1>🔥 TERMUX TRICKS HOSTING</h1>
<h3>My Own Hosting Server</h3>
<form method="POST" enctype="multipart/form-data">
<input type="file" name="file" accept=".zip" required>
<br>
<button>Upload Website</button>
</form>
<h3>Hosted Websites</h3>
{% for site in sites %}
<p><a href="/sites/{{site}}/" target="_blank">{{site}}</a></p>
{% endfor %}
</div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        f = request.files.get("file")

        if not f or not f.filename.lower().endswith(".zip"):
            return "Only ZIP files allowed", 400

        name = secure_filename(Path(f.filename).stem)

        if not name:
            return "Invalid filename", 400

        dest = SITES / name
        temp = UPLOADS / "upload.zip"

        f.save(temp)

        try:
            with zipfile.ZipFile(temp) as z:
                for item in z.infolist():
                    target = (dest / item.filename).resolve()
                    if not target.is_relative_to(dest.resolve()):
                        return "Invalid ZIP path", 400
                z.extractall(dest)
        except Exception:
            return "Invalid ZIP file", 400
        finally:
            temp.unlink(missing_ok=True)

        return redirect("/")

    sites = [p.name for p in SITES.iterdir() if p.is_dir()]
    return render_template_string(HTML, sites=sites)

@app.route("/sites/<site>/", defaults={"path": "index.html"})
@app.route("/sites/<site>/<path:path>")
def serve_site(site, path):
    folder = (SITES / secure_filename(site)).resolve()
    target = (folder / path).resolve()

    if not target.is_relative_to(folder):
        return "Forbidden", 403

    if not target.is_file():
        return "File not found", 404

    from flask import send_file
    return send_file(target)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
