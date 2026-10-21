"""Check skill metadata and local Markdown links, without network calls."""

import re
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1]
text = (root / "SKILL.md").read_text(encoding="utf-8")
frontmatter = yaml.safe_load(text.split("---", 2)[1])
assert frontmatter["name"] == root.name
assert frontmatter["description"] and len(frontmatter["name"]) < 64
for path in root.rglob("*.md"):
    if any(part in {".git", ".venv", "runs", "outputs"} for part in path.relative_to(root).parts):
        continue
    for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        if "://" in link or link.startswith(("#", "mailto:")):
            continue
        target = link.split("#", 1)[0]
        assert (path.parent / target).exists(), f"Broken link in {path}: {target}"
print("Skill metadata and local document links passed")
