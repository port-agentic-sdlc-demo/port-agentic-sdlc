"""Notification Service - Sends notifications via email, SMS, webhooks."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import uuid

app = FastAPI(
    title="Notification Service",
    description="Handles notifications (email, SMS, webhooks)",
    version="1.0.0"
)

# Mock notification store
notifications_db = {}

# Models
class NotificationType(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"

class NotificationRequest(BaseModel):
    recipient: str
    type: NotificationType
    subject: str
    body: str
    metadata: dict = None

class NotificationResponse(BaseModel):
    id: str
    recipient: str
    type: NotificationType
    subject: str
    body: str
    status: str
    created_at: datetime

# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "notification-service"}

@app.post("/notifications/send", response_model=NotificationResponse)
async def send_notification(request: NotificationRequest):
    """Send a notification."""
    notification_id = str(uuid.uuid4())
    notification = {
        "id": notification_id,
        "recipient": request.recipient,
        "type": request.type,
        "subject": request.subject,
        "body": request.body,
        "status": "sent",
        "created_at": datetime.now(),
        "metadata": request.metadata or {}
    }
    notifications_db[notification_id] = notification
    return notification

@app.get("/notifications/{notification_id}", response_model=NotificationResponse)
async def get_notification(notification_id: str):
    """Get notification status."""
    if notification_id not in notifications_db:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notifications_db[notification_id]

@app.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(recipient: str = None):
    """List notifications, optionally filtered by recipient."""
    results = list(notifications_db.values())
    if recipient:
        results = [n for n in results if n["recipient"] == recipient]
    return results

@app.post("/notifications/alert-payment-failure")
async def alert_payment_failure(user_id: str, payment_id: str, error: str, attempts: int):
    """Alert user of payment failure (called by payment service)."""
    notification_id = str(uuid.uuid4())
    notification = {
        "id": notification_id,
        "recipient": user_id,
        "type": "email",
        "subject": f"Payment Failed - Order {payment_id}",
        "body": f"Your payment failed after {attempts} retry attempts. Error: {error}",
        "status": "sent",
        "created_at": datetime.now(),
        "metadata": {"payment_id": payment_id, "error": error}
    }
    notifications_db[notification_id] = notification
    return notification

@app.post("/notifications/alert-user-profile-created")
async def alert_user_profile_created(user_id: str, profile_id: str):
    """Alert user when profile is created (called by user-profile service)."""
    notification_id = str(uuid.uuid4())
    notification = {
        "id": notification_id,
        "recipient": user_id,
        "type": "email",
        "subject": "Profile Created Successfully",
        "body": f"Your profile {profile_id} has been created successfully.",
        "status": "sent",
        "created_at": datetime.now(),
        "metadata": {"profile_id": profile_id}
    }
    notifications_db[notification_id] = notification
    return notification

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
