"""Generate per-combo BiS pages — v5 with inline exaltations + master reference table."""
import sqlite3, os, json, re

DB = '/home/hermes/eq-legends-wiki/eqlegends.db'
OUT_DIR = '/home/hermes/eq-legends-wiki/pages/'

def link(name, zone=""):
    """Generate the correct link for an item with max level view."""
    conn = sqlite3.connect(DB)
    row = conn.execute("SELECT url FROM verified_links WHERE item_name=? AND source='eqlegendstools' AND status_code=200", (name,)).fetchone()
    if row:
        conn.close(); return row[0].rstrip('/') + '/?level=10'
    
    row = conn.execute("SELECT url FROM verified_links WHERE item_name=? AND source='eqlwiki' AND status_code=200", (name,)).fetchone()
    if row:
        conn.close(); return row[0] + '?level=10'
    
    conn.close()
    # Fallback to zone page
    if zone and zone not in ("Vendor", "Unknown"):
        z = zone.replace(' ', '_')
        return f'https://eqlwiki.com/{z}'
    return None

def eq(name):
    n = name.replace(' ', '_').replace("'", "%27")
    return f'https://eqlwiki.com/{n}'

def q(query, params=()):
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row
    rows = conn.execute(query, params).fetchall(); conn.close()
    return rows

SLOT_LABELS = {'HEAD':'Head','FACE':'Face','EAR':'Ear','NECK':'Neck','SHOULDERS':'Shoulders','BACK':'Back','CHEST':'Chest','ARMS':'Arms','WRIST':'Wrist','HANDS':'Hands','FINGER':'Fingers','WAIST':'Waist','LEGS':'Legs','FEET':'Feet','PRIMARY':'Primary','SECONDARY':'Secondary','RANGE':'Range','AMMO':'Ammo','ANY':'Any','PRIMARY ANY':'Any','PRIMARY SECONDARY':'Off-Hand'}
def slot_rank(s):
    s = s.upper()
    if 'ANY' in s: return 20
    if 'RANGE' in s: return 17
    if 'AMMO' in s: return 18
    for i,k in enumerate(['HEAD','FACE','EAR','NECK','SHOULDERS','BACK','CHEST','ARMS','WRIST','HANDS','FINGER','WAIST','LEGS','FEET','PRIMARY','SECONDARY']):
        if k in s: return i
    return 99

COMBO_CONFIG = {
    "Dave":{"p":"charisma","s":"wisdom"}, "Christy":{"p":"wisdom","s":"intelligence"},
    "Brian":{"p":"strength","s":"stamina"}, "Jessy":{"p":"strength","s":"wisdom"},
    "David":{"p":"strength","s":"wisdom"},
}
HASTE = {"Mithril Two-Handed Sword":31,"Flowing Black Silk Sash (FBSS)":21,"Flowing Black Silk Sash":21,"Kitchen Toolbelt":10,"Sporali Gloves":9}

