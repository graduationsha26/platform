# Quickstart: Frontend Patient Role Cleanup (E-1.5 + E-1.6)

**Branch**: `016-frontend-patient-cleanup`
**Date**: 2026-02-18

This document describes integration scenarios to validate the changes after implementation.

---

## Scenario 1: Registration — Only Doctor and Admin Role Options Visible

**Goal**: Verify the "Patient" option is gone and "Admin" is present.

```
1. Open http://localhost:5173/register
2. Scroll to the "I am a:" role selector
3. Count the radio button options

Expected:
- "Doctor" option exists ✅
- "Admin" option exists ✅
- "Patient" option does NOT exist ✅
- Default selected option is "Doctor" ✅
```

---

## Scenario 2: Registration — Doctor Role Submits Successfully

**Goal**: Verify Doctor registration still works end-to-end.

```
POST /api/auth/register/
Form: { name: "Dr. Test", email: "doctor@example.com", password: "Test1234", role: "doctor" }
→ Redirected to /login with success message
```

---

## Scenario 3: Registration — Admin Role Submits Successfully

**Goal**: Verify Admin registration works (new option).

```
Form: { name: "Admin User", email: "admin@example.com", password: "Test1234", role: "admin" }
→ Redirected to /login with success message
→ Admin user can log in with returned JWT
→ POST /api/auth/login/ with admin credentials → 200 OK, role: "admin" in token
```

---

## Scenario 4: Post-Login Redirect — Admin Goes to Doctor Dashboard

**Goal**: Verify admin is redirected to /doctor/dashboard (not /patient/dashboard).

```
POST /api/auth/login/ { email: "admin@example.com", password: "Test1234" }
→ 200 OK, token with role: "admin"
→ Frontend redirects to /doctor/dashboard ✅
→ /patient/dashboard is NOT visited ✅
```

---

## Scenario 5: Removed Route — /patient/dashboard Redirects to Login

**Goal**: Verify the deleted route does not render a patient page.

```
1. While unauthenticated, navigate directly to http://localhost:5173/patient/dashboard
→ Redirected to /login ✅ (catch-all route + ProtectedRoute)

2. While authenticated as doctor, navigate to http://localhost:5173/patient/dashboard
→ Redirected to /login ✅ (catch-all route — no route defined)
```

---

## Scenario 6: Navigation — No Patient Links in Sidebar

**Goal**: Verify no /patient/ links appear in the doctor or admin navigation menu.

```
1. Log in as doctor → view sidebar
→ Menu items: Dashboard, Patients, Analytics, Reports, Settings
→ All paths are /doctor/* ✅
→ No /patient/* items ✅

2. Log in as admin → view sidebar
→ Menu items: same as doctor (admin shares doctor menu) ✅
→ No /patient/* items ✅
```

---

## Scenario 7: Dead Code Verification — No Patient References in Role Logic

**Goal**: Confirm all patient references are removed from role-conditional code.

```bash
# Run from frontend/ directory
grep -r "patient" src/utils/roleHelpers.js
→ (no output) ✅

grep -r "patient" src/utils/validators.js
→ (no output) ✅

grep -r "PatientDashboard" src/
→ (no output) ✅

grep -r "/patient/" src/
→ (no output) ✅
```

---

## Validation Checklist

- [ ] Registration page shows exactly 2 role options: "Doctor" and "Admin"
- [ ] "Patient" option is completely absent from registration page
- [ ] Registration default is "Doctor" (not Patient or empty)
- [ ] Doctor registration → 201 → redirected to /login
- [ ] Admin registration → 201 → redirected to /login
- [ ] Admin login → redirected to /doctor/dashboard (not /patient/dashboard)
- [ ] GET /patient/dashboard → redirected to /login (route removed)
- [ ] No /patient/ links appear in doctor or admin navigation
- [ ] `grep -r "PatientDashboard" frontend/src/` → no results
- [ ] `grep -r "/patient/" frontend/src/` → no results
