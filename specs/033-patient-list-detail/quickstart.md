# Quickstart: Patient List & Detail Pages

**Branch**: `033-patient-list-detail` | **Date**: 2026-02-20

---

## Integration Points

| Layer | File | What it does |
|-------|------|--------------|
| Backend | `backend/patients/serializers.py` | `PatientListSerializer` + `last_session_date` field |
| Backend | `backend/biometrics/serializers.py` | `BiometricSessionListSerializer` + `ml_prediction_severity` |
| Frontend service | `frontend/src/services/patientService.js` | All patient + session API calls |
| Frontend hook | `frontend/src/hooks/usePatients.js` | List state: patients, pagination, search |
| Frontend hook | `frontend/src/hooks/usePatient.js` | Detail state: profile + paginated sessions |
| Frontend component | `frontend/src/components/patients/PatientTable.jsx` | Searchable, paginated patient table |
| Frontend component | `frontend/src/components/patients/PatientForm.jsx` | Shared create/edit form |
| Frontend component | `frontend/src/components/patients/SessionHistoryList.jsx` | Session history table |
| Frontend component | `frontend/src/components/common/Pagination.jsx` | Reusable pagination control |
| Frontend pages | `frontend/src/pages/Patient*.jsx` (×4) | List, Detail, Create, Edit pages |
| Frontend routes | `frontend/src/routes/AppRoutes.jsx` | 4 new protected routes |

---

## Scenario 1: Doctor browses and searches the patient list

```
1. Doctor navigates to /doctor/patients

2. PatientListPage mounts
   → usePatients() fires
   → patientService.getPatients({ page: 1, pageSize: 20 })
   → GET /api/patients/?page=1&page_size=20

3. PatientViewSet.list()
   → queryset filtered to doctor's assigned patients
   → PatientListSerializer (includes last_session_date per patient)
   → Response 200: { count: 12, results: [...] }

4. PatientTable renders:
   | Full Name      | Date of Birth | Last Session        | |
   |----------------|---------------|---------------------|-|
   | Ahmed Hassan   | 1958-03-12    | Feb 18, 2026 14:22 | → |
   | ...            |               |                     |   |

5. Doctor types "ahmed" in search field
   → 300ms debounce → patientService.getPatients({ name: 'ahmed', page: 1 })
   → GET /api/patients/?name=ahmed&page=1
   → Table updates to show matching patients only
```

---

## Scenario 2: Doctor views patient detail and session history

```
1. Doctor clicks patient row → navigates to /doctor/patients/1

2. PatientDetailPage mounts
   → usePatient(1) fires two parallel requests:
     a. patientService.getPatient(1)  → GET /api/patients/1/
     b. patientService.getSessions(1, { page: 1, pageSize: 10 })
        → GET /api/biometric-sessions/?patient=1&page=1&page_size=10

3. Both responses arrive:
   a. Profile card renders: name, DOB, contact info, medical notes, device status
   b. SessionHistoryList renders:
      | Date & Time            | Duration | ML Severity |
      |------------------------|----------|-------------|
      | Feb 18, 2026 14:22    | 15m 30s  | Moderate    |
      | Feb 15, 2026 09:10    | 12m 00s  | Mild        |
      ...
      [1] [2] [3]  ← pagination

4. Doctor clicks page 2 → getSessions(1, { page: 2 }) → next 10 sessions load
```

---

## Scenario 3: Doctor creates a new patient

```
1. Doctor clicks "Add Patient" button on list page
   → navigates to /doctor/patients/new

2. PatientCreatePage renders PatientForm with empty fields

3. Doctor fills: full_name="Fatima Saad", date_of_birth="1965-07-20"
   (contact_phone, contact_email, medical_notes left empty)

4. Doctor clicks "Save"
   → patientService.createPatient({ full_name: "Fatima Saad", date_of_birth: "1965-07-20" })
   → POST /api/patients/
   → PatientViewSet.perform_create():
     - Sets created_by = request.user
     - Creates DoctorPatientAssignment (doctor ↔ new patient)
   → Response 201: { id: 13, full_name: "Fatima Saad", ... }

5. Frontend navigates to /doctor/patients/13 (patient detail page)
```

---

## Scenario 4: Doctor edits a patient's profile

```
1. Doctor is on /doctor/patients/1
   → clicks "Edit" button → navigates to /doctor/patients/1/edit

2. PatientEditPage mounts
   → fetches GET /api/patients/1/ to pre-populate form
   → PatientForm renders with existing values filled in

3. Doctor changes medical_notes and clicks "Save"
   → patientService.updatePatient(1, { medical_notes: "Updated notes..." })
   → PATCH /api/patients/1/
   → Response 200: updated patient

4. Frontend navigates back to /doctor/patients/1
   → detail page shows updated notes
```

---

## Scenario 5: Validation errors on form submission

```
Doctor submits create form with:
  - full_name: "" (empty)
  - date_of_birth: "2030-01-01" (future date)

→ Frontend validates before API call:
  - "Full name is required" displayed inline
  - "Date of birth cannot be in the future" displayed inline
  - No API call is made

Doctor fixes errors and resubmits → 201 Created
```

---

## Scenario 6: Access denied — wrong patient

```
Doctor navigates to /doctor/patients/999 (not their patient)

→ GET /api/patients/999/
→ PatientViewSet.get_queryset() excludes unassigned patients
→ Response 404 (patient not in queryset = not found from this doctor's perspective)

→ PatientDetailPage shows: "Patient not found or access denied."
```
