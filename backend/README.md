# TremoAI Backend API

Django REST API backend for the TremoAI platform - a smart wearable glove for Parkinson's tremor suppression monitoring.

## Features

- **Authentication**: JWT-based authentication with role-based access control (doctor/patient)
- **Patient Management**: CRUD operations for patient profiles with doctor assignment
- **Device Management**: Register and pair glove devices to patients
- **Biometric Data**: Store and retrieve sensor session data with aggregation support
- **Real-time Support**: Django Channels integration for WebSocket connections (future)
- **API Documentation**: Auto-generated Swagger/OpenAPI docs

## Tech Stack

- **Framework**: Django 5.x + Django REST Framework
- **Database**: Supabase PostgreSQL (remote)
- **Authentication**: JWT tokens (djangorestframework-simplejwt)
- **API Docs**: drf-spectacular
- **Filtering**: django-filter
- **CORS**: django-cors-headers

## Prerequisites

- Python 3.10+
- PostgreSQL (Supabase account)
- pip or pipenv

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root (not in backend/):

```env
# Database
DATABASE_URL=postgresql://user:password@host:port/database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT
JWT_SECRET_KEY=your-jwt-secret-key

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

**Important**: Use the `.env.example` file as a template.

### 3. Run Database Migrations

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Test Users (Optional)

```bash
python manage.py create_test_users
```

This creates:
- Doctor: `doctor@test.com` / `doctor123`
- Patient: `patient@test.com` / `patient123`

### 5. Create Superuser (for Django Admin)

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

### 6. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

### 7. Run MQTT Subscriber (Feature 002: Real-Time Pipeline)

**For real-time tremor data collection**, run the MQTT subscriber in a **separate terminal**:

```bash
cd backend
python manage.py run_mqtt_subscriber
```

**Prerequisites**:
- MQTT broker running (e.g., Mosquitto on localhost:1883)
- Redis server running (localhost:6379) for Django Channels
- Environment variables configured in `.env`:
  - `MQTT_BROKER_URL` (e.g., `mqtt://localhost:1883`)
  - `MQTT_USERNAME`
  - `MQTT_PASSWORD`
  - `REDIS_URL` (e.g., `redis://localhost:6379/0`)

The MQTT subscriber will:
- Connect to the MQTT broker
- Subscribe to `devices/+/data` topics
- Validate incoming sensor data
- Store data to BiometricSession in PostgreSQL
- Broadcast data to WebSocket clients (when Phase 4 is complete)

Press `Ctrl+C` to stop the MQTT subscriber.

### 8. Set Up ML Models (Feature 002: Real-Time Pipeline - Optional)

**For AI-powered tremor severity predictions**, place trained ML models in `backend/models/` directory:

**Required Model**:
- `tremor_classifier.pkl` - scikit-learn model for tremor severity classification

**Optional Model**:
- `tremor_classifier.h5` - TensorFlow/Keras model (alternative to .pkl)

**Model Format Requirements**:

**scikit-learn model** (`.pkl`):
- Must be a classifier with `predict()` and `predict_proba()` methods
- Input: numpy array of shape `(1, 4)` with features:
  - `tremor_intensity_avg` (float 0.0-1.0)
  - `tremor_intensity_max` (float 0.0-1.0)
  - `tremor_intensity_std` (float)
  - `frequency` (float, Hz)
- Output: class index (0=mild, 1=moderate, 2=severe)

**TensorFlow/Keras model** (`.h5`):
- Must be a compiled Keras model
- Input: same as sklearn (4 features)
- Output: probability distribution over 3 classes [mild, moderate, severe]

**Prediction Output Schema**:
```json
{
  "severity": "mild" | "moderate" | "severe",
  "confidence": 0.0-1.0
}
```

**How ML Predictions Work**:
1. MQTT client receives sensor data from glove device
2. ML service extracts features (tremor intensity stats + frequency)
3. Model predicts severity class and confidence score
4. Prediction stored in `BiometricSession.ml_prediction` field
5. Prediction broadcast to WebSocket clients in real-time

**No Model?** The system works without ML models - tremor data is still collected and streamed. Predictions will be `null` if models are missing.

