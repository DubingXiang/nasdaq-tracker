import requests
import subprocess
import sys

# Get credentials from git credential manager
result = subprocess.run(
    ['git', 'credential', 'fill'],
    input='protocol=https\nhost=github.com\n',
    capture_output=True, text=True
)
creds = {}
for line in result.stdout.strip().split('\n'):
    if '=' in line:
        k, v = line.split('=', 1)
        creds[k] = v

username = creds.get('username')
token = creds.get('password')

if not token:
    print("ERROR: No GitHub token found")
    sys.exit(1)

headers = {
    'Authorization': f'token {token}',
    'Accept': 'application/vnd.github.v3+json',
}

# Create repo
resp = requests.post(
    'https://api.github.com/user/repos',
    json={'name': 'nasdaq-tracker', 'private': False, 'description': 'nasdaq valuation tracker'},
    headers=headers,
    timeout=15,
)
print(f'Create repo: {resp.status_code}')

# Get actual username from API
user_resp = requests.get('https://api.github.com/user', headers=headers, timeout=10)
actual_username = user_resp.json().get('login', username)
print(f'GitHub username: {actual_username}')

if resp.status_code == 201:
    print(f'Repo created: {resp.json()["html_url"]}')
elif resp.status_code == 422:
    print('Repo already exists, continuing...')
else:
    print(f'Error: {resp.text[:300]}')

# Push via git (set remote URL with token, using actual username)
remote_url = f'https://{actual_username}:{token}@github.com/{actual_username}/nasdaq-tracker.git'
subprocess.run(['git', '-C', 'd:/AI/outputs/nasdaq-tracker', 'remote', 'set-url', 'origin', remote_url], check=True)
result = subprocess.run(
    ['git', '-C', 'd:/AI/outputs/nasdaq-tracker', 'push', '-u', 'origin', 'master'],
    capture_output=True, text=True, timeout=60,
)
print(f'Push stdout: {result.stdout}')
print(f'Push stderr: {result.stderr}')
print(f'Push returncode: {result.returncode}')
