import os
import json
import docker
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()
security = HTTPBasic()
client = docker.from_env()

CACHE_FILE = "/var/cache/inferenceport_env.json"
CONTAINER_NAME = "inferenceport-server"

def load_env_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {"GH_PAT": "", "AES_KEY": ""}

def save_env_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def auth(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.password != os.getenv("PSWRD-ADMIN"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@app.get("/", response_class=HTMLResponse)
def dashboard(auth_ok: bool = Depends(auth)):
    envs = load_env_cache()
    gh_pat = escape(envs["GH_PAT"], quote=True)
    aes_key = escape(envs["AES_KEY"], quote=True)
    return f"""
    <html>
    <head>
        <title>InferencePort Admin</title>
        <style>
            body {{ font-family: Arial; margin: 40px; }}
            input, button {{ margin: 5px; padding: 8px; }}
            #logs {{ width: 100%; height: 400px; border: 1px solid #ccc; overflow-y: scroll; background: #111; color: #0f0; }}
        </style>
    </head>
    <body>
        <h2>InferencePort Admin Dashboard</h2>
        <form id="envForm">
            <label>GH_PAT:</label><br>
            <input type="text" id="gh_pat" value="{envs['GH_PAT']}"><br>
            <label>AES_KEY:</label><br>
            <input type="text" id="aes_key" value="{envs['AES_KEY']}"><br>
        </form>
        <button onclick="action('start')">Start Container</button>
        <button onclick="action('stop')">Stop Container</button>
        <button onclick="action('restart')">Restart Container</button>
        <button onclick="action('factory-rebuild')">Factory Rebuild</button>
        <h3>Live Logs</h3>
        <pre id="logs"></pre>
        <script>
            async function action(endpoint) {{
                const gh_pat = document.getElementById('gh_pat').value;
                const aes_key = document.getElementById('aes_key').value;
                const formData = new FormData();
                formData.append("gh_pat", gh_pat);
                formData.append("aes_key", aes_key);
                const res = await fetch("/" + endpoint, {{ method: "POST", body: formData }});
                alert(await res.text());
            }}
            async function streamLogs() {{
                const res = await fetch("/logs");
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                while(true) {{
                    const {{done, value}} = await reader.read();
                    if(done) break;
                    document.getElementById("logs").textContent += decoder.decode(value);
                }}
            }}
            streamLogs();
        </script>
    </body>
    </html>
    """

@app.post("/start")
def start_container(gh_pat: str = Form(""), aes_key: str = Form(""), auth_ok: bool = Depends(auth)):
    envs = load_env_cache()
    if gh_pat: envs["GH_PAT"] = gh_pat
    if aes_key: envs["AES_KEY"] = aes_key
    save_env_cache(envs)
    client.containers.run(
        "ghcr.io/sharktide/inferenceport-server",
        name=CONTAINER_NAME,
        detach=True,
        ports={"7860/tcp": 7860},
        environment=envs,
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
