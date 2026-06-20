# Quickstart Guide: Frontend Authentication & Layout

**Feature**: Frontend Authentication & Layout (009-frontend-auth-layout)
**Phase**: 1 - Integration Scenarios
**Date**: 2026-02-16

## Overview

This guide provides practical examples and integration scenarios for implementing and using the frontend authentication and layout system in the TremoAI platform.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Basic Usage Scenarios](#basic-usage-scenarios)
5. [Advanced Integration](#advanced-integration)
6. [Testing Scenarios](#testing-scenarios)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

- Node.js 18+ and npm/yarn installed
- TremoAI backend running at `http://localhost:8000`
- Backend authentication endpoints operational:
  - `POST /api/auth/login/`
  - `POST /api/auth/register/`

## Installation

### 1. Install Dependencies

```bash
cd frontend
npm install react-router-dom@^6.22.0 axios@^1.6.7 react-hook-form@^7.50.0 lucide-react@^0.323.0
```

### 2. Environment Configuration

Create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### 3. Verify Backend Connectivity

```bash
# Test backend health
curl http://localhost:8000/api/health
```

## Configuration

### App Entry Point Setup

Update `frontend/src/main.jsx`:

```jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### Root App Component

Update `frontend/src/App.jsx`:

```jsx
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import AppRoutes from './routes/AppRoutes';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
```

## Basic Usage Scenarios

### Scenario 1: User Login Flow (Doctor)

**Objective**: Doctor logs in and accesses their dashboard

**Steps**:

1. **Navigate to login page**
   ```
   URL: http://localhost:5173/login
   ```

2. **Fill login form**
   ```
   Email: doctor@example.com
   Password: SecurePass123
   ```

3. **Submit form**
   - Frontend: `authService.login({ email, password })`
   - Backend: `POST /api/auth/login/`
   - Response: `{ access, refresh, user }`

4. **Token storage**
   - `localStorage.setItem('tremoai_token', access)`
   - `localStorage.setItem('tremoai_user', JSON.stringify(user))`

5. **Automatic redirect**
   - Redirects to: `/doctor/dashboard`
   - User sees doctor-specific layout with sidebar menu

**Expected Result**:
- User is authenticated
- JWT token stored in localStorage
- Redirected to doctor dashboard
- Sidebar shows: Dashboard, Patients, Analytics, Reports, Settings

**Code Example** (using the auth system):

```jsx
import { useAuth } from '../hooks/useAuth';

function LoginPage() {
  const { login, isSubmitting, error } = useAuth();
  const { register, handleSubmit } = useForm();

  const onSubmit = async (data) => {
    await login(data.email, data.password);
    // Automatic redirect handled by AuthContext
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} type="email" required />
      <input {...register('password')} type="password" required />
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Logging in...' : 'Login'}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
```

### Scenario 2: User Registration Flow (Patient)

**Objective**: New patient creates an account

**Steps**:

1. **Navigate to registration page**
   ```
   URL: http://localhost:5173/register
   ```

2. **Fill registration form**
   ```
   Name: John Smith
   Email: john.smith@example.com
   Password: MySecure123
   Confirm Password: MySecure123
   Role: Patient
   ```

3. **Submit form**
   - Frontend validates: password match, email format, password strength
   - Backend: `POST /api/auth/register/`
   - Response: `{ id, email, name, role, message }`

4. **Redirect to login**
   - Show success message: "Account created successfully"
   - User enters credentials on login page

5. **Login and access patient dashboard**
   - Follow Scenario 1 flow with patient credentials
   - Redirects to: `/patient/dashboard`

**Expected Result**:
- Account created in database
- Success message displayed
- User can immediately log in
- Sidebar shows: Dashboard, My Data, Sessions, Progress, Settings

### Scenario 3: Accessing Protected Route (Unauthenticated)

**Objective**: Unauthenticated user tries to access protected page

**Steps**:

1. **Clear authentication** (simulate logged-out state)
   ```javascript
   localStorage.clear();
   ```

2. **Navigate to protected route**
   ```
   URL: http://localhost:5173/doctor/dashboard
   ```

3. **Route guard activates**
   - `ProtectedRoute` checks `isAuthenticated` from `AuthContext`
   - Result: `false` (not authenticated)

4. **Automatic redirect**
   - Redirects to: `/login`
   - URL state saves attempted path: `/doctor/dashboard`

5. **After login**
   - User logs in successfully
   - Redirected to originally attempted path: `/doctor/dashboard`

**Expected Result**:
- Unauthorized users cannot access protected pages
- Automatic redirect to login
- Return to intended page after authentication

### Scenario 4: Token Expiration Handling

**Objective**: Handle expired JWT token gracefully

**Steps**:

1. **User is logged in** (token expires after 5 minutes)

2. **User makes API request** (e.g., fetch patient list)
   ```javascript
   axios.get('/api/patients/');
   ```

3. **Backend validates token**
   - Token is expired
   - Returns: `401 Unauthorized`

4. **Axios interceptor catches error**
   ```javascript
   axios.interceptors.response.use(
     response => response,
     error => {
       if (error.response?.status === 401) {
         // Clear auth state and redirect
         logout();
       }
       return Promise.reject(error);
     }
   );
   ```

5. **Automatic logout**
   - `AuthContext.logout()` called
   - localStorage cleared
   - User redirected to `/login`
   - Message: "Your session has expired. Please log in again."

**Expected Result**:
- Expired tokens trigger automatic logout
- User informed of session expiration
- Seamless return to login page

### Scenario 5: Role-Based Navigation

**Objective**: Different menu items for doctor vs patient

**Steps**:

1. **Doctor logs in**
   - Sidebar shows:
     - Dashboard (`/doctor/dashboard`)
     - Patients (`/doctor/patients`)
     - Analytics (`/doctor/analytics`)
     - Reports (`/doctor/reports`)
     - Settings (`/doctor/settings`)

2. **Patient logs in**
   - Sidebar shows:
     - Dashboard (`/patient/dashboard`)
     - My Data (`/patient/data`)
     - Sessions (`/patient/sessions`)
     - Progress (`/patient/progress`)
     - Settings (`/patient/settings`)

3. **Menu items filtered by role**
   ```javascript
   const menuItems = getMenuItems(user.role);
   // Returns role-specific menu configuration
   ```

4. **Active route highlighted**
   - Current route: `/doctor/patients`
   - "Patients" menu item has active styling (blue background)

**Expected Result**:
- Doctors and patients see different menus
- Menu items match user capabilities
- Active route visually distinguished

### Scenario 6: Responsive Mobile Layout

**Objective**: Sidebar adapts to mobile screen sizes

**Steps**:

1. **Desktop view (≥768px)**
   - Sidebar: Persistent, always visible on left
   - Width: 256px (w-64 in Tailwind)
   - Top bar: Spans remaining width

2. **Mobile view (<768px)**
   - Sidebar: Hidden by default
   - Hamburger icon: Visible in top-left of top bar
   - Click hamburger: Opens overlay menu

3. **Open mobile menu**
   - Overlay: Full-screen dark backdrop
   - Menu: Slides in from left
   - Click outside: Closes menu

4. **Navigate on mobile**
   - Click menu item: Navigate to page
   - Menu: Auto-closes after navigation

**Expected Result**:
- Desktop: Persistent sidebar
- Mobile: Hamburger menu with overlay
- Smooth transitions between states
- Touch-friendly menu items

### Scenario 7: Logout Flow

**Objective**: User logs out and session is cleared

**Steps**:

1. **User clicks logout button** (in top bar)

2. **Logout handler executes**
   ```javascript
   const logout = () => {
     // Clear localStorage
     localStorage.removeItem('tremoai_token');
     localStorage.removeItem('tremoai_user');

     // Reset auth context
     setUser(null);
     setToken(null);
     setIsAuthenticated(false);

     // Redirect to login
     navigate('/login');
   };
   ```

3. **Session cleared**
   - JWT token removed
   - User object removed
   - Auth state reset

4. **Redirect to login**
   - URL: `/login`
   - Message: "You have been logged out successfully"

**Expected Result**:
- User logged out immediately
- No traces of session remain
- Cannot access protected routes
- Clean return to login page

## Advanced Integration

### Custom Protected Route with Role Check

**Use Case**: Restrict route to specific role (e.g., doctor-only page)

```jsx
// components/auth/DoctorRoute.jsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

function DoctorRoute({ children }) {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== 'doctor') {
    return <Navigate to="/unauthorized" replace />;
  }

  return children;
}

export default DoctorRoute;
```

**Usage**:
```jsx
<Route
  path="/doctor/patients"
  element={
    <DoctorRoute>
      <PatientsPage />
    </DoctorRoute>
  }
/>
```

### API Request with Auth Header

**Use Case**: Make authenticated API request

```javascript
// services/api.js
import axios from 'axios';
import { getToken } from '../utils/tokenStorage';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

// Request interceptor: Add auth header
api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: Handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth and redirect
      localStorage.clear();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

**Usage**:
```javascript
import api from '../services/api';

// GET request (auto-includes JWT)
const patients = await api.get('/patients/');

// POST request (auto-includes JWT)
const newPatient = await api.post('/patients/', { name: 'John Doe' });
```

### Conditional UI Based on Auth State

**Use Case**: Show/hide UI elements based on authentication

```jsx
import { useAuth } from '../hooks/useAuth';

function Navbar() {
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <nav>
      <Logo />

      {isAuthenticated ? (
        <>
          <span>Welcome, {user.name}</span>
          <button onClick={logout}>Logout</button>
        </>
      ) : (
        <>
          <Link to="/login">Login</Link>
          <Link to="/register">Register</Link>
        </>
      )}
    </nav>
  );
}
```

## Testing Scenarios

### Manual Testing Checklist

**Authentication**:
- [ ] Login with valid doctor credentials → redirects to doctor dashboard
- [ ] Login with valid patient credentials → redirects to patient dashboard
- [ ] Login with invalid credentials → shows error message
- [ ] Login with empty fields → shows validation errors
- [ ] Register new doctor account → success, redirects to login
- [ ] Register new patient account → success, redirects to login
- [ ] Register with existing email → shows "email already exists" error
- [ ] Register with weak password → shows password strength error
- [ ] Logout → clears session, redirects to login

**Protected Routes**:
- [ ] Access `/doctor/dashboard` logged out → redirects to `/login`
- [ ] Access `/patient/dashboard` logged out → redirects to `/login`
- [ ] Access protected route, login, then redirected back to intended page
- [ ] Navigate between protected routes while authenticated → no redirects
- [ ] Token expires, make API request → automatic logout

**Layout & Navigation**:
- [ ] Doctor sees doctor-specific menu items
- [ ] Patient sees patient-specific menu items
- [ ] Active route highlighted in sidebar
- [ ] Mobile: Sidebar hidden by default, hamburger visible
- [ ] Mobile: Click hamburger → menu opens
- [ ] Mobile: Click menu item → navigates and closes menu
- [ ] Mobile: Click outside menu → menu closes
- [ ] Desktop: Sidebar always visible, no hamburger
- [ ] Top bar shows user name and role
- [ ] Logout button in top bar works

**Browser Refresh**:
- [ ] Logged in, refresh page → still logged in
- [ ] Logged out, refresh page → still logged out
- [ ] On protected route, refresh → stays on same route (if authenticated)

### Automated Test Examples

**Login Form Test** (Jest + React Testing Library):

```javascript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthProvider } from '../contexts/AuthContext';
import LoginForm from '../components/auth/LoginForm';

test('successful login redirects to dashboard', async () => {
  render(
    <AuthProvider>
      <LoginForm />
    </AuthProvider>
  );

  fireEvent.change(screen.getByLabelText(/email/i), {
    target: { value: 'doctor@example.com' },
  });
  fireEvent.change(screen.getByLabelText(/password/i), {
    target: { value: 'SecurePass123' },
  });

  fireEvent.click(screen.getByRole('button', { name: /login/i }));

  await waitFor(() => {
    expect(window.location.pathname).toBe('/doctor/dashboard');
  });
});
```

## Troubleshooting

### Issue: "Network Error" on Login/Register

**Cause**: Backend not running or CORS misconfiguration

**Solution**:
1. Verify backend is running: `curl http://localhost:8000/api/health`
2. Check Django CORS settings: `CORS_ALLOWED_ORIGINS` includes `http://localhost:5173`
3. Verify `.env.local` has correct `VITE_API_BASE_URL`

### Issue: Infinite Redirect Loop

**Cause**: Auth state not initializing properly

**Solution**:
1. Check `AuthContext` initial state is `isLoading: true`
2. Ensure token validation completes before rendering routes
3. Check browser console for errors

### Issue: Token Not Included in API Requests

**Cause**: Axios interceptor not configured

**Solution**:
1. Verify `api.js` has request interceptor
2. Check `getToken()` returns valid token
3. Inspect network requests: Authorization header should be `Bearer <token>`

### Issue: "Unauthorized" After Login

**Cause**: Token not stored in localStorage

**Solution**:
1. Check browser localStorage: Should have `tremoai_token` and `tremoai_user`
2. Verify `tokenStorage.js` functions work correctly
3. Check backend returns `access` token in login response

### Issue: Mobile Menu Not Opening

**Cause**: State not updating or CSS classes incorrect

**Solution**:
1. Check `isMobileMenuOpen` state in `AppLayout.jsx`
2. Verify Tailwind classes: `hidden md:block` for desktop, `fixed inset-0` for mobile
3. Ensure hamburger button toggles state correctly

### Issue: User Sees Wrong Menu Items

**Cause**: Role not correctly passed to `getMenuItems()`

**Solution**:
1. Check `user.role` in AuthContext is 'doctor' or 'patient'
2. Verify `getMenuItems()` function logic in `roleHelpers.js`
3. Inspect user object in browser console: `console.log(user)`

## Next Steps

After implementing this feature:

1. **Test thoroughly**: Use manual testing checklist
2. **Add unit tests**: Cover AuthContext, ProtectedRoute, validators
3. **Proceed to next feature**: Dashboard pages for doctors and patients
4. **Optional enhancements** (future iterations):
   - Token refresh mechanism
   - Remember me functionality
   - Password reset flow
   - Email verification

## Support

For issues or questions:
- Check backend logs: `python manage.py runserver` output
- Check frontend console: Browser DevTools → Console tab
- Verify API contracts: See `contracts/auth.yaml`
- Review data models: See `data-model.md`
