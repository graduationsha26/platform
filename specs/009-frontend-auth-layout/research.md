# Research Findings: Frontend Authentication & Layout

**Feature**: Frontend Authentication & Layout (009-frontend-auth-layout)
**Phase**: 0 - Technical Research
**Date**: 2026-02-16

## Overview

This document captures technical research and design decisions made during the planning phase for the frontend authentication and layout feature.

## Research Areas

### 1. React Authentication State Management

**Decision**: Use React Context API for authentication state

**Rationale**:
- React Context API is built-in (no additional dependencies)
- Sufficient for managing global auth state (user, token, isAuthenticated)
- Simpler than Redux/Zustand for this limited scope
- Easy to test and understand
- Recommended pattern for React 18+ applications

**Alternatives Considered**:
- **Redux Toolkit**: Rejected due to unnecessary complexity for managing just auth state. Adds ~30KB to bundle size and requires boilerplate (store setup, slices, actions). Overkill for a single global state object.
- **Zustand**: Lightweight alternative (3KB) but adds external dependency. Context API provides equivalent functionality for this use case.
- **Jotai/Recoil**: Atomic state management libraries - too experimental and unnecessary for simple auth state.

**Implementation Notes**:
- `AuthContext.jsx` provides: `{ user, token, isAuthenticated, login, logout, register }`
- `useAuth()` hook for consuming auth context in components
- Context provider wraps entire app in `App.jsx`

### 2. JWT Token Storage Strategy

**Decision**: Use localStorage for JWT token storage

**Rationale**:
- Simple implementation with native Web Storage API
- Persists across browser sessions (user stays logged in after refresh)
- Accessible from JavaScript (needed for API request headers)
- Acceptable security trade-off for local development/graduation project scope

**Alternatives Considered**:
- **httpOnly Cookies**: Most secure option (immune to XSS attacks) but requires backend CSRF protection and SameSite configuration. Rejected because:
  - Requires backend changes (Django cookie settings)
  - More complex for local development (CORS complications)
  - Not necessary for graduation project scope
- **sessionStorage**: Cleared on browser tab close. Rejected because:
  - Poor user experience (requires re-login on every tab close)
  - No benefit over localStorage for this use case
- **Memory only (React state)**: Lost on page refresh. Rejected because:
  - Terrible UX (login required on every refresh)
  - Not suitable for production-like experience

**Security Considerations**:
- Vulnerable to XSS attacks (if malicious script injected)
- Mitigation: React's built-in XSS protection (JSX escaping)
- Token expiration handled server-side (Django SimpleJWT default: 5 minutes access, 24 hours refresh)
- Logout clears localStorage immediately

**Implementation Notes**:
- `tokenStorage.js` utility with `getToken()`, `setToken()`, `removeToken()`
- Token retrieved and attached to API requests via axios interceptor
- 401 responses trigger automatic logout and redirect to login

### 3. React Router Protected Routes Pattern

**Decision**: Use wrapper component pattern with React Router v6

**Rationale**:
- Clean, declarative route protection
- Single source of truth for auth checks
- Easy to test and maintain
- Standard React Router v6 pattern

**Implementation Pattern**:
```jsx
<Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
```

**Alternatives Considered**:
- **Route-level guards (like Vue Router)**: Not native to React Router. Would require custom navigation listener.
- **Higher-order component (HOC)**: Older pattern, less readable than wrapper component.
- **Custom hook in every protected component**: Rejected due to code duplication.

**Implementation Notes**:
- `ProtectedRoute.jsx` checks `isAuthenticated` from `useAuth()`
- Unauthenticated users redirected to `/login` with `<Navigate to="/login" replace />`
- Stores attempted URL in location state for post-login redirect
- Role-based variants: `DoctorRoute`, `PatientRoute` (check user role)

### 4. Form Validation Strategy

**Decision**: Custom validation with React Hook Form

