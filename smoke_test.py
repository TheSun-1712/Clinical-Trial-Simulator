import requests
import json

try:
    res = requests.get("http://localhost:8000/simulation/disease-profiles")
    print("Profiles:", json.dumps(res.json(), indent=2))
    
    reset = requests.post("http://localhost:8000/openenv/reset", json={})
    print("Reset:", json.dumps(reset.json(), indent=2))
    
    step = requests.post("http://localhost:8000/openenv/step", json={
        "session_id": reset.json()["session_id"],
        "action_type": "recruit",
        "magnitude": 5.0
    })
    print("Step:", json.dumps(step.json()["observation"], indent=2))
except Exception as e:
    print("Test failed:", e)
