# Проблемы и решения

## Не получаю картинку с IP камеры

### Шаг 1: Проверьте, какой источник выбран

В веб-интерфейсе (http://localhost:8000) под видео есть выпадающее меню **"Источник:"**

- **"Веб-камера (обработанная)"** — локальная USB камера, работает без Docker
- **"IP камера Dahua (HLS)"** — требует Docker + MediaMTX

### Шаг 2: Запустите Docker Desktop

1. Откройте **Docker Desktop** (Applications → Docker)
2. Дождитесь запуска (whale icon станет белым в menu bar)
3. Проверьте статус:

```bash
docker ps
```

Если видите ошибку "Cannot connect to the Docker daemon" — Docker не запущен.

### Шаг 3: Укажите пароль от камеры

Откройте `.env` и замените:

```bash
DAHUA_PASSWORD=your_camera_password_here
```

На реальный пароль:

```bash
DAHUA_PASSWORD=ваш_настоящий_пароль
```

### Шаг 4: Запустите MediaMTX

```bash
cd /Users/alextabula/Desktop/vision
docker compose up -d
```

Проверьте логи:

```bash
docker compose logs -f mediamtx
```

### Шаг 5: Проверьте HLS поток

Откройте в браузере:
```
http://localhost:8888/dahua/index.m3u8
```

Или в VLC:
1. Media → Open Network Stream
2. URL: http://localhost:8888/dahua/index.m3u8
3. Play

### Шаг 6: Проверьте в приложении

1. Откройте http://localhost:8000
2. Выберите "IP камера Dahua (HLS)"
3. Подождите 5-10 секунд

## Частые ошибки

### "Cannot connect to the Docker daemon"

**Причина:** Docker не запущен

**Решение:** Запустите Docker Desktop

### "Stream not available"

**Причина:** Камера недоступна или неправильный пароль

**Решение:**
1. Проверьте IP камеры: `ping 192.168.0.200`
2. Проверьте пароль в `.env`
3. Проверьте логи: `docker compose logs mediamtx`

### Видео не играется в браузере

**Причина:** HLS поток не готов или MediaMTX не запущен

**Решение:**
1. Проверьте контейнер: `docker compose ps`
2. Перезапустите: `docker compose restart mediamtx`

## Быстрая проверка

```bash
# 1. Docker запущен?
docker ps

# 2. MediaMTX работает?
docker compose ps

# 3. HLS доступен?
curl -I http://localhost:8888/dahua/index.m3u8

# 4. Камера доступна?
ping 192.168.0.200

# 5. Пароль указан?
cat .env | grep DAHUA_PASSWORD
```
