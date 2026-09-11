"""Jalali (Persian) calendar helpers and Persian digit conversion."""
import datetime

import jdatetime

JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
EN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def to_fa_digits(value):
    return str(value).translate(FA_DIGITS)


def to_en_digits(value):
    return str(value).translate(EN_DIGITS)


def to_jalali(date):
    return jdatetime.date.fromgregorian(date=date)


def format_jalali(date):
    if date is None:
        return ""
    j = to_jalali(date)
    return f"{j.year}/{j.month:02d}/{j.day:02d}"


def parse_jalali(text):
    """Parse '1404/05/12' (Persian or Latin digits) into a Gregorian date."""
    text = to_en_digits((text or "").strip()).replace("-", "/").replace(".", "/")
    parts = text.split("/")
    if len(parts) != 3:
        raise ValueError("تاریخ باید به شکل ۱۴۰۴/۰۵/۱۲ وارد شود.")
    year, month, day = (int(p) for p in parts)
    return jdatetime.date(year, month, day).togregorian()


def jalali_month_label(year, month):
    return f"{JALALI_MONTHS[month - 1]} {year}"


def current_jalali():
    today = jdatetime.date.today()
    return today.year, today.month, today.day


def jalali_today():
    return jdatetime.date.today().togregorian()
