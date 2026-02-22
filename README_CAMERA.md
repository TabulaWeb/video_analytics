# Подключение Dahua IP камеры к People Counter

Этот гид описывает, как подключить IP камеру Dahua к приложению People Counter для отображения live-видео в веб-интерфейсе.

## Архитектура

```
Dahua Camera (RTSP) → MediaMTX (Docker) → HLS Stream → Web Browser
      ↓                                                      ↓
   Detection ←─────────── OpenCV + YOLO ───────────── Video Player
```

- **Dahua Camera**: IP камера с RTSP стримом
- **MediaMTX**: Стриминг-сервер, который получает RTSP и отдает HLS/WebRTC
- **HLS (HTTP Live Streaming)**: Формат для воспроизведения в браузере
- **hls.js**: JavaScript библиотека для воспроизведения HLS в браузере

## Требования

1. **Docker** и **Docker Compose** установлены на вашем компьютере
2. **Dahua IP камера** доступна в локальной сети
3. **Пароль от камеры** (пользователь: `admin`)

## Шаг 1: Настройка переменных окружения

1. Скопируйте `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```

2. Откройте `.env` и укажите **реальный пароль** от камеры Dahua:
   ```bash
   # ВАЖНО: Замените на реальный пароль!
   DAHUA_PASSWORD=ваш_реальный_пароль_здесь
   ```

3. **НЕ КОММИТЬТЕ `.env` В GIT!** (уже добавлен в `.gitignore`)

## Шаг 2: Проверка подключения к камере

Перед запуском MediaMTX убедитесь, что камера доступна по сети:

### Проверка 1: Ping камеры
```bash
ping 192.168.0.200
```
Должны видеть ответы от камеры.

### Проверка 2: RTSP поток через VLC (опционально)
1. Откройте **VLC Media Player**
2. `Media` → `Open Network Stream`
3. Введите URL:
   ```
   rtsp://admin:ваш_пароль@192.168.0.200:554/cam/realmonitor?channel=1&subtype=0
   ```
4. Нажмите `Play`

Если видео проигрывается — камера настроена правильно!

## Шаг 3: Запуск MediaMTX

MediaMTX будет получать RTSP поток от камеры и отдавать его через HLS.

```bash
# Запуск в фоновом режиме
docker compose up -d

# Проверка логов
docker compose logs -f mediamtx
```

Ожидаемый вывод:
```
INF [HLS] [conn 192.168.0.200:554] stream is ready
INF [HLS] [path dahua] source ready
```

## Шаг 4: Проверка HLS потока

### Вариант A: Через браузер
Откройте в браузере:
```
http://localhost:8888/dahua/index.m3u8
```

Должен скачаться `.m3u8` файл (HLS manifest).

### Вариант B: Через VLC
1. Откройте VLC
2. `Media` → `Open Network Stream`
3. URL: `http://localhost:8888/dahua/index.m3u8`
4. Нажмите `Play`

Видео должно проигрываться с небольшой задержкой (1-3 секунды — это нормально для HLS).

## Шаг 5: Просмотр в веб-приложении

1. Запустите приложение People Counter:
   ```bash
   .venv/bin/python run.py --no-debug-window
   ```

2. Откройте http://localhost:8000

3. В веб-интерфейсе выберите источник видео:
   - **"Веб-камера (обработанная)"** — локальная вебка с детекцией и счетчиками (MJPEG)
   - **"IP камера Dahua (HLS)"** — прямая трансляция с IP камеры через HLS

4. При выборе "IP камера Dahua (HLS)" должна появиться картинка с камеры.

## Порты и сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| **MediaMTX HLS** | 8888 | HLS стрим (для браузера) |
| **MediaMTX WebRTC** | 8889 | WebRTC (опционально, для низкой задержки) |
| **MediaMTX RTSP** | 8554 | RTSP proxy (опционально) |
| **MediaMTX API** | 9997 | API для управления |
| **People Counter** | 8000 | Веб-интерфейс приложения |

## Конфигурация MediaMTX

Файл: `infra/mediamtx/mediamtx.yml`

### Основные настройки потока `dahua`:

```yaml
paths:
  dahua:
    source: rtsp://admin:${DAHUA_PASSWORD}@192.168.0.200:554/cam/realmonitor?channel=1&subtype=0
    sourceProtocol: tcp          # TCP вместо UDP для стабильности
    sourceOnDemand: yes          # Запуск только при наличии зрителей
```

### Параметры RTSP URL:

- `channel=1` — номер канала камеры (обычно 1)
- `subtype=0` — **main stream** (высокое качество, ~1080p, 2-4 Mbps)
- `subtype=1` — **sub stream** (низкое качество, ~360p, 512 Kbps)

Для экономии трафика можно использовать `subtype=1`:
```yaml
source: rtsp://admin:${DAHUA_PASSWORD}@192.168.0.200:554/cam/realmonitor?channel=1&subtype=1
```

## Troubleshooting

### Проблема: "Не удалось загрузить поток" в браузере

**Возможные причины:**

1. **Камера недоступна**
   ```bash
   # Проверьте пинг
   ping 192.168.0.200
   
   # Проверьте логи MediaMTX
   docker compose logs mediamtx | grep error
   ```

2. **Неправильный пароль**
   - Убедитесь, что в `.env` указан правильный `DAHUA_PASSWORD`
   - Попробуйте подключиться через VLC (см. Шаг 2)

3. **RTSP порт закрыт**
   - Проверьте настройки камеры: `Конфигурация → Сеть → RTSP`
   - Порт должен быть `554` и доступен

