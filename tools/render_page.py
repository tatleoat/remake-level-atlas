"""Write the standalone page from the page template and a data file.

Usage: render_page.py src/app_template.html data/remake_map.json index.html
The public data file has no pictures and no Evil Resource descriptions, so the page it makes is safe to publish; the
pictures come from the player's own copies through the page's Assets dialog.
"""
import sys
from pathlib import Path

tpl, data, out = (Path(a) for a in sys.argv[1:4])
page = tpl.read_text().replace("/*__DATA__*/null", data.read_text().strip())
page = ('<!doctype html>\n<html lang="en" data-skin="remake"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + page.replace("</style>", "[hidden] { display: none !important; }\n</style>\n</head><body>", 1) + "\n</body></html>\n")
out.write_text(page)
print(out, len(page) // 1024, "KB")
