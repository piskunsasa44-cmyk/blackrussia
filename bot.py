# ─────────────────────────────────────────────
#  ПАРСЕР СООБЩЕНИЙ (MoneyTravis + ручной ввод)
# ─────────────────────────────────────────────
import re as _re

def _parse_moneytravis(text: str) -> dict | None:
    """
    Парсит 3 формата:
    1) MoneyTravis Telegram-форма (Сервер: X (#N), Никнейм: ..., Пароль: ...)
    2) MoneyTravis детали заказа (CITY (#N) на отдельной строке, потом Ник/Пароль)
    3) Ручной ввод: "сервер ник пароль [деньги]"
    """
    result = {}

    # ── Формат 1 и 2: ищем (#номер) ─────────────────────────────────────────
    m = _re.search(r'\(#(\d+)\)', text)
    if m:
        result['serverId'] = int(m.group(1))

        # Ник — ищем после Никнейм/Ник/Nick
        mn = _re.search(r'(?:Никнейм|Ник|Nick)\s*:?\s*\n?\s*([A-Za-zА-Яа-яЁё][\w]{2,}(?:_[\w]{2,})?)', text, _re.IGNORECASE)
        if mn:
            result['nick'] = mn.group(1).strip()

        # Пароль — ищем после Пароль/Password
        mp = _re.search(r'(?:Пароль|Password)\s*:?\s*\n?\s*([A-Za-z0-9!@#$%^&*()+\-=_]{4,})', text, _re.IGNORECASE)
        if mp:
            result['pass'] = mp.group(1).strip()

        # Деньги — ищем вирты/сумму
        mm = _re.search(r'(?:Количество виртов|Виртов|Сумма заказа|Деньги|Вирты)\s*:?\s*\n?\s*([\d\s.,]+)', text, _re.IGNORECASE)
        if mm:
            raw = mm.group(1).strip().replace(' ','').replace(',','').replace('.','')
            try: result['money'] = int(raw)
            except: result['money'] = 0
        else:
            result['money'] = 0

        # Номер заказа
        mo = _re.search(r'Заказ\s*[:#]?\s*([A-Z0-9]{3,})', text, _re.IGNORECASE)
        if mo:
            result['order'] = mo.group(1).strip()

        if 'nick' in result and 'pass' in result:
            return result
        return None

    # ── Формат 3: ручной ввод "сервер ник пароль [деньги]" ──────────────────
    # Разделители: пробел, запятая, слэш
    parts = [p.strip() for p in _re.split(r'[,/]|\s+', text.strip()) if p.strip()]
    if len(parts) < 3:
        return None

    # Первая часть — сервер (слово или число)
    srv_id = find_server(parts[0])
    if not srv_id:
        return None

    # Вторая часть — ник (обычно Слово_Слово или просто слово)
    nick = parts[1]
    if not _re.match(r'^[A-Za-zА-Яа-яЁё][\w]{1,}', nick):
        return None

    # Третья часть — пароль
    password = parts[2]

    # Четвёртая (опционально) — деньги
    money = 0
    if len(parts) >= 4:
        try: money = int(parts[3].replace('.','').replace(',',''))
        except: money = 0

    return {
        'serverId': srv_id,
        'nick': nick,
        'pass': password,
        'money': money,
    }


async def _quick_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE, parsed: dict):
    """Добавляет аккаунт из распарсенных данных и отправляет подтверждение."""
    srv_id = parsed['serverId']

    if srv_id not in SERVERS:
        await update.message.reply_text(
            f"❌ Сервер #{srv_id} не найден.", reply_markup=kb_menu()
        )
        return

    # Дубликат?
    existing = [a for a in DB['accounts'] if a['serverId'] == srv_id and a['nick'] == parsed['nick']]
    if existing:
        await update.message.reply_text(
            f"⚠️ Аккаунт <code>{parsed['nick']}</code> уже есть на "
            f"#{srv_id} {SERVERS[srv_id]}!\n\nЕсли хочешь обновить — удали старый через меню.",
            parse_mode="HTML", reply_markup=kb_menu()
        )
        return

    order = parsed.get('order', '')
    note = f"MoneyTravis · #{order}" if order else "Быстрое добавление"

    acc = {
        "id": new_id(),
        "serverId": srv_id,
        "nick": parsed['nick'],
        "pass": parsed['pass'],
        "money": parsed['money'],
        "note": note
    }
    DB["accounts"].append(acc)
    save_db(DB)

    srv_name = SERVERS[srv_id]
    total = len(accs_of(srv_id))

    await update.message.reply_text(
        f"✅ <b>Аккаунт добавлен!</b>\n\n"
        f"🖥 Сервер: <b>#{srv_id} {srv_name}</b>\n"
        f"👤 Ник: <code>{acc['nick']}</code>\n"
        f"🔑 Пароль: <code>{acc['pass']}</code>\n"
        f"💰 Деньги: <b>{fmt_money(acc['money'])}</b>\n"
        f"📝 {note}\n\n"
        f"На сервере {srv_name} теперь {total} акк.",
        parse_mode="HTML", reply_markup=kb_menu()
    )


