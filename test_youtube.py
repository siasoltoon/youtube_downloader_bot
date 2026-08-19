import requests

url = "https://www.youtube.com/watch?v=nXmPH-so3VY"

try:
    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    print("HTTP Status:", response.status_code)
    print("Response length:", len(response.text))
    print("YouTube reachable:", "YouTube" in response.text)

except Exception as e:
    print("ERROR:", repr(e))
