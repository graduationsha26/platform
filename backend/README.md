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
