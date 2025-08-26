import re
from flask import Flask, request, send_file, render_template_string, jsonify
from collections import defaultdict, deque
from typing import Dict
import tempfile, os, time, hashlib, secrets
from image import create_vinayagar_card, validate_name

app = Flask(__name__)

_ip_hits: Dict[str, deque] = defaultdict(deque)
RATE_LIMIT, TIME_WINDOW = 5, 10

cache_dir = os.path.join(tempfile.gettempdir(), "flag_cache")
os.makedirs(cache_dir, exist_ok=True)
image_cache: Dict[str, str] = {}
CACHE_TTL = 60 * 60 * 24

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    hits = _ip_hits[ip]
    while hits and now - hits[0] > TIME_WINDOW:
        hits.popleft()
    if len(hits) >= RATE_LIMIT:
        return True
    hits.append(now)
    return False

def get_cache_key(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()

def clean_cache():
    now = time.time()
    for key, path in list(image_cache.items()):
        if not os.path.exists(path) or now - os.path.getmtime(path) > CACHE_TTL:
            image_cache.pop(key, None)
            if os.path.exists(path):
                os.remove(path)

@app.after_request
def set_security_headers(response):
    nonce = getattr(request, "csp_nonce", "")
    csp = (
        f"default-src 'self'; "
        f"style-src 'self' https://fonts.googleapis.com 'nonce-{nonce}'; "
        f"font-src https://fonts.gstatic.com; "
        f"script-src 'self' 'nonce-{nonce}'; "
        f"img-src 'self' data: blob:; "
        "object-src 'none'; base-uri 'self';"
    )
    response.headers.update({
        "Content-Security-Policy": csp,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "public, max-age=86400"
        # "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload"
    })
    return response

@app.before_request
def generate_nonce():
    request.csp_nonce = secrets.token_urlsafe(16)

HTML_FORM = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>🙏🏻 Happy Vinayagar Chaturthi 🪔</title>
<meta name="description" content="🙏🏻 Happy Vinayagar Chaturthi 🪔 - A special 🙏🏻 Happy Vinayagar Chaturthi 🪔 greeting for your friends and Family Members.">
<link rel="preconnect" href="https://fonts.googleapis.com" nonce="{{nonce}}">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin nonce="{{nonce}}">
<link href="https://fonts.googleapis.com/css2?family=Mozilla+Text:wght@200..700&display=swap" rel="stylesheet" nonce="{{nonce}}">
<style nonce="{{nonce}}">
    body {
        background: #ffe4e9;
        color: #333;
        font-family: "Mozilla Text", sans-serif;
        font-weight: 600;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 10px;
        margin: 0;
    }
    h1 {
        color: #c2185b;
        text-align: center;
        font-family: "Mozilla Text", sans-serif;
        font-size: clamp(1.2rem, 5vw, 2rem);
    }
    .container {
        background: #fff0f5;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(194, 24, 91, 0.15);
        max-width: 500px;
        width: 100%;
        box-sizing: border-box;
    }
    input {
        width: 100%;
        padding: 12px;
        font-family: "Mozilla Text", sans-serif;
        font-size: 16px;
        background: #ffeef3;
        border: 1px solid #f8cdd7;
        border-radius: 6px;
        color: #333;
        margin-bottom: 12px;
        box-sizing: border-box;
    }
    input:focus {
        outline: none;
        border-color: #f48fb1;
        box-shadow: 0 0 0 2px rgba(244, 143, 177, 0.3);
    }
    button {
        padding: 12px;
        border: none;
        border-radius: 6px;
        font-family: "Mozilla Text", sans-serif;
        font-size: 16px;
        cursor: pointer;
        font-weight: bold;
        width: 100%;
        margin-bottom: 10px;
        transition: opacity 0.2s ease-in-out;
    }
    .primary {
        background: linear-gradient(90deg, #f06292, #ec407a);
        color: white;
    }
    .primary:hover { opacity: 0.9; }
    .success {
        background: linear-gradient(90deg, #81c784, #4caf50);
        color: white;
        display: none;
    }
    .terminal {
        background: #fff5f8;
        color: #ad1457;
        font-family: monospace;
        padding: 10px;
        height: 200px;
        overflow-y: auto;
        border-radius: 6px;
        font-size: 14px;
        margin-top: 10px;
        white-space: pre-wrap;
        border: 1px solid #f8cdd7;
        box-shadow: inset 0 0 8px rgba(0,0,0,0.05);
    }
    .terminal div::before {
        content: "$ ";
        color: #ec407a;
        font-weight: bold;
    }
    img {
        max-width: 100%;
        margin-top: 12px;
        border-radius: 8px;
        display: none;
    }
</style>
</head>
<body>

<h1>Happy Vinayagar Chaturthi 🪔</h1>
<div class="container">
    <input type="text" id="name" placeholder="Enter Your Name" maxlength="30">
    <button id="generateBtn" class="primary">Generate Image</button>
    <button id="downloadBtn" class="success">Download Image</button>
    <div class="terminal" id="terminal">$ ./vinayagar.py "your name"\n</div>
    <img id="flagImage" alt="Happy Vinayagar Chaturthi">
</div>

<script nonce="{{nonce}}">
const term = document.getElementById("terminal");
const generateBtn = document.getElementById("generateBtn");
const downloadBtn = document.getElementById("downloadBtn");
const flagImage = document.getElementById("flagImage");

function log(msg){
    const line = document.createElement("div");
    line.textContent = msg;
    term.appendChild(line);
    term.scrollTop = term.scrollHeight;
}

function generateFlag() {
    const name = document.getElementById("name").value.trim();
    term.textContent = `$ ./vinayagar.py "${name || 'your name'}"\n`;

    if (!name) {
        log("❌ Please enter a name.");
        return;
    }

    log("📦 Starting image generation...");
    log("🔍 Validating name...");

    fetch(`/generate?name=${encodeURIComponent(name)}`)
        .then(r => {
            if (!r.ok) {
                return r.json().then(data => {
                    throw new Error(data.error || "Server error");
                });
            }
            if (r.headers.get("content-type")?.includes("application/json")) {
                return r.json().then(data => { throw new Error(data.error); });
            }
            return r.blob();
        })
        .then(b => {
            log("🎨 Drawing Vinayagar Chaturthi Greeting image...");
            log("🖌 Adding footer text...");

            const url = URL.createObjectURL(b);
            flagImage.src = url;
            flagImage.style.display = "block";
            downloadBtn.onclick = () => {
               const a = document.createElement("a");
               a.href = url;
               const now = new Date();
               const yyyy = now.getFullYear();
               const mm = String(now.getMonth() + 1).padStart(2, "0");
               const dd = String(now.getDate()).padStart(2, "0");
               const number = Math.floor(Math.random() * 1000);
               a.download = `vinayagar_greeting_${yyyy}-${mm}-${dd}-${number}.png`;
               a.click();
            };
            downloadBtn.style.display = "block";
            log("✅ Vinayagar image generated successfully!");
        })
        .catch(e => {
            log("❌ " + e.message);
            flagImage.style.display = "none";
            downloadBtn.style.display = "none";
        });
}

generateBtn.addEventListener("click", generateFlag);
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_FORM, nonce=request.csp_nonce)

@app.route("/generate")
def generate_flag():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    if is_rate_limited(client_ip):
        print(f"⚠️ Rate limit hit: {client_ip}")
        return jsonify({"error": "Too many requests"}), 429

    raw_name = request.args.get("name", "").strip()

    if not raw_name:
        print("❌ Empty name received")
        return jsonify({"error": "Name cannot be empty"}), 400

    if any(ch in raw_name for ch in ['<', '>', '"', "'", '&', '`']):
        print(f"⚠️ Possible XSS attempt from {client_ip}: {raw_name}")
        return jsonify({"error": "Invalid characters in name"}), 400

    if not re.match(r"^[\w\s\-\.\u00C0-\uFFFF]+$", raw_name):
        print(f"⚠️ Disallowed characters from {client_ip}: {raw_name}")
        return jsonify({"error": "Name contains unsupported characters"}), 400

    try:

        name = validate_name(raw_name)

        clean_cache()
        cache_key = get_cache_key(name)

        if cache_key in image_cache and os.path.exists(image_cache[cache_key]):
            return send_file(image_cache[cache_key], mimetype="image/png")

        image_path = os.path.join(cache_dir, f"{cache_key}.png")
        create_vinayagar_card(name, image_path)
        image_cache[cache_key] = image_path

        return send_file(image_path, mimetype="image/png")

    except ValueError as ve:
        print(f"❌ Validation error: {ve}")
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        print(f"❌ Internal error: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

@app.route("/image/<path:raw_name>")
def generate_flag_slug(raw_name):
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    if is_rate_limited(client_ip):
        return jsonify({"error": "Too many requests"}), 429

    raw_name = raw_name.strip()

    if not raw_name:
        return jsonify({"error": "Name cannot be empty"}), 400

    if any(ch in raw_name for ch in ['<', '>', '"', "'", '&', '`']):
        return jsonify({"error": "Invalid characters in name"}), 400

    if not re.match(r"^[\w\s\-\.\u00C0-\uFFFF]+$", raw_name):
        return jsonify({"error": "Name contains unsupported characters"}), 400

    try:
        name = validate_name(raw_name)

        clean_cache()
        cache_key = get_cache_key(name)

        if cache_key in image_cache and os.path.exists(image_cache[cache_key]):
            return send_file(image_cache[cache_key], mimetype="image/png")

        image_path = os.path.join(cache_dir, f"{cache_key}.png")
        create_vinayagar_card(name, image_path)
        image_cache[cache_key] = image_path

        return send_file(image_path, mimetype="image/png")

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"❌ Internal error: {e}")
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == "__main__":
    app.run()
