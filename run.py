import sys
import subprocess
import os

def check_and_install_dependencies():
    """
    Check if required dependencies are installed, otherwise auto-install them via pip.
    """
    print("[*] Verifying python requirements...")
    required_packages = ["fastapi", "uvicorn", "pandas", "numpy", "yfinance", "multipart"]
    missing = []
    
    for pkg in required_packages:
        try:
            if pkg == "multipart":
                import multipart
            else:
                __import__(pkg)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        print(f"[!] Missing dependencies detected: {missing}")
        print("[*] Installing requirements from requirements.txt...")
        try:
            # yfinance needs yfinance, multipart needs python-multipart (which has multipart folder)
            # It's safest to run: pip install -r requirements.txt
            req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
            print("[+] Successfully installed all dependencies.")
        except Exception as e:
            print(f"[x] Error installing dependencies: {str(e)}")
            print("[!] Please run 'pip install -r requirements.txt' manually.")
            sys.exit(1)
    else:
        print("[+] All python requirements satisfied.")

def start_server():
    """
    Start the Uvicorn application server.
    """
    print("\n" + "="*60)
    print("      QUANTUM BACKTEST EXECUTION TERMINAL SERVER")
    print("="*60)
    print("[*] Server is launching on: http://127.0.0.1:8000")
    print("[*] Please copy and paste this URL into your browser.")
    print("[*] Press Ctrl+C to terminate the server session.")
    print("="*60 + "\n")
    
    import uvicorn
    # Run the uvicorn server hosting backend.app:app from current directory
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    check_and_install_dependencies()
    start_server()
