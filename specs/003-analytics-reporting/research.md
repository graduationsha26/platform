# Technical Research: Analytics and Reporting

**Feature**: Analytics and Reporting (003)
**Created**: 2026-02-15
**Purpose**: Resolve technical unknowns and make informed implementation decisions

---

## Research Area 1: PDF Generation Library

### Decision
**Use ReportLab** for PDF generation

### Rationale
- **Direct PDF generation**: ReportLab creates PDFs programmatically without HTML/CSS intermediate step
- **Better control**: Precise positioning of elements, images, and charts
- **Battle-tested**: Industry standard for Python PDF generation since 2000
- **Django integration**: Well-documented integration with Django views
- **Performance**: Faster than HTML-to-PDF converters (no rendering engine overhead)
- **File size control**: Can optimize compression, image quality programmatically

### Alternatives Considered
1. **WeasyPrint**: HTML/CSS to PDF converter
   - **Pros**: Familiar web technologies, easier styling
   - **Cons**: Slower, larger file sizes, requires HTML template maintenance, CSS compatibility issues
   - **Why rejected**: Overhead of HTML rendering not justified for structured reports

2. **xhtml2pdf (pisa)**: Another HTML to PDF library
   - **Pros**: Simple Django integration
   - **Cons**: Limited CSS support, unmaintained, poor documentation
   - **Why rejected**: Development stalled, better alternatives available

3. **wkhtmltopdf**: Command-line HTML to PDF tool
   - **Pros**: Good rendering quality
   - **Cons**: External dependency, deployment complexity, slower
   - **Why rejected**: Violates "no Docker/no external tools" principle

### Implementation Notes
- Install: `reportlab==4.0.7` (stable release)
- API: `canvas.Canvas` for low-level control, `SimpleDocTemplate` for structured documents
- Charts: Embed matplotlib PNG images using `canvas.drawImage()`
- Templates: Python code defines layout (no separate template files)

---

## Research Area 2: Chart Generation Library

### Decision
**Use matplotlib** for chart generation

### Rationale
- **Standard library**: De facto standard for Python data visualization
- **PDF integration**: Native support for saving charts as PNG/PDF for embedding
- **Django compatibility**: Works seamlessly in Django views without rendering issues
- **Documentation**: Extensive examples for medical/clinical visualizations
- **Customization**: Full control over styling, labels, colors
- **Performance**: Fast generation of static charts (< 1 second per chart)

### Alternatives Considered
1. **Plotly**: Interactive plotting library
   - **Pros**: Beautiful interactive charts, web-friendly
   - **Cons**: Overkill for static PDF charts, larger file sizes, dependency overhead
   - **Why rejected**: Interactivity not needed for PDF reports

2. **Seaborn**: Statistical visualization library built on matplotlib
   - **Pros**: Cleaner default styles, statistical plots
   - **Cons**: Additional dependency, same underlying engine as matplotlib
   - **Why rejected**: matplotlib sufficient for line charts; can add seaborn later if needed

3. **Recharts** (frontend only): React charting library
   - **Pros**: Already in tech stack for frontend
   - **Cons**: Cannot be used in backend PDF generation
   - **Why rejected**: Not applicable to backend PDF generation

### Implementation Notes
- Install: `matplotlib==3.8.2` + `pillow==10.2.0` (image processing)
- Chart types: Line charts for trends, bar charts for comparisons
- Style: Clinical/professional theme (blue/gray palette, clear labels, grid lines)
- Export: Save as PNG (96 DPI for screen, 300 DPI if needed for print)
- Cleanup: Delete temp chart files after PDF generation

---

## Research Area 3: Statistics Calculation Optimization

### Decision
**Use Django ORM with database aggregation functions**

### Rationale
- **Simplicity**: Django ORM provides `aggregate()` and `annotate()` for SQL aggregation
- **Performance**: Database performs aggregation (faster than Python loops)
- **Maintainability**: ORM queries easier to read and maintain than raw SQL
- **Type safety**: Django ORM provides type hints and query validation
- **Sufficient performance**: For datasets up to 1000 sessions, ORM performance is acceptable

### Alternatives Considered
1. **Raw SQL queries**: Direct PostgreSQL queries with `cursor.execute()`
   - **Pros**: Maximum performance, full SQL power
   - **Cons**: Loss of ORM benefits, harder to maintain, SQL injection risks
   - **Why rejected**: Premature optimization; ORM sufficient for expected data volumes

