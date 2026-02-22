# Quickstart: Remove Flex Fields from BiometricReading API Layer

**Branch**: `018-clean-biometric-api` | **Date**: 2026-02-18

This guide shows how to verify the feature is correctly implemented.

---

## Scenario 1: Verify Serializer Has No Flex Fields

After implementation, the `BiometricReadingSerializer` in `backend/biometrics/serializers.py` should not mention any flex field.

```bash
grep -n "flex_" backend/biometrics/serializers.py
# Expected: no output (zero matches)
```

Also verify the declared fields are exactly the expected nine:

```bash
grep -A 5 "class BiometricReadingSerializer" backend/biometrics/serializers.py
# Expected: fields = ['id', 'patient_id', 'timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ']
```

---

## Scenario 2: Verify ViewSet Has No Flex References

```bash
grep -n "flex_" backend/biometrics/views.py
# Expected: no output (zero matches)
```

---

## Scenario 3: List Endpoint Returns No Flex Fields

Start the development server and make an authenticated request:

```bash
cd backend && python manage.py runserver
```

```bash
# Get a JWT token first (replace credentials):
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"doctor@example.com","password":"testpass"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

# List biometric readings:
curl -s http://localhost:8000/api/biometric-readings/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

**Expected response shape** (no flex fields):
```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

Or if readings exist:
```json
{
  "results": [
    {
      "id": 1,
      "patient_id": 5,
      "timestamp": "2026-02-18T12:00:00Z",
      "aX": 0.12,
      "aY": -0.05,
      "aZ": 9.81,
      "gX": 0.01,
      "gY": 0.02,
      "gZ": -0.01
    }
  ]
}
```

**Verify absent fields**: `flex_1`, `flex_2`, `flex_3`, `flex_4`, `flex_5` must not appear in any result object.

---

## Scenario 4: Django Shell Serializer Inspection

```python
# python manage.py shell
from biometrics.serializers import BiometricReadingSerializer

s = BiometricReadingSerializer()
fields = list(s.fields.keys())
print("Fields:", fields)

for f in ['flex_1', 'flex_2', 'flex_3', 'flex_4', 'flex_5']:
    assert f not in fields, f"FAIL: {f} present in serializer!"

expected = {'id', 'patient_id', 'timestamp', 'aX', 'aY', 'aZ', 'gX', 'gY', 'gZ'}
assert set(fields) == expected, f"FAIL: unexpected fields {set(fields) - expected}"
print("PASS: BiometricReadingSerializer has no flex fields")
```

---

## Scenario 5: URL Registration Verification

```python
# python manage.py shell
from django.urls import reverse
url = reverse('biometric-reading-list')
print(f"Registered at: {url}")
# Expected: /api/biometric-readings/
```

---

## Scenario 6: Final Audit

```bash
grep -r "flex_[1-5]" backend/biometrics/serializers.py backend/biometrics/views.py backend/biometrics/reading_urls.py 2>/dev/null
# Expected: no output (zero matches in application code)
```
