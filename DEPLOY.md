# Развёртывание People Counter на VPS

## Как делегировать шаги

| Кто | Что делать |
|-----|------------|
| **Вы** | Подключиться по SSH к VPS, скопировать на сервер проект и файл `.env` с вашими паролями и IP камеры. |
| **Скрипт на сервере** | Выполнить подготовку ОС, Docker, swap и запуск контейнеров одной командой (см. ниже). |
| **AI / репозиторий** | Всё уже готово: `docker-compose.full.yml` и `docker-compose.prod.yml` берут пароли из `.env`. Достаточно заполнить `.env` и запустить compose. |

**Минимум на сервере:** склонировать репо (или загрузить архив), создать `.env` из `.env.example`, запустить `./scripts/setup-vps.sh` или выполнить шаги 1 → 2 → 4 вручную.

---

## Подходит ли ваш сервер

Конфигурация **подходит для работы**, но впритык по памяти:

| Параметр | Ваш сервер | Рекомендация |
|----------|------------|--------------|
| **ОС** | Ubuntu 24.04 | ✅ Отлично (LTS) |
| **Регион** | Москва | ✅ Низкая задержка до камеры в РФ |
| **CPU** | 1 × 3.3 ГГц | ✅ Достаточно для одной камеры + YOLOv8n |
| **RAM** | 2 ГБ | ⚠️ Минимум: используйте **swap 2 ГБ** и модель **yolov8n** |
| **Диск** | 30 ГБ NVMe | ✅ Хватает для ОС, Docker, логов |
| **Канал** | 1 Гбит/с | ✅ С запасом |

**Итог:** Сервер нормальный для одной камеры. Обязательно настройте swap и не меняйте модель на yolov8s/m/l — оставьте **yolov8n.pt**. Если позже появятся лаги или OOM — рассмотрите тариф с 4 ГБ RAM.

---

## 1. Подготовка сервера

Подключитесь по SSH и выполните:

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Выйдите и зайдите по SSH снова, чтобы группа применилась

# Установка Docker Compose (если не в комплекте)
sudo apt install -y docker-compose-plugin
```

### Swap (обязательно при 2 ГБ RAM)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Проверка: `free -h` — должен появиться 2G swap.

**Вариант «всё одной командой»:** после клонирования и настройки `.env` можно запустить скрипт `./scripts/setup-vps.sh` — он выполнит шаги 1 (без повторного выхода из SSH) и 4. См. конец раздела 2.

---

## 2. Клонирование проекта и настройка

```bash
cd ~
# Если проект в Git:
git clone <URL_вашего_репозитория> vision
cd vision

# Либо загрузите архив и распакуйте в ~/vision
```

### Переменные окружения

Создайте файл `.env` **в корне проекта** (в той же папке, где лежит `docker-compose.full.yml` — например `~/vision`).

**Способ 1 — на сервере из шаблона**

```bash
cd ~/vision
cp .env.example .env
nano .env
```

Отредактируйте значения (пароль БД, IP камеры, пароль камеры). Сохраните: **Ctrl+O**, Enter, **Ctrl+X**.

**Способ 2 — скопировать с вашего компьютера**

На **локальной** машине (в папке проекта, где уже есть настроенный `.env`):

```bash
scp .env user@IP_СЕРВЕРА:~/vision/.env
```

Подставьте `user` (логин SSH) и `IP_СЕРВЕРА`. Файл окажется в корне проекта на VPS.

**Содержимое `.env` (если создаёте вручную):**

```env
# База данных (пароль смените!)
POSTGRES_USER=people_counter
POSTGRES_PASSWORD=ваш_надёжный_пароль
POSTGRES_DB=people_counter_db

# Камера — для доступа через MediaMTX укажите IP камеры в вашей сети
# Если камера в той же сети что и VPS — её внутренний IP
PC_DAHUA_IP=192.168.x.x
PC_DAHUA_PORT=554
PC_DAHUA_USERNAME=admin
PC_DAHUA_PASSWORD=пароль_камеры

