"""Full eqlwiki link verification."""
import re, urllib.request, urllib.error, sqlite3, time

DB = '/home/hermes/eq-legends-wiki/eqlegends.db'
HTML_FILES = [
    '/home/hermes/eq-legends-wiki/pages/dave-bis.html',
    '/home/hermes/eq-legends-wiki/pages/christy-bis.html',
    '/home/hermes/eq-legends-wiki/pages/brian-bis.html',
    '/home/hermes/eq-legends-wiki/pages/jessy-bis.html',
]

conn = sqlite3.connect(DB)
cur = conn.cursor()

all_links = {}
for html_file in HTML_FILES:
    with open(html_file) as f:
        content = f.read()
    for m in re.finditer(r'<a href="(https://eqlwiki\.com/[^"]+)"[^>]*><strong>([^<]+)</strong>', content):
        url, name = m.group(1), m.group(2)
        if name not in all_links:
            all_links[name] = url

print(f"Found {len(all_links)} unique eqlwiki links to verify")

tested = 0
broken = 0
for name, url in sorted(all_links.items()):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        status = resp.getcode()
        resp.close()
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:
        status = 0
    
    cur.execute("INSERT OR REPLACE INTO verified_links (item_name, source, url, status_code) VALUES (?, 'eqlwiki', ?, ?)", (name, url, status))
    tested += 1
    
    status_str = f"{status}" if status else "ERR"
    icon = "✅" if status == 200 else "⚠️"
    print(f"  {icon} {status_str:3} | {name}")
    
    if status != 200:
        broken += 1
    if tested % 5 == 0:
        time.sleep(0.3)

conn.commit()
print(f"\n=== Summary ===")
print(f"Tested: {tested}, Working: {tested-broken}, Broken: {broken}")

if broken > 0:
    print("\nBroken links that need fixing:")
    for name, url in sorted(all_links.items()):
        row = cur.execute("SELECT status_code FROM verified_links WHERE item_name=? AND source='eqlwiki' ORDER BY verified_at DESC", (name,)).fetchone()
        if row and row[0] != 200:
            print(f"  {name:40} -> {url}")

conn.close()
