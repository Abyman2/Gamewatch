with open("templates/index.html", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "<section" in line or 'class="view' in line or "id=\"view" in line:
            print(f"{i}: {line.strip()[:100]}")