**Installing ML Dependencies** (if using models):
```bash
# For scikit-learn models
py -m pip install scikit-learn joblib

# For TensorFlow models
py -m pip install tensorflow
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login and get JWT tokens
- `POST /api/auth/refresh/` - Refresh access token

### Patients
- `GET /api/patients/` - List patients (paginated, 20 per page)
- `POST /api/patients/` - Create patient
- `GET /api/patients/{id}/` - Get patient details
- `PUT /api/patients/{id}/` - Update patient
- `GET /api/patients/search/?name=...` - Search patients by name
- `POST /api/patients/{id}/assign-doctor/` - Assign doctor to patient

### Devices
- `GET /api/devices/` - List devices (paginated, 50 per page)
- `POST /api/devices/` - Register device
- `GET /api/devices/{id}/` - Get device details
- `POST /api/devices/{id}/pair/` - Pair device to patient
- `POST /api/devices/{id}/unpair/` - Unpair device
- `PUT /api/devices/{id}/status/` - Update device status

### Biometric Sessions
- `GET /api/biometric-sessions/` - List sessions (paginated, 50 per page)
- `POST /api/biometric-sessions/` - Create session
- `GET /api/biometric-sessions/{id}/` - Get session details
- `GET /api/biometric-sessions/aggregate/` - Get aggregated metrics

Query parameters for sessions:
- `patient` - Filter by patient ID
- `device` - Filter by device ID
- `start_date` - Filter by start date (ISO format)
- `end_date` - Filter by end date (ISO format)

### Analytics and Reporting

**Feature 003: Analytics and Reporting** provides statistical analysis and PDF report generation for tremor data.

#### Statistics Endpoint

- `GET /api/analytics/stats/` - Get aggregated tremor statistics

**Query Parameters**:
- `patient_id` (required) - Patient ID to analyze
- `group_by` (optional) - Grouping level: `session` or `day` (default: `day`)
- `start_date` (optional) - Start date (ISO format YYYY-MM-DD)
- `end_date` (optional) - End date (ISO format YYYY-MM-DD)
- `page` (optional) - Page number (default: 1)
- `page_size` (optional) - Results per page (default: 50, max: 100)

**Response**:
- Paginated statistics with baseline comparison
- Average tremor amplitude (0.0-1.0)
- Dominant frequency (Hz)
- Tremor reduction percentage vs baseline
- ML severity summary (mild/moderate/severe counts)

**Access Control**:
- Doctors: Can access stats for all assigned patients
- Patients: Can only access their own statistics

**Example**:
```bash
curl -X GET "http://localhost:8000/api/analytics/stats/?patient_id=4&group_by=day&start_date=2026-01-15&end_date=2026-02-15" \
  -H "Authorization: Bearer $TOKEN"
```

#### PDF Report Generation

- `POST /api/analytics/reports/` - Generate downloadable PDF report

**Request Body** (JSON):
```json
{
  "patient_id": 4,
  "start_date": "2026-01-15",
  "end_date": "2026-02-15",
  "include_charts": true,
  "include_ml_summary": true
}
```

**Response**: PDF file (application/pdf) as attachment

**Report Contents**:
- Patient information header
- Statistics summary table
- Tremor amplitude trend chart
- Tremor reduction vs baseline chart
- ML severity distribution (if available)

**File Constraints**:
- Maximum size: 5MB
- Generation time: < 10 seconds
- Temporary files auto-deleted after download

**Example**:
```bash
curl -X POST http://localhost:8000/api/analytics/reports/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"patient_id": 4, "start_date": "2026-01-15", "end_date": "2026-02-15"}' \
  --output report.pdf
```

**Management Command** - Cleanup old reports:
```bash
py manage.py cleanup_temp_reports  # Deletes PDFs older than 24 hours
```

### WebSocket Connections (Real-Time Data)

**Feature 002: Real-Time Pipeline** provides WebSocket endpoints for streaming live tremor data from glove devices.

#### WebSocket Endpoint

**URL**: `ws://localhost:8000/ws/tremor-data/{patient_id}/`

**Authentication**: JWT token required as query parameter

**URL Format**:
```
ws://localhost:8000/ws/tremor-data/1/?token=<YOUR_JWT_ACCESS_TOKEN>
```

#### Message Types

**1. Status Message** (sent on connection):
```json
{
  "type": "status",
  "status": "connected",
  "message": "Successfully connected to patient 1 tremor data stream",
  "timestamp": "2024-02-15T10:30:00Z"
}
```

**2. Tremor Data Message** (real-time sensor data):
```json
{
  "type": "tremor_data",
  "patient_id": 1,
  "device_serial": "GLV-2024-A001",
  "timestamp": "2024-02-15T10:30:15Z",
  "tremor_intensity": [0.25, 0.30, 0.28, 0.32],
  "frequency": 4.5,
  "session_duration": 1000,
  "prediction": null,
  "received_at": "2024-02-15T10:30:15.123Z"
}
```

**3. Ping/Pong** (keepalive):
```json
// Client sends:
{"type": "ping", "timestamp": "2024-02-15T10:30:00Z"}

// Server responds:
{"type": "pong", "timestamp": "2024-02-15T10:30:00.100Z"}
```

**4. Error Message**:
```json
{
  "type": "error",
  "error_code": "unauthorized",
  "error_message": "Invalid or expired JWT token",
  "timestamp": "2024-02-15T10:30:00Z"
}
```

