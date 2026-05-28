import re

FILE_PATH = r"c:\Users\Wendy Llivichuzhca\Documents\GEOINFORMATICA\apu-pro\odoo_addons\geosis_website\views\geosis_portal_templates.xml"

def main():
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Move .table-wow to global CSS so it works everywhere
    table_wow_css = """
                .table-wow {
                    border-collapse: separate !important;
                    border-spacing: 0 10px !important;
                    background: transparent !important;
                }
                .table-wow tr {
                    background: #ffffff !important;
                    transition: all 0.3s !important;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.02) !important;
                }
                .table-wow tr:hover {
                    box-shadow: 0 8px 25px rgba(0,0,0,0.06) !important;
                    transform: translateY(-2px) !important;
                    z-index: 10;
                    position: relative;
                }
                .table-wow td, .table-wow th {
                    border: none !important;
                    padding: 16px 20px !important;
                    vertical-align: middle !important;
                }
                .table-wow td:first-child { border-radius: 12px 0 0 12px !important; }
                .table-wow td:last-child { border-radius: 0 12px 12px 0 !important; }
"""
    if ".table-wow {" not in content[:5000]: # Inject into the global style block at the top
        content = content.replace("</style>", table_wow_css + "\n            </style>", 1)

    # 1. Update tables
    def table_repl(match):
        cls = match.group(1)
        if 'table-wow' not in cls:
            # We strip old borders/hover classes and inject table-wow
            cleaned = cls.replace('table-hover', '').replace('table-bordered', '').replace('table-striped', '').strip()
            return f'class="table table-wow w-100 {cleaned}"'
        return match.group(0)
    
    content = re.sub(r'class="table\s+([^"]*)"', table_repl, content)
    content = re.sub(r'class="table"([^>]*)>', r'class="table table-wow w-100"\1>', content)

    # 2. Update cards
    def card_repl(match):
        cls = match.group(1)
        if 'wow-card' not in cls and 'geosis-metric-card' not in cls and 'geosis-panel' not in cls:
            cleaned = cls.replace('shadow-sm', '').replace('shadow', '').strip()
            return f'class="wow-card {cleaned}"'
        return match.group(0)
    
    content = re.sub(r'class="card\s+([^"]*)"', card_repl, content)
    content = re.sub(r'class="card"([^>]*)>', r'class="wow-card"\1>', content)
    
    # 3. Update panel-body / card-body
    content = content.replace('class="card-body"', 'class="p-4"')
    content = content.replace('class="card-body ', 'class="p-4 ')
    content = content.replace('class="card-header"', 'class="wow-header border-0 bg-transparent p-4 pb-0"')
    content = content.replace('class="card-header ', 'class="wow-header border-0 bg-transparent p-4 pb-0 ')

    # 4. Update badges
    def badge_repl(match):
        cls = match.group(1)
        if 'wow-badge' not in cls:
            return f'class="wow-badge {cls}"'
        return match.group(0)
        
    content = re.sub(r'class="badge\s+([^"]*)"', badge_repl, content)

    # 5. Make sure the wow-badge has some global CSS if it doesn't already
    wow_badge_css = """
                .wow-badge {
                    padding: 6px 12px !important;
                    border-radius: 30px !important;
                    font-weight: 700 !important;
                    font-size: 11px !important;
                    letter-spacing: 0.5px !important;
                    text-transform: uppercase !important;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.05) !important;
                }
"""
    if ".wow-badge {" not in content[:5000]:
        content = content.replace("</style>", wow_badge_css + "\n            </style>", 1)

    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Reemplazo masivo de clases de diseño completado.")

if __name__ == "__main__":
    main()