#!/usr/bin/env python3
"""
BR Vault Bot — менеджер аккаунтов Black Russia в Telegram
Данные хранятся в data.json на сервере.
Никакой аналитики и внешних API, только ты и твои данные.
"""

import os, json, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)

# ─────────────────────────────────────────────
#  КОНФИГ (берётся из переменных окружения)
# ─────────────────────────────────────────────
TOKEN        = os.environ.get("BOT_TOKEN", "")
ALLOWED_ID   = int(os.environ.get("ALLOWED_USER_ID", "0"))  # 0 = любой (небезопасно!)
DATA_FILE    = "data.json"
SRV_PER_PAGE = 10   # серверов на одной странице

# ─────────────────────────────────────────────
#  ПСЕВДОНИМЫ СЕРВЕРОВ (для ручного ввода)
# ─────────────────────────────────────────────
SERVER_ALIASES: dict[str, int] = {
    # #1 Red
    "red":1,"рэд":1,"ред":1,
    # #2 Green
    "green":2,"грин":2,"зеленый":2,"зелёный":2,
    # #3 Blue
    "blue":3,"блю":3,"синий":3,
    # #4 Yellow
    "yellow":4,"еллоу":4,"желтый":4,"жёлтый":4,
    # #5 Orange
    "orange":5,"оранж":5,
    # #6 Purple
    "purple":6,"пёрпл":6,"перпл":6,"фиолетовый":6,
    # #7 Lime
    "lime":7,"лайм":7,
    # #8 Pink
    "pink":8,"пинк":8,"розовый":8,
    # #9 Cherry
    "cherry":9,"черри":9,
    # #10 Black
    "black":10,"блэк":10,"черный":10,"чёрный":10,
    # #11 Indigo
    "indigo":11,"индиго":11,
    # #12 White
    "white":12,"вайт":12,"белый":12,
    # #13 Magenta
    "magenta":13,"маджента":13,"магента":13,
    # #14 Crimson
    "crimson":14,"кримсон":14,
    # #15 Gold
    "gold":15,"голд":15,"золото":15,
    # #16 Azure
    "azure":16,"эжур":16,"азур":16,
    # #17 Platinum
    "platinum":17,"платинум":17,"платина":17,
    # #18 Aqua
    "aqua":18,"аква":18,
    # #19 Gray
    "gray":19,"grey":19,"грей":19,"серый":19,
    # #20 Ice
    "ice":20,"айс":20,"лёд":20,"лед":20,
    # #21 Chilli
    "chilli":21,"chili":21,"чилли":21,"чили":21,
    # #22 Choco
    "choco":22,"чоко":22,"шоко":22,"шоколад":22,
    # #23 Moscow
    "moscow":23,"москва":23,"мск":23,"мосcow":23,
    # #24 SPB
    "spb":24,"спб":24,"питер":24,"петербург":24,"санктпетербург":24,"санкт-петербург":24,"санктпитер":24,
    # #25 UFA
    "ufa":25,"уфа":25,
    # #26 Sochi
    "sochi":26,"сочи":26,
    # #27 Kazan
    "kazan":27,"казань":27,"казан":27,
    # #28 Samara
    "samara":28,"самара":28,"самар":28,
    # #29 Rostov
    "rostov":29,"ростов":29,
    # #30 Anapa
    "anapa":30,"анапа":30,
    # #31 EKB
    "ekb":31,"екб":31,"екатеринбург":31,"yekaterinburg":31,"ekaterinburg":31,"ёбург":31,"ебург":31,
    # #32 Krasnodar
    "krasnodar":32,"краснодар":32,"краснод":32,
    # #33 Arzamas
    "arzamas":33,"арзамас":33,
    # #34 Novosibirsk
    "novosibirsk":34,"новосибирск":34,"новосиб":34,"новосибирcк":34,
    # #35 Grozny
    "grozny":35,"грозный":35,"грозни":35,
    # #36 Saratov
    "saratov":36,"саратов":36,
    # #37 Omsk
    "omsk":37,"омск":37,
    # #38 Irkutsk
    "irkutsk":38,"иркутск":38,
    # #39 Volgograd
    "volgograd":39,"волгоград":39,
    # #40 Voronezh
    "voronezh":40,"воронеж":40,
    # #41 Belgorod
    "belgorod":41,"белгород":41,
    # #42 Makhachkala
    "makhachkala":42,"махачкала":42,"махач":42,"makhach":42,
    # #43 Vladikavkaz
    "vladikavkaz":43,"владикавказ":43,"влдкавказ":43,
    # #44 Vladivostok
    "vladivostok":44,"владивосток":44,"влад":44,"vladik":44,
    # #45 Kaliningrad
    "kaliningrad":45,"калининград":45,"калинин":45,
    # #46 Chelyabinsk
    "chelyabinsk":46,"челябинск":46,"челяба":46,"chelyaba":46,
    # #47 Krasnoyarsk
    "krasnoyarsk":47,"красноярск":47,"красно":47,"краснояр":47,"krasno":47,
    # #48 Cheboksary
    "cheboksary":48,"чебоксары":48,"чебоксар":48,
    # #49 Khabarovsk
    "khabarovsk":49,"хабаровск":49,"хабар":49,"khabar":49,
    # #50 Perm
    "perm":50,"пермь":50,"перм":50,
    # #51 Tula
    "tula":51,"тула":51,
    # #52 Ryazan
    "ryazan":52,"рязань":52,"рязан":52,
    # #53 Murmansk
    "murmansk":53,"мурманск":53,"мурман":53,
    # #54 Penza
    "penza":54,"пенза":54,
    # #55 Kursk
    "kursk":55,"курск":55,
    # #56 Arkhangelsk
    "arkhangelsk":56,"архангельск":56,"архангел":56,"archangel":56,
    # #57 Orenburg
    "orenburg":57,"оренбург":57,
    # #58 Kirov
    "kirov":58,"киров":58,
    # #59 Kemerovo
    "kemerovo":59,"кемерово":59,"кемер":59,
    # #60 Tyumen
    "tyumen":60,"тюмень":60,"тюмен":60,
    # #61 Tolyatti
    "tolyatti":61,"тольятти":61,"тольяти":61,"тольяттти":61,
    # #62 Ivanovo
    "ivanovo":62,"иваново":62,"иваноо":62,
    # #63 Stavropol
    "stavropol":63,"ставрополь":63,"ставропол":63,
    # #64 Smolensk
    "smolensk":64,"смоленск":64,"смоленcк":64,
    # #65 Pskov
    "pskov":65,"псков":65,
    # #66 Bryansk
    "bryansk":66,"брянск":66,
    # #67 Orel
    "orel":67,"орёл":67,"орел":67,"oryol":67,
    # #68 Yaroslavl
    "yaroslavl":68,"ярославль":68,"ярославл":68,
    # #69 Barnaul
    "barnaul":69,"барнаул":69,
    # #70 Lipetsk
    "lipetsk":70,"липецк":70,
    # #71 Ulyanovsk
    "ulyanovsk":71,"ульяновск":71,
    # #72 Yakutsk
    "yakutsk":72,"якутск":72,
    # #73 Tambov
    "tambov":73,"тамбов":73,
    # #74 Bratsk
    "bratsk":74,"братск":74,
    # #75 Astrakhan
    "astrakhan":75,"астрахань":75,"астрахан":75,
    # #76 Chita
    "chita":76,"чита":76,
    # #77 Kostroma
    "kostroma":77,"кострома":77,
    # #78 Vladimir
    "vladimir":78,"владимир":78,
    # #79 Kaluga
    "kaluga":79,"калуга":79,
    # #80 N.Novgorod
    "novgorod":80,"нновгород":80,"нижний":80,"нижновгород":80,"нновг":80,"nnovgorod":80,"nn":80,"нн":80,
    # #81 Taganrog
    "taganrog":81,"таганрог":81,
    # #82 Vologda
    "vologda":82,"вологда":82,
    # #83 Tver
    "tver":83,"тверь":83,"твер":83,
    # #84 Tomsk
    "tomsk":84,"томск":84,
    # #85 Izhevsk
    "izhevsk":85,"ижевск":85,
    # #86 Surgut
    "surgut":86,"сургут":86,
    # #87 Podolsk
    "podolsk":87,"подольск":87,"подолск":87,
    # #88 Magadan
    "magadan":88,"магадан":88,
    # #89 Cherepovets
    "cherepovets":89,"череповец":89,"череповц":89,
    # #90 Norilsk
    "norilsk":90,"норильск":90,"норилск":90,
    # #91 Astana
    "astana":91,"астана":91,"нурсултан":91,"nursultan":91,
}

