import sys, json, base64
t = sys.argv[1]
p = t.split('.')[1]
p += '=' * (-len(p) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(p).decode()), indent=2))