# Exaltation data with proper slot restrictions
# Each entry: (display_name, source_item, zone, npc, class_req, min_level, exalt_type, valid_slots)
X = {}
X["Dave"] = [
    ("Lifetap Proc (Siphon)", "Tentacle Whip", "Najena", "Gelid Spider", "WAR/PAL/SHD/SHM", 30, "Proc (+4)", ["PRIMARY","SECONDARY","PRIMARY SECONDARY","ANY"]),
    ("Alliance (click)", "Rod of Insidious Glamour", "Temple Solusek Ro", "Quest", "ENC", 30, "Click (+2)", ["ANY","PRIMARY","RANGE"]),
    ("Improved Damage I", "Robe of the Oracle", "Plane of Hate", "K'Dal Dancer", "ALL", 25, "Focus (+1)", ["CHEST","ARMS","SHOULDERS","ANY","LEGS","BACK"]),
    ("Spell Haste III", "Shining Metallic Robes", "Mistmoore", "Glyphed Ghoul", "ALL", 35, "Focus (+1)", ["CHEST","ARMS","SHOULDERS","ANY","LEGS","BACK"]),
    ("Improved Healing I", "Turtleshell Helm", "Lower Guk", "Frogloks", "CLR/PAL/DRU/SHM", 25, "Focus (+1)", ["CHEST","SHOULDERS","ARMS","ANY","LEGS","BACK"]),
]
X["Christy"] = [
    ("Improved Healing III", "Idol of the Underking", "Plane of Hate", "Various", "CLR/PAL/DRU/SHM", 50, "Focus (+1)", ["CHEST","SHOULDERS","ARMS","ANY","LEGS","BACK"]),
    ("Improved Damage I", "Robe of the Oracle", "Plane of Hate", "K'Dal Dancer", "ALL", 25, "Focus (+1)", ["CHEST","ARMS","SHOULDERS","ANY","LEGS","BACK"]),
    ("Burning Affliction III", "Spirit Wracked Cords", "Kedge Keep", "Seahorse Matriarch", "NEC/MAG", 50, "Focus (+1)", ["CHEST","ARMS","SHOULDERS","ANY","LEGS","BACK"]),
    ("Affliction Efficiency III", "Polished Bone Bracelet", "Lower Guk", "Froglok Yun", "NEC/SHM", 50, "Focus (+1)", ["CHEST","ARMS","SHOULDERS","ANY","LEGS","BACK"]),
    ("Shock of Fire (DD proc)", "Rod of Crystals", "Solusek A", "Goblin High Shaman", "WIZ", 20, "Proc (+4)", ["PRIMARY","SECONDARY","PRIMARY SECONDARY","ANY"]),
    ("Conflagration (click)", "Staff of Temperate Flux", "Temple Solusek Ro", "Quest", "WIZ", 20, "Click (+2)", ["ANY","PRIMARY","RANGE"]),
    ("Sicken (Disease DoT proc)", "Rotting Scimitar", "Plane of Fear", "Dracoliche", "NEC/SHD", 46, "Proc (+4)", ["PRIMARY","SECONDARY","PRIMARY SECONDARY","ANY"]),
]
X["Brian"] = [
    ("Affliction Efficiency III", "Polished Bone Bracelet", "Lower Guk", "Froglok Yun", "NEC/SHM", 50, "Focus (+1)", ["CHEST","ARMS","SHOULDERS","ANY","LEGS","BACK"]),
    ("Spell Haste III", "Shining Metallic Robes", "Mistmoore", "Glyphed Ghoul", "ALL", 35, "Focus (+1)", ["CHEST","ARMS","SHOULDERS","ANY","LEGS","BACK"]),
    ("Improved Damage I", "Robe of the Oracle", "Plane of Hate", "K'Dal Dancer", "ALL", 25, "Focus (+1)", ["CHEST","ARMS","SHOULDERS","ANY","LEGS","BACK"]),
    ("Lifetap (Siphon 50)", "Soul Leech Blade", "Plane of Hate", "Various", "SHD", 45, "Proc (+4)", ["PRIMARY","SECONDARY","PRIMARY SECONDARY","ANY"]),
    ("Laceration (proc)", "Sharp Claws", "Various", "Various", "MNK", 10, "Proc (+4)", ["PRIMARY","SECONDARY","PRIMARY SECONDARY","ANY"]),
    ("Feign Death (click)", "Shroud of the Simulacrum", "Various", "Quest", "SHM", 30, "Click (+2)", ["ANY","PRIMARY","RANGE"]),
]
X["Jessy"] = [
    ("Improved Healing I", "Turtleshell Helm", "Lower Guk", "Frogloks", "CLR/PAL/DRU/SHM", 25, "Focus (+1)", ["CHEST","SHOULDERS","ARMS","ANY","LEGS","BACK"]),
    ("Spell Haste III", "Shining Metallic Robes", "Mistmoore", "Glyphed Ghoul", "ALL", 35, "Focus (+1)", ["CHEST","ARMS","SHOULDERS","ANY","LEGS","BACK"]),
    ("Lifetap Proc (Siphon)", "Tentacle Whip", "Najena", "Gelid Spider", "WAR/PAL/SHD/SHM", 30, "Proc (+4)", ["PRIMARY","SECONDARY","PRIMARY SECONDARY","ANY"]),
    ("Alliance (click)", "Rod of Insidious Glamour", "Temple Solusek Ro", "Quest", "ENC", 30, "Click (+2)", ["ANY","PRIMARY","RANGE"]),
]