def find_server(query: str) -> int | None:
    """Ищет сервер по номеру, названию или псевдониму."""
    q = query.strip().lower().replace("ё","е")
    # по номеру
    if q.isdigit():
        sid = int(q)
        return sid if sid in SERVERS else None
    # точное совпадение псевдонима
    if q in SERVER_ALIASES:
        return SERVER_ALIASES[q]
    # частичное совпадение (начало слова)
    for alias, sid in SERVER_ALIASES.items():
        if alias.startswith(q) and len(q) >= 3:
            return sid
    return None



# ─────────────────────────────────────────────
#  СПИСОК СЕРВЕРОВ
# ─────────────────────────────────────────────
SERVERS = {
    1:"Red", 2:"Green", 3:"Blue", 4:"Yellow", 5:"Orange", 6:"Purple",
    7:"Lime", 8:"Pink", 9:"Cherry", 10:"Black", 11:"Indigo", 12:"White",
    13:"Magenta", 14:"Crimson", 15:"Gold", 16:"Azure", 17:"Platinum",
    18:"Aqua", 19:"Gray", 20:"Ice", 21:"Chilli", 22:"Choco", 23:"Moscow",
    24:"SPB", 25:"UFA", 26:"Sochi", 27:"Kazan", 28:"Samara", 29:"Rostov",
    30:"Anapa", 31:"EKB", 32:"Krasnodar", 33:"Arzamas", 34:"Novosibirsk",
    35:"Grozny", 36:"Saratov", 37:"Omsk", 38:"Irkutsk", 39:"Volgograd",
    40:"Voronezh", 41:"Belgorod", 42:"Makhachkala", 43:"Vladikavkaz",
    44:"Vladivostok", 45:"Kaliningrad", 46:"Chelyabinsk", 47:"Krasnoyarsk",
    48:"Cheboksary", 49:"Khabarovsk", 50:"Perm", 51:"Tula", 52:"Ryazan",
    53:"Murmansk", 54:"Penza", 55:"Kursk", 56:"Arkhangelsk", 57:"Orenburg",
    58:"Kirov", 59:"Kemerovo", 60:"Tyumen", 61:"Tolyatti", 62:"Ivanovo",
    63:"Stavropol", 64:"Smolensk", 65:"Pskov", 66:"Bryansk", 67:"Orel",
    68:"Yaroslavl", 69:"Barnaul", 70:"Lipetsk", 71:"Ulyanovsk", 72:"Yakutsk",
    73:"Tambov", 74:"Bratsk", 75:"Astrakhan", 76:"Chita", 77:"Kostroma",
    78:"Vladimir", 79:"Kaluga", 80:"N.Novgorod", 81:"Taganrog", 82:"Vologda",
    83:"Tver", 84:"Tomsk", 85:"Izhevsk", 86:"Surgut", 87:"Podolsk",
    88:"Magadan", 89:"Cherepovets", 90:"Norilsk", 91:"Astana"
}

