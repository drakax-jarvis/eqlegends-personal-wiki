"""Add David's Combo section to all page sidebars."""
import glob, re

SIDEBAR = '''        </ul></div>
        <div class="nav-section"><h3>David's Combo</h3><ul>
            <li><a href="paladin.html">Paladin</a></li><li><a href="shaman.html">Shaman</a></li><li><a href="necromancer.html">Necromancer</a></li><li><a href="david-combo.html">Pal/Shm/Nec Guide</a></li><li><a href="david-bis.html">David's BiS</a></li>
        </ul></div>
        <div class="nav-section"><h3>Brian's Combo</h3><ul>'''

# Pages that should have the sidebar - exclude david-bis.html and david-combo.html since they already have it
for f in glob.glob('/home/hermes/eq-legends-wiki/pages/*.html') + ['/home/hermes/eq-legends-wiki/index.html']:
    with open(f) as fh:
        content = fh.read()
    
    # Skip files that already have David's section
    if "David's Combo" in content:
        continue
    
    # Brian's section - insert David's section before it
    if "nav-section\"><h3>Brian" in content or "Brian's Combo" in content:
        content = content.replace(
            '<div class="nav-section"><h3>Brian\'s Combo</h3><ul>',
            '<div class="nav-section"><h3>David\'s Combo</h3><ul>\n            <li><a href="paladin.html">Paladin</a></li><li><a href="shaman.html">Shaman</a></li><li><a href="necromancer.html">Necromancer</a></li><li><a href="david-combo.html">Pal/Shm/Nec Guide</a></li><li><a href="david-bis.html">David\'s BiS</a></li>\n        </ul></div>\n        <div class="nav-section"><h3>Brian\'s Combo</h3><ul>'
        )
        with open(f, 'w') as fh:
            fh.write(content)
        print(f"Updated: {f.split('/')[-1]}")
    elif "nav-section\"><h3>Jessy" in content or "Jessy's Combo" in content:
        # Some pages might have different order
        content = content.replace(
            '<div class="nav-section"><h3>Jessica',
            '<div class="nav-section"><h3>David\'s Combo</h3><ul>\n            <li><a href="paladin.html">Paladin</a></li><li><a href="shaman.html">Shaman</a></li><li><a href="necromancer.html">Necromancer</a></li><li><a href="david-combo.html">Pal/Shm/Nec Guide</a></li><li><a href="david-bis.html">David\'s BiS</a></li>\n        </ul></div>\n        <div class="nav-section"><h3>Jessy\'s Combo</h3><ul>'
        )
        print(f"Updated: {f.split('/')[-1]}")

print("\nDone. David's combo section added to sidebar.")
