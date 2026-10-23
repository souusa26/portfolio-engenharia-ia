#!/usr/bin/env python3
"""
Servidor Visual CMS & Showcase de Engenharia com IA (Porta 8089)
Permite:
- Visualização limpa estilo Linear/Apple/Bento
- Edição visual de projetos, blocos, temas e textos (POST /api/save)
- Upload de imagens via Drag & Drop / Arquivo / Ctrl+V (POST /api/upload)
- Regeneração automática do README.md e sincronização com GitHub (POST /api/sync-github)
"""
import base64
import json
import os
import re
import subprocess
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_FILE = os.path.join(BASE_DIR, "projects_data.json")
PORT = int(os.getenv("PORT", "8089"))

os.makedirs(ASSETS_DIR, exist_ok=True)


def generate_markdown_from_data(data: dict) -> str:
    settings = data.get("settings", {})
    projects = data.get("projects", [])

    lines = [
        f"# {settings.get('title', 'Portfólio de Engenharia & Gestão com Agentes de IA')}",
        "",
        f"> **{settings.get('badge', 'Tiago Sousa (souusa26)')}**  ",
        f"> {settings.get('subtitle', '')}",
        "",
        "---",
        "",
        "## 📊 Indicadores do Ecossistema",
        "",
        "| Indicador | Destaque |",
        "| :--- | :--- |",
    ]
    for m in settings.get("metrics", []):
        lines.append(f"| **{m.get('label', '')}** | `{m.get('value', '')}` |")

    lines.extend([
        "",
        "---",
        "",
        "## 🗂️ Índice dos Projetos",
        "",
        "| # | Projeto | Categoria | Stack Principal | Status |",
        "| :-: | :--- | :--- | :--- | :--- |",
    ])

    for p in projects:
        num = p.get("number", "")
        title = p.get("title", "")
        cat = p.get("category", "")
        tags = ", ".join(p.get("tags", [])[:4])
        status = p.get("status", "")
        anchor = re.sub(r"[^a-z0-9\-]", "", f"{num}-{title.lower().replace(' ', '-')}")
        lines.append(f"| **{num}** | **{title}** | {cat} | `{tags}` | {status} |")

    lines.extend(["", "---", ""])

    for p in projects:
        num = p.get("number", "")
        title = p.get("title", "")
        subtitle = p.get("subtitle", "")
        cat = p.get("category", "")
        status = p.get("status", "")
        path = p.get("path", "")
        tags = p.get("tags", [])
        images = p.get("images", [])
        blocks = p.get("blocks", [])

        lines.append(f"## {num}. {title}")
        lines.append("")
        if subtitle:
            lines.append(f"**Resumo:** {subtitle}")
            lines.append("")
        lines.append(f"- **Categoria:** `{cat}`")
        lines.append(f"- **Status:** `{status}`")
        if path:
            lines.append(f"- **Caminho no Servidor:** `{path}`")
        if tags:
            lines.append(f"- **Tecnologias:** {' • '.join(f'`{t}`' for t in tags)}")
        lines.append("")

        if images:
            lines.append("### 📸 Galeria & Evidências Visuais")
            lines.append("")
            for img in images:
                url = img.get("url", "")
                cap = img.get("caption", title)
                if url:
                    lines.append(f"#### {cap}")
                    lines.append(f"![{cap}]({url})")
                    lines.append("")

        for b in blocks:
            b_title = b.get("title", "")
            b_content = b.get("content", "")
            if b_title:
                lines.append(f"### {b_title}")
                lines.append("")
            if b_content:
                lines.append(b_content)
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def save_data_and_markdown(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    md_content = generate_markdown_from_data(data)
    with open(os.path.join(BASE_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(os.path.join(BASE_DIR, "DOSSIE_ENGENHARIA_IA_CEO.md"), "w", encoding="utf-8") as f:
        f.write(md_content)


def get_live_telemetry():
    containers_count = 26
    try:
        out = subprocess.check_output(
            ["docker", "ps", "-q"], stderr=subprocess.DEVNULL, timeout=2
        ).decode("utf-8").strip()
        if out:
            containers_count = len(out.splitlines())
    except Exception:
        pass

    ram_str = "16 GB"
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            mem = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    mem[parts[0].strip()] = int(parts[1].strip().split()[0])
            total_gb = mem.get("MemTotal", 0) / (1024 * 1024)
            avail_gb = mem.get("MemAvailable", 0) / (1024 * 1024)
            used_gb = total_gb - avail_gb
            ram_str = f"{used_gb:.1f}GB / {total_gb:.1f}GB"
    except Exception:
        pass

    return {
        "status": "online",
        "containers_running": containers_count,
        "ram_usage": ram_str,
    }


class PortfolioCMSHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def _send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/data"):
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json(200, data)
            else:
                self._send_json(404, {"error": "projects_data.json not found"})
            return

        if self.path.startswith("/api/telemetry"):
            self._send_json(200, get_live_telemetry())
            return

        if self.path.startswith("/api/dossier"):
            dossier_path = os.path.join(BASE_DIR, "README.md")
            if os.path.exists(dossier_path):
                with open(dossier_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header(
                    "Content-Disposition",
                    'inline; filename="README.md"',
                )
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        return super().do_GET()

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_len) if content_len > 0 else b"{}"

        if self.path == "/api/save":
            try:
                data = json.loads(raw_body.decode("utf-8"))
                save_data_and_markdown(data)
                self._send_json(200, {"ok": True, "message": "Alterações salvas e README.md atualizado!"})
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if self.path == "/api/upload":
            try:
                payload = json.loads(raw_body.decode("utf-8"))
                filename = payload.get("filename", f"upload-{int(time.time())}.png")
                data_url = payload.get("data_url", "")
                if "," in data_url:
                    _, b64_data = data_url.split(",", 1)
                else:
                    b64_data = data_url

                safe_name = re.sub(r"[^a-zA-Z0-9._-]", "-", filename)
                safe_name = f"{int(time.time())}-{safe_name}"
                dest_path = os.path.join(ASSETS_DIR, safe_name)

                with open(dest_path, "wb") as f:
                    f.write(base64.b64decode(b64_data))

                self._send_json(200, {"ok": True, "url": f"assets/{safe_name}"})
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if self.path == "/api/sync-github":
            try:
                if os.path.exists(DATA_FILE):
                    with open(DATA_FILE, "r", encoding="utf-8") as f:
                        save_data_and_markdown(json.load(f))
                subprocess.run(["git", "add", "."], cwd=BASE_DIR, check=False)
                subprocess.run(
                    ["git", "commit", "-m", "docs: atualiza portfólio e imagens pelo Visual Studio"],
                    cwd=BASE_DIR,
                    check=False,
                )
                push_res = subprocess.run(
                    ["git", "push", "origin", "main"],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                )
                if push_res.returncode == 0:
                    self._send_json(200, {"ok": True, "message": "Sincronizado com o GitHub com sucesso!"})
                else:
                    self._send_json(200, {"ok": True, "message": "Salvo localmente e README atualizado!"})
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        self._send_json(404, {"ok": False, "error": "Rota não encontrada"})

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                save_data_and_markdown(json.load(f))
        except Exception:
            pass
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("0.0.0.0", PORT), PortfolioCMSHandler)
    print(f"Portfolio Visual CMS rodando em http://0.0.0.0:{PORT}")
    server.serve_forever()
