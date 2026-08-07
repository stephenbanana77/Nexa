"""Fix preview function name collision + route ordering."""
with open('api/projects.py', encoding='utf-8') as f:
    content = f.read()

# 1. Rename POST preview function
content = content.replace(
    'async def preview_dataset(\n    file: UploadFile = File(...),\n    current_user: User = Depends(get_current_user),',
    'async def preview_file_upload(\n    file: UploadFile = File(...),\n    current_user: User = Depends(get_current_user),'
)

# 2. Rename GET preview function
content = content.replace(
    'def preview_dataset(\n    dataset_id: str,\n    limit: int = 1000,\n    current_user: User = Depends(get_current_user),',
    'def fetch_dataset_preview(\n    dataset_id: str,\n    limit: int = 1000,\n    current_user: User = Depends(get_current_user),'
)

with open('api/projects.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed')
"