# ─────────────────────────────────────────────
#  БАЗА ДАННЫХ (JSON-файл)
# ─────────────────────────────────────────────
def load_db() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # Первый запуск — вставляем аккаунты с твоих скринов
    db = {
        "next_id": 10,
        "accounts": [
            {"id":1,"serverId":51,"nick":"Hamir_Dory",          "pass":"KIgx27r4oW","money":500000,"note":"Test1 · ⚠ сверь пароль (I/l)"},
            {"id":2,"serverId":16,"nick":"Rusan_Guzunov",       "pass":"FCZNZRRPoU","money":500000,"note":"Test1"},
            {"id":3,"serverId":77,"nick":"Tenechek_Yanechev",   "pass":"IEtPHlQL9l","money":500000,"note":"Test1 · ⚠ сверь пароль (I/l)"},
            {"id":4,"serverId":36,"nick":"Ionmarina_Gotlibina", "pass":"McMU7yYx4O","money":500000,"note":"Test1 · ⚠ сверь пароль (O/0)"},
            {"id":5,"serverId":78,"nick":"Tarasis_Lipnickij",   "pass":"1XgBPvPgkz","money":555555,"note":"Test1"},
            {"id":6,"serverId":21,"nick":"Elza_Shapk",          "pass":"5bbOaxrZeB","money":500000,"note":"Test1 · ⚠ сверь пароль (O/0)"},
            {"id":7,"serverId":24,"nick":"Apuk_Wear",           "pass":"dXaxvHMOom","money":500000,"note":"Test1 · ⚠ сверь пароль (O/0)"},
            {"id":8,"serverId":56,"nick":"Vinder_Nesre",        "pass":"F8XKcv3jJt","money":555555,"note":"Test1"},
            {"id":9,"serverId":54,"nick":"Afesto_Gylic",        "pass":"LSpJ5QNdyn","money":500000,"note":"Test1"},
        ]
    }
    save_db(db)
    return db

