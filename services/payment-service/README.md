# Payment Service

Handles payment processing, transactions, and retry logic. Integrates with Notification Service for alerts.

## Quick Start

```bash
pip install -r requirements.txt
python src/main.py
```

Service runs on `http://localhost:8003`

## API Endpoints

### Health Check
- `GET /health` - Service health

### Payment Management
- `POST /payments/process` - Process a payment
- `GET /payments/{payment_id}` - Get payment details
- `GET /payments?user_id={user_id}` - List payments

### Advanced
- `POST /payments/process-with-retry` - Process payment with retry logic (exponential backoff)
- `GET /transactions/{transaction_id}` - Get transaction record

## Architecture

- **Framework**: FastAPI
- **Runtime**: Async (Python 3.10+)
- **Data**: Mock in-memory store
- **Port Integration**: Owned by `platform-team`

## Dependencies

- **Notification Service** (http://localhost:8002) - for failure alerts
- Used by: User Profile Service (future)

## Tech Stack

- Python 3.10+
- FastAPI 0.104+
- Pydantic 2.5+
- httpx (async HTTP client)

## Key Models

- `PaymentRequest` - Payment to process
- `PaymentResponse` - Payment with status
- `PaymentStatus` - PENDING, PROCESSING, COMPLETED, FAILED
- `TransactionRecord` - Transaction history

## Retry Pattern

The `process-with-retry` endpoint demonstrates the retry logic pattern that agents will implement:

```python
# Retry with exponential backoff
backoff_delays = [1, 5, 30]  # seconds
for attempt in range(1, max_retries + 1):
    try:
        # Process payment
        return payment_result
    except Exception:
        if attempt == max_retries:
            # Notify user of final failure
            notify_payment_failure()
            raise
        # Backoff and retry
        await asyncio.sleep(backoff_delays[attempt - 1])
```

## Integration with Notification Service

On payment failure after retries:
```
POST http://localhost:8002/notifications/alert-payment-failure
  user_id: str
  payment_id: str
  error: str
  attempts: int
```

## Future: Agent Implementation

The Developer Agent will add retry logic to the core `process` endpoint following this pattern.
