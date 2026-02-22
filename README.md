# TremoAI Web Platform

Graduation project providing doctors with real-time monitoring for patients using smart wearable gloves for Parkinson's tremor suppression.

## Project Structure

This is a monorepo with:
- `backend/` - Django 5.x + Django REST Framework + Django Channels
- `frontend/` - React 18+ + Vite + Tailwind CSS

## Frontend Setup

### Prerequisites

- Node.js 18+ and npm
- Backend running at `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Environment Configuration

Create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### Running the Frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Features Implemented

### Feature 009: Frontend Authentication & Layout

✅ **User Story 1 (P1)** - User Login with JWT Authentication
- Login page with email/password form
- JWT token management and secure storage
- Role-based redirects (doctor/patient dashboards)
- Token persistence across browser refreshes

✅ **User Story 2 (P2)** - User Registration
- Registration page with role selection
- Form validation (React Hook Form)
- Success messages and error handling

✅ **User Story 3 (P3)** - Protected Routes & Role-Based Access
- Route guards preventing unauthorized access
- Automatic redirects for unauthenticated users
- Post-login redirect to originally attempted URL
- Token expiration handling with auto-logout

✅ **User Story 4 (P4)** - Responsive Layout with Role-Based Navigation
- Responsive sidebar (desktop persistent, mobile hamburger)
- Top bar with user info and logout
- Role-based menu items (doctor vs patient)
- Active route highlighting

## Tech Stack

### Frontend
- **Framework**: React 18+ with Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router v6
- **Forms**: React Hook Form
- **HTTP Client**: Axios
- **Icons**: Lucide React
- **State Management**: React Context API

### Backend
- **Framework**: Django 5.x
- **API**: Django REST Framework
- **Authentication**: JWT (SimpleJWT)
- **Database**: Supabase PostgreSQL
- **Real-time**: Django Channels (WebSocket)

## User Roles

- **Doctor**: Monitor patients, view analytics, generate reports
- **Patient**: View personal data, track sessions, monitor progress

## Development Notes

- All secrets stored in `.env` files (never committed)
- JWT tokens stored in localStorage (acceptable for graduation project scope)
- Modern browser support only (Chrome, Firefox, Safari, Edge - last 2 versions)
- Local development only (no Docker/CI/CD in this phase)

## Testing the Feature

### Manual Testing Checklist

**Authentication:**
- [ ] Login with valid doctor credentials → redirects to doctor dashboard
- [ ] Login with valid patient credentials → redirects to patient dashboard
- [ ] Login with invalid credentials → shows error message
- [ ] Register new account → success, redirects to login

**Protected Routes:**
- [ ] Access `/doctor/dashboard` logged out → redirects to `/login`
- [ ] Log in, then access originally attempted URL → success
- [ ] Token expiration → automatic logout

**Layout & Navigation:**
- [ ] Doctor sees doctor-specific menu (Patients, Analytics, Reports)
- [ ] Patient sees patient-specific menu (My Data, Sessions, Progress)
- [ ] Mobile: Sidebar collapses to hamburger menu
- [ ] Active route highlighted in sidebar
- [ ] Logout button works

**Browser Refresh:**
- [ ] Logged in, refresh page → still logged in
- [ ] On protected route, refresh → stays on same route

## Next Steps

- Implement actual dashboard pages (currently placeholders)
- Add password reset functionality
- Implement email verification
- Add real-time tremor data visualization
- Connect MQTT sensor data integration

## License

Graduation Project - TremoAI Platform
