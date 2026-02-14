import sys
import time

print("Goose Mock: Starting task...")
sys.stdout.flush()
time.sleep(1)

print("File 'config.py' already exists. Overwrite? (y/n)")
sys.stdout.flush()

# Wait for input
line = sys.stdin.readline()
if line.strip().lower() == 'y':
    print("User said yes! Proceeding...")
    sys.stdout.flush()
    time.sleep(1)
    print("Task completed successfully.")
else:
    print(f"Goose Mock: User said '{line.strip()}'. Aborting.")
    sys.stdout.flush()
    sys.exit(1)