2. **Pandas DataFrames**: Load data into pandas, compute aggregations
   - **Pros**: Powerful data manipulation, familiar API
   - **Cons**: Memory overhead (loads all data into RAM), additional dependency
   - **Why rejected**: Overkill for simple aggregations; database already does this

3. **Caching/pre-computation**: Store pre-computed statistics in database
   - **Pros**: Fastest query time
   - **Cons**: Complexity (cache invalidation), stale data risks, storage overhead
   - **Why rejected**: Added complexity not justified; on-demand calculation acceptable

### Implementation Examples

**Average amplitude by day**:
```python
from django.db.models import Avg, F
from django.db.models.functions import TruncDate

BiometricSession.objects.filter(
    patient_id=patient_id,
    session_start__range=(start_date, end_date)
).annotate(
    date=TruncDate('session_start')
).values('date').annotate(
    avg_amplitude=Avg('sensor_data__tremor_intensity__0')  # Simplified
).order_by('date')
```

**Note**: Actual implementation will iterate `sensor_data['tremor_intensity']` array and compute average in Python (JSONField aggregation limited in Django ORM).

**Performance Target**: < 3 seconds for 365 days of data per spec SC-001

---

## Research Area 4: Baseline Calculation for Tremor Reduction

### Decision
**Use first 3 sessions as baseline** (or all sessions if < 3 total)

### Rationale
- **Clinical validity**: Initial sessions represent untreated/baseline tremor state
- **Statistical stability**: 3 sessions reduce noise from single session variability
- **Simple to explain**: Doctors understand "improvement vs initial state"
- **Computationally simple**: Always look at earliest sessions by timestamp

### Alternatives Considered
1. **Single first session as baseline**
   - **Pros**: Simplest to calculate
   - **Cons**: Single session may be anomaly (sensor error, patient fatigue)
   - **Why rejected**: Less statistically robust

2. **First week/month average as baseline**
   - **Pros**: More stable baseline
   - **Cons**: Time-dependent (what if only 1 session in first week?), complex edge cases
   - **Why rejected**: Too complex for MVP; time-based logic fragile

3. **Rolling average (each session vs previous 3)**
   - **Pros**: Shows continuous improvement
   - **Cons**: Not a true "baseline", harder to interpret, computationally expensive
   - **Why rejected**: Not what "tremor reduction" means in clinical context

4. **User-specified baseline session**
   - **Pros**: Maximum flexibility
   - **Cons**: UX complexity, doctors may not know which session to choose
   - **Why rejected**: Out of scope for MVP (can add as P3 customization)

### Implementation Logic
```python
def calculate_baseline_amplitude(patient_id):
    """Get baseline tremor amplitude from first 3 sessions."""
    baseline_sessions = BiometricSession.objects.filter(
        patient_id=patient_id
    ).order_by('session_start')[:3]

    if not baseline_sessions:
        return None  # No baseline available

    amplitudes = [
        np.mean(session.sensor_data['tremor_intensity'])
        for session in baseline_sessions
    ]
    return np.mean(amplitudes)

def calculate_tremor_reduction(current_amplitude, baseline_amplitude):
    """Calculate tremor reduction percentage."""
    if baseline_amplitude is None or baseline_amplitude == 0:
        return None  # Cannot calculate reduction

    reduction_pct = ((baseline_amplitude - current_amplitude) / baseline_amplitude) * 100
    return round(reduction_pct, 1)  # Return percentage (e.g., 25.3%)
```

**Edge Cases**:
- **< 3 sessions total**: Use all available sessions as baseline
- **Baseline = 0**: Return None (cannot divide by zero)
- **Negative reduction**: Patient's tremor worsened (show negative percentage)

---

## Research Area 5: Temporary File Management for PDFs

### Decision
**Immediate deletion after download + daily cleanup task**

### Rationale
- **Security**: Minimize exposure window for sensitive medical data
- **Storage**: Prevent disk space exhaustion from forgotten temp files
- **Simplicity**: No complex file tracking database needed
- **Django native**: Use Django management command for cleanup