**Rationale**:
- React Hook Form is lightweight (9KB) and performant
- Provides form state management + validation in one library
- Minimal re-renders (uses uncontrolled inputs)
- Built-in integration with native HTML5 validation
- Industry standard for React forms

**Alternatives Considered**:
- **Formik**: Popular but heavier (13KB) and more boilerplate. Declining in popularity vs React Hook Form.
- **Native HTML5 validation**: Too limited (no custom async validation, poor error UX).
- **Custom validation from scratch**: Rejected due to reinventing wheel (error state, touched fields, submit handling).

**Validation Rules**:
- Email: HTML5 email pattern + required
- Password (login): Required only
- Password (registration): Min 8 chars, required, must match confirmation
- Name: Required, min 2 chars
- Role: Required, enum (doctor, patient)

**Implementation Notes**:
- `useForm()` hook from React Hook Form for each form
- `validators.js` exports reusable validation functions
- Display errors inline below each input field
- Disable submit button while submitting (prevent double-submit)

### 5. Responsive Sidebar with Tailwind CSS

**Decision**: Mobile-first responsive sidebar with Tailwind utility classes

**Rationale**:
- Tailwind provides responsive utilities out of the box
- No custom CSS needed (Tailwind utility classes sufficient)
- Mobile-first approach (sm:, md:, lg: breakpoints)
- Standard pattern: hamburger menu on mobile, persistent sidebar on desktop

**Implementation Pattern**:
- **Mobile (<768px)**: Hidden sidebar, hamburger icon in top bar, overlay menu when opened
- **Desktop (≥768px)**: Persistent sidebar, auto-open by default, collapsible with toggle
- **Breakpoint**: 768px (Tailwind `md:` breakpoint)

**Alternatives Considered**:
- **Always visible sidebar (no mobile menu)**: Poor mobile UX.
- **Drawer libraries (React Drawer, react-modern-drawer)**: Unnecessary dependency. Tailwind classes + React state sufficient.
- **Bottom tab bar (mobile)**: Better for mobile apps, but web apps typically use hamburger menu pattern.

**Implementation Notes**:
- `Sidebar.jsx`: Desktop persistent sidebar
- `MobileMenu.jsx`: Mobile overlay menu
- State: `isMobileMenuOpen` (boolean) managed in `AppLayout.jsx`
- Hamburger icon in `TopBar.jsx` toggles mobile menu
- Backdrop overlay closes menu when clicked outside
- Tailwind classes: `hidden md:block` (desktop sidebar), `fixed inset-0` (mobile overlay)

### 6. Role-Based Navigation & Redirects

**Decision**: Centralized role configuration with helper utilities

**Rationale**:
- Single source of truth for role-based UI logic
- Easy to add/modify menu items per role
- Testable and maintainable
- Avoids duplicating role checks across components

**Implementation Pattern**:
- `roleHelpers.js` exports:
  - `getMenuItems(role)`: Returns menu items array for given role
  - `getDashboardPath(role)`: Returns dashboard route for role
  - `hasAccess(role, route)`: Checks if role can access route

**Menu Items by Role**:
- **Doctor**: Dashboard, Patients, Analytics, Reports, Settings
- **Patient**: Dashboard, My Data, Sessions, Progress, Settings
- **Common**: Logout (in top bar, not sidebar)

**Implementation Notes**:
- Post-login redirect uses `getDashboardPath(user.role)`
- `Sidebar.jsx` renders `getMenuItems(user.role).map(...)`
- Menu items include: `{ label, icon, path, badge? }`
- Active route highlighting via React Router `useLocation()`

### 7. API Client Architecture

**Decision**: Axios with request/response interceptors for JWT injection

**Rationale**:
- Axios provides clean interceptor API for adding auth headers
- Centralized error handling (401 → logout, 500 → error page)
- Request/response transformation in one place
- Industry standard for React API clients

**Alternatives Considered**:
- **Fetch API**: Native but lacks interceptors. Would need manual token injection in every request.
- **React Query / SWR**: Great for caching but overkill for this feature. Consider for future features.