def save_db(db: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

DB = load_db()

# ─── хелперы базы ───────────────────────────
def accs_of(srv_id: int) -> list:
    return [a for a in DB["accounts"] if a["serverId"] == srv_id]

def acc_by_id(acc_id: int) -> dict | None:
    return next((a for a in DB["accounts"] if a["id"] == acc_id), None)

def new_id() -> int:
    i = DB.get("next_id", 10)
    DB["next_id"] = i + 1
    return i

def fmt_money(n) -> str:
    return f"{int(n or 0):,}".replace(",", " ")

# ─────────────────────────────────────────────
#  АВТОРИЗАЦИЯ — только ты пользуешься ботом
# ─────────────────────────────────────────────
def is_allowed(update: Update) -> bool:
    ALLOWED_IDS = [int(x) for x in os.environ.get("ALLOWED_USER_ID", "0").split(",")]
    uid = update.effective_user.id if update.effective_user else 0
    return 0 in ALLOWED_IDS or uid in ALLOWED_IDS

# ─────────────────────────────────────────────
#  КЛАВИАТУРЫ
# ─────────────────────────────────────────────
def kb_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Серверы", callback_data="servers:0:0"),
         InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("⚡ Быстрое добавление", callback_data="quick_help")],
        [InlineKeyboardButton("🔍 Поиск по нику", callback_data="search_start")],
        [InlineKeyboardButton("💾 Экспорт", callback_data="export"),
         InlineKeyboardButton("📂 Импорт", callback_data="import_hint")],
    ])

def kb_servers(page: int, only_with: bool) -> InlineKeyboardMarkup:
    all_srvs = list(SERVERS.items())
    if only_with:
        all_srvs = [(i, n) for i, n in all_srvs if accs_of(i)]

    total_pages = max(1, (len(all_srvs) + SRV_PER_PAGE - 1) // SRV_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    chunk = all_srvs[page * SRV_PER_PAGE:(page + 1) * SRV_PER_PAGE]

    rows = []
    row = []
    for sid, name in chunk:
        cnt = len(accs_of(sid))
        label = f"#{sid} {name} {'✅'+str(cnt) if cnt else '❌'}"
        row.append(InlineKeyboardButton(label, callback_data=f"server:{sid}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"servers:{page-1}:{int(only_with)}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"servers:{page+1}:{int(only_with)}"))
    rows.append(nav)

    toggle = ("🟢 Все серверы", f"servers:0:0") if only_with else ("🔽 Только с аккаунтами", f"servers:0:1")
    rows.append([InlineKeyboardButton(toggle[0], callback_data=toggle[1])])
    rows.append([InlineKeyboardButton("◀ Меню", callback_data="menu")])
    return InlineKeyboardMarkup(rows)

def kb_server(srv_id: int, has_accs: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_accs:
        rows.append([InlineKeyboardButton("👁 Посмотреть аккаунты", callback_data=f"acc_list:{srv_id}:0:0")])
    rows.append([InlineKeyboardButton("➕ Добавить аккаунт", callback_data=f"add_start:{srv_id}")])
    rows.append([InlineKeyboardButton("◀ К серверам", callback_data="servers:0:0")])
    return InlineKeyboardMarkup(rows)

def kb_acc(srv_id: int, idx: int, total: int, acc_id: int, show: bool) -> InlineKeyboardMarkup:
    rows = []
    nav = []
    if idx > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"acc_list:{srv_id}:{idx-1}:{int(show)}"))
    nav.append(InlineKeyboardButton(f"{idx+1}/{total}", callback_data="noop"))
    if idx < total - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"acc_list:{srv_id}:{idx+1}:{int(show)}"))
    if nav: rows.append(nav)

    eye = "🙈 Скрыть пароль" if show else "👁 Показать пароль"
    rows.append([InlineKeyboardButton(eye, callback_data=f"acc_list:{srv_id}:{idx}:{int(not show)}")])
    rows.append([
        InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_start:{acc_id}"),
        InlineKeyboardButton("🗑 Удалить",  callback_data=f"del_ask:{acc_id}:{srv_id}"),
    ])
    rows.append([InlineKeyboardButton("◀ К серверу", callback_data=f"server:{srv_id}")])
    return InlineKeyboardMarkup(rows)

def kb_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="menu")]])

def kb_del_confirm(acc_id: int, srv_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Да, удалить", callback_data=f"del_confirm:{acc_id}:{srv_id}"),
        InlineKeyboardButton("❌ Отмена", callback_data=f"server:{srv_id}"),
    ]])

# ─────────────────────────────────────────────
#  ТЕКСТЫ
# ─────────────────────────────────────────────
def text_acc(acc: dict, show: bool) -> str:
    srv = SERVERS.get(acc["serverId"], "?")
    pw  = acc["pass"] if show else "••••••••"
    note = f"\n📝 <i>{acc['note']}</i>" if acc.get("note") else ""
    return (
        f"<b>#{acc['serverId']} {srv}</b>\n\n"
        f"👤 Ник: <code>{acc['nick']}</code>\n"
        f"🔑 Пароль: <code>{pw}</code>\n"
        f"💰 Деньги: <b>{fmt_money(acc['money'])}</b>"
        f"{note}"
    )

