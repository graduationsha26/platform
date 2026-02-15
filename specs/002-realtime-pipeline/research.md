# Technical Research: Real-Time Pipeline

**Feature**: Real-Time Pipeline (002-realtime-pipeline)
**Date**: 2026-02-15
**Purpose**: Resolve technical unknowns and document architectural decisions for MQTT + WebSocket real-time data pipeline

---

## R1: Django Channels + Redis Channel Layer

### Decision
Use Django Channels 4.x with Redis channel layer backend (`channels-redis`) for WebSocket support and inter-process communication.

### Rationale
- **Django Channels** is the standard Django extension for WebSocket support, fully integrated with Django auth
- **Redis channel layer** provides production-grade message passing between ASGI processes (MQTT subscriber → WebSocket consumers)
- Redis is lightweight, easy to install locally, and well-documented with Django Channels
- Alternative (in-memory channel layer) only works for single-process development, not suitable for separate MQTT subscriber process

### Implementation Details
```python
# settings.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://localhost:6379/0")],
        },
    },
}
```

**Best Practices**:
- Use channel groups for patient-specific broadcasting: `group_add("patient_{patient_id}_tremor_data")`
- Use `async` consumers for better performance
- Gracefully handle channel layer connection failures
- Set Redis `maxmemory-policy` to `allkeys-lru` for channel layer

### Alternatives Considered
- **In-memory channel layer**: Only works single-process, not suitable for separate MQTT subscriber
- **RabbitMQ backend**: More complex setup, overkill for local development
- **PostgreSQL backend**: Not recommended by Channels documentation

---

## R2: paho-mqtt Client Patterns

### Decision
Use `paho-mqtt` library with persistent connection pattern, running as Django management command.

### Rationale
- **paho-mqtt** is the standard Python MQTT client library, stable and well-maintained
- **Management command** pattern allows MQTT subscriber to run as separate long-lived process
- Persistent connection with auto-reconnect ensures reliability for 24/7 operation

### Implementation Pattern
```python
# management/commands/run_mqtt_subscriber.py
import paho.mqtt.client as mqtt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def on_connect(client, userdata, flags, rc):
    logger.info(f"Connected to MQTT broker with code {rc}")
    client.subscribe("devices/+/data")  # Wildcard subscription

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # Validate device, patient, data schema
        # Store to database
        # Broadcast via channel layer
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"patient_{patient_id}_tremor_data",
            {"type": "tremor_data", "data": payload}
        )
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(username, password)
client.connect(broker_host, broker_port, keepalive=60)
client.loop_forever()  # Blocking call
```

**Best Practices**:
- Use `loop_forever()` for persistent connection in management command
- Implement `on_disconnect` callback with exponential backoff reconnection
- Use `keepalive` parameter (60 seconds) to detect dead connections
- Use topic wildcards (`devices/+/data`) for multiple devices
- Validate device serial number from topic against database before processing

### Alternatives Considered
- **asyncio-mqtt**: Async MQTT client, but adds complexity for Django integration
- **Celery task polling**: Would poll broker instead of persistent connection, inefficient
- **Django Channels consumer for MQTT**: Channels doesn't natively support MQTT protocol

---

## R3: ML Model Loading and Inference Optimization

### Decision
Load ML models once at application startup, cache in memory, use thread-safe prediction functions.

### Rationale
- Loading models on every prediction is too slow (models can be 10-100MB)
- In-memory caching enables <10ms inference after load
- Thread-safe access required for concurrent MQTT messages

### Implementation Pattern
```python
# ml_service.py
import joblib
import tensorflow as tf
import threading

class MLPredictionService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._load_models()
        return cls._instance

    def _load_models(self):
        self.sklearn_model = joblib.load("models/tremor_severity_model.pkl")
        self.keras_model = tf.keras.models.load_model("models/tremor_model.h5")
        logger.info("ML models loaded successfully")

    def predict_severity(self, sensor_data):
        # Preprocess data
        features = self._extract_features(sensor_data)
        # Predict
        prediction = self.sklearn_model.predict([features])[0]
        confidence = float(self.sklearn_model.predict_proba([features]).max())
        return {"severity": prediction, "confidence": confidence}

# Usage
ml_service = MLPredictionService()  # Singleton
result = ml_service.predict_severity(sensor_data)
```

**Best Practices**:
- Use singleton pattern to load models once
- Use thread lock for thread-safe initialization
- Preprocess sensor data (normalization, feature extraction) before inference
- Handle model loading errors gracefully (log, fallback to no predictions)
- Document model file locations and expected input/output formats

