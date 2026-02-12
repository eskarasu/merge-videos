# Pars Video Merge Platform

Bu proje, masaustu script mantigini cok kullanicili bir Django web uygulamasina tasir.
Her kullanici kendi videolarini yukler, merge job olusturur ve cikti dosyasini indirir.
Video birlestirme isleri Celery + Redis ile arka planda calisir.
Job durumlari Django Channels + WebSocket ile anlik guncellenir.

## Mimari (Clean Architecture + SOLID)

Katmanlar:
- `video_merge/domain`: Entity, interface ve hata siniflari
- `video_merge/application`: Use-case siniflari
- `video_merge/infrastructure`: Django ORM repository + FFmpeg adapter + Celery queue adapter
- `video_merge/presentation`: Form ve view katmani

Bu ayrim sayesinde:
- Is kurallari framework bagimindan ayrildi
- Repository ve merger soyutlamalari ile degisebilir altyapi elde edildi
- Siniflar tek sorumlulukla tasarlandi (SRP)

## Lokal Calistirma

1. Bagimliliklari yukle:
```bash
pip install -r requirements.txt
```

2. FFmpeg kurulu oldugunu dogrula:
```bash
ffmpeg -version
```

3. Veritabani migration:
```bash
python manage.py migrate
```

4. Kullanici olustur (opsiyonel admin):
```bash
python manage.py createsuperuser
```

5. Redis'i calistir:
```bash
docker run --name pars-redis -p 6379:6379 -d redis:7-alpine
```

6. Django uygulamasini calistir:
```bash
python manage.py runserver
```

7. Celery worker calistir:
```bash
celery -A pars_vid_bir worker -l info
```

8. Giris ekrani:
- `http://127.0.0.1:8000/accounts/login/`
- Yeni kayit: `http://127.0.0.1:8000/signup/`
- WebSocket endpoint: `ws://127.0.0.1:8000/ws/jobs/`

### Redis olmadan gelistirme (hizli mod)

Redis kurulu degilse su ayarlariyla devam edebilirsiniz:
- `USE_REDIS=0`
- `REALTIME_UPDATES_ENABLED=0`

Bu modda:
- Celery gorevleri `eager` calisir (ayni process)
- WebSocket canli guncelleme kapali olur
- `runserver` ile 404 `/ws/jobs/` ve Redis baglanti hatalari gorulmez

## Uretim Ortamina Alma Adimlari

1. Ortam degiskenlerini tanimla:
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=0`
- `DJANGO_ALLOWED_HOSTS=alanadiniz.com,www.alanadiniz.com`
- `FFMPEG_BINARY=ffmpeg`
- `CELERY_BROKER_URL=redis://redis:6379/0`
- `CELERY_RESULT_BACKEND=redis://redis:6379/1`
- `CHANNELS_BACKEND=redis`
- `CHANNELS_REDIS_URL=redis://redis:6379/2`

2. Statik dosyalari topla:
```bash
python manage.py collectstatic --noinput
```

3. ASGI sunucu ile ayaga kaldir:
```bash
gunicorn pars_vid_bir.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

4. Celery worker ayaga kaldir:
```bash
celery -A pars_vid_bir worker -l info
```

5. Nginx ile:
- `/static/` -> `staticfiles/`
- `/media/` -> `media/`
- Uygulama proxy -> Gunicorn

6. TLS sertifikasi ekle (Let's Encrypt).
