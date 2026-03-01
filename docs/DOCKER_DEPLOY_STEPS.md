# Пошаговый деплой на сервер с Docker

Как применить изменения (режим VPS, плеер HLS/WebRTC) и запустить стек в Docker.

---

## Шаг 1. Код на сервере

На сервере перейди в каталог проекта и подтяни изменения:

```bash
cd /path/to/video_analytics   # или где у тебя лежит проект
git pull
```

Если код копируешь вручную — убедись, что на сервере есть все обновлённые файлы (backend, frontend/admin, frontend/analytics, infra/mediamtx, docker-compose.full.yml).

---

## Шаг 2. Файл `.env`

В корне проекта создай или отредактируй `.env` (можно скопировать из `.env.example`).

**Обязательные переменные (как и раньше):**

- `POSTGRES_PASSWORD`
- `PC_DAHUA_PASSWORD` (если используешь камеру)
- `VITE_API_URL` — публичный URL бэкенда (например `http://ТВОЙ_СЕРВЕР:8000` или `https://api.example.com`)

**Если используешь режим VPS** — добавь или раскомментируй:

```env
STREAM_MODE=vps
VPS_HLS_URL=http://ТВОЙ_СЕРВЕР:8888/dahua_push/index.m3u8
VPS_WEBRTC_URL=http://ТВОЙ_СЕРВЕР:8889/dahua_push
STREAM_PREFERRED_PROTOCOL=webrtc
```

Замени `ТВОЙ_СЕРВЕР` на IP или домен сервера, до которого из браузера достучишься (тот же хост, что и приложение, или отдельный VPS с MediaMTX). Путь `dahua_push` должен совпадать с путём в MediaMTX (см. шаг 4).

Если оставляешь режим по умолчанию (камера через RTSP/MediaMTX) — ничего из VPS не добавляй, можно не задавать `STREAM_MODE` (будет `local`).

---

## Шаг 3. Сборка и запуск

Из корня проекта:

```bash
docker compose -f docker-compose.full.yml --env-file .env up -d --build
```

Флаг `--build` пересоберёт образы backend, admin и analytics (там новые изменения). Postgres и MediaMTX подтянутся как образы без пересборки.

Проверка, что контейнеры запущены:

```bash
docker compose -f docker-compose.full.yml ps
```

Должны быть в состоянии `running`: postgres, mediamtx, backend, admin, analytics.

---

## Шаг 4. Режим VPS: камера пушит RTMP на этот же сервер

Если MediaMTX крутится в том же Docker и камера пушит RTMP на этот сервер:

1. В `infra/mediamtx/mediamtx.yml` уже добавлен путь **`dahua_push`** без источника (приём RTMP).
2. На камере Dahua укажи RTMP push:
   - URL: `rtmp://IP_СЕРВЕРА:1935/dahua_push`
   - Кодек: H.264.
3. В `.env` (как в шаге 2):
   - `VPS_HLS_URL=http://IP_СЕРВЕРА:8888/dahua_push/index.m3u8`
   - `VPS_WEBRTC_URL=http://IP_СЕРВЕРА:8889/dahua_push`
   - `STREAM_MODE=vps`
4. Перезапусти только backend, чтобы подхватить env:
   ```bash
   docker compose -f docker-compose.full.yml --env-file .env up -d backend
   ```

Если камера пушит на **другой** VPS (отдельная машина с MediaMTX) — в `VPS_HLS_URL` и `VPS_WEBRTC_URL` укажи адрес того сервера и путь потока, который там настроен.

---

## Шаг 5. Логи и отладка

Логи бэкенда пишутся в stderr и видны в Docker:

```bash
docker compose -f docker-compose.full.yml logs -f backend
```

Уровень детализации задаётся в `.env`:
- `PC_LOG_LEVEL=INFO` (по умолчанию) — старт/стоп, камера, режим VPS, ошибки
- `PC_LOG_LEVEL=DEBUG` — дополнительно детали VPS health-check, кадры стрима и т.п.
- `PC_LOG_LEVEL=WARNING` — только предупреждения и ошибки

При ошибках смотри строки с `[ERROR]` и `[WARNING]` и полный traceback после `Exception`.

---

## Шаг 6. Проверка

- **Backend:** `http://ТВОЙ_СЕРВЕР:8000/health` — в ответе будет `stream_mode` и при `vps` — `vps_status`.
- **Stream config:** `http://ТВОЙ_СЕРВЕР:8000/api/stream/config` — режим и URL HLS/WebRTC.
- **Админка:** `http://ТВОЙ_СЕРВЕР:3000` — логин, затем на дашборде должен быть плеер (local — MJPEG с бэка, vps — HLS/WebRTC с указанных URL).
- **Аналитика:** `http://ТВОЙ_СЕРВЕР:3001` — тот же плеер по конфигу.

Если в режиме VPS статус "offline" — проверь, что камера реально пушит на выбранный путь и что порты 8888/8889 доступны с той машины, откуда открываешь фронт (файрвол, CORS при необходимости).

**Ошибки 400 (WHEP) или 404 (HLS):** путь в URL должен совпадать с путём в MediaMTX.
- Камера пушит RTMP в `rtmp://сервер:1935/**dahua_push**` → в `.env` указывай **`dahua_push`**:  
  `VPS_HLS_URL=http://...:8888/dahua_push/index.m3u8`, `VPS_WEBRTC_URL=http://...:8889/dahua_push`.
- Поток тянется по RTSP (path **`dahua`**) → в `.env` указывай **`dahua`**:  
  `VPS_HLS_URL=http://...:8888/dahua/index.m3u8`, `VPS_WEBRTC_URL=http://...:8889/dahua`.

---

## Краткий чеклист

| Шаг | Действие |
|-----|----------|
| 1 | `git pull` (или скопировать обновлённый код) |
| 2 | Настроить `.env` (обязательные + при VPS: `STREAM_MODE`, `VPS_HLS_URL`, `VPS_WEBRTC_URL`) |
| 3 | `docker compose -f docker-compose.full.yml --env-file .env up -d --build` |
| 4 | При VPS: на камере RTMP push на `rtmp://сервер:1935/dahua_push`, путь в .env тот же |
| 5 | При необходимости задать `PC_LOG_LEVEL=DEBUG` в .env и смотреть `docker compose logs -f backend` |
| 6 | Проверить /health, /api/stream/config, админку и аналитику |

После этого изменения применены и выполняются в Docker.
