# Notification Service

Sends notifications via email, SMS, and webhooks. Provides async notification handling for other services.

## Quick Start

```bash
pip install -r requirements.txt
python src/main.py
```

Service runs on `http://localhost:8002`

## API Endpoints

### Health Check
- `GET /health` - Service health

### Notification Management
- `POST /notifications/send` - Send a notification
- `GET /notifications/{notification_id}` - Get notification status
- `GET /notifications?recipient={recipient}` - List notifications

### Domain-Specific Alerts
- `POST /notifications/alert-payment-failure` - Alert on payment failure (called by Payment Service)
- `POST /notifications/alert-user-profile-created` - Alert on profile creation (called by User Profile Service)

## Architecture

- **Framework**: FastAPI
- **Runtime**: Async (Python 3.10+)
- **Data**: Mock in-memory store
- **Port Integration**: Owned by `platform-team`

## Dependencies

- No external service dependencies
- Called by: Payment Service, User Profile Service

## Tech Stack

- Python 3.10+
- FastAPI 0.104+
- Pydantic 2.5+

## Key Models

- `NotificationRequest` - Notification to send
- `NotificationResponse` - Notification status
- `NotificationType` - EMAIL, SMS, WEBHOOK

## Integration Pattern

Services should call domain-specific endpoints:
```python
# From Payment Service
POST /notifications/alert-payment-failure
  user_id: str
  payment_id: str
  error: str
  attempts: int

# From User Profile Service
POST /notifications/alert-user-profile-created
  user_id: str
  profile_id: str
```

## Notification Types

- **EMAIL**: Email notifications (default)
- **SMS**: SMS alerts (mock)
- **WEBHOOK**: HTTP webhooks (mock)
