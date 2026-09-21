from decimal import Decimal, ROUND_HALF_UP

def get_currency() -> str:
    """
    Returns the standard currency for the platform.
    """
    return "INR"

def quantize_money(amount) -> Decimal:
    """
    Safely converts an amount to a Decimal rounded to 2 decimal places.
    Uses ROUND_HALF_UP logic.
    """
    if amount is None:
        return Decimal("0.00")
    
    if not isinstance(amount, Decimal):
        try:
            # Convert float to str first to avoid precision issues before decimalizing
            if isinstance(amount, float):
                amount = str(amount)
            amount = Decimal(amount)
        except (ValueError, TypeError, ArithmeticError):
            amount = Decimal("0.00")
            
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def add_money(*amounts) -> Decimal:
    """
    Adds multiple monetary amounts and quantizes the final sum.
    """
    total = sum((quantize_money(a) for a in amounts), Decimal("0.00"))
    return quantize_money(total)

def subtract_money(minuend, subtrahend) -> Decimal:
    """
    Subtracts subtrahend from minuend and quantizes the result.
    """
    result = quantize_money(minuend) - quantize_money(subtrahend)
    return quantize_money(result)

def calculate_percentage(amount, percentage) -> Decimal:
    """
    Calculates a percentage of an amount and returns the quantized result.
    """
    amt = quantize_money(amount)
    pct = quantize_money(percentage)
    result = (amt * pct) / Decimal("100.00")
    return quantize_money(result)
