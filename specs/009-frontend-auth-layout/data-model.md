# Data Model: Frontend Authentication & Layout

**Feature**: Frontend Authentication & Layout (009-frontend-auth-layout)
**Phase**: 1 - Data & Contract Design
**Date**: 2026-02-16

## Overview

This document defines the frontend data structures, state management schema, and client-side data entities for the authentication and layout feature. These are TypeScript-style interfaces for clarity but will be implemented in JavaScript.

## Frontend State Models

### 1. Authentication State (AuthContext)

**Purpose**: Global authentication state managed by React Context

**Structure**:
```typescript
interface AuthState {
  // User authentication status
  isAuthenticated: boolean;

  // Currently authenticated user (null if not authenticated)
  user: User | null;

  // JWT access token (null if not authenticated)
  token: string | null;

  // Loading states
  isLoading: boolean;      // Initial auth check (token validation)
  isSubmitting: boolean;   // Login/register in progress

  // Error state
  error: string | null;    // Authentication error message
}
```

**State Transitions**:
1. **Initial**: `{ isAuthenticated: false, user: null, token: null, isLoading: true, isSubmitting: false, error: null }`
2. **Authenticated**: `{ isAuthenticated: true, user: <User>, token: <string>, isLoading: false, isSubmitting: false, error: null }`
3. **Unauthenticated**: `{ isAuthenticated: false, user: null, token: null, isLoading: false, isSubmitting: false, error: null }`
4. **Submitting**: `{ ..., isSubmitting: true, error: null }`
5. **Error**: `{ ..., isSubmitting: false, error: <string> }`

**Actions** (Context methods):
- `login(email: string, password: string): Promise<void>` - Authenticate user
- `register(data: RegisterData): Promise<void>` - Create new account
- `logout(): void` - Clear authentication state
- `clearError(): void` - Clear error message

### 2. User Entity

**Purpose**: Represents an authenticated user

**Structure**:
```typescript
interface User {
  // User identification
  id: number;              // Backend user ID (primary key)
  email: string;           // User email (unique identifier)

  // User profile
  name: string;            // Full name or display name
  role: 'doctor' | 'patient';  // User role (enum)

  // Optional metadata (future expansion)
  avatar?: string;         // Profile picture URL (future)
  createdAt?: string;      // Account creation date (ISO 8601)
}
```

**Validation Rules**:
- `id`: Positive integer
- `email`: Valid email format, lowercase
- `name`: Non-empty string, 2-100 characters
- `role`: Must be exactly 'doctor' or 'patient'

**Source**: Backend API response from `/api/auth/login/` or `/api/auth/register/`

### 3. Login Form Data

**Purpose**: Login form state and validation

**Structure**:
```typescript
interface LoginFormData {
  email: string;           // Required, email format
  password: string;        // Required, min 1 char (any password accepted for login)
}
```

**Validation Rules**:
- `email`: Required, must match email regex pattern
- `password`: Required, min 1 character (no strength requirement for login)

**Default Values**:
```javascript
{
  email: '',
  password: ''
}
```

### 4. Register Form Data

**Purpose**: Registration form state and validation

**Structure**:
```typescript
interface RegisterFormData {
  name: string;            // Required, 2-100 chars
  email: string;           // Required, email format, unique
  password: string;        // Required, min 8 chars, strength rules
  passwordConfirm: string; // Required, must match password
  role: 'doctor' | 'patient';  // Required, enum
}
```

**Validation Rules**:
- `name`: Required, 2-100 characters, trim whitespace
- `email`: Required, valid email format, lowercase
- `password`: Required, min 8 characters, must contain:
  - At least one letter (a-z or A-Z)
  - At least one number (0-9)
- `passwordConfirm`: Required, must match `password` field exactly
- `role`: Required, must be 'doctor' or 'patient'

**Default Values**:
```javascript
{
  name: '',
  email: '',
  password: '',
  passwordConfirm: '',
  role: 'patient'  // Default to patient role
}
```

### 5. Navigation Menu Item

**Purpose**: Sidebar menu item configuration

**Structure**:
```typescript
interface MenuItem {
  label: string;           // Display text (e.g., "Dashboard")
  path: string;            // Route path (e.g., "/doctor/dashboard")
  icon: string;            // Icon name from lucide-react (e.g., "LayoutDashboard")
  badge?: number;          // Optional badge count (e.g., notifications)
  roles: ('doctor' | 'patient')[];  // Roles that can see this item
}
```

**Example**:
```javascript
{
  label: 'Dashboard',
  path: '/doctor/dashboard',
  icon: 'LayoutDashboard',
  roles: ['doctor']
}
```

**Menu Configuration** (see `roleHelpers.js`):
- Doctor menu: Dashboard, Patients, Analytics, Reports, Settings
- Patient menu: Dashboard, My Data, Sessions, Progress, Settings

### 6. Layout State

**Purpose**: UI state for responsive layout

**Structure**:
```typescript
interface LayoutState {
  isMobileMenuOpen: boolean;   // Mobile menu overlay visibility
  sidebarCollapsed: boolean;   // Desktop sidebar collapsed state (future)
}
```

**Default Values**:
```javascript
{
  isMobileMenuOpen: false,
  sidebarCollapsed: false
}
```

**State Management**: Local state in `AppLayout.jsx` (no Context needed)

## Client-Side Storage Schema

### localStorage Keys

**Purpose**: Persist authentication state across browser sessions

