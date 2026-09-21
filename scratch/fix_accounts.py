import re

file_path = 'accounts/api/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'tags=\["Login"\]', 'tags=["Authentication"]', content)
content = re.sub(r'tags=\["SignUp"\]', 'tags=["Authentication"]', content)
content = re.sub(r'tags=\["Logout"\]', 'tags=["Authentication"]', content)
content = re.sub(r'tags=\["Accounts"\]', 'tags=["Account"]', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