### Alternatives Considered
- **Load model per prediction**: Too slow (100-500ms per load)
- **Separate ML microservice**: Overkill for local development, adds network latency
- **TensorFlow Serving**: Production tool, out of scope for local dev

---

## R4: WebSocket Authentication with JWT

### Decision
Validate JWT token in WebSocket consumer's `connect()` method by reading from query parameter or header.

### Rationale
- WebSocket connections don't support standard HTTP headers in browser API
- Query parameter is widely supported: `ws://localhost:8000/ws/tremor-data/123/?token=<jwt>`
- Validate token using Django SimpleJWT before accepting connection

### Implementation Pattern
```python
# consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

class TremorDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract token from query params
        token_str = self.scope['query_string'].decode().split('token=')[1]

        try:
            # Validate JWT token
            token = AccessToken(token_str)
            user_id = token['user_id']
            user_role = token['role']

            # Load user from database
            self.user = await self.get_user(user_id)

            # Check access control
            patient_id = self.scope['url_route']['kwargs']['patient_id']
            if not await self.has_access(self.user, patient_id):
                await self.close(code=4403)  # Forbidden
                return

            # Join channel group
            await self.channel_layer.group_add(
                f"patient_{patient_id}_tremor_data",
                self.channel_name
            )
            await self.accept()

        except (TokenError, KeyError):
            await self.close(code=4401)  # Unauthorized
```

**Best Practices**:
- Close connection with custom WebSocket close codes (4401 for auth, 4403 for forbidden)
- Use async database queries (`sync_to_async` wrapper for Django ORM)
- Validate token expiry (SimpleJWT handles this automatically)
- Send error message before closing: `await self.send(json.dumps({"error": "Unauthorized"}))`

### Alternatives Considered
- **Session-based auth**: Doesn't work well with WebSocket, requires cookies
- **Custom header**: Not supported in browser WebSocket API
- **Subprotocol**: More complex, query param is simpler

---

## R5: MQTT Message Schema and Validation

### Decision
Define strict JSON schema for MQTT messages, validate all fields before database storage.

### Rationale
- Prevents malformed data from corrupting database
- Provides clear contract with glove device firmware
- Enables early error detection and debugging

### MQTT Message Schema
```json
{
  "serial_number": "GLV123456789",
  "timestamp": "2026-02-15T14:30:00Z",
  "tremor_intensity": [0.12, 0.15, 0.18, 0.14, 0.11],
  "frequency": 4.5,
  "timestamps": [
    "2026-02-15T14:30:00.000Z",
    "2026-02-15T14:30:00.020Z",
    "2026-02-15T14:30:00.040Z",
    "2026-02-15T14:30:00.060Z",
    "2026-02-15T14:30:00.080Z"
  ],
  "session_duration": 100
}
```

**Field Specifications**:
- `serial_number`: String, 8-20 alphanumeric characters (validated against Device model)
- `timestamp`: ISO 8601 format UTC timestamp (session start time)
- `tremor_intensity`: Array of floats (0.0-1.0 range, normalized tremor magnitude)
- `frequency`: Float (Hz, dominant tremor frequency)
- `timestamps`: Array of ISO 8601 timestamps (one per intensity measurement)
- `session_duration`: Integer (milliseconds, calculated by device)

**Validation Rules**:
1. All fields required (reject if missing)
2. `serial_number` must match registered Device in database
3. Device must be paired to a patient
4. `tremor_intensity` and `timestamps` arrays must have equal length
5. `timestamps` must be chronologically ordered
6. `tremor_intensity` values must be in range [0.0, 1.0]

### Implementation
```python
def validate_mqtt_message(payload):
    required_fields = ["serial_number", "timestamp", "tremor_intensity", "frequency", "timestamps", "session_duration"]
    for field in required_fields:
        if field not in payload:
            raise ValidationError(f"Missing required field: {field}")

    if len(payload["tremor_intensity"]) != len(payload["timestamps"]):
        raise ValidationError("tremor_intensity and timestamps length mismatch")

    for intensity in payload["tremor_intensity"]:
        if not (0.0 <= intensity <= 1.0):
            raise ValidationError(f"tremor_intensity out of range: {intensity}")

    # Additional validation...
```

---

## R6: Message Serialization (JSON vs MessagePack)

### Decision
Use JSON for WebSocket messages (not MessagePack).