#### JavaScript Example

```javascript
// 1. Get JWT token from login response
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";

// 2. Connect to WebSocket with token
const patientId = 1;
const ws = new WebSocket(`ws://localhost:8000/ws/tremor-data/${patientId}/?token=${token}`);

// 3. Handle connection open
ws.onopen = () => {
  console.log("WebSocket connected");

  // Send ping every 30 seconds (keepalive)
  setInterval(() => {
    ws.send(JSON.stringify({
      type: "ping",
      timestamp: new Date().toISOString()
    }));
  }, 30000);
};

// 4. Handle incoming messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case "status":
      console.log("Status:", data.message);
      break;

    case "tremor_data":
      console.log("Tremor data received:", data);
      // Update UI with real-time data
      updateChart(data.tremor_intensity, data.timestamp);
      break;

    case "pong":
      console.log("Pong received");
      break;

    case "error":
      console.error("WebSocket error:", data.error_message);
      break;
  }
};

// 5. Handle errors
ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

// 6. Handle connection close
ws.onclose = (event) => {
  console.log("WebSocket closed:", event.code, event.reason);

  // Reconnect logic (optional)
  if (event.code === 4401) {
    console.error("Authentication failed - token invalid or expired");
  } else if (event.code === 4403) {
    console.error("Access forbidden - user does not have access to this patient");
  }
};
```

#### Access Control

- **Patient users**: Can only connect to their own data (patient_id must match their user)
- **Doctor users**: Can connect to data for patients assigned to them
- **WebSocket close codes**:
  - `4401`: Unauthorized (invalid/missing JWT token)
  - `4403`: Forbidden (no access to patient)
  - `4500`: Internal server error

#### Prerequisites for WebSocket

- Redis server running (`redis-server`)
- MQTT subscriber running (`python manage.py run_mqtt_subscriber`)
- Django Channels configured (automatic with Feature 002)

## Project Structure

```
backend/
├── tremoai_backend/         # Django project settings
│   ├── settings.py          # Configuration
│   ├── urls.py              # Root URL routing
│   └── exceptions.py        # Custom exception handler
├── authentication/          # User authentication app
│   ├── models.py            # CustomUser model
│   ├── serializers.py       # User serializers
│   ├── views.py             # Auth endpoints
│   └── permissions.py       # Role-based permissions
├── patients/                # Patient management app
│   ├── models.py            # Patient, DoctorPatientAssignment
│   ├── serializers.py       # Patient serializers
│   ├── views.py             # Patient CRUD endpoints
│   └── filters.py           # Search filters
├── devices/                 # Device management app
│   ├── models.py            # Device model
│   ├── serializers.py       # Device serializers
│   └── views.py             # Device endpoints
├── biometrics/              # Biometric data app
│   ├── models.py            # BiometricSession model
│   ├── serializers.py       # Session serializers
│   ├── views.py             # Session endpoints
│   └── aggregation.py       # Data aggregation utilities
├── requirements.txt         # Python dependencies
└── manage.py                # Django CLI
```

## Development

### Running Tests

```bash
python manage.py test
```

### Code Style

This project follows Django and PEP 8 conventions.

### Logging

Logs are stored in `backend/logs/django.log`. Log levels:
- Authentication: DEBUG
- Patients, Devices, Biometrics: INFO
- Django: INFO

### Database Migrations

After model changes:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Common Tasks

### Add a new API endpoint

1. Add route to app's `urls.py`
2. Create view in `views.py`
3. Add serializer if needed in `serializers.py`
4. Update permissions if needed
5. Run server to see endpoint in API docs

### Access Django Admin

1. Create superuser: `python manage.py createsuperuser`
2. Visit http://localhost:8000/admin/
3. Login with superuser credentials

### Reset Database

```bash
python manage.py flush
python manage.py migrate
python manage.py create_test_users
```

## Troubleshooting

### Database Connection Error

- Verify `DATABASE_URL` in `.env` is correct
- Check Supabase project is running
- Ensure IP address is allowed in Supabase settings

### Module Not Found Error

```bash
pip install -r requirements.txt
```

### Migration Errors

```bash
python manage.py migrate --run-syncdb
```

### CORS Errors

- Add frontend URL to `CORS_ALLOWED_ORIGINS` in `.env`
- Restart Django server

## Security Notes

- Never commit `.env` file
- Use strong `DJANGO_SECRET_KEY` and `JWT_SECRET_KEY` in production
- Set `DEBUG=False` in production
- Configure proper `ALLOWED_HOSTS` in production
- Review CORS settings before deployment

## Support

For issues or questions, refer to:
- Django Documentation: https://docs.djangoproject.com/
- DRF Documentation: https://www.django-rest-framework.org/
- Project Repository: (your repo URL)

## License

(Add your license here)
