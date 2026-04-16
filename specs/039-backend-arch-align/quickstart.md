# Quickstart: Backend Architecture Alignment

**Branch**: `039-backend-arch-align` | **Date**: 2026-04-12

## What This Feature Changes

Three targeted hardening changes to the backend — no new apps, no migrations, no frontend changes.

---

## Scenario 1: Verifying Inference API Permission (US1)

After implementing, confirm the permission gate works:

```bash
# From repo root — get a doctor token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "doctor@example.com", "password": "pass"}'
# Copy access token → DOCTOR_TOKEN

# Should return 200
curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer $DOCTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6]]}'

# Get an admin token → ADMIN_TOKEN
# Should also return 200
curl -X POST http://localhost:8000/api/inference/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6]]}'

# Unauthenticated → should return 401
curl -X POST http://localhost:8000/api/inference/ \
  -H "Content-Type: application/json" \
  -d '{"sensor_data": [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6]]}'
```

---

## Scenario 2: Verifying MQTT Config Loads from .env (US2)

Confirm settings are read from the environment:

```bash
# In backend/.env, set:
# MQTT_BROKER_URL=mqtt://localhost:1883
# MQTT_USERNAME=testuser
# MQTT_PASSWORD=testpass

# Start Django shell
cd backend
python manage.py shell

# Verify settings values
from django.conf import settings
print(settings.MQTT_BROKER_URL)   # mqtt://localhost:1883
print(settings.MQTT_USERNAME)     # testuser
print(settings.MQTT_PASSWORD)     # testpass
```

---

## Scenario 3: Verifying Named Loggers Are Active (US2)

```python
# In Django shell:
import logging

# Each of these should produce output when level <= DEBUG
logging.getLogger('inference').info('Test inference logger')
logging.getLogger('cmg').info('Test cmg logger')
logging.getLogger('realtime').info('Test realtime logger')

# Check it also reaches the file handler
# tail backend/logs/django.log
```

---

## Scenario 4: Verifying Bidirectional MQTT Publish (US3)

```python
# Start a local MQTT broker (e.g., Mosquitto)
# Subscribe to watch outbound messages:
#   mosquitto_sub -t "devices/#" -v

# In Django shell:
from realtime.mqtt_client import MQTTClient
client = MQTTClient()
client.connect()  # Run in a thread in practice

# In another shell/thread after connect completes:
result = client.publish_cmg_command('GLOVE-001', 'START')
print(result)  # True if broker connected

result = client.publish_pid_config('GLOVE-001', {
    'kp': 1.0, 'ki': 0.1, 'kd': 0.05
})
print(result)  # True if broker connected
```

When the broker is offline, both calls should return `False` and log a WARNING — no exception raised.

---

## .env Reference

Minimum entries needed for this feature:

```env
# MQTT Broker (Bidirectional)
MQTT_BROKER_URL=mqtt://localhost:1883
MQTT_USERNAME=
MQTT_PASSWORD=
```

These must be present in `backend/.env` (or left at defaults for local dev).
