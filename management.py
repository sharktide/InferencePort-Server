import os
import json
import docker
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()
security = HTTPBasic()
client = docker.from_env()

CACHE_FILE = "/var/cache/inferenceport_env.json"
CONTAINER_NAME = "inferenceport-server"
CONTAINER_PORT = 7860
IMAGE_NAME = "ghcr.io/sharktide/inferenceport-server"
LOGOUT_URL = "/cdn-cig/access/logout"

def load_env_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {"GH_PAT": "", "AES_KEY": ""}

def save_env_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def auth(credentials: HTTPBasicCredentials = Depends(security)):
    expected_pass = os.getenv("PSWRD_ADMIN")  # underscore version
    if credentials.password != expected_pass:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

import html

@app.get("/", response_class=HTMLResponse)
def dashboard(auth_ok: bool = Depends(auth)):
    envs = load_env_cache()
    gh_pat_safe = html.escape(envs["GH_PAT"])
    aes_key_safe = html.escape(envs["AES_KEY"])
    return f"""
    <html>
    <head>
        <title>InferencePort Admin</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            :root {{
                --bg: #0b0d12;
                --panel: #12151c;
                --panel-2: #171b24;
                --border: #232838;
                --text: #e6e9f0;
                --muted: #8a90a2;
                --accent: #5b8cff;
                --accent-2: #4472e8;
                --green: #35d07f;
                --amber: #ffb454;
                --red: #ff5c5c;
                --purple: #b18cff;
                --radius: 12px;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                margin: 0;
                background: radial-gradient(circle at top left, #131722, #0b0d12 60%);
                color: var(--text);
                min-height: 100vh;
            }}
            .topbar {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 18px 32px;
                border-bottom: 1px solid var(--border);
                background: rgba(18, 21, 28, 0.7);
                backdrop-filter: blur(6px);
                position: sticky;
                top: 0;
                z-index: 10;
            }}
            .brand {{
                display: flex;
                align-items: center;
                gap: 10px;
                font-weight: 600;
                font-size: 18px;
                letter-spacing: 0.2px;
            }}
            .brand .dot {{
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: var(--green);
                box-shadow: 0 0 8px var(--green);
            }}
            .logout-btn {{
                background: transparent;
                color: var(--muted);
                border: 1px solid var(--border);
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 13px;
                cursor: pointer;
                transition: all 0.15s ease;
                text-decoration: none;
            }}
            .logout-btn:hover {{
                color: var(--red);
                border-color: var(--red);
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 32px;
            }}
            .card {{
                background: var(--panel);
                border: 1px solid var(--border);
                border-radius: var(--radius);
                padding: 24px 28px;
                margin-bottom: 24px;
            }}
            .card h3 {{
                margin: 0 0 4px 0;
                font-size: 15px;
                font-weight: 600;
                color: var(--text);
            }}
            .card .sub {{
                margin: 0 0 18px 0;
                font-size: 13px;
                color: var(--muted);
            }}
            .field {{
                margin-bottom: 16px;
            }}
            .field label {{
                display: block;
                font-size: 12px;
                color: var(--muted);
                margin-bottom: 6px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .field input {{
                width: 100%;
                background: var(--panel-2);
                border: 1px solid var(--border);
                color: var(--text);
                padding: 10px 12px;
                border-radius: 8px;
                font-size: 14px;
                font-family: "SF Mono", Consolas, monospace;
                outline: none;
                transition: border-color 0.15s ease;
            }}
            .field input:focus {{
                border-color: var(--accent);
            }}
            .btn-row {{
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }}
            button.action {{
                border: none;
                padding: 11px 18px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                color: white;
                transition: transform 0.1s ease, opacity 0.15s ease;
            }}
            button.action:hover {{ opacity: 0.9; }}
            button.action:active {{ transform: scale(0.97); }}
            .btn-start {{ background: var(--green); color: #06210f; }}
            .btn-stop {{ background: var(--panel-2); color: var(--text); border: 1px solid var(--border); }}
            .btn-restart {{ background: var(--accent); }}
            .btn-rebuild {{ background: var(--purple); color: #1b0e33; }}
            .btn-repull {{ background: var(--amber); color: #2e1c00; }}
            .btn-danger {{ background: var(--red); }}
            .danger-zone {{
                border-color: rgba(255, 92, 92, 0.35);
            }}
            .danger-zone h3 {{ color: var(--red); }}
            #logs {{
                width: 100%;
                height: 380px;
                border-radius: 10px;
                border: 1px solid var(--border);
                overflow-y: scroll;
                background: #05070a;
                color: #35d07f;
                font-family: "SF Mono", Consolas, monospace;
                font-size: 12.5px;
                padding: 14px;
                white-space: pre-wrap;
            }}
            .status-pill {{
                display: inline-block;
                font-size: 11px;
                padding: 3px 9px;
                border-radius: 999px;
                background: rgba(91, 140, 255, 0.15);
                color: var(--accent);
                margin-left: 8px;
                vertical-align: middle;
            }}
            .toast {{
                position: fixed;
                bottom: 24px;
                right: 24px;
                background: var(--panel-2);
                border: 1px solid var(--border);
                color: var(--text);
                padding: 12px 18px;
                border-radius: 10px;
                font-size: 13px;
                max-width: 360px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.4);
                opacity: 0;
                transform: translateY(10px);
                transition: all 0.2s ease;
                pointer-events: none;
            }}
            .toast.show {{
                opacity: 1;
                transform: translateY(0);
            }}
        </style>
    </head>
    <body>
        <div class="topbar">
            <div class="brand"><span class="dot"></span> InferencePort Admin</div>
            <a class="logout-btn" href="{LOGOUT_URL}">Log out</a>
        </div>

        <div class="container">
            <div class="card">
                <h3>Environment</h3>
                <p class="sub">Stored and injected into the container on next start.</p>
                <form id="envForm">
                    <div class="field">
                        <label>GH_PAT</label>
                        <input type="text" id="gh_pat" value="{gh_pat_safe}" autocomplete="off">
                    </div>
                    <div class="field">
                        <label>AES_KEY</label>
                        <input type="text" id="aes_key" value="{aes_key_safe}" autocomplete="off">
                    </div>
                </form>
            </div>

            <div class="card">
                <h3>Container Controls <span class="status-pill">{CONTAINER_NAME}</span></h3>
                <p class="sub">Manage the InferencePort server container.</p>
                <div class="btn-row">
                    <button class="action btn-start" onclick="action('start')">Start Container</button>
                    <button class="action btn-stop" onclick="action('stop')">Stop Container</button>
                    <button class="action btn-restart" onclick="action('restart')">Restart Container</button>
                    <button class="action btn-rebuild" onclick="action('factory-rebuild')">Factory Rebuild</button>
                    <button class="action btn-repull" onclick="action('repull')">Re-Pull Image</button>
                </div>
            </div>

            <div class="card danger-zone">
                <h3>Danger Zone</h3>
                <p class="sub">Force-remove any containers sharing this name or bound to port {CONTAINER_PORT}. Use this if start fails due to a name/port conflict.</p>
                <div class="btn-row">
                    <button class="action btn-danger" onclick="action('force-remove-conflicts')">Remove Conflicting Containers</button>
                </div>
            </div>

            <div class="card">
                <h3>Live Logs</h3>
                <pre id="logs"></pre>
            </div>
        </div>

        <div id="toast" class="toast"></div>

        <script>
            function toast(msg) {{
                const t = document.getElementById('toast');
                t.textContent = msg;
                t.classList.add('show');
                clearTimeout(window._toastTimer);
                window._toastTimer = setTimeout(() => t.classList.remove('show'), 3500);
            }}
            async function action(endpoint) {{
                const gh_pat = document.getElementById('gh_pat').value;
                const aes_key = document.getElementById('aes_key').value;
                const formData = new FormData();
                formData.append("gh_pat", gh_pat);
                formData.append("aes_key", aes_key);
                try {{
                    const res = await fetch("/" + endpoint, {{ method: "POST", body: formData }});
                    const text = await res.text();
                    toast(text);
                }} catch (e) {{
                    toast("Request failed: " + e);
                }}
            }}
            async function streamLogs() {{
                try {{
                    const res = await fetch("/logs");
                    const reader = res.body.getReader();
                    const decoder = new TextDecoder();
                    while(true) {{
                        const {{done, value}} = await reader.read();
                        if(done) break;
                        const logs = document.getElementById("logs");
                        logs.textContent += decoder.decode(value);
                        logs.scrollTop = logs.scrollHeight;
                    }}
                }} catch (e) {{
                    // container likely not running yet
                }}
            }}
            streamLogs();
        </script>
    </body>
    </html>
    """