**Implementation Pattern**:
```javascript
// Request interceptor: Add Authorization header
axios.interceptors.request.use(config => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor: Handle 401 (expired token)
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      logout(); // Clear token, redirect to login
    }
    return Promise.reject(error);
  }
);
```

**Implementation Notes**:
- `api.js`: Base axios instance with base URL from env var
- `authService.js`: Login, register, logout functions using axios instance
- All backend API calls use this configured axios instance

## Dependencies to Add

**npm packages** (add to `frontend/package.json`):
- `react-router-dom@^6.22.0` - Client-side routing
- `axios@^1.6.7` - HTTP client
- `react-hook-form@^7.50.0` - Form validation
- `lucide-react@^0.323.0` - Icon library (lightweight, tree-shakeable)

**Total bundle size impact**: ~50KB gzipped

## Environment Variables

**Frontend** (`.env.local`):
```
VITE_API_BASE_URL=http://localhost:8000/api
```

**Backend** (`.env` - no changes needed):
- JWT settings already configured in Django
- CORS already configured for local development

## Testing Strategy

**Unit Tests** (Jest/Vitest):
- `AuthContext`: Login, logout, token persistence
- `ProtectedRoute`: Redirect logic for authenticated/unauthenticated users
- `useAuth` hook: Context consumption
- `validators.js`: Validation functions

**Integration Tests**:
- Login flow: Form submit → API call → token storage → redirect
- Protected route access: Unauthenticated → redirect to login
- Role-based routing: Doctor login → doctor dashboard

**Manual Testing Checklist**:
- Login with valid doctor/patient credentials
- Login with invalid credentials (error display)
- Register new account (all roles)
- Access protected route while logged out (redirect)
- Token expiration handling (wait for expiry, access route → redirect)
- Mobile responsive behavior (hamburger menu, sidebar)
- Logout and verify token cleared

## Performance Considerations

**Optimization Strategies**:
- Code splitting: Lazy load dashboard pages (`React.lazy()`)
- Tree shaking: Lucide React icons (import only used icons)
- Memoization: `useMemo()` for menu items, `useCallback()` for auth functions
- Avoid unnecessary re-renders: Context optimization with `useMemo()` for context value

**Expected Metrics**:
- Initial bundle size: ~150KB (React + Router + Axios + RHF)
- Login page load: <1s (local dev)
- Form validation feedback: <100ms (synchronous validation)
- Route navigation: <500ms (client-side only, no API calls)

## Security Best Practices

**Implemented**:
- JWT tokens in localStorage (acceptable for graduation project)
- Automatic logout on 401 responses
- HTTPS in production (noted in constraints, out of scope for local dev)
- React's built-in XSS protection (JSX escaping)

**Not Implemented** (out of scope):
- Token refresh mechanism (future enhancement)
- Rate limiting (backend responsibility)
- CSRF protection (not needed for JWT in Authorization header)
- Content Security Policy (production concern)

## Open Questions (Resolved)

1. **Q**: Should we implement token refresh logic?
   **A**: No. Django SimpleJWT default expiration (5 min access, 24 hour refresh) is sufficient. User re-login every 24 hours is acceptable for graduation project scope.

2. **Q**: Should we add "Remember Me" functionality?
   **A**: No. Out of scope for P1-P4 user stories. Can be added in future iteration.

3. **Q**: Should we validate JWT token structure on frontend?
   **A**: No. Backend validates tokens. Frontend only stores and sends them. Avoid duplicating validation logic.

4. **Q**: Should we implement SSO or social login?
   **A**: No. Explicitly out of scope in feature specification.

## References

- [React Router v6 Documentation](https://reactrouter.com/en/main)
- [React Hook Form Documentation](https://react-hook-form.com/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [Tailwind CSS Responsive Design](https://tailwindcss.com/docs/responsive-design)
- [Django SimpleJWT Documentation](https://django-rest-framework-simplejwt.readthedocs.io/)
