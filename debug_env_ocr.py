import sys
import os
import traceback

print("=== Environment Info ===")
print(f"Python Executable: {sys.executable}")
print(f"CWD: {os.getcwd()}")
print(f"Sys Path: {sys.path}")

print("\n=== Import Check ===")
try:
    import paddle
    print(f"PaddlePaddle Version: {paddle.__version__}")
    print(f"Paddle Location: {paddle.__file__}")
except Exception:
    print("Failed to import paddle:")
    traceback.print_exc()

try:
    import paddleocr
    print(f"PaddleOCR Location: {paddleocr.__file__}")
except Exception:
    print("Failed to import paddleocr:")
    traceback.print_exc()

print("\n=== Initialization Check ===")
try:
    from paddleocr import PaddleOCR
    print("Attempting to initialize PaddleOCR(use_angle_cls=True, lang='ch')...")
    ocr = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
    print("PaddleOCR initialized successfully!")
except Exception:
    print("CRITICAL: Failed to initialize PaddleOCR:")
    traceback.print_exc()
