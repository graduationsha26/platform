# Tasks: Reports Page & PDF Download

**Input**: Design documents from `/specs/035-reports-pdf/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/api-endpoints.md ✅ quickstart.md ✅

**Tests**: Not requested — no test tasks included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US2)
- Exact file paths included in all descriptions

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Add the two API service functions that BOTH user stories depend on. Both functions live in the same file and must be added before any US1 or US2 work can call the backend.

**⚠️ CRITICAL**: US1 stats fetch and US2 PDF download both depend on these service functions.

- [X] T001 Add `fetchPatientStats(patientId, startDate, endDate)` named export to `frontend/src/services/analyticsService.js` — call `api.get('/analytics/stats/', { params: { patient_id: patientId, start_date: startDate, end_date: endDate, group_by: 'day', page_size: 365 } })` and return `response.data`; add JSDoc comment describing the return shape `{ count, baseline, results }`
- [X] T002 Add `downloadPatientReport(patientId, startDate, endDate)` named export to `frontend/src/services/analyticsService.js` — call `api.post('/analytics/reports/', { patient_id: patientId, start_date: startDate, end_date: endDate }, { responseType: 'blob' })` and return `response.data` (Blob); **error unwrapping**: wrap the `api.post` call in a try/catch — in the catch block, if `err.response?.data` is a Blob, read it with `const text = await err.response.data.text()` then `const parsed = JSON.parse(text)` and rethrow `Object.assign(err, { parsedCode: parsed.code })`; re-throw so callers can read `err.parsedCode` for user-facing error routing

**Checkpoint**: Both analytics service functions are available. All US1 and US2 work can now begin.

---

## Phase 2: User Story 1 — Date Range Selection & Statistics Preview (Priority: P1) 🎯 MVP

**Goal**: Doctor navigates to `/doctor/patients/:id/reports`, selects a date range, and sees four aggregated tremor metrics: avg amplitude, max amplitude, dominant frequency, and tremor reduction %.

**Independent Test**: Navigate to `/doctor/patients/1/reports`, verify the default 30-day stats load on mount. Change the date range, click Apply, verify the metrics update. Select a range with no data, verify the empty state appears. Select end date before start date, verify inline error prevents the Apply call.

- [X] T003 [US1] Create `frontend/src/hooks/usePatientReport.js` — hook `usePatientReport(patientId)` that: **(a) Date range state**: `dateRange` initialized to `{ startDate: <29 days ago YYYY-MM-DD>, endDate: <today YYYY-MM-DD> }` computed via `new Date()` arithmetic; `setDateRange` setter; **(b) Stats state**: `stats` (null or `{ hasData, sessionCount, avgAmplitude, maxAmplitude, dominantFrequency, tremorReductionPct }`), `statsLoading` (false), `statsError` (null); **(c) `applyDateRange()` async function**: sets `statsLoading(true)`, calls `fetchPatientStats(patientId, dateRange.startDate, dateRange.endDate)`, on success computes summary from `data.results` — `hasData: results.length > 0`, `sessionCount: results.reduce((s,r) => s + r.session_count, 0)`, `avgAmplitude: results.reduce((s,r) => s + r.avg_amplitude, 0) / results.length`, `maxAmplitude: Math.max(...results.map(r => r.avg_amplitude))` (or 0 if empty), `dominantFrequency: results.reduce((s,r) => s + r.dominant_frequency, 0) / results.length`, `tremorReductionPct: (() => { const v = results.filter(r => r.tremor_reduction_pct != null); return v.length ? v.reduce((s,r) => s + r.tremor_reduction_pct, 0) / v.length : null; })()` — calls `setStats(summary)`, on error calls `setStatsError('Failed to load statistics — please try again.')`, always `setStatsLoading(false)`; **(d) Download state**: `downloadLoading` (false), `downloadError` (null); **(e) `downloadPDF()` async function**: sets `setDownloadLoading(true); setDownloadError(null)`, calls `downloadPatientReport(patientId, dateRange.startDate, dateRange.endDate)`, on success creates `URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))`, creates `<a>` element with `href=url` and `download=\`report_patient${patientId}_${dateRange.startDate}_${dateRange.endDate}.pdf\``, calls `a.click()`, then `URL.revokeObjectURL(url)`, on error reads `err.parsedCode` and maps: `'NO_DATA_FOR_REPORT'` → `'No data available for this period — try a different date range.'`, `'PDF_SIZE_LIMIT_EXCEEDED'` → `'Report too large — try a smaller date range (max ~90 days recommended).'`, otherwise → `'Report generation failed — please try again.'`, calls `setDownloadError(message)`, always `setDownloadLoading(false)` in finally; **(f) Return**: `{ dateRange, setDateRange, stats, statsLoading, statsError, applyDateRange, downloadLoading, downloadError, downloadPDF }`
- [X] T004 [P] [US1] Create `frontend/src/components/reports/DateRangePicker.jsx` — receives props `{ startDate, endDate, onChange, onApply, loading }`; compute `today = new Date().toISOString().split('T')[0]`; render two labeled `<input type="date">` — both with `max={today}` to prevent future date selection; `onChange` for Start: calls `onChange(newStart, endDate)`; `onChange` for End: calls `onChange(startDate, newEnd)`; validation: `const error = endDate && startDate && endDate < startDate ? 'End date must be on or after start date.' : null`; render error paragraph when `error` is set; "Apply" `<button>` with `onClick={onApply}` and `disabled={!!error || loading}`; when `loading` show "Loading..." text on button; Tailwind input classes: `px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-400` with `border-red-400` when error, `border-neutral-300` otherwise; Apply button: `px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors`
- [X] T005 [P] [US1] Create `frontend/src/components/reports/StatsPreview.jsx` — receives props `{ stats, loading, error }`; **(a) loading state**: render a 2×2 grid of 4 skeleton cards (`<div className="h-24 bg-neutral-100 rounded-xl animate-pulse" />`); **(b) error state** (when `error` and not loading): render `<p className="text-sm text-red-600">{error}</p>`; **(c) empty state** (when `!stats?.hasData && !loading && !error`): render `<p className="text-sm text-neutral-500 text-center py-8">No sessions recorded for this period. Try adjusting the date range.</p>`; **(d) data state**: render `<div className="grid grid-cols-2 gap-4">` with 4 metric cards — each card: `<div className="bg-white border border-neutral-200 rounded-xl p-4"><p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-1">{label}</p><p className="text-xl font-semibold text-neutral-900">{value}</p></div>`; card values: Avg Amplitude = `stats.avgAmplitude.toFixed(3)`, Max Amplitude = `stats.maxAmplitude.toFixed(3)`, Dominant Frequency = `` `${stats.dominantFrequency.toFixed(1)} Hz` ``, Tremor Reduction = when null show `<span className="text-neutral-400">—</span>`, when ≥ 0 show `<span className="text-green-700">+{stats.tremorReductionPct.toFixed(1)}%</span>`, when < 0 show `<span className="text-red-700">{stats.tremorReductionPct.toFixed(1)}%</span>`
- [X] T006 [US1] Create `frontend/src/pages/PatientReportsPage.jsx` — uses `useParams` to get `id`; calls `usePatientReport(id)` for all state; renders inside `AppLayout`: **(a) header**: `<div className="flex items-center justify-between">` with left side having a back `<Link to={\`/doctor/patients/${id}\`} className="text-sm text-neutral-500 hover:text-neutral-700 block mb-1">← Back to patient</Link>` and `<h1>Reports</h1>`, right side having `<ConnectionStatus>`-style nothing (no status indicator needed); **(b) access-denied state**: if `statsError` contains "403" or "forbidden" (case-insensitive), render an error card with "You do not have access to this patient's reports." and a `<Link to="/doctor/patients">← Back to patients</Link>`; **(c) main card**: `<div className="bg-white border border-neutral-200 rounded-xl p-6 space-y-6">` containing `<DateRangePicker startDate={dateRange.startDate} endDate={dateRange.endDate} onChange={(s,e) => setDateRange({startDate:s, endDate:e})} onApply={applyDateRange} loading={statsLoading} />` and `<StatsPreview stats={stats} loading={statsLoading} error={statsError} />`; **(d) download section placeholder**: `{/* T008: Download PDF button */}` comment div; **(e) mount effect**: `useEffect(() => { applyDateRange(); }, [])` — triggers the default 30-day stats load on page open
- [X] T007 [US1] Add lazy-loaded route for `/doctor/patients/:id/reports` to `frontend/src/routes/AppRoutes.jsx` — add `const PatientReportsPage = lazy(() => import('../pages/PatientReportsPage'))` in the lazy imports section and add `<Route path="/doctor/patients/:id/reports" element={<ProtectedRoute><PatientReportsPage /></ProtectedRoute>} />` placed after the `/doctor/patients/:id/monitor` route

