# حساب‌بان (Hesabban)

حساب‌بان یک وب‌اپلیکیشن ساده و متمرکز برای مدیریت مالی ساختمان‌های مسکونی است: واحدها، ساکنان، شارژها، پرداخت‌ها، هزینه‌ها، دفتر مالی، درخواست‌های تعمیرات، فاکتور و رسید PDF و خروجی اکسل.

کل رابط کاربری فارسی و راست‌به‌چپ (RTL) است، تقویم شمسی و واحد پول تومان است. سیستم طراحی «شیشه مایع» (Liquid Glass) با حالت روشن/تاریک، فونت وزیرمتن سلف‌هاست و تعاملات HTMX + Alpine.js بدون رفرش صفحه.

این ابزار برای یک مدیر ساختمان است؛ **لاگین و نقش ندارد** و هر کاربر دسترسی کامل دارد. دیتابیس SQLite و بدون هیچ سرویس خارجی است.

## معماری

- **فریمورک:** Python 3.12+، Django 5، قالب‌های سمت سرور
- **دیتابیس:** SQLite (پیش‌فرض جنگو، بدون تنظیمات)
- **تعامل:** HTMX + Alpine.js (سلف‌هاست، بدون CDN)
- **طراحی:** CSS سفارشی با توکن‌های طراحی (`static/css/app.css`)، فونت وزیرمتن (`static/fonts/`)
- **PDF:** ReportLab + arabic-reshaper + python-bidi (فارسی RTL با وزیرمتن)
- **اکسل:** openpyxl — **تقویم:** jdatetime (ذخیره میلادی، نمایش شمسی)
- **استاتیک در محیط واقعی:** WhiteNoise — **تست:** pytest + pytest-django

| اپ | مسئولیت |
|---|---|
| `buildings` | ساختمان، واحد، ساکن + داشبورد |
| `charges` | قوانین شارژ، صورتحساب دوره‌ای، صورتحساب دستی |
| `payments` | پرداخت، تخصیص FIFO، ابطال/ویرایش |
| `expenses` | هزینه‌ها |
| `ledger` | دفتر مالی فقط-الحاقی و محاسبه مانده |
| `maintenance` | درخواست‌های تعمیرات |
| `invoices` | PDF فاکتور/رسید و خروجی اکسل |

### مدل‌های اصلی

`Building` · `Unit` · `Resident` · `ChargeRule` · `Charge` · `ChargeItem` · `Payment` · `Allocation` · `Expense` · `LedgerEntry` · `MaintenanceRequest`

### منطق مالی (سرویس‌ها)

منطق مالی در توابع سرویس است، نه در ویو یا قالب:

- `charges.services`: `compute_unit_items`، `preview_billing`، `generate_charges`، `create_manual_charge`، `update_manual_charge`، `cancel_charge`
- `payments.services`: `record_payment`، `void_payment`، `update_payment`، `unit_balance`
- `expenses.services`: `record_expense`، `update_expense`، `delete_expense`
- `ledger.services`: `post_entry`، `remove_entries`، `building_summary`

قواعد تضمین‌شده: مبالغ `DecimalField` (هرگز float) · صورتحساب اسنپ‌شات و مستقل از تغییر قوانین بعدی · عملیات چندمدلی در `transaction.atomic` · دفتر مالی فقط از طریق سرویس‌ها · جلوگیری از دوره تکراری با Constraint دیتابیس (`unique_billing_period_per_unit`).

## اجرا

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo      # داده نمونه (ساختمان گلستان)
.venv/bin/python manage.py runserver
```

سپس `http://127.0.0.1:8000` را باز کنید. برای پنل مدیریتی جنگو (`/admin/`) با کاربر `admin`:

```bash
.venv/bin/python manage.py createsuperuser
```

## ویژگی‌ها

