"""Persian RTL PDF documents (charge invoice, payment receipt) via ReportLab."""
from decimal import Decimal
from pathlib import Path

import jdatetime
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from django.conf import settings
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas

from buildings.jalali import format_jalali, to_fa_digits

FONT_DIR = Path(settings.BASE_DIR) / "static" / "fonts"
_REGISTERED = False

INK = HexColor("#1c1c1e")
MUTED = HexColor("#6e6e73")
ACCENT = HexColor("#0a84ff")
LINE = HexColor("#d8d8dc")


def _register_fonts():
    global _REGISTERED
    if _REGISTERED:
        return
    pdfmetrics.registerFont(TTFont("Vazirmatn", str(FONT_DIR / "Vazirmatn-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Vazirmatn-Bold", str(FONT_DIR / "Vazirmatn-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Vazirmatn-Medium", str(FONT_DIR / "Vazirmatn-Medium.ttf")))
    _REGISTERED = True


def par(text):
    """Shape and reorder Persian text for correct visual rendering."""
    return get_display(reshape(str(text)))


def money(value):
    return to_fa_digits(f"{Decimal(value).quantize(Decimal('1')):,}")


def toman(value):
    return f"{money(value)} تومان"


class Doc:
    """Small RTL drawing helper on top of a reportlab canvas."""

    def __init__(self, response):
        _register_fonts()
        self.c = pdfcanvas.Canvas(response, pagesize=A4)
        self.w, self.h = A4
        self.y = self.h - 60

    def text(self, value, x, y, size=11, font="Vazirmatn", color=INK, align="right"):
        c = self.c
        c.setFont(font, size)
        c.setFillColor(color)
        value = par(value)
        if align == "right":
            c.drawRightString(x, y, value)
        elif align == "center":
            c.drawCentredString(x, y, value)
        else:
            c.drawString(x, y, value)

    def header(self, building_name, doc_title, date):
        c = self.c
        w = self.w
        c.setFillColor(ACCENT)
        c.roundRect(w - 60, self.y - 14, 10, 34, 5, stroke=0, fill=1)
        self.text("حساب‌بان", w - 80, self.y + 8, size=20, font="Vazirmatn-Bold")
        self.text("سامانه مدیریت مالی ساختمان", w - 80, self.y - 10, size=9, color=MUTED)
        self.text(f"تاریخ: {to_fa_digits(format_jalali(date))}", 60, self.y + 8, size=10, color=MUTED, align="left")
        self.text(building_name, 60, self.y - 10, size=10, color=MUTED, align="left")
        self.y -= 40
        c.setStrokeColor(LINE)
        c.setLineWidth(0.7)
        c.line(50, self.y, w - 50, self.y)
        self.y -= 34
        self.text(doc_title, w / 2, self.y, size=14, font="Vazirmatn-Bold", align="center")
        self.y -= 30

    def info_row(self, pairs):
        x = self.w - 60
        for label, value in pairs:
            label_text = par(f"{label}: ")
            label_w = pdfmetrics.stringWidth(label_text, "Vazirmatn-Medium", 10)
            self.text(f"{label}: ", x, self.y, size=10, color=MUTED, font="Vazirmatn-Medium")
            self.text(str(value), x - label_w, self.y, size=10)
            x -= label_w + pdfmetrics.stringWidth(par(str(value)), "Vazirmatn", 10) + 34
        self.y -= 22

    def table(self, headers, rows, widths):
        """Draw a simple RTL table; widths are columns from the right edge."""
        c = self.c
        w = self.w
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.setFillColor(HexColor("#f5f5f7"))
        c.roundRect(50, self.y - 6, w - 100, 22, 6, stroke=0, fill=1)
        x = w - 50
        for i, header in enumerate(headers):
            self.text(header, x - 8, self.y, size=9, font="Vazirmatn-Medium", color=MUTED)
            x -= widths[i]
        self.y -= 26
        for row in rows:
            x = w - 50
            for i, cell in enumerate(row):
                self.text(str(cell), x - 8, self.y, size=9.5)
                x -= widths[i]
            self.y -= 20
            c.line(50, self.y + 6, w - 50, self.y + 6)
        self.y -= 10

    def kv_right(self, pairs):
        for label, value in pairs:
            self.text(f"{label}:", self.w - 60, self.y, size=10, color=MUTED, font="Vazirmatn-Medium")
            self.text(str(value), 60, self.y, size=10, align="left")
            self.y -= 20

    def total_band(self, label, value):
        c = self.c
        c.setFillColor(HexColor("#eef4ff"))
        c.roundRect(50, self.y - 10, self.w - 100, 30, 10, stroke=0, fill=1)
        self.text(label, self.w - 66, self.y, size=11, font="Vazirmatn-Bold")
        self.text(value, 66, self.y, size=11, font="Vazirmatn-Bold", color=ACCENT, align="left")
        self.y -= 32

    def save(self):
        self.text("این سند توسط حساب‌بان صادر شده است.", self.w / 2, 46, size=8.5, color=MUTED, align="center")
        self.c.showPage()
        self.c.save()


def charge_invoice(charge, response):
    from charges.services import period_label

    doc = Doc(response)
    doc.header(
        charge.building.name,
        f"صورتحساب شارژ {period_label(charge.year, charge.month)}",
        jdatetime.date.fromgregorian(date=charge.created_at),
    )
    residents = "، ".join(r.full_name for r in charge.unit.residents.filter(is_active=True)) or "—"
    doc.info_row([
        ("واحد", f"واحد {charge.unit.number}"),
        ("ساکنان", residents[:36]),
        ("متراژ", f"{to_fa_digits(f'{charge.unit.area:n}')} متر"),
    ])

    rows = [
        [
            to_fa_digits(i),
            item.title,
            to_fa_digits(f"{item.quantity:n}"),
            toman(item.unit_amount),
            toman(item.amount),
        ]
        for i, item in enumerate(charge.items.all(), start=1)
    ]
    if not rows:
        rows.append(["—", "قلمی ثبت نشده است", "—", "—", toman(charge.total_amount)])
    doc.table(["#", "شرح", "تعداد", "مبلغ واحد", "مبلغ"], rows, widths=[30, 200, 60, 115, 110])
    doc.y -= 6
    paid = charge.paid_amount()
    doc.kv_right([
        ("پرداخت‌شده", toman(paid)),
        ("مانده", toman(charge.total_amount - paid)),
    ])
    doc.total_band("جمع کل صورتحساب", toman(charge.total_amount))
    doc.save()


def payment_receipt(payment, response):
    from charges.services import period_label
    from payments.services import unit_balance

    unit = payment.unit
    doc = Doc(response)
    doc.header(unit.building.name, "رسید پرداخت", jdatetime.date.fromgregorian(date=payment.created_at))
    residents = "، ".join(r.full_name for r in unit.residents.filter(is_active=True)) or "—"
    doc.info_row([
        ("واحد", f"واحد {unit.number}"),
        ("ساکنان", residents[:36]),
    ])
    doc.info_row([
        ("تاریخ", to_fa_digits(format_jalali(payment.date))),
        ("روش", payment.get_method_display()),
    ])
    if payment.note:
        doc.info_row([("یادداشت", payment.note)])

    rows = [
        [
            f"شارژ {period_label(a.charge.year, a.charge.month)}",
            toman(a.charge.total_amount),
            toman(a.amount),
        ]
        for a in payment.allocations.select_related("charge")
    ]
    if not rows:
        rows.append(["بدون تخصیص", "—", toman(payment.amount)])
    doc.table(["بابت", "مبلغ شارژ", "مبلغ تخصیص"], rows, widths=[240, 130, 145])
    doc.y -= 6
    _, _, outstanding = unit_balance(unit)
    doc.kv_right([("مانده کل بدهی واحد", toman(outstanding))])
    doc.total_band("مبلغ پرداخت", toman(payment.amount))
    doc.save()