def text_stats() -> str:
    accs = DB["accounts"]
    with_acc  = len({a["serverId"] for a in accs})
    tot_money = sum(a.get("money") or 0 for a in accs)
    lines = [
        "📊 <b>Статистика BR Vault</b>\n",
        f"🖥 Серверов всего: <b>91</b>",
        f"✅ С аккаунтами: <b>{with_acc}</b>",
        f"👤 Аккаунтов: <b>{len(accs)}</b>",
        f"💰 Сумма: <b>{fmt_money(tot_money)}</b>",
    ]
    if accs:
        by_srv: dict[int, list] = {}
        for a in accs:
            by_srv.setdefault(a["serverId"], []).append(a)
        lines.append("\n<b>По серверам:</b>")
        for sid in sorted(by_srv):
            bunch = by_srv[sid]
            m = sum(a.get("money") or 0 for a in bunch)
            lines.append(f"  #{sid} {SERVERS[sid]}: {len(bunch)} акк. · {fmt_money(m)}")
    return "\n".join(lines)

# ─────────────────────────────────────────────
#  КОМАНДЫ
# ─────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return
    ctx.user_data.clear()
    await update.message.reply_text(
        "🎮 <b>BR Vault</b> — твой менеджер аккаунтов Black Russia\n\n"
        "Все данные хранятся только на сервере бота.\nВыбери действие:",
        reply_markup=kb_menu(), parse_mode="HTML"
    )

async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    await _send_export(update.message)

# ─────────────────────────────────────────────
#  CALLBACK (кнопки)
# ─────────────────────────────────────────────
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    q = update.callback_query
    await q.answer()
    d = q.data

    async def edit(text: str, kb=None):
        try:
            await q.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass  # Telegram бросает ошибку если текст не изменился

    # ── меню ──────────────────────────────────
    if d == "noop":
        return

    if d == "menu":
        ctx.user_data.clear()
        await edit("🎮 <b>BR Vault</b>\n\nВыбери действие:", kb_menu())

    # ── список серверов ───────────────────────
    elif d.startswith("servers:"):
        _, page, only = d.split(":")
        label = "📋 <b>Серверы Black Russia</b>\n✅ — есть аккаунт | ❌ — нет\n"
        if only == "1":
            label = "📋 <b>Серверы с аккаунтами</b>\n"
        await edit(label, kb_servers(int(page), only == "1"))

    # ── карточка сервера ──────────────────────
    elif d.startswith("server:"):
        sid = int(d.split(":")[1])
        accs = accs_of(sid)
        m = sum(a.get("money") or 0 for a in accs)
        await edit(
            f"🖥 <b>#{sid} {SERVERS[sid]}</b>\n\n"
            f"👤 Аккаунтов: <b>{len(accs)}</b>\n"
            f"💰 Суммарно: <b>{fmt_money(m)}</b>",
            kb_server(sid, bool(accs))
        )

    # ── просмотр аккаунтов сервера ────────────
    elif d.startswith("acc_list:"):
        _, sid, idx, show = d.split(":")
        sid, idx, show = int(sid), int(idx), bool(int(show))
        accs = accs_of(sid)
        if not accs:
            await edit(f"На сервере #{sid} пусто.", kb_server(sid, False))
            return
        idx = max(0, min(idx, len(accs) - 1))
        acc = accs[idx]
        await edit(text_acc(acc, show), kb_acc(sid, idx, len(accs), acc["id"], show))

    # ── статистика ────────────────────────────
    elif d == "stats":
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="menu")]])
        await edit(text_stats(), back_kb)

    # ── экспорт ───────────────────────────────
    elif d == "quick_help":
        txt = (
            "⚡ <b>Быстрое добавление аккаунта</b>\n\n"
            "Просто перешли мне сообщение от <b>MoneyTravis бота</b> — "
            "аккаунт добавится автоматически.\n\n"
            "Или напиши вручную в одну строку:\n"
            "<code>сервер ник пароль деньги</code>\n\n"
            "<b>Примеры:</b>\n"
            "<code>красноярск Weety_Talbert Id6DBxAPOo 575000</code>\n"
            "<code>47 Weety_Talbert Id6DBxAPOo 575000</code>\n"
            "<code>краснояр Weety_Talbert Id6DBxAPOo</code>\n"
            "<code>white Nick_Name PassWord123 100000</code>\n\n"
            "<b>Как писать сервер:</b>\n"
            "По номеру: <code>47</code>\n"
            "По-русски: <code>красноярск</code> или <code>красно</code>\n"
            "По-английски: <code>krasnoyarsk</code> или <code>krasno</code>\n\n"
            "<b>Популярные серверы:</b>\n"
            "москва/moscow/23 · питер/spb/24 · краснояр/47\n"
            "вайт/white/12 · астана/astana/91 · екб/ekb/31\n"
            "чили/chilli/21 · голд/gold/15 · блэк/black/10\n\n"
            "Деньги можно не указывать — поставится 0."
        )
        await edit(txt, InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="menu")]]))

    elif d == "export":
        await _send_export(q.message)

    elif d == "import_hint":
        await edit(
            "📂 <b>Импорт</b>\n\n"
            "Просто отправь мне JSON-файл бэкапа.\n"
            "<i>Файл должен быть создан через «Экспорт».</i>",
            InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="menu")]])
        )

    # ── поиск ────────────────────────────────
    elif d == "search_start":
        ctx.user_data["state"] = "search"
        await edit("🔍 Введи ник для поиска (или его часть):", kb_cancel())

    # ── начало добавления ─────────────────────
    elif d.startswith("add_start:"):
        sid = int(d.split(":")[1])
        ctx.user_data.update({"state": "add_nick", "srv": sid, "tmp": {}})
        await edit(
            f"➕ <b>Новый аккаунт · #{sid} {SERVERS[sid]}</b>\n\n"
            "👤 Введи ник:",
            kb_cancel()
        )

    # ── начало редактирования ─────────────────
    elif d.startswith("edit_start:"):
        acc_id = int(d.split(":")[1])
        acc = acc_by_id(acc_id)
        if not acc: await edit("❌ Не найдено."); return
        ctx.user_data.update({
            "state": "edit_nick",
            "tmp": {"acc_id": acc_id, "nick": acc["nick"], "pass": acc["pass"],
                    "money": acc["money"], "srv": acc["serverId"]}
        })
        await edit(
            f"✏️ <b>Редактирование · {acc['nick']}</b>\n\n"
            f"👤 Новый ник (сейчас: <code>{acc['nick']}</code>)\n"
            f"Или отправь «.» чтобы оставить без изменений:",
            kb_cancel()
        )

    # ── удалить (запрос) ──────────────────────
    elif d.startswith("del_ask:"):
        _, acc_id, srv_id = d.split(":")
        acc = acc_by_id(int(acc_id))
        nick = acc["nick"] if acc else "?"
        await edit(
            f"🗑 Удалить аккаунт <b>{nick}</b>?\nОтменить нельзя.",
            kb_del_confirm(int(acc_id), int(srv_id))
        )

    # ── удалить (подтверждение) ───────────────
    elif d.startswith("del_confirm:"):
        _, acc_id, srv_id = d.split(":")
        acc_id, srv_id = int(acc_id), int(srv_id)
        acc = acc_by_id(acc_id)
        nick = acc["nick"] if acc else "?"
        DB["accounts"] = [a for a in DB["accounts"] if a["id"] != acc_id]
        save_db(DB)
        accs = accs_of(srv_id)
        m = sum(a.get("money") or 0 for a in accs)
        await edit(
            f"✅ Аккаунт <code>{nick}</code> удалён.\n\n"
            f"🖥 <b>#{srv_id} {SERVERS[srv_id]}</b>\n"
            f"👤 Осталось: {len(accs)} | 💰 {fmt_money(m)}",
            kb_server(srv_id, bool(accs))
        )

