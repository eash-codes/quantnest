"""Day 6A: Domain Demo + FastAPI Server."""

import uvicorn
from quantnest.api.main import app
import subprocess

print("🚀 QuantNest Day 6A - Architecture Boundaries")
print("\n✅ Your Day 5 domain is SAFE (domain_demo.py)")
print("\n🌐 NEW FastAPI Layer:")
print("1. uvicorn quantnest.api.main:app --reload")
print("2. Visit http://localhost:8000/docs")
print("3. Test: curl http://localhost:8000/api/v1/portfolio/demo-user/summary")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
