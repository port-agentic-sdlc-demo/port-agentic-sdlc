"""Payment Service - Handles payment processing and transactions."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import uuid
import httpx
import asyncio
import logging
import time

app = FastAPI(
    title="Payment Service",
    description="Handles payment processing and transactions",
    version="1.0.0"
)

# Structured logger for the retry flow. Fields are passed via `extra` so a
# JSON formatter can emit them. No handler/config is installed here.
logger = logging.getLogger("payment_service.retry")

_MAX_ERROR_MESSAGE_LEN = 200


def _safe_log(level: int, event: str, **fields) -> None:
    """Emit a structured log record. Never raises, so logging can't change payment results."""
    try:
        logger.log(level, event, extra={"event": event, **fields})
    except Exception:
        pass


def _short_error(e: Exception) -> str:
    """Shortened exception message. Request bodies and payment data are never logged."""
    try:
        return str(e)[:_MAX_ERROR_MESSAGE_LEN]
    except Exception:
        return ""


def _elapsed_ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 2)

# Mock data stores
payments_db = {}
transactions_db = {}

# Models
class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class PaymentRequest(BaseModel):
    user_id: str
    amount: float
    currency: str = "USD"
    description: str

class PaymentResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    currency: str
    status: PaymentStatus
    created_at: datetime
    transaction_id: str = None

class TransactionRecord(BaseModel):
    id: str
    payment_id: str
    status: str
    timestamp: datetime
    details: dict = None

# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "payment-service"}

@app.post("/payments/process", response_model=PaymentResponse)
async def process_payment(request: PaymentRequest):
    """Process a payment."""
    payment_id = str(uuid.uuid4())
    transaction_id = str(uuid.uuid4())

    payment = {
        "id": payment_id,
        "user_id": request.user_id,
        "amount": request.amount,
        "currency": request.currency,
        "status": "completed",
        "created_at": datetime.now(),
        "transaction_id": transaction_id
    }
    payments_db[payment_id] = payment

    # Record transaction
    transaction = {
        "id": transaction_id,
        "payment_id": payment_id,
        "status": "completed",
        "timestamp": datetime.now(),
        "details": {"amount": request.amount, "currency": request.currency}
    }
    transactions_db[transaction_id] = transaction

    return payment

@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str):
    """Get payment details."""
    if payment_id not in payments_db:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payments_db[payment_id]

@app.get("/payments", response_model=list[PaymentResponse])
async def list_payments(user_id: str = None):
    """List payments, optionally filtered by user."""
    results = list(payments_db.values())
    if user_id:
        results = [p for p in results if p["user_id"] == user_id]
    return results

@app.get("/transactions/{transaction_id}", response_model=TransactionRecord)
async def get_transaction(transaction_id: str):
    """Get transaction record."""
    if transaction_id not in transactions_db:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transactions_db[transaction_id]


def _attempt_payment(payment_id: str, request: PaymentRequest, attempt: int) -> dict:
    """Single simulated payment attempt (unchanged logic, extracted as a test seam)."""
    transaction_id = str(uuid.uuid4())
    payment = {
        "id": payment_id,
        "user_id": request.user_id,
        "amount": request.amount,
        "currency": request.currency,
        "status": "completed",
        "created_at": datetime.now(),
        "transaction_id": transaction_id,
        "attempts": attempt
    }
    payments_db[payment_id] = payment
    return payment


@app.post("/payments/process-with-retry")
async def process_payment_with_retry(request: PaymentRequest, max_retries: int = 3):
    """
    Process payment with retry logic (exponential backoff).
    This endpoint demonstrates the pattern agents will implement.
    """
    payment_id = str(uuid.uuid4())
    backoff_delays = [1, 5, 30]
    start = time.monotonic()

    for attempt in range(1, max_retries + 1):
        try:
            # Simulate payment processing
            payment = _attempt_payment(payment_id, request, attempt)

            if attempt > 1:
                _safe_log(
                    logging.INFO,
                    "payment.retry.succeeded",
                    payment_id=payment_id,
                    transaction_id=payment.get("transaction_id"),
                    attempt=attempt,
                    max_attempts=max_retries,
                    duration_ms=_elapsed_ms(start),
                    outcome="success",
                )
            else:
                _safe_log(
                    logging.DEBUG,
                    "payment.process.succeeded",
                    payment_id=payment_id,
                    transaction_id=payment.get("transaction_id"),
                    attempt=attempt,
                    max_attempts=max_retries,
                    duration_ms=_elapsed_ms(start),
                    outcome="success",
                )
            return payment

        except Exception as e:
            if attempt == max_retries:
                _safe_log(
                    logging.ERROR,
                    "payment.retry.exhausted",
                    payment_id=payment_id,
                    attempt=attempt,
                    max_attempts=max_retries,
                    duration_ms=_elapsed_ms(start),
                    outcome="failure",
                    error_type=type(e).__name__,
                    error_message=_short_error(e),
                )

                # Final failure - notify user
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            "http://localhost:8002/notifications/alert-payment-failure",
                            params={
                                "user_id": request.user_id,
                                "payment_id": payment_id,
                                "error": str(e),
                                "attempts": attempt
                            }
                        )
                except:
                    pass

                failure_payment = {
                    "id": payment_id,
                    "user_id": request.user_id,
                    "amount": request.amount,
                    "currency": request.currency,
                    "status": "failed",
                    "created_at": datetime.now(),
                    "transaction_id": None,
                    "attempts": attempt,
                    "error": str(e)
                }
                payments_db[payment_id] = failure_payment
                raise HTTPException(status_code=400, detail=f"Payment failed after {attempt} attempts")

            _safe_log(
                logging.DEBUG,
                "payment.retry.attempt_failed",
                payment_id=payment_id,
                attempt=attempt,
                max_attempts=max_retries,
                duration_ms=_elapsed_ms(start),
                outcome="failure",
                error_type=type(e).__name__,
                error_message=_short_error(e),
            )

            # Backoff and retry
            delay = backoff_delays[attempt - 1]
            await asyncio.sleep(delay)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
