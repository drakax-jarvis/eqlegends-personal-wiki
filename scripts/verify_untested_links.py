"""
Check all untested items against eqlegendstools.com and eqlwiki.com.
Mark truly broken items as unusable in the DB.
"""
import sqlite3, urllib.request, urllib.error, re, time

DB = '/home/hermes/eq-legends-wiki/eqlegends.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Get all items that have no verified link entry at all
untested = cur.execute("""
    SELECT DISTINCT i.name FROM combo_items ci
    JOIN items i ON ci.item_id = i.id
    WHERE i.name NOT IN (SELECT item_name FROM verified_links)
    ORDER BY i.name
""").fetchall()

print(f"Found {len(untested)} untested items")

def check_url(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=8)
        code = resp.getcode()
        resp.close()
        return code
    except urllib.error.HTTPError as e:
        return e.code
    except:
        return 0

# Check each untested item
broken = []
fixed = 0
for (name,) in untested:
    # Try eqlegendstools first (they have a more standard URL format)
    slug = name.lower().replace("'", "").replace(" ", "-").replace("--", "-").strip("-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    eqleg_url = f'https://eqlegendstools.com/items/{slug}/'
    
    eqleg_status = check_url(eqleg_url)
    
    if eqleg_status == 200:
        cur.execute("INSERT OR REPLACE INTO verified_links (item_name, source, url, status_code) VALUES (?, 'eqlegendstools', ?, 200)", (name, eqleg_url))
        fixed += 1
        continue
    
    # Try eqlwiki
    wiki_name = name.replace(' ', '_').replace("'", "%27")
    wiki_url = f'https://eqlwiki.com/{wiki_name}'
    wiki_status = check_url(wiki_url)
    
    if wiki_status == 200:
        cur.execute("INSERT OR REPLACE INTO verified_links (item_name, source, url, status_code) VALUES (?, 'eqlwiki', ?, 200)", (name, wiki_url))
        fixed += 1
        continue
    
    # Neither works - mark as broken
    if eqleg_status == 404:
        cur.execute("INSERT OR REPLACE INTO verified_links (item_name, source, url, status_code) VALUES (?, 'eqlegendstools', ?, 404)", (name, eqleg_url))
    if wiki_status == 404:
        cur.execute("INSERT OR REPLACE INTO verified_links (item_name, source, url, status_code) VALUES (?, 'eqlwiki', ?, 404)", (name, wiki_url))
    
    broken.append(name)
    print(f"  ❌ {name}")

conn.commit()

print(f"\n=== Results ===")
print(f"New working links found: {fixed}")
print(f"Truly broken items: {len(broken)}")

# Remove truly broken items from combo_items
if broken:
    print("\nRemoving broken items from BiS lists...")
    for name in broken:
        iid = cur.execute("SELECT id FROM items WHERE name=?", (name,)).fetchone()
        if iid:
            cur.execute("DELETE FROM combo_items WHERE item_id=?", (iid[0],))
            print(f"  Removed: {name}")
    conn.commit()

# Summary
print(f"\n=== DB Stats After Cleanup ===")
items_left = cur.execute("SELECT COUNT(DISTINCT item_id) FROM combo_items").fetchone()[0]
links = cur.execute("SELECT COUNT(*) FROM combo_items").fetchone()[0]
print(f"Unique items in BiS lists: {items_left}")
print(f"Total combo-item links: {links}")

conn.close()
