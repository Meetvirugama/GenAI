import requests
session = requests.Session()
res = session.get("http://localhost:7860/login/google", allow_redirects=False)
print("Login redirect status:", res.status_code)
print("Cookies after login:", session.cookies.get_dict())
location = res.headers.get("Location")
print("Redirect location:", location)
from urllib.parse import urlparse, parse_qs
parsed = urlparse(location)
qs = parse_qs(parsed.query)
state = qs.get("state", [""])[0]
print("State from URL:", state)
# Now pretend we got redirected back
auth_url = f"http://localhost:7860/auth?state={state}&code=testcode"
res2 = session.get(auth_url, allow_redirects=False)
print("Auth redirect status:", res2.status_code)
print("Auth response body:", res2.text)
