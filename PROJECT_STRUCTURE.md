# Health Data Exchange Project Structure

## Project Organization

This document outlines the current project structure and recent reorganization efforts to improve code maintainability and reduce redundancy.

### Directory Structure

```
├── app/                  # Next.js application (main frontend)
│   ├── components/       # React components
│   ├── context/          # React context providers
│   ├── services/         # API and utility services
│   └── ...               # Pages and other Next.js files
│
├── backend/              # FastAPI backend
│   ├── routers/          # API route definitions
│   ├── models/           # Database models
│   ├── services/         # Business logic services
│   └── ...               # Utility files and configuration
│
├── docs/                 # Project documentation
└── public/               # Static assets
```

## Recent Reorganization

### Authentication Context

- Consolidated duplicate AuthContext implementations
- Standardized on `app/context/AuthContext.jsx` as the primary implementation
- Created compatible implementation for frontend components in `frontend/src/contexts/AuthContext.js`

### Backend Tests

- Original backend tests were located in `backend/tests/` and have been removed in this cleaned project version.

### Frontend Consolidation

- Copied components from `frontend/src/components/` to `app/components/`
- Converted .js files to .jsx for Next.js compatibility
- Copied services from `frontend/src/services/` to `app/services/`
- Copied tests from `frontend/src/tests/` to `app/tests/` (tests have since been removed from the cleaned project)

## Development Guidelines

### Component Development

- Place all new React components in `app/components/`
- Use `.jsx` extension for all React components
- Follow existing naming conventions

### Authentication

- Use `useAuth()` hook from `app/context/AuthContext.jsx` for authentication
- The hook provides: `{ user, login, logout, loading, isAuthenticated }`

### API Services

- Place API service functions in `app/services/`
- Use the API endpoints defined in `app/config/api.js`

### Testing

- Backend tests should be placed in `backend/tests/`
- Frontend tests should be placed in `app/tests/`

## Future Improvements

1. Complete real-time collaboration features (WebSockets)
2. Finish advanced analytics implementation (federated learning)
3. Prepare production deployment configuration
4. Implement remaining security features
5. Complete documentation