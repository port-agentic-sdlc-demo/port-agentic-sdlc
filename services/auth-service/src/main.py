"""Auth Service - User authentication and authorization."""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid

app = FastAPI(
    title="Auth Service",
    description="Handles user authentication and authorization",
    version="1.0.0"
)

# Mock data store
users_db = {
    "user-001": {
        "id": "user-001",
        "email": "alice@example.com",
        "username": "alice",
        "hashed_password": "hashed_pwd_123",
        "created_at": datetime.now(),
        "is_active": True
    },
    "user-002": {
        "id": "user-002",
        "email": "bob@example.com",
        "username": "bob",
        "hashed_password": "hashed_pwd_456",
        "created_at": datetime.now(),
        "is_active": True
    }
}

# Models
class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class User(BaseModel):
    id: str
    email: str
    username: str
    created_at: datetime
    is_active: bool

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "auth-service"}

@app.post("/auth/register", response_model=User)
async def register(user_create: UserCreate):
    """Register a new user."""
    user_id = f"user-{str(uuid.uuid4())[:8]}"
    new_user = {
        "id": user_id,
        "email": user_create.email,
        "username": user_create.username,
        "hashed_password": f"hashed_{user_create.password}",
        "created_at": datetime.now(),
        "is_active": True
    }
    users_db[user_id] = new_user
    return new_user

@app.post("/auth/login", response_model=AuthToken)
async def login(credentials: LoginRequest):
    """Login and get access token."""
    user = None
    for u in users_db.values():
        if u["username"] == credentials.username:
            user = u
            break

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = f"token_{user['id']}_{int(datetime.now().timestamp())}"
    return {"access_token": token, "token_type": "bearer"}

@app.get("/auth/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    """Get user by ID."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[user_id]

@app.get("/auth/users", response_model=list[User])
async def list_users():
    """List all users."""
    return list(users_db.values())

@app.post("/auth/validate")
async def validate_token(token: str):
    """Validate an access token."""
    if not token.startswith("token_"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"valid": True, "token": token}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
