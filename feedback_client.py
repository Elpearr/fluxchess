import json
import threading
import urllib.request


def request_feedback(prompt, model="llama3.2:3b", url="http://localhost:11434/api/generate", max_tokens=40, temperature=0.15, cb=None):
    """
    Fire-and-forget call to a local Ollama server. Returns via callback when done.
    """
    def _worker():
        text = "No feedback available."
        try:
            body = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            }).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                out = json.load(resp)
                text = out.get("response", "").strip() or text
        except Exception as e:
            print(f"[COACH-ERR] feedback request failed: {e}")

        if cb:
            cb(text)

    threading.Thread(target=_worker, daemon=True).start()
