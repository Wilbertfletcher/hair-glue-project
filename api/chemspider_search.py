import requests
import time

BASE_URL = "https://api.rsc.org/compounds/v1"

def search_compound(name, api_key, order_by="default", order_direction="default"):
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json"
    }
    # Step 1: Submit filter query
    payload = {
        "name": name,
        "orderBy": order_by,
        "orderDirection": order_direction
    }
    response = requests.post(f"{BASE_URL}/filter/name", json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")

    query_id = response.json()["queryId"]

    # Step 2: Poll for status until complete
    for _ in range(30):
        status_resp = requests.get(f"{BASE_URL}/filter/{query_id}/status", headers=headers)
        if status_resp.status_code != 200:
            raise Exception(f"Status check error {status_resp.status_code}: {status_resp.text}")
        status_data = status_resp.json()
        if status_data.get("status") == "Complete":
            break
        time.sleep(1)
    else:
        raise TimeoutError(f"Query {query_id} did not complete within 30 seconds")

    # Step 3: Fetch results
    results_resp = requests.get(f"{BASE_URL}/filter/{query_id}/results", headers=headers)
    if results_resp.status_code != 200:
        raise Exception(f"Results error {results_resp.status_code}: {results_resp.text}")
    return results_resp.json()

# Example usage
if __name__ == "__main__":
    import os
    API_KEY = os.environ.get("CHEMSPIDER_API_KEY")
    if not API_KEY:
        raise SystemExit("Set CHEMSPIDER_API_KEY environment variable before running.")
    result = search_compound("aspirin", API_KEY)
    print(result)
