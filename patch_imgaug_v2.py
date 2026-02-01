cimport os

file_path = r"D:\Anaconda3\Lib\site-packages\imgaug\imgaug.py"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    replacements = [
        ('set(np.sctypes["float"])', '{np.float16, np.float32, np.float64}'),
        ('set(np.sctypes["int"])', '{np.int8, np.int16, np.int32, np.int64}'),
        ('set(np.sctypes["uint"])', '{np.uint8, np.uint16, np.uint32, np.uint64}')
    ]
    
    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully patched all np.sctypes usages in imgaug.py")
    else:
        print("No more occurrences found or already patched.")

except Exception as e:
    print(f"Error patching file: {e}")
