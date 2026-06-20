# Quickstart: Personalized Doctor Dashboard Greeting

**Branch**: `001-doctor-greeting` | **Date**: 2026-06-14

## Integration Scenarios

### Scenario 1: Doctor logs in and sees personalized greeting

**Flow**:
1. Doctor submits credentials to `POST /api/auth/login/`
2. Response includes `user.first_name` and `user.last_name`
3. `AuthContext` stores the user object
4. `TopBar` reads `user` from `useAuth()`, renders: **"Dr. Ahmed Hassan"** with role "doctor" below

**Prerequisite**: Doctor account must exist with `first_name` and `last_name` set (required at registration).

---

### Scenario 2: Doctor refreshes the page — greeting persists

**Flow**:
1. On page load, `AuthContext.initializeAuth()` reads from `localStorage`
2. Both `token` and `user` (including `first_name`/`last_name`) are restored
3. TopBar renders the same greeting without any additional API call

**Prerequisite**: Doctor was previously logged in and hasn't cleared storage.

---

### Scenario 3: Fetching current profile via GET /api/auth/me/

**Request**:
```http
GET /api/auth/me/ HTTP/1.1
Authorization: Bearer <access_token>
```

**Response (200 OK)**:
```json
{
  "id": 1,
  "email": "doctor@example.com",
  "first_name": "Ahmed",
  "last_name": "Hassan",
  "role": "doctor",
  "date_joined": "2026-01-01T00:00:00Z",
  "last_login": "2026-06-14T10:00:00Z"
}
```

**Unauthenticated request response (401)**:
```json
{
  "error": "Authentication credentials were not provided."
}
```

---

### Scenario 4: Fallback — name fields empty or missing

**Condition**: `user.first_name` or `user.last_name` is an empty string.

**TopBar behavior**: Falls back to displaying "Doctor" as the name label so the greeting is never blank. The role sub-label continues to show "doctor" regardless.

---

## Manual Test Steps

After implementation, verify with these manual steps:

1. Start backend: `python manage.py runserver` in `backend/`
2. Start frontend: `npm run dev` in `frontend/`
3. Log in as a test doctor account
4. Verify the TopBar shows "Dr. [First] [Last]" and "doctor" role
5. Refresh the page — verify the greeting persists
6. Call `GET /api/auth/me/` with a valid token (e.g. via curl or Postman) — verify `first_name` and `last_name` are in the response
7. Call `GET /api/auth/me/` without a token — verify 401 response

## Test Doctor Account

Use an account created via registration with non-empty `first_name` and `last_name`. Refer to `backend/create_test_users.py` if test accounts need to be seeded.