# ─────────────────────────────────────────────
#  ХЭНДЛЕР СООБЩЕНИЙ (диалог ввода)
# ─────────────────────────────────────────────

async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return

    # JSON-файл = импорт
    doc = update.message.document
    if doc and doc.file_name and doc.file_name.endswith(".json"):
        await _do_import(update, ctx)
        return

    state = ctx.user_data.get("state")
    text  = (update.message.text or "").strip()

    # ── быстрое добавление по форме MoneyTravis ──────────
    if text and not state:
        parsed = _parse_moneytravis(text)
        if parsed:
            await _quick_add(update, ctx, parsed)
            return

    if not state or not text:
        return

    # ── поиск ───────────────────────────────
    if state == "search":
        q = text.lower()
        results = [a for a in DB["accounts"] if q in a["nick"].lower()]
        ctx.user_data.clear()
        if not results:
            await update.message.reply_text(
                f"🔍 По запросу «{text}» ничего не найдено.", reply_markup=kb_menu()
            )
        else:
            lines = [f"🔍 <b>Найдено по «{text}»</b>:\n"]
            for a in results:
                lines.append(f"• #{a['serverId']} {SERVERS[a['serverId']]} — <code>{a['nick']}</code> — {fmt_money(a['money'])}")
            await update.message.reply_text(
                "\n".join(lines), parse_mode="HTML", reply_markup=kb_menu()
            )

    # ── добавление ───────────────────────────
    elif state == "add_nick":
        ctx.user_data["tmp"]["nick"] = text
        ctx.user_data["state"] = "add_pass"
        await update.message.reply_text("🔑 Введи пароль:", reply_markup=kb_cancel())

    elif state == "add_pass":
        ctx.user_data["tmp"]["pass"] = text
        ctx.user_data["state"] = "add_money"
        await update.message.reply_text("💰 Введи сумму денег (только цифры, 0 если нет):", reply_markup=kb_cancel())

    elif state == "add_money":
        try: money = int(text.replace(" ", "").replace(".", "").replace(",", ""))
        except: money = 0
        ctx.user_data["tmp"]["money"] = money
        ctx.user_data["state"] = "add_note"
        await update.message.reply_text(
            "📝 Заметка (место регистрации, дата и т.д.)\nИли отправь «нет» чтобы пропустить:",
            reply_markup=kb_cancel()
        )

    elif state == "add_note":
        note = "" if text.lower() in ("нет", "no", "-", "0") else text
        tmp = ctx.user_data["tmp"]
        srv = ctx.user_data["srv"]
        acc = {"id": new_id(), "serverId": srv,
               "nick": tmp["nick"], "pass": tmp["pass"],
               "money": tmp["money"], "note": note}
        DB["accounts"].append(acc)
        save_db(DB)
        ctx.user_data.clear()
        await update.message.reply_text(
            f"✅ Аккаунт <code>{acc['nick']}</code> добавлен на #{srv} {SERVERS[srv]}!",
            parse_mode="HTML", reply_markup=kb_menu()
        )

    # ── редактирование ────────────────────────
    elif state == "edit_nick":
        tmp = ctx.user_data["tmp"]
        if text != ".":
            tmp["nick"] = text
        ctx.user_data["state"] = "edit_pass"
        await update.message.reply_text(
            f"🔑 Новый пароль (сейчас: <code>{tmp['pass']}</code>)\n"
            "Или «.» чтобы оставить:",
            parse_mode="HTML", reply_markup=kb_cancel()
        )

    elif state == "edit_pass":
        if text != ".":
            ctx.user_data["tmp"]["pass"] = text
        ctx.user_data["state"] = "edit_money"
        await update.message.reply_text(
            f"💰 Новая сумма (сейчас: {fmt_money(ctx.user_data['tmp']['money'])})\n"
            "Или «.» чтобы оставить:",
            reply_markup=kb_cancel()
        )

    elif state == "edit_money":
        if text != ".":
            try: ctx.user_data["tmp"]["money"] = int(text.replace(" ", "").replace(".", "").replace(",", ""))
            except: pass
        ctx.user_data["state"] = "edit_note"
        await update.message.reply_text(
            "📝 Новая заметка (или «нет» чтобы очистить, «.» чтобы оставить):",
            reply_markup=kb_cancel()
        )

    elif state == "edit_note":
        tmp = ctx.user_data["tmp"]
        acc = acc_by_id(tmp["acc_id"])
        if not acc:
            await update.message.reply_text("❌ Аккаунт не найден.", reply_markup=kb_menu())
            ctx.user_data.clear(); return
        if text == ".":
            note = acc.get("note", "")
        elif text.lower() in ("нет", "no", "-"):
            note = ""
        else:
            note = text
        acc.update({"nick": tmp["nick"], "pass": tmp["pass"], "money": tmp["money"], "note": note})
        save_db(DB)
        ctx.user_data.clear()
        await update.message.reply_text(
            f"✅ Аккаунт <code>{acc['nick']}</code> обновлён!",
            parse_mode="HTML", reply_markup=kb_menu()
        )

