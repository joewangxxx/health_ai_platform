import os

file_path = r"D:\Anaconda3\Lib\site-packages\imgaug\imgaug.py"

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The line causing error is: NP_FLOAT_TYPES = set(np.sctypes["float"])
    # We replace it with explicit types compatible with new and old numpy
    target = 'NP_FLOAT_TYPES = set(np.sctypes["float"])'
    replacement = 'NP_FLOAT_TYPES = {np.float16, np.float32, np.float64}'

    if target in content:
        new_content = content.replace(target, replacement)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully patched imgaug.py")
    else:
        print("Target string not found. File might vary or already be patched.")
        # Fallback for slight variations
        import re
        pattern = re.compile(r'NP_FLOAT_TYPES\s*=\s*set\(np\.sctypes\["float"\]\)')
        if pattern.search(content):
            new_content = pattern.sub(replacement, content)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print("Successfully patched imgaug.py using regex")
        else:
            print("Could not find the problematic line.")

except Exception as e:
    print(f"Error patching file: {e}")
