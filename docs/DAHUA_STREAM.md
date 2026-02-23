# Как транслировать поток с камеры Dahua на сервер

В проекте поток идёт так:

```
Dahua (RTSP сервер)  →  MediaMTX (на VPS)  →  Backend (распознавание)
```

**MediaMTX на VPS сам подтягивает (pull) поток с камеры.** Камера ничего не «пушит» — сервер подключается к ней по RTSP. Чтобы это работало, **с VPS должен быть доступен адрес камеры** (IP и порт 554).

---

## Шаг 1: Сделать камеру доступной с VPS

Выберите один вариант.

| Ситуация | Что указать в `.env` |
|----------|----------------------|
| Камера в той же сети, что и VPS (дата-центр, VPN) | `CAMERA_IP=192.168.0.201`, `CAMERA_PORT=554` |
| Камера дома, на роутере проброшен порт 554 на камеру | Узнайте белый IP дома (или DynDNS). `CAMERA_IP=ВАШ_БЕЛЫЙ_IP`, `CAMERA_PORT=554` |
| Используете Tailscale/VPN: с VPS видна домашняя сеть | `CAMERA_IP=192.168.0.201` (локальный IP камеры), `CAMERA_PORT=554` |

В `.env` на сервере также укажите логин и пароль камеры:

```env
PC_DAHUA_USERNAME=admin
PC_DAHUA_PASSWORD=пароль_от_камеры
CAMERA_IP=...   # см. таблицу выше
CAMERA_PORT=554
```

---

## Шаг 2: Перезапустить MediaMTX

MediaMTX читает URL камеры из переменных окружения (они подставляются из `.env` при запуске compose):

```bash
cd ~/vision
docker compose -f docker-compose.full.yml --env-file .env up -d mediamtx
```

Проверка логов:

```bash
docker compose -f docker-compose.full.yml logs -f mediamtx
```

При первом обращении к потоку MediaMTX подключится к камере по адресу `rtsp://admin:****@CAMERA_IP:554/cam/realmonitor?channel=1&subtype=0`.

---

## Шаг 3: Админка и бэкенд

- **Backend** уже настроен подключаться к MediaMTX (`PC_DAHUA_IP=mediamtx`, порт 8554) — ничего менять не нужно.
- В **админке** в настройках камеры можно оставить подключение через MediaMTX: если бэкенд в Docker и получает поток из контейнера `mediamtx`, то форма «Настройки камеры» может показывать «localhost» или «mediamtx» — главное, чтобы в `.env` на сервере были верные `CAMERA_IP`, `CAMERA_PORT`, логин и пароль.

---

## Кратко

1. Сделать камеру доступной с VPS (одна сеть, проброс порта или VPN).
2. В `.env` на сервере задать: `CAMERA_IP`, `CAMERA_PORT`, `PC_DAHUA_USERNAME`, `PC_DAHUA_PASSWORD`.
3. Запустить/перезапустить стек с `--env-file .env`; MediaMTX сам подтянет поток с камеры, бэкенд возьмёт его уже с MediaMTX.

Подробнее про проброс порта, VPN и MediaMTX дома — раздел 5 в [DEPLOY.md](../DEPLOY.md).