# ─────────────────────────────────────────────
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────────
async def _send_export(message):
    raw  = json.dumps(DB, ensure_ascii=False, indent=2).encode("utf-8")
    date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    await message.reply_document(
        document=raw,
        filename=f"br-vault-{date}.json",
        caption=f"✅ Бэкап · {len(DB['accounts'])} аккаунтов · {date}"
    )

async def _do_import(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    doc  = update.message.document
    file = await doc.get_file()
    raw  = await file.download_as_bytearray()
    try:
        new_db = json.loads(raw.decode("utf-8"))
        if "accounts" not in new_db: raise ValueError("no accounts key")
        DB.clear(); DB.update(new_db)
        save_db(DB)
        await update.message.reply_text(
            f"✅ Импортировано {len(DB['accounts'])} аккаунтов!",
            reply_markup=kb_menu()
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка при импорте: {e}\nОтправь файл бэкапа из этого бота.",
            reply_markup=kb_menu()
        )
    ctx.user_data.clear()

# ─────────────────────────────────────────────
#  ЗАПУСК
# ─────────────────────────────────────────────
def main():
    if not TOKEN:
        print("❌ Переменная BOT_TOKEN не задана!")
        print("   Локальный запуск: BOT_TOKEN=твой_токен python bot.py")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.ALL, on_message))

    print("✅ BR Vault Bot запущен. Нажми Ctrl+C для остановки.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
