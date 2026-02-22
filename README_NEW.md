# People Counter - Система подсчета людей v2.0

Комплексная система подсчета людей с использованием YOLOv8, ByteTrack, и современной веб-архитектурой.

## 📐 Архитектура

Приложение разделено на **3 независимых компонента**:

1. **Backend (FastAPI)** - порт 8000
   - Computer Vision worker с YOLOv8 + ByteTrack
   - REST API для управления и аналитики
   - JWT авторизация
   - WebSocket для real-time обновлений
   - Экспорт данных (CSV, Excel, PDF)
   - Интеграция с IP камерой через MediaMTX

2. **Admin Panel (React + Vite + Chakra UI)** - порт 3000
   - Авторизация администратора
   - Настройка IP камеры (IP, логин, пароль, порт)
   - Настройка линии подсчета (позиция X, направление IN/OUT)
   - Live видео с детекцией
   - Статус системы (FPS, активные треки, камера онлайн)
   - Текущие счетчики

3. **Analytics Dashboard (React + Vite + Chakra UI)** - порт 3001
   - Авторизация пользователя
   - Live видео
   - Текущие счетчики и активные треки
   - Статистика (день/неделя/месяц)
   - Графики активности (почасовые, пиковые часы)
   - Экспорт данных (CSV, Excel, PDF с графиками)

## 🚀 Быстрый старт

### Вариант 1: Локальная разработка

#### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Backend будет доступен на `http://localhost:8000`

#### Admin Panel
```bash
cd frontend/admin
npm install
npm run dev
```

Admin Panel будет доступен на `http://localhost:3000`

#### Analytics Dashboard
```bash
cd frontend/analytics
npm install
npm run dev
```

Analytics Dashboard будет доступен на `http://localhost:3001`

### Вариант 2: Docker (все сервисы)

```bash
docker-compose -f docker-compose.full.yml up --build
```

Это запустит все 4 сервиса:
- MediaMTX (RTSP proxy): `localhost:8554`, HLS: `localhost:8888`
- Backend API: `http://localhost:8000`
- Admin Panel: `http://localhost:3000`
- Analytics Dashboard: `http://localhost:3001`

## 🔐 Авторизация

По умолчанию:
- **Username**: `admin`
- **Password**: `secret`

> ⚠️ **ВАЖНО**: Измените пароль в production! См. `backend/app/auth.py`

## 📷 Настройка IP камеры

### Через Admin Panel (рекомендуется)

1. Войдите в Admin Panel (`http://localhost:3000`)
2. Перейдите в "Настройки камеры"
3. Введите параметры вашей Dahua камеры:
   - IP адрес (например, `192.168.0.201`)
   - Порт (обычно `554`)
   - Имя пользователя (обычно `admin`)
   - Пароль
   - Канал (обычно `1`)
   - Подтип потока:
     - `0` - основной поток (HD, ~1080p)
     - `1` - дополнительный поток (SD, ~360p)
4. Настройте линию подсчета:
   - Позиция X (пиксели) - оставьте пустым для авто-центрирования
   - Направление IN: `L->R` (слева направо) или `R->L` (справа налево)
5. Нажмите "Сохранить настройки"

### Через .env файл

```bash
# backend/.env
PC_DAHUA_IP=192.168.0.201
PC_DAHUA_PORT=554
PC_DAHUA_USERNAME=admin
PC_DAHUA_PASSWORD=your_password
PC_DAHUA_CHANNEL=1
PC_DAHUA_SUBTYPE=0

# Line settings
PC_LINE_X=480  # Или оставьте пустым для авто
PC_DIRECTION_IN=L->R
```

## 📊 API Endpoints

### Авторизация
- `POST /api/auth/login` - Вход (получить JWT token)
- `GET /api/auth/me` - Информация о текущем пользователе

### Настройки камеры
- `GET /api/camera/settings` - Получить настройки
- `POST /api/camera/settings` - Создать настройки
- `PUT /api/camera/settings/{id}` - Обновить настройки

### Статистика
- `GET /api/stats/current` - Текущие счетчики
- `GET /api/analytics/day` - Статистика за день
- `GET /api/analytics/week` - Статистика за неделю
- `GET /api/analytics/month` - Статистика за месяц
- `GET /api/analytics/hourly` - Почасовая статистика
- `GET /api/analytics/peak-hours` - Пиковые часы

### Экспорт
- `POST /api/export` - Экспорт данных (CSV, Excel, PDF)

