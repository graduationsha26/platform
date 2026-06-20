# Implementation Plan: Analytics and Reporting

**Feature Branch**: `003-analytics-reporting`
**Created**: 2026-02-15
**Spec File**: [spec.md](./spec.md)

## Technical Context

### Tech Stack (from Constitution)

**Backend** (Python):
- Django 5.x + Django REST Framework
- Database: Supabase PostgreSQL (remote)
- Testing: pytest
- Dependencies: Existing BiometricSession model from Feature 002

**Required Libraries**:
- **reportlab** or **WeasyPrint** - PDF generation library
- **matplotlib** or **plotly** - Chart generation for PDFs
- **Pillow** - Image processing for chart embedding
- **numpy** - Statistical calculations
- **pandas** (optional) - Data aggregation helper

**Frontend** (JavaScript/React):
- React 18+ with Vite
- Recharts - For displaying statistics in UI (if implementing frontend visualization)
- Tailwind CSS

### Known Technology

**Database Schema**:
- Existing: `BiometricSession` model with `sensor_data` (tremor_intensity, frequency, timestamps), `ml_prediction`, `session_start`, `session_duration`
- New: No new models needed - analytics computed on-demand from existing data

**API Patterns**:
- RESTful endpoints
- JSON request/response
- JWT authentication
- Pagination for large result sets

**PDF Generation**:
- Library: WeasyPrint (HTML/CSS to PDF) or ReportLab (programmatic PDF)
- Charts: Generate matplotlib/plotly charts as PNG images, embed in PDF
- Templates: HTML templates for report layout (if using WeasyPrint)

### Unknowns / Research Needed

**RESOLVED** (see research.md):
- PDF library choice (WeasyPrint vs ReportLab)
- Chart generation approach (matplotlib vs plotly)
- Statistics calculation optimization (raw queries vs ORM)
- Baseline definition for tremor reduction calculation
- Temporary file management for PDFs

## Constitution Check

### Principle I: Monorepo Architecture ✅ PASS
- Analytics endpoints in `backend/analytics/` app
- Frontend visualization components in `frontend/src/components/analytics/` (if needed)
- Contracts in `specs/003-analytics-reporting/contracts/`

**Verdict**: Compliant - follows monorepo structure

### Principle II: Tech Stack Immutability ✅ PASS
- Backend: Django + DRF (no new frameworks)
- Database: Supabase PostgreSQL (existing)
- Frontend: React + Vite + Recharts (if adding UI)
- New dependencies: reportlab/WeasyPrint, matplotlib (Python libraries, compatible with Django)

**Verdict**: Compliant - all additions are Python libraries compatible with existing Django stack

### Principle III: Database Sovereignty ✅ PASS
- Uses existing Supabase PostgreSQL database
- No new databases required
- Reads from existing BiometricSession table
- No caching layer needed (statistics computed on-demand)

**Verdict**: Compliant - uses existing Supabase PostgreSQL only

### Principle IV: Authentication & Authorization ✅ PASS
- JWT authentication (existing from Feature 001)
- Role-based access control:
  - Doctors: Access statistics for assigned patients
  - Patients: Access only their own statistics
- Uses existing CustomUser roles and DoctorPatientAssignment

**Verdict**: Compliant - uses existing JWT + RBAC system

### Principle V: API Standards ✅ PASS
- RESTful endpoints: `/api/analytics/stats/`, `/api/analytics/reports/`
- JSON responses for statistics
- Binary response (PDF file) for report downloads
- Standard HTTP status codes (200, 400, 401, 403, 404, 500)
- snake_case for JSON keys

**Verdict**: Compliant - follows established API conventions

### Principle VI: Real-Time & Integration ✅ PASS
- No real-time requirements for analytics (on-demand queries acceptable)
- Reads existing MQTT-collected data from BiometricSession
- No new MQTT subscriptions needed

**Verdict**: Compliant - integrates with existing real-time data

### Principle VII: Development Environment ✅ PASS
- Local development: `python manage.py runserver`
- Configuration: `.env` file for any new settings
- No Docker, no production config

**Verdict**: Compliant - maintains local development approach

**Overall Constitution Compliance**: ✅ ALL PRINCIPLES PASS

## Project Structure

```
backend/
├── analytics/              # NEW Django app for analytics
│   ├── __init__.py
│   ├── apps.py
│   ├── views.py            # API views for statistics and reports
│   ├── serializers.py      # Statistics response serializers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── statistics.py   # Statistics calculation logic
│   │   └── report_generator.py  # PDF generation logic
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── calculations.py # Statistical calculations (avg, dominant freq)
│   │   └── charts.py       # Chart generation for PDFs
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_statistics.py
│   │   └── test_report_generator.py
│   └── urls.py             # Analytics URL routing
│
├── tremoai_backend/
│   ├── settings.py         # Add 'analytics' to INSTALLED_APPS
│   └── urls.py             # Include analytics.urls
│
├── media/                  # EXISTING - temporary PDF storage
│   └── reports/            # NEW - temporary PDF files
│
└── requirements.txt        # Add reportlab, matplotlib, pillow

frontend/                   # OPTIONAL - if adding UI visualization
├── src/
│   ├── components/
│   │   └── analytics/      # NEW (optional)
│   │       ├── StatisticsView.jsx
│   │       └── ReportViewer.jsx
│   └── services/
│       └── analyticsApi.js # NEW (optional)
```

