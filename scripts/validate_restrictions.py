"""
Validate ALL items against eqlegendstools.com and eqlwiki.com for class restrictions.
Removes items from combos where the class restriction doesn't match.
"""
import sqlite3, re, urllib.request, urllib.error, time

DB = '/home/hermes/eq-legends-wiki/eqlegends.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

combo_classes = {
    "Dave": {"BRD","PAL","ENC"}, "Christy": {"CLR","NEC","WIZ"},
    "Brian": {"SHD","SHM","MNK"}, "Jessy": {"PAL","BRD","BER"},
    "David": {"PAL","SHM","NEC"},
}

# Get all unique items linked to combos
items = cur.execute("""
    SELECT DISTINCT i.id, i.name FROM combo_items ci
    JOIN items i ON i.id = ci.item_id
    ORDER BY i.name
""").fetchall()

print(f"Checking {len(items)} unique items against eqlegendstools.com for class restrictions...")

removed_count = 0
fixes = []

for item_id, item_name in items:
    slug = item_name.lower().replace("'", "").replace(" ", "-").replace("--", "-").strip("-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    url = f'https://eqlegendstools.com/items/{slug}/'
    
    class_str = None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=6)
        html = resp.read().decode()
        resp.close()
        
        m = re.search(r'Class:\s*([^<]+)', html)
        if m:
            class_str = m.group(1).strip()
    except urllib.error.HTTPError:
        pass  # 404 - not on eqlegendstools
    except:
        pass
    
    if class_str is None:
        continue  # Can't determine restriction
    
    # Parse restriction
    item_classes = set(re.findall(r'\b[A-Z]{3}\b', class_str))
    
    if 'ALL' in item_classes and class_str == 'ALL':
        continue  # Unrestricted
    
    is_all_except = 'ALL except' in class_str
    
    # Get all combos linked to this item
    linked_combos = cur.execute("""
        SELECT DISTINCT c.name FROM combo_items ci
        JOIN combos c ON c.id = ci.combo_id
        WHERE ci.item_id = ?
    """, (item_id,)).fetchall()
    
    for (combo_name,) in linked_combos:
        if is_all_except:
            # Can use if none of combo's classes are in the excluded list
            excluded = item_classes - {'ALL'}
            can_use = not bool(combo_classes[combo_name] & excluded)
        else:
            # Can use if any of combo's classes are in the item's class list
            can_use = bool(combo_classes[combo_name] & item_classes)
        
        if not can_use:
            cid = cur.execute("SELECT id FROM combos WHERE name=?", (combo_name,)).fetchone()[0]
            cur.execute("DELETE FROM combo_items WHERE combo_id=? AND item_id=?", (cid, item_id))
            removed_count += 1
            fixes.append((item_name, combo_name, class_str))
            if removed_count <= 15:
                print(f"  ❌ {item_name:40} | {combo_name:8} | requires: {class_str:30}")

conn.commit()

print(f"\n=== Summary ===")
print(f"Total items removed: {removed_count}")

# Final counts
print(f"\n=== Final item counts ===")
for c in ["Dave","Christy","Brian","Jessy","David"]:
    cid = cur.execute("SELECT id FROM combos WHERE name=?", (c,)).fetchone()[0]
    cnt = cur.execute("SELECT COUNT(*) FROM combo_items WHERE combo_id=?", (cid,)).fetchone()[0]
    print(f"  {c:8}: {cnt} items")

conn.close()
