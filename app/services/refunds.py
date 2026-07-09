"""Refund bookkeeping.

When a booking is cancelled a refund is calculated from its price and the
applicable notice tier, then written to the refund ledger with a processed
status. Amounts are stored in whole cents.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..errors import AppError
from ..models import Booking, RefundLog


def log_refund(db: Session, booking: Booking, percent: int) -> RefundLog:
    if not 0 <= percent <= 100:
        raise AppError(400, "INVALID_REFUND_PERCENT", "percent must be between 0 and 100")

    # Integer-only math: multiply first, divide last, and round to the
    # nearest cent (rather than truncating) using integer floor division
    # with a manual round-half-up on cents.
    amount_cents, remainder = divmod(booking.price_cents * percent, 100)
    if remainder * 2 >= 100:
        amount_cents += 1

    entry = RefundLog(
        booking_id=booking.id,
        amount_cents=amount_cents,
        status="processed",
        processed_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(entry)
    return entry