**Keys**:
1. `tremoai_token` (string | null) - JWT access token
2. `tremoai_user` (string | null) - JSON-stringified User object

**Storage Operations**:
- **Set token**: `localStorage.setItem('tremoai_token', token)`
- **Get token**: `localStorage.getItem('tremoai_token')`
- **Remove token**: `localStorage.removeItem('tremoai_token')`
- **Set user**: `localStorage.setItem('tremoai_user', JSON.stringify(user))`
- **Get user**: `JSON.parse(localStorage.getItem('tremoai_user') || 'null')`
- **Clear all**: `localStorage.clear()` (on logout)

**Security Notes**:
- Vulnerable to XSS (acceptable for graduation project scope)
- No sensitive data beyond JWT token stored
- Token expiration enforced server-side
- Auto-logout on 401 responses

## API Request/Response Models

### Login Request

**Endpoint**: `POST /api/auth/login/`

**Request Body**:
```typescript
{
  email: string;     // Required
  password: string;  // Required
}
```

**Success Response** (200):
```typescript
{
  access: string;    // JWT access token
  refresh: string;   // JWT refresh token (not used in P1-P4)
  user: {
    id: number;
    email: string;
    name: string;
    role: 'doctor' | 'patient';
  }
}
```

**Error Response** (400, 401):
```typescript
{
  error: string;     // Error message (e.g., "Invalid credentials")
}
```

### Register Request

**Endpoint**: `POST /api/auth/register/`

**Request Body**:
```typescript
{
  name: string;      // Required, 2-100 chars
  email: string;     // Required, unique
  password: string;  // Required, min 8 chars
  role: 'doctor' | 'patient';  // Required
}
```

**Success Response** (201):
```typescript
{
  id: number;        // New user ID
  email: string;
  name: string;
  role: 'doctor' | 'patient';
  message: string;   // Success message (e.g., "Account created successfully")
}
```

**Error Response** (400):
```typescript
{
  error: string;     // Error message (e.g., "Email already exists")
  field_errors?: {   // Optional field-specific errors
    email?: string[];
    password?: string[];
    name?: string[];
  }
}
```

### Logout

**Implementation**: Client-side only (no backend endpoint needed)

**Actions**:
1. Clear `localStorage` (token and user)
2. Reset `AuthContext` state
3. Redirect to `/login`

## Data Flow Diagrams

### Login Flow

```
User → LoginPage → LoginForm → authService.login()
                                    ↓
                                POST /api/auth/login/
                                    ↓
                            Backend validates credentials
                                    ↓
                        Success: { access, refresh, user }
                                    ↓
                    AuthContext.login() → setToken(), setUser()
                                    ↓
                            localStorage.setItem(token, user)
                                    ↓
                        Navigate to role-based dashboard
```

### Register Flow

```
User → RegisterPage → RegisterForm → authService.register()
                                          ↓
                                  POST /api/auth/register/
                                          ↓
                                  Backend creates user
                                          ↓
                              Success: { id, email, name, role }
                                          ↓
                              Navigate to /login with success message
                                          ↓
                              User logs in (see Login Flow)
```

### Protected Route Access Flow

```
User → Navigate to protected route (e.g., /dashboard)
                ↓
        ProtectedRoute component
                ↓
        Check isAuthenticated (AuthContext)
                ↓
        ┌─────────────────┬─────────────────┐
        │  Authenticated  │ Unauthenticated │
        └─────────────────┴─────────────────┘
                ↓                     ↓
        Render children     Navigate to /login
            (Dashboard)      (save attempted URL)
```

### Token Expiration Flow

```
User → Make API request (e.g., fetch data)
                ↓
        Axios request interceptor adds Authorization header
                ↓
        Backend validates JWT token
                ↓
        ┌───────────────────┬────────────────────┐
        │  Token valid      │  Token expired     │
        └───────────────────┴────────────────────┘
                ↓                       ↓
        Return data (200)      Return error (401)
                                        ↓
                            Axios response interceptor catches 401
                                        ↓
                                AuthContext.logout()
                                        ↓
                                Clear localStorage
                                        ↓
                            Navigate to /login with message
```

## State Management Summary

**Global State** (React Context):
- `AuthContext`: Authentication state (user, token, isAuthenticated)

**Local Component State**:
- `LoginForm`: Form data, validation errors, submit status
- `RegisterForm`: Form data, validation errors, submit status
- `AppLayout`: Mobile menu open/closed, sidebar collapsed
- `Sidebar`: Active route highlighting

**Persistent State** (localStorage):
- JWT access token
- User object (id, email, name, role)

**Server State** (fetched from backend):
- User profile data (future: extended profile info)
- Menu item counts/badges (future: notification counts)

## Validation Summary

**Client-Side Validation** (React Hook Form):
- Email format
- Password strength (registration only)
- Password confirmation match
- Required fields
- Character limits (name: 2-100 chars)

**Server-Side Validation** (Django backend):
- Email uniqueness
- Password hashing
- SQL injection prevention
- Rate limiting (future)

**Error Display**:
- Inline errors below form fields (field-specific)
- Toast/alert for API errors (global errors)
- 401 errors trigger automatic logout

## Future Enhancements (Out of Scope for P1-P4)

- Token refresh mechanism (automatic renewal before expiration)
- Remember me (extended session persistence)
- Email verification (confirm email before activation)
- Password reset flow (forgot password)
- Multi-factor authentication (2FA)
- User profile editing (change name, avatar, password)
- OAuth2 social login (Google, Facebook)
- Audit log (login history, device tracking)