def calc_score(item_row, combo_name, tier):
    level = int(tier.split('-')[0])
    lw = 3 if level <= 20 else 2 if level <= 40 else 1
    cfg = COMBO_CONFIG[combo_name]
    ac = item_row['ac'] or 0
    primary = item_row[cfg['p']] or 0
    secondary = item_row[cfg['s']] or 0
    hp = item_row['hp'] or 0; mana = item_row['mana'] or 0
    score = (ac*lw) + (primary*2) + (hp//10) + (mana//10) + secondary
    if combo_name in ["Dave","Brian","Jessy","David"]:
        score += HASTE.get(item_row['name'], 0)
    if item_row['on_path']: score += 5
    # Vendor penalty
    try:
        zone = item_row['zone']
        if zone == 'Vendor' or zone == 'Unknown':
            score -= 20
    except (KeyError, IndexError):
        pass
    
    return score

def stat_str(r, combo_name):
    parts = []
    if r['ac']: parts.append(f'AC {r["ac"]}')
    if r['dmg'] and r['delay']: parts.append(f'{r["dmg"]}/{r["delay"]}')
    for l,f in [('STR','strength'),('STA','stamina'),('AGI','agility'),('DEX','dexterity'),('WIS','wisdom'),('INT','intelligence'),('CHA','charisma')]:
        if r[f]: parts.append(f'{l}+{r[f]}')
    if r['hp']: parts.append(f'HP+{r["hp"]}')
    if r['mana']: parts.append(f'Mana+{r["mana"]}')
    if combo_name in ["Dave","Brian","Jessy","David"]:
        h = HASTE.get(r['name'],0)
        if h: parts.append(f'{h}% Haste')
    rs = []
    for l,f in [('FR','sv_fire'),('CR','sv_cold'),('MR','sv_magic'),('DR','sv_disease'),('PR','sv_poison')]:
        if r[f]: rs.append(f'{l}+{r[f]}')
    if rs: parts.append('('+','.join(rs)+')')
    return ', '.join(parts) if parts else '—'

def build_slot_section(combo_name, tier):
    rows = q("""SELECT i.*, d.zone, d.npc, d.on_path, d.path_order FROM combo_items ci JOIN items i ON ci.item_id=i.id JOIN drops d ON d.item_id=i.id WHERE ci.combo_id=(SELECT id FROM combos WHERE name=?) AND ci.tier=? ORDER BY d.path_order""", (combo_name, tier))
    if not rows: return ''
    
    slots = {}
    for r in rows:
        s = r['slot']; score = calc_score(r, combo_name, tier)
        if s not in slots: slots[s] = []
        slots[s].append((score, r))
    
    # Build per-slot exaltation map
    x_data = X.get(combo_name, [])
    tier_x_map = {}  # slot_upper -> list of (exalt_idx, alt1, alt2)
    tier_level = int(tier.split('-')[0])
    for xi, entry in enumerate(x_data):
        name_val, src_val, zone_val, npc_val, cls_val, lvl_val, etype_val, slots_val = entry
        if tier_level < lvl_val: continue  # Not yet attainable
        for vs in slots_val:
            if vs not in tier_x_map: tier_x_map[vs] = []
            # Find alternatives (same exalt type, different source)
            alts = []
            for j, e2 in enumerate(x_data):
                if j == xi or tier_level < e2[5]: continue
                if e2[6] == etype_val:  # Same exalt type
                    alts.append(j)
            tier_x_map[vs].append((xi, alts[0] if len(alts) > 0 else -1, alts[1] if len(alts) > 1 else -1))
    
    used_xi = set()  # Track which exaltations have been assigned
    html = ''
    for slot_key in sorted(slots.keys(), key=lambda s: slot_rank(s)):
        items = slots[slot_key]
        items.sort(key=lambda x: -x[0])
        su = slot_key.upper()
        is_double = su in ('EAR','FINGER','WRIST','ANY') or 'ANY' in su
        if su in ('PRIMARY SECONDARY','SECONDARY'): is_double = False
        count = min(2, len(items)) if is_double else 1
        
        for idx in range(count):
            score, item = items[idx]
            sl = SLOT_LABELS.get(su, slot_key.replace('_',' ').title())
            if is_double and count > 1: sl = f'{sl} {idx+1}'
            on_path = item['on_path']
            pl = '<span class="conf-eql">ON PATH</span>' if on_path else '<span class="conf-beta">off-path</span>'
            lk = link(item['name'], item['zone'])
            if lk:
                dp = f'<a href="{lk}" target="_blank"><strong>{item["name"]}</strong></a>'
            else:
                dp = f'<strong>{item["name"]}</strong>'
            st = stat_str(item, combo_name)
            
            # Build tooltip showing stats at max level (+10) - only max values
            tip_parts = []
            if item['ac']:
                ac_max = int(item['ac'] * 2.0)
                tip_parts.append(f'AC {ac_max}')
            if item['dmg'] and item['delay']:
                dmg_max = int(item['dmg'] * 2.0)
                ratio = dmg_max / item['delay']
                tip_parts.append(f'{dmg_max}/{item["delay"]} ({ratio:.2f})')
            for label, field in [('STR','strength'),('STA','stamina'),('AGI','agility'),('DEX','dexterity'),('WIS','wisdom'),('INT','intelligence'),('CHA','charisma')]:
                v = item[field] or 0
                if v:
                    mv = int(v * 2.0)
                    tip_parts.append(f'{label}+{mv}')
            if item['hp']:
                hp_max = int(item['hp'] * 2.0)
                tip_parts.append(f'HP{hp_max}')
            if item['mana']:
                mn_max = int(item['mana'] * 2.0)
                tip_parts.append(f'Mana{mn_max}')
            if combo_name in ["Dave","Brian","Jessy","David"]:
                h = HASTE.get(item['name'], 0)
                if h:
                    hm = h + 10
                    tip_parts.append(f'Haste {hm}%')
            
            tip_text = ' | '.join(tip_parts)
            st_display = f'<span class="stat" title="{tip_text}">{st}</span>'
            
            zo = item['zone']
            
            # Find matching exaltation for this slot
            x_html = ''
            # Only match exact slot - no ANY fallback for non-ANY slots
            if su in tier_x_map:
                for xi_val, alt1, alt2 in tier_x_map[su]:
                    if xi_val in used_xi: continue
                    used_xi.add(xi_val)
                    ent = x_data[xi_val]
                    src_link = link(ent[1])
                    if src_link:
                        x_html = f'<div class="exalt-inline">→ Socket <strong>{ent[6]}: {ent[0]}</strong> from <a href="{src_link}">{ent[1]}</a> ({ent[2]})'
                    else:
                        x_html = f'<div class="exalt-inline">→ Socket <strong>{ent[6]}: {ent[0]}</strong> from {ent[1]} ({ent[2]})'
                    if alt1 >= 0:
                        a1_name = x_data[alt1][0]
                        a1_src = x_data[alt1][1]
                        a1_link = link(a1_src)
                        if a1_link:
                            x_html += f' | Alt: <a href="{a1_link}">{a1_name}</a>'
                        else:
                            x_html += f' | Alt: {a1_name}'
                    if alt2 >= 0:
                        a2_name = x_data[alt2][0]
                        a2_src = x_data[alt2][1]
                        a2_link = link(a2_src)
                        if a2_link:
                            x_html += f', <a href="{a2_link}">{a2_name}</a>'
                        else:
                            x_html += f', {a2_name}'
                    x_html += '</div>'
                    break
            
            alts = []
            for ascore, alt in items[count:]:
                alts.append(f'<a href="{link(alt["name"])}">{alt["name"]}</a>')
            at = f' <span class="alt">(alt: {", ".join(alts[:2])})</span>' if alts else ''
            
            html += f'<div class="bis-slot"><span class="slot-label">{sl}</span> {dp} {st_display} <span class="zone">{zo}</span> {pl}{at}{x_html}</div>\n'
    return html

def build_master_table(combo_name):
    data = X.get(combo_name, [])
    if not data: return ''
    rows = []
    for name, src, zone, npc, cls, lvl, etype, valid_slots in data:
        src_link_res = link(src)
        src_display = f'<a href="{src_link_res}" target="_blank">{src}</a>' if src_link_res else src
        zone_link = eq(zone)
        zone_display = f'<a href="{zone_link}" target="_blank">{zone}</a>' if 'Unknown' not in zone else zone
        slot_str = ', '.join([s.replace('PRIMARY SECONDARY','Weapons').replace('_',' ').title() for s in valid_slots])
        rows.append(f'<tr><td><strong>{name}</strong></td><td>{etype}</td><td>{src_display}</td><td>{zone_display}</td><td>{npc}</td><td>{cls}</td><td>L{lvl}+</td><td>{slot_str}</td></tr>')
    return f'''<h2>Exaltation Source Reference</h2>
<p>All exaltations recommended for {combo_name}, where to get them, and their requirements.</p>
<table><tr><th>Effect</th><th>Type</th><th>Source Item</th><th>Zone</th><th>NPC</th><th>Classes</th><th>Min Level</th><th>Valid Slots</th></tr>
{''.join(rows)}</table>'''

def generate():
    combos = q("SELECT * FROM combos")
    tier_config = [("1-10","Levels 1–10 — Starter Gear"),("11-20","Levels 11–20 — Befallen"),("21-30","Levels 21–30 — Najena"),("31-40","Levels 31–40 — Lower Guk"),("41-45","Levels 41–45 — Nagafen's Lair"),("46-48","Levels 46–48 — Plane of Hate"),("48-50","Levels 48–50 — Plane of Fear")]
    
    SIDEBAR = '''<nav class="sidebar">
    <div class="sidebar-header"><h1>EQ Legends</h1><span class="subtitle">Class Combo Wiki</span></div>
    <div class="sidebar-nav">
        <div class="nav-section"><h3>Getting Started</h3><ul>
            <li><a href="../index.html">Home</a></li><li><a href="game-overview.html">Game Overview</a></li><li><a href="multiclassing.html">Multiclassing Guide</a></li><li><a href="leveling.html">Leveling 1-50</a></li><li><a href="ritual-guide.html">Ritual Travel</a></li><li><a href="race-unlock.html">Race Unlock</a></li><li><a href="quests.html">Quests</a></li><li><a href="clickies.html">Clickies</a></li><li><a href="exaltations.html">Exaltations</a></li><li><a href="patch-notes.html">Patch Notes</a></li>
        </ul></div>
        <div class="nav-section"><h3>Dave's Combo</h3><ul>
            <li><a href="bard.html">Bard</a></li><li><a href="paladin.html">Paladin</a></li><li><a href="enchanter.html">Enchanter</a></li><li><a href="dave-combo.html">Bard/Pal/Enc Guide</a></li><li><a href="dave-bis.html">Dave's BiS</a></li>
        </ul></div>
        <div class="nav-section"><h3>Christy's Combo</h3><ul>
            <li><a href="cleric.html">Cleric</a></li><li><a href="necromancer.html">Necromancer</a></li><li><a href="wizard.html">Wizard</a></li><li><a href="christy-combo.html">Christy's Guide</a></li><li><a href="christy-bis.html">Christy's BiS</a></li>
        </ul></div>
        <div class="nav-section"><h3>Brian's Combo</h3><ul>
            <li><a href="shaman-sk-monk.html">SK/Shaman/Monk Guide</a></li><li><a href="shadow-knight.html">Shadow Knight</a></li><li><a href="shaman.html">Shaman</a></li><li><a href="monk.html">Monk</a></li><li><a href="brian-bis.html">Brian's BiS</a></li>
        </ul></div>
        <div class="nav-section"><h3>Jessy's Combo</h3><ul>
            <li><a href="paladin-bard-berserker.html">Pal/Bard/Berserker Guide</a></li><li><a href="paladin.html">Paladin</a></li><li><a href="bard.html">Bard</a></li><li><a href="berserker.html">Berserker</a></li><li><a href="jessy-bis.html">Jessy's BiS</a></li>
        </ul></div>
    </div>
    <div class="sidebar-footer"><p>Live Launch: July 28, 2026 | Class Combo Wiki</p></div>
</nav>'''
    
    for combo in combos:
        name = combo['name']
        stat_prio = ', '.join(json.loads(combo["stat_priority"]))
        classes = f'{combo["primary_class"]} / {combo["class2"]} / {combo["class3"]}'
        
        sections = ''
        for tier_key, tier_label in tier_config:
            content = build_slot_section(name, tier_key)
            if content:
                sections += f'<h2>{tier_label}</h2>\n<div class="bis-grid">\n{content}</div>\n'
        
        master = build_master_table(name)
        
        if name in ["Dave","Brian","Jessy","David"]:
            mn = '<p class="page-subtitle"><strong>Dual Wield:</strong> PRIMARY + SECONDARY 1H weapons. <strong>ANY 1:</strong> Mithril 2H Sword (31% haste). <strong>ANY 2:</strong> Shield (AC + exaltations). Never use a 2H weapon in PRIMARY.</p>'
        else:
            mn = '<p class="page-subtitle"><strong>Caster Setup:</strong> 1H weapon + Shield or Staff. Mana regen > raw INT for uptime.</p>'
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{name}'s BiS - EQ Legends Wiki</title>
<link rel="stylesheet" href="../css/style.css">
<style>
.conf-eql {{ background:rgba(63,185,80,0.15); color:#3fb950; padding:1px 8px; border-radius:10px; font-size:0.7rem; font-weight:600; }}
.conf-beta {{ background:rgba(210,153,34,0.15); color:#d29922; padding:1px 8px; border-radius:10px; font-size:0.7rem; font-weight:600; }}
.bis-slot {{ padding:6px 10px; border-bottom:1px solid rgba(255,255,255,0.06); font-size:0.9rem; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
.bis-slot:hover {{ background:rgba(255,255,255,0.03); }}
.slot-label {{ min-width:80px; font-weight:600; color:#d4a843; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.03em; }}
.stat {{ color:#8b949e; font-size:0.85rem; cursor:help; }}
.stat[title]:hover {{ text-decoration:underline; text-decoration-style:dotted; }}
.zone {{ color:#58a6ff; font-size:0.8rem; }}
.alt {{ color:#6e7681; font-size:0.8rem; font-style:italic; }}
.alt a {{ color:#6e7681; text-decoration:underline dotted; }}
.alt a:hover {{ color:#58a6ff; }}
.exalt-inline {{ font-size:0.8rem; color:#d29922; width:100%; padding:2px 0 0 88px; }}
.exalt-inline a {{ color:#d29922; }}
a {{ color:#58a6ff; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
table {{ width:100%; border-collapse:collapse; margin:8px 0; }}
th, td {{ padding:6px 10px; text-align:left; border-bottom:1px solid rgba(255,255,255,0.08); font-size:0.85rem; }}
th {{ color:#d4a843; font-size:0.8rem; text-transform:uppercase; }}
</style>
</head>
<body>
{SIDEBAR}
<main class="content">
<div class="page-content">
<h1>{name}'s Best-in-Slot</h1>
<p class="page-subtitle">{classes} — Stat priority: {stat_prio}</p>
{mn}
<p class="page-subtitle"><span class="conf-eql">ON PATH</span> = drops in progression zone. <span class="conf-beta">off-path</span> = farm later. Items link to <strong>max level (+10)</strong> view — hover over names for details. Score: AC×lvl_weight + primary_stat×2 + haste_bonus. Vendor items penalized -20.</p>
{sections}
{master}
</div>
<footer class="page-footer"><p>Data from eqlegendstools.com and eqlwiki.com. Ruleset: eqlegends-bis-ruleset.</p></footer>
</main>
</body>
</html>'''
        
        path = os.path.join(OUT_DIR, f'{name.lower()}-bis.html')
        with open(path, 'w') as f:
            f.write(html)
        os.chmod(path, 0o644)
        print(f"Generated: {name.lower()}-bis.html")

if __name__ == '__main__':
    generate()
