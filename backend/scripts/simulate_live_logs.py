import time
import sys
import os

def append_to_log(filepath: str):
    if not os.path.exists(filepath):
        print(f"File {filepath} does not exist yet. Please upload it via the UI first.")
        return

    print(f"Simulating live log updates for {filepath}")
    print("Press Ctrl+C to stop.")
    
    try:
        count = 1
        while True:
            # Simulate a new log entry
            new_line = f"2026-08-26 14:00:{count:02d} [INFO] Simulated log entry number {count} - System operating normally\n"
            
            with open(filepath, 'a') as f:
                f.write(new_line)
                
            print(f"Appended: {new_line.strip()}")
            count += 1
            
            # Wait 16 seconds (slightly longer than the 15s polling interval)
            time.sleep(16)
            
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simulate_live_logs.py <path_to_persistent_log_file>")
        sys.exit(1)
        
    append_to_log(sys.argv[1])