# Модель YOLO — не меняйте на 2 ГБ RAM!
PC_MODEL_NAME=yolov8n.pt
```

В nano: сохранить — **Ctrl+O**, Enter; выйти — **Ctrl+X**.

**Запуск скрипта (шаги 1 + 4 одной командой):** из корня проекта выполните `chmod +x scripts/setup-vps.sh && ./scripts/setup-vps.sh`. Скрипт установит Docker, настроит swap, поднимет контейнеры. Если Docker уже установлен, можно запустить только часть с compose: `./scripts/setup-vps.sh --compose-only`.

---

## 3. Docker Compose и .env

В репозитории уже настроено: **`docker-compose.full.yml`** и **`docker-compose.prod.yml`** берут пароли и настройки из `.env` (никаких захардкоженных паролей). Достаточно создать `.env` на сервере (шаг 2) и запускать с `--env-file .env`.

---

## 4. Запуск

```bash
cd ~/vision
docker compose -f docker-compose.full.yml --env-file .env up -d --build
```

Проверка контейнеров:

```bash
docker compose -f docker-compose.full.yml ps
docker compose -f docker-compose.full.yml logs -f backend
```

Когда в логах backend появится что-то вроде «Application startup complete», сервисы готовы.

- Backend API: `http://IP_СЕРВЕРА:8000`
- Admin: `http://IP_СЕРВЕРА:3000`
- Analytics: `http://IP_СЕРВЕРА:3001`
- Документация API: `http://IP_СЕРВЕРА:8000/docs`

---

## 5. Доступ камеры до сервера (поток из локальной сети на VPS)

MediaMTX на VPS должен получать RTSP-поток с камеры. Если камера у вас дома (192.168.x.x), до неё с интернета напрямую не достучаться. Ниже три рабочих варианта.

### Вариант A: Проброс порта на роутере (проще всего)

Камера остаётся в локальной сети, роутер «показывает» её в интернет по одному порту.

1. Узнайте **внутренний IP камеры** (например 192.168.0.201) и что RTSP слушает порт **554** (у Dahua обычно так).
2. В веб-интерфейсе **роутера** найдите раздел «Проброс портов» / «Port Forwarding» / «NAT».
3. Создайте правило:
   - Внешний порт: **554** (или другой свободный, например 1554).
   - Внутренний IP: **192.168.0.201**, внутренний порт: **554**.
   - Протокол: **TCP** (для RTSP).
4. Узнайте **белый IP дома** (на сайте типа 2ip.ru или в личном кабинете провайдера). Если IP динамический — используйте DynDNS (No-IP, DuckDNS и т.п.) и подставляйте в настройки домен вместо IP.
5. На VPS в `.env` укажите адрес камеры **как с сервера**:
   - Если пробросили порт 554 на белый IP: `PC_DAHUA_IP=ВАШ_БЕЛЫЙ_IP` (или домен), `PC_DAHUA_PORT=554`.
   - В админке People Counter укажите тот же IP/порт и логин/пароль камеры.

**Минус:** камера оказывается доступна из интернета на порту 554. Пароль на камере должен быть сложным; по возможности закройте доступ по RTSP с других портов.

---

### Вариант B: VPN между домом и VPS (рекомендуется)

Сервер и «домашняя» сеть объединяются в одну виртуальную сеть — VPS видит камеру по её локальному IP, порты наружу не открываем.

**Пример: Tailscale (бесплатно, без своего сервера)**

