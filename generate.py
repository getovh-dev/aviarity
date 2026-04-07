# =========================================
# Aviarity Bird2 Automation
# Version: 0.1
# Telegram: @aviarity
# =========================================

import yaml
import subprocess
import sys
import shutil
import os
import difflib
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

YAML_PATH = "./peers.yaml"
TEMPLATE_DIR = "./templates"
OUTPUT_PATH = "./bird.conf"
BACKUP_DIR = "./backups"
MAX_BACKUPS = 10

def load_data():
    with open(YAML_PATH) as f:
        data = yaml.safe_load(f)
    for key in ["downstreams", "byoip", "collectors", "ixps", "upstreams"]:
        if key not in data or data[key] is None:
            data[key] = []
    return data

def render_config(data):
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("bird.conf.j2")
    return template.render(**data)

def show_diff(new_config):
    if not os.path.exists(OUTPUT_PATH):
        print("Первичная генерация конфигурации")
        return
    with open(OUTPUT_PATH) as f:
        old = f.readlines()
    new = new_config.splitlines(keepends=True)
    diff = difflib.unified_diff(old, new, fromfile="old", tofile="new")
    output = "".join(diff)
    print(output if output else "Изменений нет")

def backup_config():
    if not os.path.exists(OUTPUT_PATH):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(OUTPUT_PATH, os.path.join(BACKUP_DIR, f"bird.conf.{timestamp}"))

def cleanup_backups():
    if not os.path.exists(BACKUP_DIR):
        return
    backups = sorted(os.listdir(BACKUP_DIR))
    while len(backups) > MAX_BACKUPS:
        os.remove(os.path.join(BACKUP_DIR, backups.pop(0)))

def validate_config():
    result = subprocess.run(
        ["bird", "-p", "-c", OUTPUT_PATH],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0

def apply_config():
    result = subprocess.run(
        ["birdc", "configure"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0

def rollback():
    if not os.path.exists(BACKUP_DIR):
        return False
    backups = sorted(os.listdir(BACKUP_DIR))
    if not backups:
        return False
    shutil.copy2(os.path.join(BACKUP_DIR, backups[-1]), OUTPUT_PATH)
    return True

def main():
    data = load_data()
    config = render_config(data)

    if "--dry-run" in sys.argv:
        print(config)
        return
    if "--diff" in sys.argv:
        show_diff(config)
        return

    backup_config()
    with open(OUTPUT_PATH, "w") as f:
        f.write(config)

    if not validate_config():
        rollback()
        sys.exit(1)

    apply_config()
    cleanup_backups()

if __name__ == "__main__":
    main()
