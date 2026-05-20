import requests

url = "http://192.111.111.42:3000/api/filtered"
payload = {
    "module": "import",
    "filterMode": "xcont_only",
    "pageSize": -1
}
headers = {'Content-Type': 'application/json'}

try:
    print(f"Fetching from {url}...")
    res = requests.post(url, json=payload, headers=headers, timeout=60)
    print(f"Status Code: {res.status_code}")
    data = res.json()
    print(f"Response keys: {data.keys()}")
    if 'data' in data:
        print(f"Number of items in 'data': {len(data['data'])}")
        missing_docs = set()
        for row in data.get("data", []):
            if row.get("cont_no"):
                missing_docs.add(row["cont_no"].strip())
            if row.get("xcont_no"):
                missing_docs.add(row["xcont_no"].strip())
        
        print(f"Extracted missing_docs count: {len(missing_docs)}")
        print("Sample extracted missing_docs:", list(missing_docs)[:5])
    else:
        print("No 'data' field in response.")
        
except Exception as e:
    print(f"Error: {e}")
