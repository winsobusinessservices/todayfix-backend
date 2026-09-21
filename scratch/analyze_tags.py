import os
import re
from collections import defaultdict

pattern = re.compile(r'tags=\[[\'"]([^\'"]+)[\'"]\]')
tag_files = defaultdict(list)

for root, _, files in os.walk('.'):
    if 'venv' in root or '.git' in root: continue
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = pattern.findall(content)
                for m in matches:
                    tag_files[m].append(path)

for tag, files in sorted(tag_files.items()):
    print(f"TAG: {tag}")
    for file in sorted(set(files)):
        print(f"  - {file}")