def quoted_env(envs):
    return envs

@app.post("/start")
def start_container(gh_pat: str = Form(""), aes_key: str = Form(""), auth_ok: bool = Depends(auth)):
    envs = load_env_cache()
    if gh_pat: envs["GH_PAT"] = gh_pat
    if aes_key: envs["AES_KEY"] = aes_key
    save_env_cache(envs)
    q_envs = quoted_env(envs)
    client.containers.run(
        IMAGE_NAME,
        name=CONTAINER_NAME,
        detach=True,
        ports={"7860/tcp": CONTAINER_PORT},
        environment=q_envs,
        volumes={
            "/buckets/tools": {"bind": "/app/tools", "mode": "rw"},
            "/buckets/shield": {"bind": "/app/shield", "mode": "rw"},
            "/buckets/shield-intel": {"bind": "/app/shield-intel", "mode": "rw"},
            "/buckets/tools": {"bind": "/tools", "mode": "rw"},
            "/buckets/shield": {"bind": "/shield", "mode": "rw"},
            "/buckets/shield-intel": {"bind": "/shield-intel", "mode": "rw"},
        },
        platform="linux/aarch64"
    )
    return {"status": "started"}

@app.post("/stop")
def stop_container(auth_ok: bool = Depends(auth)):
    try:
        c = client.containers.get(CONTAINER_NAME)
        c.stop()
        c.remove()
        return {"status": "stopped"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/restart")
def restart_container(auth_ok: bool = Depends(auth)):
    try:
        c = client.containers.get(CONTAINER_NAME)
        c.restart()
        return {"status": "restarted"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/factory-rebuild")
def factory_rebuild(auth_ok: bool = Depends(auth)):
    stop_container(auth_ok)
    envs = load_env_cache()
    return start_container(envs["GH_PAT"], envs["AES_KEY"], auth_ok)

@app.post("/repull")
def repull_image(auth_ok: bool = Depends(auth)):
    try:
        client.images.pull(IMAGE_NAME)
        return {"status": "image re-pulled"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/force-remove-conflicts")
def force_remove_conflicts(auth_ok: bool = Depends(auth)):
    """
    Force-remove (docker rm -f) any containers that either:
      - share CONTAINER_NAME, or
      - have a host port binding matching CONTAINER_PORT
    Useful when /start fails because a stale/conflicting container
    is holding the name or the port.
    """
    removed = []
    errors = []
    try:
        all_containers = client.containers.list(all=True)
    except Exception as e:
        return {"error": f"could not list containers: {e}"}

    for c in all_containers:
        try:
            name_match = c.name == CONTAINER_NAME
            port_match = False
            ports = c.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
            for _, bindings in ports.items():
                if not bindings:
                    continue
                for b in bindings:
                    if str(b.get("HostPort")) == str(CONTAINER_PORT):
                        port_match = True
                        break
                if port_match:
                    break

            if name_match or port_match:
                c.remove(force=True)
                removed.append(c.name)
        except Exception as e:
            errors.append(f"{c.name}: {e}")

    if errors:
        return {"status": "completed_with_errors", "removed": removed, "errors": errors}
    if not removed:
        return {"status": "no conflicts found"}
    return {"status": "removed", "containers": removed}

@app.get("/logs")
def stream_logs(auth_ok: bool = Depends(auth)):
    try:
        c = client.containers.get(CONTAINER_NAME)
        def log_stream():
            for line in c.logs(stream=True, follow=True):
                yield line
        return StreamingResponse(log_stream(), media_type="text/plain")
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7861, reload=True)
