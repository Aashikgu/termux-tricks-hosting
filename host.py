import os
import sys
import socket
import subprocess
import signal
import time

# TERMUX TRICKS HOST PRO
# Version 1.0

SERVER = None

def banner():
    os.system("clear")
    print("""
╔══════════════════════════════════════╗
║       TERMUX TRICKS HOST PRO         ║
║              VERSION 1.0             ║
╚══════════════════════════════════════╝
""")

def ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def start_php():
    global SERVER

    port = input("Enter PHP Port [8080]: ") or "8080"

    if not port.isdigit() or not 1 <= int(port) <= 65535:
        print("Invalid port!")
        return

    os.makedirs("website", exist_ok=True)

    if not os.path.exists("website/index.php"):
        with open("website/index.php", "w") as f:
            f.write("""
<h1>TERMUX TRICKS HOST PRO</h1>
<p>PHP Server Running Successfully!</p>
""")

    if SERVER:
        stop_server()

    SERVER = subprocess.Popen([
        "php", "-S", f"127.0.0.1:{port}", "-t", "website"
    ])

    print("\nPHP Server Started!")
    print(f"URL: http://127.0.0.1:{port}")
    print("\nPress ENTER to return.")
    input()

def start_python():
    global SERVER

    port = input("Enter Python Port [8000]: ") or "8000"

    if not port.isdigit() or not 1 <= int(port) <= 65535:
        print("Invalid port!")
        return

    os.makedirs("website", exist_ok=True)

    if SERVER:
        stop_server()

    SERVER = subprocess.Popen([
        sys.executable, "-m", "http.server",
        port, "--bind", "127.0.0.1"
    ], cwd="website")

    print("\nPython Server Started!")
    print(f"URL: http://127.0.0.1:{port}")
    print("\nPress ENTER to return.")
    input()

def stop_server():
    global SERVER

    if SERVER and SERVER.poll() is None:
        SERVER.terminate()
        SERVER.wait()
        print("Server stopped successfully!")
    else:
        print("No server running!")

    SERVER = None
    input("\nPress ENTER...")

def server_status():
    if SERVER and SERVER.poll() is None:
        print("STATUS: RUNNING")
    else:
        print("STATUS: STOPPED")

    input("\nPress ENTER...")

def menu():
    while True:
        banner()

        print("""
[1] Start PHP Hosting
[2] Start Python Hosting
[3] Server Status
[4] Stop Server
[5] Exit
""")

        choice = input("Select Option: ")

        if choice == "1":
            start_php()

        elif choice == "2":
            start_python()

        elif choice == "3":
            server_status()

        elif choice == "4":
            stop_server()

        elif choice == "5":
            stop_server()
            print("Thank you for using TERMUX TRICKS HOST PRO!")
            break

        else:
            print("Invalid Option!")
            time.sleep(1)

if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        stop_server()
