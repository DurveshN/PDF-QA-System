import sys
import subprocess
import importlib.util

def check_package(package_name):
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        return False
    return True

def check_ollama():
    try:
        # Check if ollama is running (default port 11434)
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(("localhost", 11434))
        return True
    except:
        return False

def main():
    print("=== PDF-QA System Verification ===")

    # 1. Python version
    print(f"Python version: {sys.version.split()[0]} - OK")

    # 2. Key Dependencies
    dependencies = [
        ("fastapi", "FastAPI"),
        ("langchain_core", "LangChain Core"),
        ("chromadb", "ChromaDB"),
        ("sentence_transformers", "Sentence Transformers"),
        ("exa_py", "Exa SDK")
    ]

    print("\nChecking Dependencies:")
    for pkg, name in dependencies:
        status = "INSTALLED" if check_package(pkg) else "MISSING"
        print(f"  {name:25}: {status}")

    # 3. Ollama Status
    print("\nChecking External Services:")
    ollama_status = "RUNNING" if check_ollama() else "NOT REACHABLE (Start Ollama locally)"
    print(f"  Ollama (localhost:11434) : {ollama_status}")

    print("\nVerification Complete.")

if __name__ == "__main__":
    main()