1. На **компьютере дома** (или Raspberry Pi): установите [Tailscale](https://tailscale.com), войдите в аккаунт.
2. На **VPS**: установите Tailscale и войдите в тот же аккаунт:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
3. В личном кабинете Tailscale включите **Subnet router** для домашней сети (или разрешите exit node при необходимости). Тогда VPS сможет ходить в 192.168.0.0/24.
4. Либо установите Tailscale на **одно устройство в той же сети, что и камера** (например Raspberry Pi), включите «Subnet routes» для 192.168.0.0/24 — и с VPS будет виден 192.168.0.201.
5. На VPS в `.env`: `PC_DAHUA_IP=192.168.0.201`, `PC_DAHUA_PORT=554`. В админке укажите те же данные.

Камера в интернет не светится, весь трафик идёт через зашифрованный VPN.

---

### Вариант C: MediaMTX у себя дома, один порт наружу

Поток с камеры забирает только ваш домашний ПК (или одноплатный ПК), наружу отдаётся уже один поток (RTSP/HLS).

1. **Дома** на ПК с доступом к камере (192.168.0.201) поставьте [MediaMTX](https://github.com/bluenviron/mediamtx) (или другой RTSP-прокси).
2. Настройте MediaMTX подключаться к камере, например:
   - источник: `rtsp://admin:пароль@192.168.0.201:554/cam/realmonitor?channel=1&subtype=0`
   - отдавать наружу по одному порту (например RTSP 8554 или HLS 8888).
3. На роутере пробросьте **один** порт (например 8554) на этот ПК.
4. На VPS в `.env`: `PC_DAHUA_IP=ВАШ_БЕЛЫЙ_IP` (или домен), `PC_DAHUA_PORT=8554`. В админке — тот же адрес; логин/пароль можно оставить пустыми, если MediaMTX не требует авторизации.

Плюс: наружу открыт только MediaMTX, сама камера в интернет не выставляется.

---

### Что указывать в приложении

- В **docker-compose** backend подключается к контейнеру MediaMTX по имени `mediamtx`. В `infra/mediamtx/mediamtx.yml` источник потока задаётся так, чтобы MediaMTX ходил по адресу из `.env` (`PC_DAHUA_IP`, `PC_DAHUA_PORT`) или по URL, который вы настроили (вариант C).
- В **админке People Counter** в настройках камеры укажите тот же IP/порт (и при необходимости логин/пароль), к которому с VPS должен подключаться MediaMTX или backend: для вариантов A и B — IP камеры и 554 (или ваш проброс), для варианта C — адрес домашнего MediaMTX и порт (например 8554).

---

## 6. Файрвол

Откройте только нужные порты:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 3000/tcp
sudo ufw allow 3001/tcp
sudo ufw enable
```

Если позже поставите Nginx перед приложением, можно оставить только 22, 80, 443 и закрыть 3000, 3001, 8000 снаружи.

---

## 7. (Рекомендуется) Nginx и HTTPS

Чтобы зайти по домену и с SSL:

1. Назначьте домен (например, `counter.example.com`) A-записью на IP сервера.
2. Установите Nginx и certbot:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo certbot --nginx -d counter.example.com
```

3. Добавьте конфиг Nginx (например, `/etc/nginx/sites-available/people-counter`):

```nginx
# API
upstream backend { server 127.0.0.1:8000; }
# Админка и аналитика — либо через тот же backend, либо отдельные порты
upstream admin { server 127.0.0.1:3000; }
upstream analytics { server 127.0.0.1:3001; }

server {
    listen 443 ssl;
    server_name counter.example.com;
    # ssl_* директивы certbot добавит сам

    location /api/ { proxy_pass http://backend; proxy_http_version 1.1; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme; }
    location /ws { proxy_pass http://backend; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; proxy_set_header Host $host; }
    location /video_feed { proxy_pass http://backend; }
    location /health { proxy_pass http://backend; }
    location /docs { proxy_pass http://backend; }
    location /openapi.json { proxy_pass http://backend; }

    location /admin { proxy_pass http://admin; proxy_http_version 1.1; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; }
    location /analytics { proxy_pass http://analytics; proxy_http_version 1.1; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; }

    # Корень — редирект или одна из панелей
    location = / { return 302 /admin/; }
}
```

Включите сайт и перезапустите Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/people-counter /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Тогда доступ будет по `https://counter.example.com/admin` и `https://counter.example.com/analytics`. В настройках фронтов (если есть) укажите `VITE_API_URL=https://counter.example.com` и пересоберите образы.

---

## 8. Автозапуск после перезагрузки

Контейнеры уже с `restart: unless-stopped`, поэтому после перезагрузки сервера они поднимутся сами. Проверка:

```bash
sudo reboot
# После входа снова:
docker compose -f docker-compose.full.yml ps
```

---

## 9. Полезные команды

**Сборка admin/analytics падает на `npm install`:** выполните сборку с полным выводом и посмотрите последние строки ошибки:
```bash
docker compose -f docker-compose.full.yml build --no-cache --progress=plain admin 2>&1 | tail -80
```
Если в логе видно нехватку памяти (OOM / killed) — добавьте swap (шаг 1) или соберите образ на более мощной машине и загрузите в registry.

```bash
# Логи всех сервисов
docker compose -f docker-compose.full.yml logs -f

# Только backend
docker compose -f docker-compose.full.yml logs -f backend

# Остановка
docker compose -f docker-compose.full.yml down

# Обновление кода и пересборка
git pull
docker compose -f docker-compose.full.yml up -d --build
```

---

## 10. Смена пароля администратора

По умолчанию логин `admin`, пароль `secret`. В production обязательно смените: отредактируйте `backend/app/auth.py` (переменные или хэш пароля) и пересоберите образ backend, либо задайте пароль через переменную окружения, если вы добавите такую поддержку в код.

---

Кратко: ваш сервер (Ubuntu 24.04, 1 CPU, 2 ГБ RAM, 30 ГБ, Москва) подходит для одной камеры при наличии swap и модели YOLOv8n. Следуйте шагам выше для выкладки; при росте нагрузки или второй камере лучше взять конфигурацию с 4 ГБ RAM.