### Rationale
- **JSON** is universally supported, human-readable, easy to debug
- **MessagePack** provides 20-30% size reduction but adds complexity
- For tremor data at 50Hz, JSON size (~500 bytes/message) is acceptable for local network
- Browser WebSocket API natively supports JSON

### Message Format
```json
{
  "type": "tremor_data",
  "patient_id": 123,
  "device_serial": "GLV123456789",
  "timestamp": "2026-02-15T14:30:00Z",
  "tremor_intensity": [0.12, 0.15, 0.18],
  "frequency": 4.5,
  "prediction": {
    "severity": "moderate",
    "confidence": 0.92
  }
}
```

**Best Practices**:
- Use `json.dumps()` with `separators=(',', ':')` to minimize whitespace
- Send timestamps in ISO 8601 format (JavaScript Date can parse natively)
- Include `type` field for message discrimination (future extensibility)

### Alternatives Considered
- **MessagePack**: More efficient but requires library on frontend, harder to debug
- **Protocol Buffers**: Overkill, requires schema compilation

---

## R7: Error Handling and Reconnection Logic

### Decision
Implement exponential backoff reconnection for MQTT subscriber, graceful WebSocket closure for clients.

### Rationale
- Network failures are inevitable, system must auto-recover
- Exponential backoff prevents overwhelming broker during outages
- Graceful closure allows clients to display user-friendly error messages

### MQTT Reconnection Pattern
```python
def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"Unexpected MQTT disconnect, code {rc}")
        retry_count = 0
        max_delay = 60

        while retry_count < 10:
            delay = min(2 ** retry_count, max_delay)
            logger.info(f"Reconnecting in {delay} seconds...")
            time.sleep(delay)

            try:
                client.reconnect()
                logger.info("Reconnected successfully")
                break
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                retry_count += 1
        else:
            logger.critical("Max reconnection attempts reached, exiting")
            sys.exit(1)
```

### WebSocket Error Handling
```python
async def disconnect(self, close_code):
    # Leave channel group
    await self.channel_layer.group_discard(
        f"patient_{self.patient_id}_tremor_data",
        self.channel_name
    )
    logger.info(f"WebSocket disconnected: user={self.user.id}, code={close_code}")

async def receive(self, text_data):
    try:
        data = json.loads(text_data)
        # Process message
    except json.JSONDecodeError:
        await self.send(json.dumps({"error": "Invalid JSON"}))
    except Exception as e:
        logger.error(f"Error in WebSocket receive: {e}")
        await self.send(json.dumps({"error": "Internal server error"}))
```

**Best Practices**:
- Log all connection/disconnection events with user ID and timestamp
- Send error messages to WebSocket clients before closing connection
- Use custom close codes (4xxx range) for application-level errors
- Implement health check endpoint for monitoring MQTT connection status

---

## R8: WebSocket Group Broadcasting for Patient Isolation

### Decision
Use Django Channels group names with patient ID: `patient_{patient_id}_tremor_data`.

### Rationale
- **Channel groups** provide isolated broadcast channels per patient
- Multiple consumers can join same group (multiple doctors monitoring one patient)
- Group names with patient ID ensure data isolation (no cross-patient leakage)

### Implementation Pattern
```python
# MQTT subscriber sends to group
channel_layer = get_channel_layer()
async_to_sync(channel_layer.group_send)(
    f"patient_{patient_id}_tremor_data",
    {
        "type": "tremor.data",  # Maps to tremor_data() method in consumer
        "message": sensor_data_json
    }
)

# WebSocket consumer receives from group
class TremorDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        patient_id = self.scope['url_route']['kwargs']['patient_id']
        self.patient_id = patient_id
        await self.channel_layer.group_add(
            f"patient_{patient_id}_tremor_data",
            self.channel_name
        )
        await self.accept()

    async def tremor_data(self, event):
        # Called when group receives message
        await self.send(text_data=event["message"])
```

**Best Practices**:
- Validate patient access before joining group (in `connect()`)
- Remove from group on disconnect (in `disconnect()`)
- Use `group_send` with `type` field to route to correct consumer method
- Method name uses underscores: `type="tremor.data"` → `async def tremor_data(self, event)`

---

## R9: Performance Optimization - Batching Database Writes

### Decision
For high-frequency data (>10Hz), batch MQTT messages before database writes.

### Rationale
- Writing every message to DB at 50Hz = 50 writes/sec per device = potential bottleneck
- Batching 10 messages reduces DB writes to 5/sec with minimal latency impact
- PostgreSQL performs better with batch inserts than individual inserts

