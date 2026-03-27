import requests

def search_compound(name, api_key, order_by="default", order_direction="default"):
    url = "https://api.rsc.org/compounds/v1/filter/name"
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "orderBy": order_by,
        "orderDirection": order_direction
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")

# Example usage
if __name__ == "__main__":
    import pdb; pdb.set_trace()
    API_KEY = "iGwpOmu4q12AzySgUFcDYaeXFsuUZFNb2ETBzXsy"
    result = search_compound("aspirin", API_KEY)
    for item in result.get("results", []):
        print(item)