### Система
- `GET /api/system/status` - Статус системы
- `GET /health` - Health check
- `GET /video_feed` - MJPEG видео поток
- `WS /ws` - WebSocket для real-time обновлений

📖 Полная документация API: `http://localhost:8000/docs`

## 🛠️ Разработка

### Структура проекта

```
vision/
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── auth.py           # JWT авторизация
│   │   ├── config.py         # Настройки из .env
│   │   ├── counter.py        # Логика подсчета
│   │   ├── crud.py           # CRUD операции
│   │   ├── cv_worker.py      # CV worker (YOLO + ByteTrack)
│   │   ├── db.py             # База данных (legacy)
│   │   ├── export.py         # Экспорт данных
│   │   ├── main.py           # FastAPI app
│   │   ├── models.py         # SQLAlchemy модели
│   │   └── schemas.py        # Pydantic схемы
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── admin/                # Admin Panel (React)
│   │   ├── src/
│   │   │   ├── pages/
│   │   │   │   ├── Login.tsx
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   └── CameraSettings.tsx
│   │   │   ├── services/api.ts
│   │   │   ├── contexts/AuthContext.tsx
│   │   │   ├── theme.ts
│   │   │   ├── App.tsx
│   │   │   └── main.tsx
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   └── analytics/            # Analytics Dashboard (React)
│       ├── src/
│       │   ├── pages/
│       │   │   ├── Login.tsx
│       │   │   └── Analytics.tsx
│       │   ├── services/api.ts
│       │   ├── contexts/AuthContext.tsx
│       │   └── ...
│       ├── package.json
│       └── Dockerfile
│
├── infra/
│   └── mediamtx/
│       └── mediamtx.yml      # MediaMTX config
│
├── docker-compose.yml         # MediaMTX only
├── docker-compose.full.yml    # All services
└── README_NEW.md             # This file
```

### Backend (Python)

**Технологии:**
- FastAPI (web framework)
- Ultralytics YOLOv8 (object detection)
- ByteTrack (multi-object tracking)
- OpenCV (video processing)
- SQLAlchemy (ORM)
- SQLite (database)
- python-jose (JWT)
- pandas, openpyxl, reportlab (data export)

**Запуск с hot-reload:**
```bash
cd backend
uvicorn app.main:app --reload
```

### Frontend (React + TypeScript)

**Технологии:**
- React 18
- TypeScript
- Vite (build tool)
- Chakra UI (UI library)
- React Router (routing)
- Axios (HTTP client)
- Recharts (charts)

**Запуск dev серверов:**
```bash
# Admin Panel
cd frontend/admin
npm run dev

# Analytics Dashboard
cd frontend/analytics
npm run dev
```

## 🐛 Troubleshooting

### Backend не подключается к камере

1. Проверьте настройки в Admin Panel или `.env`
2. Убедитесь, что камера доступна в сети:
   ```bash
   ping 192.168.0.201
   ```
3. Проверьте, что MediaMTX запущен:
   ```bash
   docker ps | grep mediamtx
   ```
4. Проверьте логи MediaMTX:
   ```bash
   docker logs people-counter-mediamtx
   ```

### Frontend не может подключиться к Backend

1. Убедитесь, что Backend запущен на `http://localhost:8000`
2. Проверьте CORS настройки в `backend/app/main.py`
3. Откройте `http://localhost:8000/docs` для проверки API

### Ошибка авторизации

1. Проверьте credentials: `admin / secret`
2. Очистите LocalStorage в браузере:
   ```javascript
   localStorage.clear()
   ```
3. Перезагрузите страницу

### FPS = 0 или низкий FPS

1. Попробуйте `subtype=1` (SD поток) вместо `subtype=0` (HD)
2. Уменьшите `PC_RESIZE_WIDTH` в `.env` (например, `640`)
3. Используйте более легкую модель: `PC_MODEL_NAME=yolov8n.pt` (nano)

## 📝 TODO

- [ ] Добавить хранение паролей в хешированном виде в БД
- [ ] Добавить управление пользователями (создание/удаление)
- [ ] Добавить настройку YOLO модели через Admin Panel
- [ ] Добавить webhooks для уведомлений
- [ ] Добавить поддержку нескольких камер
- [ ] Добавить heat maps
- [ ] Добавить поддержку PostgreSQL
- [ ] Production Docker builds (multi-stage, optimized)

## 📄 Лицензия

MIT

## 👨‍💻 Автор

Создано с помощью Cursor AI
