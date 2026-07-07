"""
Verify all BiS item links and store results in the database.
- eqlegendstools.com = items with extractable effects (focus, proc, clicky, worn)
- eqlwiki.com = stat-only items

Run: python3 scripts/verify_links.py
"""
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

# Create a table for verified links if not exists
cur.execute("""
CREATE TABLE IF NOT EXISTS verified_links (
    item_name TEXT,
    source TEXT,          -- 'eqlegendstools' or 'eqlwiki'
    url TEXT,
    status_code INTEGER,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (item_name, source)
)
""")

# Extract all unique item links from all HTML files
all_links = {}
for html_file in HTML_FILES:
    with open(html_file) as f:
        content = f.read()
    
    # Find all item links (both eqlegendstools and eqlwiki)
    for m in re.finditer(r'<a href="(https://(?:eqlegendstools\.com/items/|eqlwiki\.com/)[^"]+)"[^>]*><strong>([^<]+)</strong>', content):
        url = m.group(1)
        name = m.group(2)
        source = 'eqlegendstools' if 'eqlegendstools' in url else 'eqlwiki'
        
        if name not in all_links:
            all_links[name] = {'eqlegendstools': None, 'eqlwiki': None}
        
        if source == 'eqlegendstools':
            all_links[name]['eqlegendstools'] = url
        else:
            all_links[name]['eqlwiki'] = url

print(f"Found {len(all_links)} unique items with links")

# Check each link
tested = 0
for name, sources in sorted(all_links.items()):
    for source_type, url in sources.items():
        if url is None:
            continue
        
        # Check if already verified recently
        existing = cur.execute("SELECT status_code FROM verified_links WHERE item_name=? AND source=?", (name, source_type)).fetchone()
        if existing and existing[0] == 200:
            continue  # Already verified as working
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=8)
            status = resp.getcode()
            resp.close()
        except urllib.error.HTTPError as e:
            status = e.code
        except Exception as e:
            status = 0  # Network error
        
        cur.execute("""
            INSERT OR REPLACE INTO verified_links (item_name, source, url, status_code)
            VALUES (?, ?, ?, ?)
        """, (name, source_type, url, status))
        
        tested += 1
        
        if status != 200:
            print(f"  {status:3} | [{source_type:15}] {name[:40]:40} {url[:60]}")
        
        if tested % 10 == 0:
            time.sleep(0.3)

conn.commit()

# Summary
print(f"\n=== Verification Summary ===")
for name, sources in sorted(all_links.items()):
    for stype in ['eqlegendstools', 'eqlwiki']:
        if sources[stype]:
            row = cur.execute("SELECT status_code FROM verified_links WHERE item_name=? AND source=?", (name, stype)).fetchone()
            status = row[0] if row else '?'
            icon = '✅' if status == 200 else '⚠️' if status == 404 else '❌'
            print(f"  {icon} [{stype:15}] {status:3} | {name[:45]}")

conn.close()
