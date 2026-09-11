from django import template

from buildings.jalali import format_jalali, JALALI_MONTHS, to_fa_digits

register = template.Library()


@register.filter
def fa(value):
    """Convert digits to Persian digits."""
    return to_fa_digits(value)


@register.filter
def money(value):
    """Format a Decimal amount with thousand separators and Persian digits."""
    if value in (None, ""):
        return ""
    try:
        quantized = Decimal(value).quantize(Decimal("1"))
    except Exception:
        return to_fa_digits(value)
    return to_fa_digits(f"{quantized:,}")


from decimal import Decimal  # noqa: E402  (kept next to money())


@register.filter
def toman(value):
    amount = money(value)
    return f"{amount} تومان" if amount != "" else ""


@register.filter
def jdate(value):
    if not value:
        return ""
    return to_fa_digits(format_jalali(value))


@register.filter
def month_name(month):
    try:
        return JALALI_MONTHS[int(month) - 1]
    except (TypeError, ValueError, IndexError):
        return ""