### Implementation Pattern
```python
class MQTTMessageBatcher:
    def __init__(self, batch_size=10, flush_interval=1.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer = []
        self.last_flush = time.time()

    def add_message(self, payload):
        self.buffer.append(payload)

        # Flush if batch size reached or time interval elapsed
        if len(self.buffer) >= self.batch_size or (time.time() - self.last_flush) > self.flush_interval:
            self.flush()

    def flush(self):
        if not self.buffer:
            return

        # Bulk create BiometricSession records
        sessions = [
            BiometricSession(
                patient_id=msg["patient_id"],
                device_id=msg["device_id"],
                session_start=msg["timestamp"],
                sensor_data=msg["sensor_data"]
            )
            for msg in self.buffer
        ]
        BiometricSession.objects.bulk_create(sessions)

        logger.info(f"Flushed {len(self.buffer)} messages to database")
        self.buffer = []
        self.last_flush = time.time()
```

**Trade-offs**:
- **Latency**: Adds up to 1 second delay before data appears in historical records
- **Risk**: If process crashes, buffered messages lost (acceptable for non-critical historical data)
- **Complexity**: More code, more edge cases

**Decision**: Implement batching only if performance testing reveals DB bottleneck. Start with direct writes.

---

## R10: Testing Strategies

### Decision
Use pytest with mocking for unit tests, integration tests with test MQTT broker.

### Rationale
- **pytest** is standard for Django testing, good async support
- **Mocking** (unittest.mock) isolates components for fast unit tests
- **Integration tests** with real MQTT broker validate end-to-end flow

### Test Structure
```python
# Unit tests - mock channel layer and MQTT client
@pytest.mark.asyncio
async def test_websocket_consumer_connect():
    consumer = TremorDataConsumer()
    consumer.scope = {
        'query_string': b'token=valid_jwt_token',
        'url_route': {'kwargs': {'patient_id': 1}}
    }
    consumer.channel_layer = Mock()

    await consumer.connect()

    assert consumer.channel_layer.group_add.called
    assert consumer.user.id == 1

# Integration tests - use in-memory channel layer
@pytest.mark.django_db
def test_mqtt_to_websocket_flow():
    # Start WebSocket consumer (background)
    # Publish MQTT message
    # Assert WebSocket receives message
    pass
```

**Testing Tools**:
- `pytest-django`: Django integration for pytest
- `pytest-asyncio`: Async test support
- `unittest.mock`: Mocking channel layer, MQTT client
- `channels.testing`: Test utilities for consumers
- **Mosquitto MQTT broker**: Lightweight broker for integration tests

**Manual Testing**:
- Use `mosquitto_pub` CLI to publish test messages
- Use browser console WebSocket API to connect manually
- Use Postman or `websocat` CLI tool for WebSocket testing

---

## Summary of Decisions

| Area | Decision | Key Technology |
|------|----------|----------------|
| **Real-time Infrastructure** | Django Channels + Redis | `channels`, `channels-redis` |
| **MQTT Client** | paho-mqtt persistent connection | `paho-mqtt` |
| **ML Inference** | In-memory singleton, thread-safe | `joblib`, `tensorflow` |
| **WebSocket Auth** | JWT in query parameter | `djangorestframework-simplejwt` |
| **Message Format** | JSON (not MessagePack) | Native JSON |
| **MQTT Schema** | Strict validation, required fields | JSON schema |
| **Error Handling** | Exponential backoff MQTT, graceful WebSocket | Custom logic |
| **Broadcasting** | Channel groups with patient ID | Django Channels groups |
| **Performance** | Direct writes (batch if needed) | Django ORM `bulk_create` |
| **Testing** | pytest + mocking + integration tests | `pytest-django`, `pytest-asyncio` |

---

## Dependencies to Add

```
# requirements.txt additions
channels==4.0.0
channels-redis==4.1.0
paho-mqtt==1.6.1
redis==5.0.1
```

**External Services Required**:
- Redis server (local): `redis-server` (default port 6379)
- MQTT broker (remote or local): Mosquitto, EMQX, or AWS IoT Core

---

## Next Steps

1. Proceed to **Phase 1: Design & Contracts**
   - Create `data-model.md` with BiometricSession extensions
   - Create `contracts/websocket-messages.yaml` with message schemas
   - Create `quickstart.md` with integration test scenarios

2. After Phase 1, run `/speckit.tasks` to generate task breakdown

3. Implementation order:
   - Setup Django Channels + Redis
   - Implement MQTT subscriber (User Story 1)
   - Implement WebSocket consumers (User Story 2)
   - Integrate ML predictions (User Story 3)
