"""Launch the MimiClaw Electron desktop dashboard."""
import os
import subprocess
import sys

DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")


def check_node():
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def ensure_node_modules():
    modules_path = os.path.join(DASHBOARD_DIR, "node_modules", "electron")
    if not os.path.exists(modules_path):
        print("Installing Electron (first run only)...")
        subprocess.run(["npm", "install"], cwd=DASHBOARD_DIR, check=True, shell=True)
        print("Done.")


if __name__ == "__main__":
    if not check_node():
        print("ERROR: Node.js is not installed or not in PATH.")
        print("Download from https://nodejs.org")
        sys.exit(1)

    ensure_node_modules()

    print("Launching MimiClaw Dashboard...")
    subprocess.run(["npm", "start"], cwd=DASHBOARD_DIR, shell=True)