4. **Firewall блокирует порты**
   ```bash
   # macOS: проверьте Firewall в System Preferences
   # Linux: проверьте iptables/ufw
   sudo ufw allow 8888
   sudo ufw allow 554
   ```

### Проблема: MediaMTX не запускается

```bash
# Проверьте статус контейнера
docker compose ps

# Посмотрите логи
docker compose logs mediamtx

# Перезапустите
docker compose restart mediamtx
```

**Частые ошибки:**

- `source is not ready` — камера недоступна или неправильный URL
- `authentication failed` — неправильный логин/пароль
- `connection timeout` — камера не отвечает (проверьте сеть)

### Проблема: Видео тормозит или рвется

1. **Используйте sub stream** (меньше битрейт):
   ```yaml
   source: rtsp://admin:${DAHUA_PASSWORD}@192.168.0.200:554/cam/realmonitor?channel=1&subtype=1
   ```

2. **Проверьте нагрузку на сеть**:
   ```bash
   # Пинг должен быть < 10ms
   ping 192.168.0.200
   
   # Проверьте загрузку сети
   docker stats people-counter-mediamtx
   ```

3. **Уменьшите буфер HLS** (в `mediamtx.yml`):
   ```yaml
   hlsSegmentDuration: 1s
   hlsSegmentCount: 5
   ```

### Проблема: CORS ошибки в консоли браузера

Убедитесь, что в `mediamtx.yml` установлено:
```yaml
hlsAllowOrigin: "*"
webrtcAllowOrigin: "*"
```

После изменений перезапустите:
```bash
docker compose restart mediamtx
```

### Проблема: "Stream not available" (поток недоступен)

MediaMTX использует режим `sourceOnDemand: yes`, поэтому поток запускается только при наличии зрителей.

Первое подключение может занять 5-10 секунд. Если через 10 секунд поток не появился:

```bash
# Проверьте логи
docker compose logs -f mediamtx

# Попробуйте force-запуск потока через API
curl -X POST http://localhost:9997/v3/config/paths/dahua/sourceOnDemand/state -H "Content-Type: application/json" -d '{"state":"start"}'
```

## Команды управления

```bash
# Запуск MediaMTX
docker compose up -d

# Остановка
docker compose down

# Перезапуск
docker compose restart mediamtx

# Логи (live)
docker compose logs -f mediamtx

# Статус контейнера
docker compose ps

# Обновление образа MediaMTX
docker compose pull
docker compose up -d
```

## Переключение между камерами в коде

Если нужно обрабатывать IP камеру через OpenCV + YOLO (а не просто показывать видео):

1. Откройте `.env`
2. Измените `PC_CAMERA_INDEX`:
   ```bash
   # Вместо локальной вебки (0)
   # PC_CAMERA_INDEX=0
   
   # Используйте RTSP URL
   PC_CAMERA_INDEX=rtsp://admin:ваш_пароль@192.168.0.200:554/cam/realmonitor?channel=1&subtype=1
   ```

3. Перезапустите приложение:
   ```bash
   .venv/bin/python run.py --no-debug-window
   ```

**Важно:** RTSP через OpenCV может быть нестабильным. Рекомендуется использовать MediaMTX + HLS для отображения и отдельный поток для детекции.

## Дополнительные ресурсы

- [MediaMTX Documentation](https://github.com/bluenviron/mediamtx)
- [HLS.js Documentation](https://github.com/video-dev/hls.js/)
- [Dahua RTSP URL Format](https://www.unifore.net/ip-video-surveillance/dahua-rtsp-url-format.html)

## Безопасность

⚠️ **ВАЖНО:**

1. **НЕ КОММИТЬТЕ `.env` В GIT!**
   ```bash
   # Проверьте .gitignore
   grep ".env" .gitignore
   ```

2. **Не используйте дефолтный пароль** на камере Dahua!
   - Зайдите в веб-интерфейс камеры
   - Смените пароль на сильный (12+ символов, буквы, цифры, символы)

3. **Ограничьте доступ к камере** в локальной сети:
   - В настройках камеры: `Конфигурация → Сеть → TCP/IP`
   - Установите статический IP
   - Включите блокировку по IP (whitelist)

4. **Не открывайте порты камеры** в интернет напрямую!
   - Используйте VPN для удаленного доступа
   - Или настройте reverse proxy с аутентификацией

## FAQ

**Q: Какая задержка у HLS?**  
A: Обычно 2-5 секунд. Это нормально для HLS. Для меньшей задержки используйте WebRTC (настройка сложнее).

**Q: Можно ли использовать несколько камер?**  
A: Да! Добавьте новые paths в `mediamtx.yml`:
```yaml
paths:
  dahua1:
    source: rtsp://admin:${DAHUA_PASSWORD}@192.168.0.200:554/...
  dahua2:
    source: rtsp://admin:${DAHUA_PASSWORD}@192.168.0.201:554/...
```

**Q: Поддерживаются ли другие камеры (не Dahua)?**  
A: Да! Большинство IP камер поддерживают RTSP. Найдите RTSP URL для вашей камеры:
- Hikvision: `rtsp://admin:password@ip:554/Streaming/Channels/101`
- TP-Link: `rtsp://admin:password@ip:554/stream1`
- Generic ONVIF: `rtsp://admin:password@ip:554/onvif1`

**Q: Можно ли записывать видео?**  
A: MediaMTX поддерживает запись, но функция пока не настроена. См. [документацию MediaMTX](https://github.com/bluenviron/mediamtx#recording) для настройки.

---

**Поддержка:** Если возникли проблемы, откройте issue в репозитории или напишите в поддержку.
