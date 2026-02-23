#!/usr/bin/env bash
# Развёртывание People Counter на VPS (см. DEPLOY.md)
# Запуск из корня проекта: ./scripts/setup-vps.sh
# Только compose: ./scripts/setup-vps.sh --compose-only

set -e

COMPOSE_ONLY=false
if [[ "${1:-}" == "--compose-only" ]]; then
  COMPOSE_ONLY=true
fi

# Переход в корень проекта (скрипт может быть вызван из scripts/ или из корня)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$COMPOSE_ONLY" != true ]]; then
  echo "=== 1. Подготовка сервера ==="
  sudo apt-get update -qq
  sudo apt-get upgrade -y -qq

  if ! command -v docker &>/dev/null; then
    echo "Установка Docker..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER" || true
    echo "Группа docker добавлена. Если 'docker compose' ниже выдаст ошибку прав — выйдите из SSH и зайдите снова, затем выполните: ./scripts/setup-vps.sh --compose-only"
  fi

  if ! command -v docker &>/dev/null; then
    echo "Docker не найден после установки. Перелогиньтесь по SSH и запустите: ./scripts/setup-vps.sh --compose-only"
    exit 1
  fi

  sudo apt-get install -y -qq docker-compose-plugin 2>/dev/null || true

  if [[ ! -f /swapfile ]]; then
    echo "Настройка swap 2 ГБ..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap включён. Проверка: free -h"
    free -h
  else
    echo "Swap уже настроен (/swapfile существует)."
  fi
fi

echo "=== Запуск контейнеров ==="
if [[ ! -f docker-compose.full.yml ]]; then
  echo "Ошибка: docker-compose.full.yml не найден. Запускайте скрипт из корня проекта (например ~/vision)."
  exit 1
fi
if [[ ! -f .env ]]; then
  echo "Ошибка: файл .env не найден. Скопируйте .env.example в .env и заполните пароли и PC_DAHUA_IP."
  exit 1
fi

sudo docker compose -f docker-compose.full.yml --env-file .env up -d --build

echo ""
echo "Готово. Проверка: sudo docker compose -f docker-compose.full.yml ps"
echo "Логи backend: sudo docker compose -f docker-compose.full.yml logs -f backend"
echo "Сервисы: Backend :8000, Admin :3000, Analytics :3001"
