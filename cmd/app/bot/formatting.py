from datetime import datetime


STATUS_EMOJI = {
    "new": "🆕",
    "in_progress": "🔧",
    "done": "✅",
}

STATUS_RU = {
    "new": "Новая",
    "in_progress": "В работе",
    "done": "Выполнена",
}

CATEGORY_RU = {
    "split": "Сплит-система",
    "vrf": "VRF-система",
    "fan_coil": "Фанкойл",
    "kkb": "ККБ",
    "chiller": "Чиллер",
    "obvyazka": "Обвязка",
    "ventilation": "Вентиляция",
}


def esc(value) -> str:
    import html

    return html.escape(str(value if value is not None else ""))


def fmt_price(price) -> str:
    if not price:
        return "цена по запросу"
    return f"{int(price):,}".replace(",", " ") + " ₽"


def fmt_dt(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.strftime("%d.%m.%Y %H:%M")


def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def kind_label(kind: str) -> str:
    return "📞 Заказ звонка" if kind == "callback" else "🛒 Заказ товара"


def status_line(status: str) -> str:
    return f"{STATUS_EMOJI.get(status, '❔')} {STATUS_RU.get(status, status)}"
