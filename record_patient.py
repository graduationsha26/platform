import paho.mqtt.client as mqtt
import json
import csv
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────
BROKER = "192.168.137.1"
PORT = 1883
TOPIC = "tremo/sensors/GLOVE001A"
USERNAME = "ZIYAD_ASHRAF"
PASSWORD = "ZIYAD_ASHRAF"  # In production, use environment variables or secure vaults for credentials

# ─── File Setup ───────────────────────────────────────────────────────────────
# Create a unique filename for each session based on the current time
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
FILENAME = f"patient_data_{timestamp}.csv"

# Open file in append/write mode
csv_file = open(FILENAME, mode='w', newline='')
csv_writer = csv.writer(csv_file)

# Write CSV Headers
csv_writer.writerow(['Timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ'])

# ─── MQTT Callbacks ───────────────────────────────────────────────────────────
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        # Extract data with default 0 if missing
        ax = data.get('aX', 0.0)
        ay = data.get('aY', 0.0)
        az = data.get('aZ', 0.0)
        gx = data.get('gX', 0.0)
        gy = data.get('gY', 0.0)
        gz = data.get('gZ', 0.0)
        
        # Get exact current time down to milliseconds
        current_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        # Write to CSV and flush immediately to disk
        csv_writer.writerow([current_time, ax, ay, az, gx, gy, gz])
        csv_file.flush() 
        
        # Minimal print to avoid terminal lag
        print(f"[{current_time}] Recorded | aX: {ax:.2f}, aZ: {az:.2f}")
        
    except json.JSONDecodeError:
        print("Error: Received non-JSON payload.")
    except Exception as e:
        print(f"Error saving data: {e}")

# ─── Main Execution ───────────────────────────────────────────────────────────
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, PASSWORD)
client.on_message = on_message

print(f"Connecting to Local Broker ({BROKER})...")
print(f"Data will be securely saved to: {FILENAME}")

client.connect(BROKER, PORT, 60)
client.subscribe(TOPIC)

try:
    print("\n[REC] Recording started! Tell the patient to begin.")
    print("Press Ctrl+C to stop recording and safely close the file.\n")
    client.loop_forever()
except KeyboardInterrupt:
    print("\n[STOP] Recording stopped. File saved successfully!")
    csv_file.close()