- ساختمان‌ها و واحدها: ایجاد، ویرایش، حذف + ساکنان هر واحد
- قوانین شارژ: ثابت، متراژ، سرانه، پارکینگ، انباری، اضافه، تخفیف
- صدور صورتحساب دوره‌ای با پیش‌نمایش، جلوگیری از تکرار و اسنپ‌شات ردیف‌ها
- صورتحساب دستی (ارزیابی ویژه) برای یک واحد با ویرایش/ابطال؛ ویرایش شارژ دارای پرداخت مسدود می‌شود
- ثبت پرداخت با تخصیص خودکار FIFO به بدهی‌های باز و وضعیت شارژ (پرداخت نشده/جزئی/کامل/ابطال)
- ویرایش و ابطال پرداخت با بازگشت تخصیص‌ها، اصلاح وضعیت شارژها و اصلاح دفتر مالی
- هزینه‌ها با دسته، فروشنده، روش پرداخت، شماره پیگیری و پیوست + ویرایش/حذف با اصلاح دفتر
- دفتر مالی فقط-الحاقی با محاسبه مستقیم مانده صندوق و بدهی جاری
- درخواست‌های تعمیرات با وضعیت (در انتظار، در حال انجام، انجام شد، رد شد)
- داشبورد ساختمان: مانده صندوق، بدهی واحدی، نمودار درآمد/هزینه، وضعیت واحدها
- فاکتور و رسید PDF فارسی (وزیرمتن + RTL) و خروجی اکسل پرداخت‌ها و هزینه‌ها
- طراحی Liquid Glass، حالت روشن/تاریک، ریسپانسیو، Toast و مودال شیشه‌ای

## تست‌ها

```bash
.venv/bin/python -m pytest
```

۷ تست روی منطق مالی: محاسبه ردیف‌های شارژ، جلوگیری از دوره تکراری (سرویس + Constraint)، اسنپ‌شات شارژ، تخصیص پرداخت و مانده، ابطال پرداخت و اصلاح دفتر، ویرایش/حذف هزینه و اصلاح دفتر، جریان صورتحساب دستی.

## استقرار (Deployment)

متغیرهای محیطی:

- `DJANGO_SECRET_KEY` — کلید امن (الزامی در محیط واقعی)
- `DJANGO_DEBUG` — `1` فقط برای توسعه؛ پیش‌فرض `0`
- `DJANGO_ALLOWED_HOSTS` — میزبان‌های اضافه، جداشده با کاما

Build & start:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn hesabban.wsgi:application --bind 0.0.0.0:$PORT
```

نکته‌ها:

- فایل‌های استاتیک با WhiteNoise از همان gunicorn سرو می‌شوند؛ اجرای `collectstatic` در Build الزامی است (`STATIC_ROOT` روی `staticfiles/`).
- `db.sqlite3` و `media/` به گیت کامیت نمی‌شوند؛ در محیط واقعی از دیسک پایدار میزبان استفاده کنید.
- نمونه Render: Build = `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`، Start = `gunicorn hesabban.wsgi:application --bind 0.0.0.0:$PORT`، Health Check = `/`.

## مسیرهای اصلی

- `buildings/<id>/` داشبورد — `buildings/<id>/units/` واحدها و ساکنان
- `billing/buildings/<id>/billing/` صدور صورتحساب — `billing/buildings/<id>/charges/` شارژها
- `payments/buildings/<id>/payments/` پرداخت‌ها — `units/<id>/finance/` وضعیت مالی واحد
- `expenses/buildings/<id>/expenses/` هزینه‌ها — `ledger/buildings/<id>/ledger/` دفتر مالی
- `maintenance/buildings/<id>/maintenance/` تعمیرات
- `invoices/charge/<id>.pdf` فاکتور — `invoices/receipt/<id>.pdf` رسید — `invoices/export/{payments,expenses}/<id>.xlsx` اکسل

## محدودیت‌ها

- بدون لاگین/نقش (بر اساس نیاز پروژه)؛ `/admin/` فقط ابزار مدیریتی اپراتور است
- SQLite تک‌فایلی؛ مناسب یک اپراتور، نه استقرار چندسازمانی
- PDF با ReportLab تولید می‌شود (WeasyPrint روی این محیط نصب نشد؛ خروجی معادل با RTL و وزیرمتن است)
