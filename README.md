# PDF Data Base

Система управления договорами и PDF-документами на Django.

## Возможности

- CRUD документов с загрузкой PDF в Backblaze B2
- Категории, теги, поиск и фильтрация
- Полнотекстовый поиск по содержимому PDF
- Сроки договоров с уведомлениями об истечении
- Роли пользователей: просмотр, редактор, администратор
- Версионирование PDF при замене файла
- Журнал аудита изменений
- Экспорт в CSV и Excel
- REST API (`/api/documents/`, `/api/categories/`)
- Встроенный просмотр PDF на странице документа

## Быстрый старт

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Откройте http://127.0.0.1:8000/login/

## Переменные окружения

См. `.env.example`. В production обязательны `SECRET_KEY` и переменные Backblaze B2.

## PostgreSQL (Railway)

Добавьте переменную `DATABASE_URL` — приложение автоматически переключится с SQLite.

## Уведомления о сроках

```bash
python manage.py check_expiring_contracts
python manage.py check_expiring_contracts --days 14
```

Настройте `NOTIFY_EMAIL` для отправки письма.

## REST API

Аутентификация через сессию Django. Примеры:

- `GET /api/documents/`
- `GET /api/documents/{slug}/`
- `POST /api/documents/` (редактор/админ)

## Роли

Назначаются в Django Admin → Профили пользователей:

| Роль | Права |
|------|-------|
| Просмотр | Только чтение |
| Редактор | Создание и редактирование документов |
| Администратор | Полный доступ, категории, удаление, экспорт |

## Деплой

```bash
# Procfile выполняет migrate + gunicorn
gunicorn config.wsgi:application
```

Проверка подключения к B2:

```bash
python manage.py test_b2
```

Рекомендуется настроить cron для `check_expiring_contracts` на Railway.
