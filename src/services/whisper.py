import sys
import json

def main():
    data = sys.stdin.read()
    try:
        payload = json.loads(data) if data else {}
    except Exception:
        payload = {}
    audio_url = payload.get("audio_url") or ""
    result = {
        "text": "",
        "duration_seconds": 0,
        "status": "not_implemented",
        "audio_url": audio_url
    }
    print(json.dumps(result))

if __name__ == "__main__":
    main()

