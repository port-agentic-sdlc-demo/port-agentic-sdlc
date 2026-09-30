# Auth Service

User authentication and authorization service. Handles user registration, login, and token validation.

## Quick Start

```bash
pip install -r requirements.txt
python src/main.py
```

Service runs on `http://localhost:8001`

## API Endpoints

### Health Check
- `GET /health` - Service health

### User Management
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get token
- `GET /auth/users/{user_id}` - Get user by ID
- `GET /auth/users` - List all users

### Token Validation
- `POST /auth/validate` - Validate access token

## Architecture

- **Framework**: FastAPI
- **Runtime**: Async (Python 3.10+)
- **Data**: Mock in-memory store
- **Port Integration**: Owned by `platform-team`

## Dependencies

- No external service dependencies (standalone)
- Used by: Payment Service, User Profile Service

## Tech Stack

- Python 3.10+
- FastAPI 0.104+
- Pydantic 2.5+

## Key Models

- `User` - User entity with email, username, created_at
- `AuthToken` - Access token response
- `LoginRequest` - Login credentials

## Integration Points

Other services can call:
- `GET /auth/users/{user_id}` to fetch user details
- `POST /auth/validate` to validate tokens
