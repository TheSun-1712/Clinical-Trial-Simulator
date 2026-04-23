from __future__ import annotations

import requests

BASE_URL = "http://127.0.0.1:8000"


if __name__ == "__main__":
    metadata = requests.get(f"{BASE_URL}/openenv/metadata", timeout=10).json()
    print("metadata:", metadata)

    reset = requests.post(f"{BASE_URL}/openenv/reset", json={"seed": 7}, timeout=10).json()
    print("reset:", reset)

    session_id = reset["session_id"]
    step = requests.post(
        f"{BASE_URL}/openenv/step",
        json={"session_id": session_id, "action_type": "recruit", "magnitude": 2.0},
        timeout=10,
    ).json()
    print("step:", step)
