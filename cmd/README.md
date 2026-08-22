# «Райский холод» — сайт + админка + API + Telegram-бот

Сайт компании кондиционеров: FastAPI-бэкенд, SQLite, админ-панель для управления товарами и заявками,
Telegram-бот с уведомлениями о заявках. Дизайн основного сайта не изменён.

## Структура проекта

```
├── app/                    # Бэкенд (FastAPI)
│   ├── main.py             # Точка входа: приложение, раздача статики, запуск бота
│   ├── config.py           # Настройки из .env
│   ├── database.py         # SQLAlchemy (async) + SQLite
│   ├── models.py           # Product, Lead
│   ├── schemas.py          # Pydantic-схемы
│   ├── auth.py             # JWT для админки
│   ├── seed.py             # Автоимпорт products.json при первом запуске
│   ├── routers/
│   │   ├── auth.py         # POST /api/auth/login
│   │   ├── products.py     # CRUD товаров (+ GET публичный для каталога)
│   │   ├── leads.py        # Заявки: создание (публично), список/статусы (админ)
│   │   ├── stats.py        # Дашборд /api/stats/dashboard
│   │   └── uploads.py      # Загрузка фото товаров
│   ├── services/
│   │   └── telegram.py     # Уведомления о заявках в чат админа
│   └── bot/
│       ├── run.py          # aiogram 3, polling
│       ├── handlers.py     # /stats /find /lead /top, кнопки статусов
│       └── keyboards.py    # Inline-клавиатура статусов заявок
├── admin/index.html        # Админ-панель (/admin)
├── index.html              # Основной сайт (дизайн без изменений)
├── products.json           # Первичный каталог (импортируется в БД один раз)
├── images/                 # Фото по брендам: images/<brand>/<id>.jpg
├── data/                   # SQLite (app.db) и загруженные фото (uploads/) — в git не входит
├── requirements.txt
├── Dockerfile
└── fly.toml                # Конфиг деплоя Fly.io
```

## Локальный запуск

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # заполнить значения
.venv/bin/uvicorn app.main:app --reload --port 8000
```

- Сайт: http://127.0.0.1:8000/
- Админка: http://127.0.0.1:8000/admin
- Swagger: http://127.0.0.1:8000/docs

При первом старте таблицы создаются автоматически, а `products.json` импортируется в БД.

## Переменные окружения (.env)

| Переменная        | Описание                                                        |
|-------------------|-----------------------------------------------------------------|
| `BOT_TOKEN`       | Токен Telegram-бота (@BotFather). Пусто = бот выключен          |
| `ADMIN_CHAT_ID`   | Куда слать заявки: ваш id или id чата (узнать: @userinfobot)    |
| `TG_PROXY`        | Прокси для Telegram, если API недоступен напрямую               |
| `JWT_SECRET`      | Любая случайная строка для подписи токенов админки              |
| `ADMIN_USERNAME`  | Логин администратора                                            |
| `ADMIN_PASSWORD`  | Пароль администратора — обязательно сменить                     |
| `DB_PATH`         | Путь к SQLite (по умолчанию `data/app.db`)                      |
| `UPLOAD_DIR`      | Папка загруженных фото (по умолчанию `data/uploads`)            |

Примеры `TG_PROXY`: `socks5://127.0.0.1:10808`, `http://127.0.0.1:10809`.
На сервере (Fly.io) оставьте пустым — Telegram доступен напрямую.


## Telegram-бот

Уведомления: каждая заявка с сайта мгновенно приходит в чат `ADMIN_CHAT_ID`
с inline-кнопками смены статуса (Новая / В работе / Выполнена) — статус сохраняется в БД.

Команды бота:
- `/stats` — статистика заявок за день/неделю и по статусам
- `/find <запрос>` — поиск по каталогу с ценами (например `/find ballu 09`)
- `/lead <id>` — детали заявки и кнопки смены статуса
- `/top` — топ товаров по заказам

Как подключить:
1. Создайте бота у [@BotFather](https://t.me/BotFather), получите токен → `BOT_TOKEN`.
2. Узнайте свой числовой id через [@userinfobot](https://t.me/userinfobot) → `ADMIN_CHAT_ID`.
3. Напишите боту `/start` (иначе он не сможет писать вам первым).

## Деплой на Fly.io (бесплатный persistent volume)

SQLite требует постоянный диск — на бесплатных тарифах Render/Railway диск очищается
при деплое, поэтому используется Fly.io с volume:

```bash
fly launch                 # возьмёт fly.toml
fly volumes create rayskiy_data --size 3 --region waw
fly secrets set BOT_TOKEN=... ADMIN_CHAT_ID=... JWT_SECRET=... ADMIN_PASSWORD=...
fly deploy
```

Volume монтируется в `/app/data`, там же хранятся загруженные фото.

## Безопасность

⚠️ Ранее GitHub-токен и токен бота были опубликованы в клиентском коде (`admin.html`,
`index.html`) и остались в истории git. Обязательно:

1. Отзовите GitHub-токен: GitHub → Settings → Developer settings → Personal access tokens.
2. Перевыпустите токен бота: @BotFather → /revoke.
3. Смените `ADMIN_PASSWORD`.

Теперь все секреты живут только в `.env` / `fly secrets`.