**Checkpoint**: Navigate to `/doctor/patients/1/reports` — default 30-day stats load on mount, date range picker visible, four metric cards populate. Date changes and Apply trigger fresh fetch. Empty ranges show the empty state.

---

## Phase 3: User Story 2 — PDF Report Download (Priority: P2)

**Goal**: A "Download PDF" button appears below the stats preview. Clicking it calls the backend report endpoint and delivers the PDF as a browser file download.

**Independent Test**: With valid stats loaded, click "Download PDF". Verify the button shows "Generating...", a `.pdf` file is downloaded within ~5 seconds, and the button returns to its default state. With no data loaded, verify the button is disabled. Simulate a server error (stop the backend), verify a user-friendly error message appears below the button.

- [X] T008 [US2] Add Download PDF button section to `frontend/src/pages/PatientReportsPage.jsx` — replace the `{/* T008: Download PDF button */}` placeholder with: import nothing new (all state already from hook); render below `<StatsPreview>` inside the main card: `<div className="pt-4 border-t border-neutral-100">` containing `<button onClick={downloadPDF} disabled={downloadLoading || !stats?.hasData} className="px-6 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">` — when `downloadLoading`: show `<svg>` spinner + "Generating..." text; otherwise: "Download PDF"; below the button when `!stats?.hasData && !statsLoading`: render `<p className="text-xs text-neutral-400 mt-2">Select a date range with data to enable download.</p>`; when `downloadError`: render `<p className="text-sm text-red-600 mt-2">{downloadError}</p>` below the button; destructure `downloadLoading`, `downloadError`, `downloadPDF` from the `usePatientReport` hook call (already called at top of component)