### Alternatives Considered
1. **Store PDFs permanently in media/reports/**
   - **Pros**: Enable re-download without regeneration
   - **Cons**: Privacy risk (files accumulate), storage costs, GDPR concerns
   - **Why rejected**: Reports should be generated on-demand; no need for persistence

2. **In-memory PDF generation** (no temp files)
   - **Pros**: No file cleanup needed, maximum security
   - **Cons**: Memory spikes for large PDFs, harder to debug
   - **Why rejected**: ReportLab requires file-like objects; in-memory adds complexity

3. **Cloud storage** (S3, Supabase Storage)
   - **Pros**: Offload local disk, scalable
   - **Cons**: Additional service dependency, cost, violates "local dev only" principle
   - **Why rejected**: Not applicable for local development setup

### Implementation Strategy

**Immediate deletion**:
```python
def download_report(request, report_id):
    pdf_path = generate_pdf(...)
    try:
        with open(pdf_path, 'rb') as pdf:
            response = HttpResponse(pdf.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="report.pdf"'
            return response
    finally:
        os.remove(pdf_path)  # Delete immediately after read
```

**Daily cleanup** (for failed downloads):
```python
# management/commands/cleanup_temp_reports.py
from django.core.management.base import BaseCommand
import os
from datetime import datetime, timedelta

class Command(BaseCommand):
    def handle(self, *args, **options):
        reports_dir = settings.MEDIA_ROOT / 'reports'
        cutoff_time = datetime.now() - timedelta(hours=24)

        for filename in os.listdir(reports_dir):
            filepath = reports_dir / filename
            if os.path.getmtime(filepath) < cutoff_time.timestamp():
                os.remove(filepath)
                self.stdout.write(f'Deleted old report: {filename}')
```

**Cron/scheduled task**: Run `python manage.py cleanup_temp_reports` daily (use system cron or APScheduler)

---

## Best Practices Summary

### Statistics Calculation
1. Use database aggregation where possible (leverage PostgreSQL)
2. Handle missing data gracefully (None values, empty arrays)
3. Validate date ranges before querying
4. Log slow queries (> 3 seconds) for optimization
5. Cache baseline calculations per patient (recompute only when new sessions added)

### PDF Generation
1. Use templates/functions for consistent layout
2. Compress images before embedding (optimize file size)
3. Set PDF metadata (title, author, creation date)
4. Handle ReportLab exceptions gracefully (file write errors, memory errors)
5. Validate PDF file size before returning (reject if > 5MB)

### API Design
1. Paginate statistics responses (default 50 data points per page)
2. Return meaningful error messages (e.g., "No sessions found in date range")
3. Use query parameters for filters (RESTful convention)
4. Return 202 Accepted for long-running PDF generation (if > 5 seconds)
5. Provide progress feedback for large reports (optional enhancement)

### Testing
1. Test with various data volumes (1, 10, 100, 500 sessions)
2. Test edge cases (no sessions, single session, missing ML predictions)
3. Test date range edge cases (same day, invalid ranges, future dates)
4. Test concurrent PDF generation (5+ simultaneous requests)
5. Validate PDF file integrity (open PDFs to verify they're not corrupted)

---

## Dependencies & Installation

**Python Packages** (add to `requirements.txt`):
```
# Analytics & Reporting (Feature 003)
reportlab==4.0.7
matplotlib==3.8.2
pillow==10.2.0
numpy==1.26.3
```

**System Requirements**:
- No additional system packages needed
- Sufficient disk space for temp PDFs (estimate 1-5MB per report)
- Adequate memory for matplotlib chart generation (minimal, < 100MB)

**Configuration** (add to `.env` if needed):
```
# Analytics settings (optional)
REPORTS_TEMP_DIR=media/reports/
MAX_PDF_SIZE_MB=5
PDF_CHART_DPI=96
```

---

## Performance Benchmarks (Expected)

Based on similar Django projects and library benchmarks:

| Operation | Expected Time | Max Acceptable |
|-----------|---------------|----------------|
| Statistics query (30 days) | 0.5-1 second | 3 seconds |
| Statistics query (365 days) | 1-2 seconds | 3 seconds |
| Chart generation (1 chart) | 0.2-0.5 seconds | 1 second |
| PDF generation (10 pages) | 2-4 seconds | 10 seconds |
| PDF generation (100+ sessions) | 5-8 seconds | 10 seconds |

**Bottlenecks to watch**:
1. Database query time with large datasets → Add indexes on `session_start`, `patient_id`
2. Chart generation with many data points → Limit chart to 100 data points max
3. PDF file size growth → Compress images to 96 DPI

---

## Conclusion

All technical unknowns have been resolved with informed decisions based on:
- Django/Python ecosystem best practices
- TremoAI constitutional compliance
- Performance requirements from spec (SC-001 through SC-007)
- Clinical validity (baseline calculation)
- Security and privacy considerations (temp file management)

**Ready to proceed** to data model design and API contract specification.
