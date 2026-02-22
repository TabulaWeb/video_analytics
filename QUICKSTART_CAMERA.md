# Быстрый старт с Dahua IP камерой

## 1. Настройка пароля

Откройте `.env` и укажите пароль от камеры:

```bash
# ВАЖНО: Замените на реальный пароль!
DAHUA_PASSWORD=ваш_реальный_пароль
```

## 2. Запуск MediaMTX

```bash
docker compose up -d
```

## 3. Проверка потока

Откройте в VLC или браузере:
```
http://localhost:8888/dahua/index.m3u8
```

Должно проигрываться видео с камеры (с задержкой 2-5 сек — это нормально).

## 4. Запуск приложения

```bash
.venv/bin/python run.py --no-debug-window
```

## 5. Просмотр в браузере

1. Откройте http://localhost:8000
2. В выпадающем меню **"Источник"** выберите **"IP камера Dahua (HLS)"**
3. Должна появиться картинка с камеры

## Troubleshooting

### Проблема: "Не удалось загрузить поток"

```bash
# 1. Проверьте, что камера доступна
ping 192.168.0.200

# 2. Проверьте логи MediaMTX
docker compose logs -f mediamtx

# 3. Проверьте правильность пароля в .env
cat .env | grep DAHUA_PASSWORD
```

### Проблема: Видео не играется в браузере

1. Проверьте, что MediaMTX запущен: `docker compose ps`
2. Попробуйте открыть HLS напрямую: http://localhost:8888/dahua/index.m3u8
3. Если HLS не открывается — проверьте настройки камеры (RTSP порт 554 должен быть доступен)

## Полная документация

См. [README_CAMERA.md](README_CAMERA.md) для подробной документации.

## Команды

```bash
# Запуск MediaMTX
docker compose up -d

# Остановка MediaMTX
docker compose down

# Логи MediaMTX
docker compose logs -f mediamtx

# Перезапуск
docker compose restart mediamtx
```