**Checkpoint**: With data loaded, clicking "Download PDF" triggers a file download. With no data, button is disabled. Errors display below the button with human-readable messages.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Navigation entry point and integration validation.

- [X] T009 [P] Add "Reports" `<Link>` button to `frontend/src/pages/PatientDetailPage.jsx` — in the existing `<div className="flex items-center gap-2">` header div (where "Live Monitor" and "Edit" buttons are), add `<Link to={\`/doctor/patients/${id}/reports\`} className="px-4 py-2 border border-neutral-300 text-sm font-medium rounded-lg hover:bg-neutral-50 transition-colors">Reports</Link>` as the first button in the group (order: Reports → Live Monitor → Edit); `Link` is already imported
- [X] T010 [P] Validate all six quickstart scenarios in `specs/035-reports-pdf/quickstart.md` via code review — verify the implemented code handles: (1) happy path stats load + PDF download, (2) no data for range → empty state + disabled button, (3) invalid date range → inline error, Apply disabled, no fetch sent, (4) PDF too large → `PDF_SIZE_LIMIT_EXCEEDED` error message appears, (5) no baseline → `tremorReductionPct` is null → Tremor Reduction card shows "—", (6) unauthorized access → 403 → access-denied error card

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — start immediately; BLOCKS all user story work
- **User Story 1 (Phase 2)**: Depends on Phase 1 (T001, T002) — T003 can start once T001 is done; T004 and T005 can start in parallel with T003; T006 needs T003+T004+T005; T007 needs T006
- **User Story 2 (Phase 3)**: Depends on T006 (page exists to extend); T008 adds download UI to the page
- **Polish (Phase 4)**: Depends on all user stories complete (T009 needs T007 route; T010 needs T008)

### User Story Dependencies

- **US1 (P1)**: Requires Phase 1 (T001+T002) — no dependency on US2
- **US2 (P2)**: Requires US1 page (T006) to exist — T008 extends PatientReportsPage.jsx

### Within User Story 1

- T003 (`usePatientReport.js`) starts after T001 (service function must exist to import)
- T004 (`DateRangePicker.jsx`) and T005 (`StatsPreview.jsx`) can run in parallel to T003 (different files, no dependency on hook)
- T006 (`PatientReportsPage.jsx`) needs T003 + T004 + T005 complete
- T007 (`AppRoutes.jsx`) needs T006 (route points to the page)

---

## Parallel Opportunities

### Phase 1 (Foundational)
```
T001 [analyticsService.js — fetchPatientStats]  ──┐
T002 [analyticsService.js — downloadPatientReport] ┘ (same file: T002 after T001)
```

### Phase 2 (US1)
```
T003 [usePatientReport.js] ──┐
T004 [DateRangePicker.jsx]   ├──→ T006 [PatientReportsPage.jsx] → T007 [AppRoutes.jsx]
T005 [StatsPreview.jsx]     ──┘
```

T004 and T005 are both [P] — they touch separate files and depend only on knowing the prop contract (documented in data-model.md), not on T003's implementation being complete.

### Phase 3 (US2)
```
T008 [PatientReportsPage.jsx — download button] (single task, extends T006)
```

### Phase 4 (Polish)
```
T009 [PatientDetailPage.jsx — Reports button]  ──┐  (parallel, different files)
T010 [Quickstart validation — code review]     ──┘
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Foundational (T001, T002)
2. Complete Phase 2: User Story 1 (T003–T007)
3. **STOP and VALIDATE**: Open `/doctor/patients/1/reports`, verify default stats load, date range changes, empty state, validation
4. Deliver MVP: doctor can preview tremor statistics for any date range

### Incremental Delivery

1. Foundational → service functions ready
2. US1 (T003–T007) → stats preview page live → **MVP demo-ready**
3. US2 (T008) → PDF download available
4. Polish (T009–T010) → navigation entry point + validation

---

## Notes

- `usePatientReport.js` is built fully in T003 (including download logic) — it doesn't need extending in US2; only the page UI changes in T008
- `PatientReportsPage.jsx` is built with a placeholder comment in T006 and extended in T008 — this matches the incremental pattern from Feature 034
- The `downloadPatientReport` service function handles the tricky blob-error unwrapping so the hook receives a structured `err.parsedCode` field
- `maxAmplitude` is computed client-side as `Math.max(...results.map(r => r.avg_amplitude))` — no backend changes needed
- `tremorReductionPct` null means no baseline exists (patient has too few sessions for baseline calculation) — displayed as "—" in the Tremor Reduction card
- Both `<DateRangePicker>` and `<StatsPreview>` are in `frontend/src/components/reports/` — this directory is created implicitly when the first file is written
