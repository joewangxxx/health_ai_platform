import uvicorn
import os
import sys

# Add project root to sys.path explicitly to be safe
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Use standard uvicorn run arguments
    # reload=True is good for development
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