## Complexity Tracking

### Estimated Implementation Effort

**Phase 1: Statistics Endpoint** (User Story 1 - P1) - **MEDIUM**
- **Effort**: 12-16 hours
- **Complexity**: Medium
  - Database queries with date filtering
  - Statistical calculations (average, dominant frequency, tremor reduction)
  - Grouping logic (by session vs by day)
  - Edge case handling (missing data, insufficient sessions)
- **Dependencies**: BiometricSession model, Patient model, Device model
- **Risk**: Performance with large datasets (100+ sessions)

**Phase 2: PDF Generation** (User Story 2 - P2) - **HIGH**
- **Effort**: 16-24 hours
- **Complexity**: High
  - PDF library integration (WeasyPrint or ReportLab)
  - Chart generation (matplotlib)
  - Template design for reports
  - Image embedding in PDFs
  - File cleanup and temporary storage
- **Dependencies**: Statistics service from Phase 1
- **Risk**: PDF file size control, chart rendering quality

**Phase 3: Report Customization** (User Story 3 - P3) - **LOW-MEDIUM**
- **Effort**: 6-8 hours
- **Complexity**: Low-Medium
  - Parameter validation
  - Conditional report sections
  - Chart type selection
- **Dependencies**: PDF generation from Phase 2
- **Risk**: Minimal (extends existing functionality)

**Total Estimated Effort**: 34-48 hours (approximately 1 week for single developer)

### Technical Risks

1. **Performance**: Statistics queries for large datasets (500+ sessions) may be slow
   - **Mitigation**: Use database aggregation functions, add indexes on date fields

2. **PDF File Size**: Charts and images may inflate PDF size beyond 5MB
   - **Mitigation**: Compress images before embedding, limit chart resolution

3. **Tremor Reduction Baseline**: Defining "baseline" for reduction calculation
   - **Mitigation**: Use first 3 sessions as baseline (see research.md)

4. **Concurrent PDF Generation**: Multiple doctors generating reports simultaneously
   - **Mitigation**: Use unique temporary filenames, implement file cleanup task

## Phase 0: Research Findings

**See**: [research.md](./research.md) for detailed research on:
- PDF library selection (WeasyPrint vs ReportLab)
- Chart generation approach
- Statistics optimization strategies
- Baseline calculation methodology
- File management best practices

**Key Decisions**:
1. **PDF Library**: ReportLab (better control, no HTML/CSS dependency)
2. **Charts**: matplotlib (standard Python library, good PDF integration)
3. **Statistics**: Django ORM with aggregation (balance of simplicity and performance)
4. **Baseline**: First 3 sessions or single earliest session if < 3 total
5. **File Cleanup**: Delete after download + daily cleanup task

## Phase 1: Design Artifacts

**See**:
- [data-model.md](./data-model.md) - Entity definitions (TremorStatistics, PDFReport)
- [contracts/analytics-api.yaml](./contracts/analytics-api.yaml) - OpenAPI spec for statistics and report endpoints
- [quickstart.md](./quickstart.md) - Integration test scenarios

**Data Model Summary**:
- **TremorStatistics** (computed entity): avg_amplitude, dominant_freq, tremor_reduction_pct, period, session_count
- **No new database models** - statistics computed on-demand from BiometricSession

**API Endpoints**:
- `GET /api/analytics/stats/?patient_id=X&group_by=day|session&start_date=Y&end_date=Z` - Statistics query
- `POST /api/analytics/reports/` - Generate PDF report (returns file or download URL)

## Implementation Notes

### MVP Strategy (User Story 1 Only)
**MVP Scope**: Statistics endpoint with session and daily grouping
- Delivers clinical value immediately (doctors see trends)
- Does not require PDF generation complexity
- Can be tested independently with existing BiometricSession data
- Estimated: 12-16 hours

**Post-MVP**: Add PDF generation (US2) and customization (US3) incrementally

### Testing Strategy
- **Unit tests**: Statistics calculations, baseline logic, aggregation
- **Integration tests**: Full endpoint tests with sample BiometricSession data
- **Performance tests**: Query time with 365 days of data, 100+ sessions
- **PDF tests**: File generation, size validation, content verification

### Deployment Notes
- No new infrastructure needed (uses existing Django server)
- Add `media/reports/` directory to `.gitignore`
- Configure periodic cleanup task (Django management command)
- Document PDF library installation in README

## Next Steps

1. ✅ Complete research (research.md)
2. ✅ Define data model (data-model.md)
3. ✅ Design API contracts (contracts/analytics-api.yaml)
4. ✅ Create test scenarios (quickstart.md)
5. → Generate task breakdown (`/speckit.tasks`)
6. → Begin implementation (`/speckit.implement`)
