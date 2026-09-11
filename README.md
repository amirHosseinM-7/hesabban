## اجرا

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo      # داده نمونه
.venv/bin/python manage.py runserver
```

تست‌ها:

```bash
.venv/bin/python -m pytest
```

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

نکته: `STATIC_ROOT` روی `staticfiles/` تنظیم است؛ اگر میزبان (مثل Render) فایل استاتیک را خودش سرو کند، پوشه Static File Path را روی `staticfiles` تنظیم کنید. فایل `db.sqlite3` و پوشه `media/` به گیت کامیت نمی‌شوند و پایداری فایل‌های آپلودی به سیاست میزبان بستگی دارد.
