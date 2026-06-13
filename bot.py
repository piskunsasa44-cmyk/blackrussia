#!/usr/bin/env python3
"""
BR Vault Bot — менеджер аккаунтов Black Russia
Версия 3.0 — с рич-аккаунтами, владельцами, поиском по серверу
"""
import os, json, re, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)

# ─────────────────────────────────────────────
#  КОНФИГ
# ─────────────────────────────────────────────
TOKEN        = os.environ.get("BOT_TOKEN", "")
DATA_FILE    = "data.json"
SRV_PER_PAGE = 10

# Кто имеет доступ к боту вообще
# Формат: "id1,id2,id3" или "0" = все
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID", "0")

# Кто имеет доступ к РИЧ-аккаунтам (только 2 человека из 5)
# Формат: "id1,id2" — вписать реальные Telegram ID
RICH_USER_IDS = os.environ.get("RICH_USER_IDS", "0")

OWNERS = ["ванклик", "саня", "сром", "даня", "блессед"]

# ─────────────────────────────────────────────
#  СЕРВЕРЫ
# ─────────────────────────────────────────────
SERVERS = {
    1:"Red",2:"Green",3:"Blue",4:"Yellow",5:"Orange",6:"Purple",
    7:"Lime",8:"Pink",9:"Cherry",10:"Black",11:"Indigo",12:"White",
    13:"Magenta",14:"Crimson",15:"Gold",16:"Azure",17:"Platinum",
    18:"Aqua",19:"Gray",20:"Ice",21:"Chilli",22:"Choco",23:"Moscow",
    24:"SPB",25:"UFA",26:"Sochi",27:"Kazan",28:"Samara",29:"Rostov",
    30:"Anapa",31:"EKB",32:"Krasnodar",33:"Arzamas",34:"Novosibirsk",
    35:"Grozny",36:"Saratov",37:"Omsk",38:"Irkutsk",39:"Volgograd",
    40:"Voronezh",41:"Belgorod",42:"Makhachkala",43:"Vladikavkaz",
    44:"Vladivostok",45:"Kaliningrad",46:"Chelyabinsk",47:"Krasnoyarsk",
    48:"Cheboksary",49:"Khabarovsk",50:"Perm",51:"Tula",52:"Ryazan",
    53:"Murmansk",54:"Penza",55:"Kursk",56:"Arkhangelsk",57:"Orenburg",
    58:"Kirov",59:"Kemerovo",60:"Tyumen",61:"Tolyatti",62:"Ivanovo",
    63:"Stavropol",64:"Smolensk",65:"Pskov",66:"Bryansk",67:"Orel",
    68:"Yaroslavl",69:"Barnaul",70:"Lipetsk",71:"Ulyanovsk",72:"Yakutsk",
    73:"Tambov",74:"Bratsk",75:"Astrakhan",76:"Chita",77:"Kostroma",
    78:"Vladimir",79:"Kaluga",80:"N.Novgorod",81:"Taganrog",82:"Vologda",
    83:"Tver",84:"Tomsk",85:"Izhevsk",86:"Surgut",87:"Podolsk",
    88:"Magadan",89:"Cherepovets",90:"Norilsk",91:"Astana"
}

SERVER_ALIASES = {
    "red":1,"рэд":1,"ред":1,
    "green":2,"грин":2,"зеленый":2,
    "blue":3,"блю":3,"синий":3,
    "yellow":4,"желтый":4,
    "orange":5,"оранж":5,
    "purple":6,"перпл":6,"фиолетовый":6,
    "lime":7,"лайм":7,
    "pink":8,"пинк":8,"розовый":8,
    "cherry":9,"черри":9,
    "black":10,"блэк":10,"черный":10,
    "indigo":11,"индиго":11,
    "white":12,"вайт":12,"белый":12,
    "magenta":13,"магента":13,
    "crimson":14,"кримсон":14,
    "gold":15,"голд":15,"золото":15,
    "azure":16,"азур":16,
    "platinum":17,"платинум":17,
    "aqua":18,"аква":18,
    "gray":19,"grey":19,"серый":19,
    "ice":20,"айс":20,"лед":20,
    "chilli":21,"chili":21,"чилли":21,"чили":21,
    "choco":22,"чоко":22,
    "moscow":23,"москва":23,"мск":23,
    "spb":24,"спб":24,"питер":24,"петербург":24,
    "ufa":25,"уфа":25,
    "sochi":26,"сочи":26,
    "kazan":27,"казань":27,
    "samara":28,"самара":28,
    "rostov":29,"ростов":29,
    "anapa":30,"анапа":30,
    "ekb":31,"екб":31,"екатеринбург":31,
    "krasnodar":32,"краснодар":32,
    "arzamas":33,"арзамас":33,
    "novosibirsk":34,"новосибирск":34,"новосиб":34,
    "grozny":35,"грозный":35,
    "saratov":36,"саратов":36,
    "omsk":37,"омск":37,
    "irkutsk":38,"иркутск":38,
    "volgograd":39,"волгоград":39,
    "voronezh":40,"воронеж":40,
    "belgorod":41,"белгород":41,
    "makhachkala":42,"махачкала":42,"махач":42,
    "vladikavkaz":43,"владикавказ":43,
    "vladivostok":44,"владивосток":44,
    "kaliningrad":45,"калининград":45,
    "chelyabinsk":46,"челябинск":46,"челяба":46,
    "krasnoyarsk":47,"красноярск":47,"красно":47,"краснояр":47,"krasno":47,
    "cheboksary":48,"чебоксары":48,
    "khabarovsk":49,"хабаровск":49,"хабар":49,
    "perm":50,"пермь":50,
    "tula":51,"тула":51,
    "ryazan":52,"рязань":52,
    "murmansk":53,"мурманск":53,
    "penza":54,"пенза":54,
    "kursk":55,"курск":55,
    "arkhangelsk":56,"архангельск":56,"архангел":56,
    "orenburg":57,"оренбург":57,
    "kirov":58,"киров":58,
    "kemerovo":59,"кемерово":59,
    "tyumen":60,"тюмень":60,
    "tolyatti":61,"тольятти":61,"тольяти":61,
    "ivanovo":62,"иваново":62,
    "stavropol":63,"ставрополь":63,
    "smolensk":64,"смоленск":64,
    "pskov":65,"псков":65,
    "bryansk":66,"брянск":66,
    "orel":67,"орел":67,"орёл":67,
    "yaroslavl":68,"ярославль":68,
    "barnaul":69,"барнаул":69,
    "lipetsk":70,"липецк":70,
    "ulyanovsk":71,"ульяновск":71,
    "yakutsk":72,"якутск":72,
    "tambov":73,"тамбов":73,
    "bratsk":74,"братск":74,
    "astrakhan":75,"астрахань":75,
    "chita":76,"чита":76,
    "kostroma":77,"кострома":77,
    "vladimir":78,"владимир":78,
    "kaluga":79,"калуга":79,
    "novgorod":80,"нижний":80,"нн":80,"nn":80,
    "taganrog":81,"таганрог":81,
    "vologda":82,"вологда":82,
    "tver":83,"тверь":83,
    "tomsk":84,"томск":84,
    "izhevsk":85,"ижевск":85,
    "surgut":86,"сургут":86,
    "podolsk":87,"подольск":87,
    "magadan":88,"магадан":88,
    "cherepovets":89,"череповец":89,
    "norilsk":90,"норильск":90,
    "astana":91,"астана":91,"нурсултан":91,
}

def find_server(query: str):
    q = query.strip().lower().replace("ё","е")
    if q.isdigit():
        sid = int(q)
        return sid if sid in SERVERS else None
    if q in SERVER_ALIASES:
        return SERVER_ALIASES[q]
    for alias, sid in SERVER_ALIASES.items():
        if alias.startswith(q) and len(q) >= 3:
            return sid
    return None

# ─────────────────────────────────────────────
#  БАЗА ДАННЫХ
# ─────────────────────────────────────────────
def load_db():
    if os.path.exists(DATA_FILE):
        db = json.load(open(DATA_FILE,"r",encoding="utf-8"))
        if "rich_accounts" not in db:
            db["rich_accounts"] = []
            save_db(db)
        return db
    db = {
        "next_id": 10,
        "accounts": [
            {"id":1,"serverId":51,"nick":"Hamir_Dory","pass":"KIgx27r4oW","money":500000,"note":"Test1 · ⚠ сверь пароль","owner":None},
            {"id":2,"serverId":16,"nick":"Rusan_Guzunov","pass":"FCZNZRRPoU","money":500000,"note":"Test1","owner":None},
            {"id":3,"serverId":77,"nick":"Tenechek_Yanechev","pass":"IEtPHlQL9l","money":500000,"note":"Test1 · ⚠ сверь пароль","owner":None},
            {"id":4,"serverId":36,"nick":"Ionmarina_Gotlibina","pass":"McMU7yYx4O","money":500000,"note":"Test1","owner":None},
            {"id":5,"serverId":78,"nick":"Tarasis_Lipnickij","pass":"1XgBPvPgkz","money":555555,"note":"Test1","owner":None},
            {"id":6,"serverId":21,"nick":"Elza_Shapk","pass":"5bbOaxrZeB","money":500000,"note":"Test1","owner":None},
            {"id":7,"serverId":24,"nick":"Apuk_Wear","pass":"dXaxvHMOom","money":500000,"note":"Test1","owner":None},
            {"id":8,"serverId":56,"nick":"Vinder_Nesre","pass":"F8XKcv3jJt","money":555555,"note":"Test1","owner":None},
            {"id":9,"serverId":54,"nick":"Afesto_Gylic","pass":"LSpJ5QNdyn","money":500000,"note":"Test1","owner":None},
        ],
        "rich_accounts": []
    }
    save_db(db)
    return db

def save_db(db):
    json.dump(db, open(DATA_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

DB = load_db()

def accs_of(srv_id, rich=False):
    key = "rich_accounts" if rich else "accounts"
    return [a for a in DB[key] if a["serverId"] == srv_id]

def acc_by_id(acc_id, rich=False):
    key = "rich_accounts" if rich else "accounts"
    return next((a for a in DB[key] if a["id"] == acc_id), None)

def new_id():
    i = DB.get("next_id", 10)
    DB["next_id"] = i + 1
    return i

def fmt_money(n):
    return f"{int(n or 0):,}".replace(",", " ")

# ─────────────────────────────────────────────
#  АВТОРИЗАЦИЯ
# ─────────────────────────────────────────────
def get_uid(update: Update) -> int:
    return update.effective_user.id if update.effective_user else 0

def is_allowed(update: Update) -> bool:
    uid = get_uid(update)
    ids = [int(x) for x in ALLOWED_USER_ID.split(",")]
    return 0 in ids or uid in ids

def is_rich(uid: int) -> bool:
    ids = [int(x) for x in RICH_USER_IDS.split(",")]
    return 0 in ids or uid in ids

# ─────────────────────────────────────────────
#  КЛАВИАТУРЫ
# ─────────────────────────────────────────────
def kb_menu(uid=0):
    rows = [
        [InlineKeyboardButton("📋 Серверы", callback_data="servers:0:0"),
         InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("⚡ Быстрое добавление", callback_data="quick_help")],
        [InlineKeyboardButton("🔍 Поиск по нику", callback_data="srch_nick"),
         InlineKeyboardButton("🔎 Поиск по серверу", callback_data="srch_srv")],
    ]
    if is_rich(uid):
        rows.append([InlineKeyboardButton("💎 РИЧ аккаунты", callback_data="rich_menu")])
    rows.append([InlineKeyboardButton("💾 Экспорт", callback_data="export"),
                 InlineKeyboardButton("📂 Импорт", callback_data="import_hint")])
    return InlineKeyboardMarkup(rows)

def kb_servers(page, only_with, rich=False):
    pfx = "r" if rich else ""
    all_srvs = list(SERVERS.items())
    if only_with:
        all_srvs = [(i,n) for i,n in all_srvs if accs_of(i, rich)]
    total = max(1, (len(all_srvs)+SRV_PER_PAGE-1)//SRV_PER_PAGE)
    page = max(0, min(page, total-1))
    chunk = all_srvs[page*SRV_PER_PAGE:(page+1)*SRV_PER_PAGE]
    rows = []
    row = []
    for sid, name in chunk:
        cnt = len(accs_of(sid, rich))
        label = f"#{sid} {name} {'✅'+str(cnt) if cnt else '❌'}"
        row.append(InlineKeyboardButton(label, callback_data=f"{pfx}srv:{sid}"))
        if len(row) == 2: rows.append(row); row = []
    if row: rows.append(row)
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("◀", callback_data=f"{pfx}srvs:{page-1}:{int(only_with)}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total}", callback_data="noop"))
    if page < total-1: nav.append(InlineKeyboardButton("▶", callback_data=f"{pfx}srvs:{page+1}:{int(only_with)}"))
    rows.append(nav)
    tog = ("🟢 Все", f"{pfx}srvs:0:0") if only_with else ("🔽 С аккаунтами", f"{pfx}srvs:0:1")
    rows.append([InlineKeyboardButton(tog[0], callback_data=tog[1])])
    back = "rich_menu" if rich else "menu"
    rows.append([InlineKeyboardButton("◀ Назад", callback_data=back)])
    return InlineKeyboardMarkup(rows)

def kb_server(srv_id, has_accs, rich=False):
    pfx = "r" if rich else ""
    rows = []
    if has_accs:
        rows.append([InlineKeyboardButton("👁 Аккаунты", callback_data=f"{pfx}al:{srv_id}:0:0")])
    rows.append([InlineKeyboardButton("➕ Добавить", callback_data=f"{pfx}add:{srv_id}")])
    rows.append([InlineKeyboardButton("◀ К серверам", callback_data=f"{pfx}srvs:0:0")])
    return InlineKeyboardMarkup(rows)

def kb_acc(srv_id, idx, total, acc_id, show, rich=False):
    pfx = "r" if rich else ""
    rows = []
    nav = []
    if idx > 0: nav.append(InlineKeyboardButton("◀", callback_data=f"{pfx}al:{srv_id}:{idx-1}:{int(show)}"))
    nav.append(InlineKeyboardButton(f"{idx+1}/{total}", callback_data="noop"))
    if idx < total-1: nav.append(InlineKeyboardButton("▶", callback_data=f"{pfx}al:{srv_id}:{idx+1}:{int(show)}"))
    if nav: rows.append(nav)
    eye = "🙈 Скрыть" if show else "👁 Показать пароль"
    rows.append([InlineKeyboardButton(eye, callback_data=f"{pfx}al:{srv_id}:{idx}:{int(not show)}")])
    rows.append([
        InlineKeyboardButton("✏️ Изменить", callback_data=f"{pfx}edit:{acc_id}"),
        InlineKeyboardButton("🗑 Удалить", callback_data=f"{pfx}del:{acc_id}:{srv_id}"),
    ])
    rows.append([InlineKeyboardButton("👑 Владелец", callback_data=f"{pfx}own:{acc_id}:{srv_id}:{idx}")])
    rows.append([InlineKeyboardButton("◀ К серверу", callback_data=f"{pfx}srv:{srv_id}")])
    return InlineKeyboardMarkup(rows)

def kb_owner(acc_id, srv_id, idx, rich=False):
    pfx = "r" if rich else ""
    rows = []
    row = []
    for o in OWNERS:
        row.append(InlineKeyboardButton(o.capitalize(), callback_data=f"{pfx}so:{acc_id}:{srv_id}:{idx}:{o}"))
        if len(row) == 3: rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton("❌ Убрать", callback_data=f"{pfx}so:{acc_id}:{srv_id}:{idx}:none")])
    rows.append([InlineKeyboardButton("◀ Назад", callback_data=f"{pfx}al:{srv_id}:{idx}:0")])
    return InlineKeyboardMarkup(rows)

def kb_del_confirm(acc_id, srv_id, rich=False):
    pfx = "r" if rich else ""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Да", callback_data=f"{pfx}delok:{acc_id}:{srv_id}"),
        InlineKeyboardButton("❌ Отмена", callback_data=f"{pfx}srv:{srv_id}"),
    ]])

def kb_cancel(back="menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data=back)]])

# ─────────────────────────────────────────────
#  ТЕКСТЫ
# ─────────────────────────────────────────────
def text_acc(acc, show):
    srv = SERVERS.get(acc["serverId"], "?")
    pw = acc["pass"] if show else "••••••••"
    note = f"\n📝 <i>{acc['note']}</i>" if acc.get("note") else ""
    owner = f"\n👑 <b>{acc['owner'].capitalize()}</b>" if acc.get("owner") and acc["owner"] != "none" else ""
    return (f"<b>#{acc['serverId']} {srv}</b>\n\n"
            f"👤 Ник: <code>{acc['nick']}</code>\n"
            f"🔑 Пароль: <code>{pw}</code>\n"
            f"💰 Деньги: <b>{fmt_money(acc['money'])}</b>{owner}{note}")

def text_stats(uid=0):
    accs = DB["accounts"]
    with_acc = len({a["serverId"] for a in accs})
    tot = sum(a.get("money") or 0 for a in accs)
    lines = ["📊 <b>Статистика BR Vault</b>\n",
             f"🖥 Серверов: <b>91</b>",
             f"✅ С аккаунтами: <b>{with_acc}</b>",
             f"👤 Аккаунтов: <b>{len(accs)}</b>",
             f"💰 Сумма: <b>{fmt_money(tot)}</b>"]
    if is_rich(uid):
        raccs = DB["rich_accounts"]
        rtot = sum(a.get("money") or 0 for a in raccs)
        lines.append(f"\n💎 <b>Рич аккаунтов: {len(raccs)}</b>")
        lines.append(f"💰 Рич сумма: <b>{fmt_money(rtot)}</b>")
    if accs:
        by_srv = {}
        for a in accs: by_srv.setdefault(a["serverId"],[]).append(a)
        lines.append("\n<b>Обычные по серверам:</b>")
        for sid in sorted(by_srv):
            bunch = by_srv[sid]
            m = sum(a.get("money") or 0 for a in bunch)
            lines.append(f"  #{sid} {SERVERS[sid]}: {len(bunch)} акк. · {fmt_money(m)}")
    return "\n".join(lines)

# ─────────────────────────────────────────────
#  ПАРСЕР БЫСТРОГО ДОБАВЛЕНИЯ
# ─────────────────────────────────────────────
def parse_quick(text: str, rich=False):
    result = {}
    m = re.search(r'\(#(\d+)\)', text)
    if m:
        result['serverId'] = int(m.group(1))
        mn = re.search(r'(?:Никнейм|Ник|Nick)\s*:?\s*\n?\s*([A-Za-z][A-Za-z0-9_]{2,})', text, re.IGNORECASE)
        if mn: result['nick'] = mn.group(1).strip()
        mp = re.search(r'(?:Пароль|Password)\s*:?\s*\n?\s*([A-Za-z0-9!@#$%^&*()+\-=_]{4,})', text, re.IGNORECASE)
        if mp: result['pass'] = mp.group(1).strip()
        mm = re.search(r'(?:Количество виртов|Виртов|Сумма заказа|Деньги|Вирты)\s*:?\s*\n?\s*([\d\s.,]+)', text, re.IGNORECASE)
        if mm:
            try: result['money'] = int(mm.group(1).strip().replace(' ','').replace(',','').replace('.',''))
            except: result['money'] = 0
        else: result['money'] = 0
        mo = re.search(r'Заказ\s*[:#]?\s*([A-Z0-9]{3,})', text, re.IGNORECASE)
        if mo: result['order'] = mo.group(1).strip()
        if 'nick' in result and 'pass' in result:
            result['rich'] = rich
            return result
        return None
    parts = [p.strip() for p in re.split(r'[,/]|\s+', text.strip()) if p.strip()]
    if len(parts) < 3: return None
    srv_id = find_server(parts[0])
    if not srv_id: return None
    nick = parts[1]
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]{1,}', nick): return None
    password = parts[2]
    money = 0
    if len(parts) >= 4:
        try: money = int(parts[3].replace('.','').replace(',',''))
        except: money = 0
    return {'serverId': srv_id, 'nick': nick, 'pass': password, 'money': money, 'rich': rich}

# ─────────────────────────────────────────────
#  КОМАНДЫ
# ─────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): await update.message.reply_text("⛔ Нет доступа."); return
    ctx.user_data.clear()
    uid = get_uid(update)
    await update.message.reply_text(
        "🎮 <b>BR Vault</b> — менеджер аккаунтов Black Russia\n\nВыбери действие:",
        reply_markup=kb_menu(uid), parse_mode="HTML")

async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    await _send_export(update.message)

# ─────────────────────────────────────────────
#  CALLBACK HANDLER
# ─────────────────────────────────────────────
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = get_uid(update)

    async def edit(text, kb=None):
        try: await q.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        except: pass

    if d == "noop": return

    # ── ГЛАВНОЕ МЕНЮ ──────────────────────────────────────────────────────────
    elif d == "menu":
        ctx.user_data.clear()
        await edit("🎮 <b>BR Vault</b>\n\nВыбери действие:", kb_menu(uid))

    # ── БЫСТРОЕ ДОБАВЛЕНИЕ (инструкция) ──────────────────────────────────────
    elif d == "quick_help":
        await edit(
            "⚡ <b>Быстрое добавление</b>\n\n"
            "Перешли сообщение от <b>MoneyTravis</b> — аккаунт добавится сам.\n\n"
            "Или напиши одной строкой:\n"
            "<code>сервер ник пароль деньги</code>\n\n"
            "<b>Примеры:</b>\n"
            "<code>47 Nick_Name Pass123 575000</code>\n"
            "<code>красно Nick_Name Pass123</code>\n"
            "<code>white Nick_Name Pass123 100000</code>\n\n"
            "<b>Сервер можно писать:</b>\n"
            "Номером: <code>47</code>\n"
            "По-русски: <code>красноярск</code> / <code>красно</code>\n"
            "По-английски: <code>krasnoyarsk</code> / <code>krasno</code>\n\n"
            "Деньги можно не писать → поставится 0.",
            InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="menu")]]))

    # ── СТАТИСТИКА ────────────────────────────────────────────────────────────
    elif d == "stats":
        await edit(text_stats(uid), InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="menu")]]))

    # ── ПОИСК ─────────────────────────────────────────────────────────────────
    elif d == "srch_nick":
        ctx.user_data["state"] = "search_nick"
        await edit("🔍 Введи ник для поиска:", kb_cancel())

    elif d == "srch_srv":
        ctx.user_data["state"] = "search_srv"
        await edit("🔎 Введи номер или название сервера:\n<code>47</code> / <code>красно</code> / <code>krasno</code>", kb_cancel())

    # ── ЭКСПОРТ / ИМПОРТ ──────────────────────────────────────────────────────
    elif d == "export":
        raw = json.dumps(DB, ensure_ascii=False, indent=2).encode("utf-8")
        date = datetime.now().strftime("%Y-%m-%d_%H-%M")
        await q.message.reply_document(document=raw, filename=f"br-vault-{date}.json",
                                        caption=f"✅ Бэкап · {len(DB['accounts'])} обычных · {len(DB['rich_accounts'])} рич")

    elif d == "import_hint":
        await edit("📂 Просто отправь мне JSON-файл бэкапа.",
                   InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="menu")]]))

    # ══════════════════════════════════════════════════════════════════════════
    #  ОБЫЧНЫЕ АККАУНТЫ
    # ══════════════════════════════════════════════════════════════════════════
    elif d.startswith("servers:"):
        _, page, only = d.split(":")
        await edit("📋 <b>Серверы Black Russia</b>\n✅ — есть | ❌ — нет\n",
                   kb_servers(int(page), only=="1", rich=False))

    elif d.startswith("srv:"):
        sid = int(d.split(":")[1])
        accs = accs_of(sid, False)
        m = sum(a.get("money") or 0 for a in accs)
        await edit(f"🖥 <b>#{sid} {SERVERS[sid]}</b>\n\n"
                   f"👤 Аккаунтов: <b>{len(accs)}</b>\n"
                   f"💰 Суммарно: <b>{fmt_money(m)}</b>",
                   kb_server(sid, bool(accs), rich=False))

    elif d.startswith("al:"):
        _, sid, idx, show = d.split(":")
        sid, idx, show = int(sid), int(idx), bool(int(show))
        accs = accs_of(sid, False)
        if not accs: await edit(f"На #{sid} пусто.", kb_server(sid, False, rich=False)); return
        idx = max(0, min(idx, len(accs)-1))
        acc = accs[idx]
        await edit(text_acc(acc, show), kb_acc(sid, idx, len(accs), acc["id"], show, rich=False))

    elif d.startswith("add:"):
        sid = int(d.split(":")[1])
        ctx.user_data.update({"state":"add_nick","srv":sid,"tmp":{},"rich":False})
        await edit(f"➕ <b>Новый аккаунт · #{sid} {SERVERS[sid]}</b>\n\n👤 Введи ник:", kb_cancel())

    elif d.startswith("edit:"):
        acc_id = int(d.split(":")[1])
        acc = acc_by_id(acc_id, False)
        if not acc: await edit("❌ Не найдено."); return
        ctx.user_data.update({"state":"edit_nick","rich":False,
                               "tmp":{"acc_id":acc_id,"nick":acc["nick"],"pass":acc["pass"],"money":acc["money"]}})
        await edit(f"✏️ <b>{acc['nick']}</b>\n\n👤 Новый ник (или «.» оставить):", kb_cancel())

    elif d.startswith("del:"):
        _, acc_id, srv_id = d.split(":")
        acc = acc_by_id(int(acc_id), False)
        nick = acc["nick"] if acc else "?"
        await edit(f"🗑 Удалить <b>{nick}</b>?", kb_del_confirm(int(acc_id), int(srv_id), rich=False))

    elif d.startswith("delok:"):
        _, acc_id, srv_id = d.split(":")
        acc_id, srv_id = int(acc_id), int(srv_id)
        acc = acc_by_id(acc_id, False); nick = acc["nick"] if acc else "?"
        DB["accounts"] = [a for a in DB["accounts"] if a["id"] != acc_id]
        save_db(DB)
        accs = accs_of(srv_id, False)
        await edit(f"✅ <code>{nick}</code> удалён.\n\n🖥 #{srv_id} {SERVERS[srv_id]} · {len(accs)} акк.",
                   kb_server(srv_id, bool(accs), rich=False))

    elif d.startswith("own:"):
        _, acc_id, srv_id, idx = d.split(":")
        acc = acc_by_id(int(acc_id), False)
        cur = acc.get("owner") if acc else None
        cur_txt = f"Сейчас: <b>{cur.capitalize()}</b>" if cur and cur != "none" else "Не назначен"
        await edit(f"👑 Владелец <code>{acc['nick'] if acc else '?'}</code>\n{cur_txt}\n\nВыбери:",
                   kb_owner(int(acc_id), int(srv_id), int(idx), rich=False))

    elif d.startswith("so:"):
        parts = d.split(":")
        acc_id, srv_id, idx, owner = int(parts[1]), int(parts[2]), int(parts[3]), parts[4]
        acc = acc_by_id(acc_id, False)
        if acc: acc["owner"] = None if owner == "none" else owner; save_db(DB)
        accs = accs_of(srv_id, False); idx = max(0, min(idx, len(accs)-1))
        if accs:
            a = accs[idx]
            await edit(text_acc(a, False), kb_acc(srv_id, idx, len(accs), a["id"], False, rich=False))

    # ══════════════════════════════════════════════════════════════════════════
    #  РИЧ АККАУНТЫ
    # ══════════════════════════════════════════════════════════════════════════
    elif d == "rich_menu":
        if not is_rich(uid):
            await edit("⛔ У тебя нет доступа к рич-аккаунтам.")
            return
        raccs = DB["rich_accounts"]
        tot = sum(a.get("money") or 0 for a in raccs)
        rows = [
            [InlineKeyboardButton("📋 Серверы", callback_data="rsrvs:0:0"),
             InlineKeyboardButton("📊 Статистика рич", callback_data="rich_stats")],
            [InlineKeyboardButton("⚡ Быстрое добавление", callback_data="rich_qadd_hint")],
            [InlineKeyboardButton("◀ Главное меню", callback_data="menu")],
        ]
        await edit(
            f"💎 <b>РИЧ аккаунты</b>\n\n"
            f"👤 Аккаунтов: <b>{len(raccs)}</b>\n"
            f"💰 Суммарно: <b>{fmt_money(tot)}</b>\n\n"
            f"<i>Этот раздел виден только избранным.</i>",
            InlineKeyboardMarkup(rows))

    elif d == "rich_stats":
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        raccs = DB["rich_accounts"]
        tot = sum(a.get("money") or 0 for a in raccs)
        lines = [f"💎 <b>Рич статистика</b>\n",
                 f"👤 Аккаунтов: <b>{len(raccs)}</b>",
                 f"💰 Суммарно: <b>{fmt_money(tot)}</b>"]
        if raccs:
            by_srv = {}
            for a in raccs: by_srv.setdefault(a["serverId"],[]).append(a)
            lines.append("\n<b>По серверам:</b>")
            for sid in sorted(by_srv):
                bunch = by_srv[sid]
                m = sum(a.get("money") or 0 for a in bunch)
                lines.append(f"  #{sid} {SERVERS[sid]}: {len(bunch)} акк. · {fmt_money(m)}")
        await edit("\n".join(lines), InlineKeyboardMarkup([[InlineKeyboardButton("◀ Назад", callback_data="rich_menu")]]))

    elif d == "rich_qadd_hint":
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        ctx.user_data["rich_quick"] = True
        await edit(
            "💎 <b>Быстрое добавление в РИЧ</b>\n\n"
            "Перешли сообщение MoneyTravis или напиши:\n"
            "<code>сервер ник пароль деньги</code>\n\n"
            "Аккаунт попадёт в рич-раздел.",
            InlineKeyboardMarkup([[InlineKeyboardButton("◀ Отмена", callback_data="rich_menu")]]))

    elif d.startswith("rsrvs:"):
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        _, page, only = d.split(":")
        await edit("💎 <b>Рич серверы</b>\n✅ — есть | ❌ — нет\n",
                   kb_servers(int(page), only=="1", rich=True))

    elif d.startswith("rsrv:"):
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        sid = int(d.split(":")[1])
        accs = accs_of(sid, True)
        m = sum(a.get("money") or 0 for a in accs)
        await edit(f"💎 <b>#{sid} {SERVERS[sid]}</b>\n\n"
                   f"👤 Рич аккаунтов: <b>{len(accs)}</b>\n"
                   f"💰 Суммарно: <b>{fmt_money(m)}</b>",
                   kb_server(sid, bool(accs), rich=True))

    elif d.startswith("ral:"):
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        _, sid, idx, show = d.split(":")
        sid, idx, show = int(sid), int(idx), bool(int(show))
        accs = accs_of(sid, True)
        if not accs: await edit(f"На #{sid} нет рич аккаунтов.", kb_server(sid, False, rich=True)); return
        idx = max(0, min(idx, len(accs)-1))
        acc = accs[idx]
        await edit(text_acc(acc, show), kb_acc(sid, idx, len(accs), acc["id"], show, rich=True))

    elif d.startswith("radd:"):
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        sid = int(d.split(":")[1])
        ctx.user_data.update({"state":"add_nick","srv":sid,"tmp":{},"rich":True})
        await edit(f"💎 <b>Новый РИЧ аккаунт · #{sid} {SERVERS[sid]}</b>\n\n👤 Введи ник:", kb_cancel("rich_menu"))

    elif d.startswith("redit:"):
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        acc_id = int(d.split(":")[1])
        acc = acc_by_id(acc_id, True)
        if not acc: await edit("❌ Не найдено."); return
        ctx.user_data.update({"state":"edit_nick","rich":True,
                               "tmp":{"acc_id":acc_id,"nick":acc["nick"],"pass":acc["pass"],"money":acc["money"]}})
        await edit(f"✏️ <b>{acc['nick']}</b>\n\n👤 Новый ник (или «.» оставить):", kb_cancel("rich_menu"))

    elif d.startswith("rdel:"):
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        _, acc_id, srv_id = d.split(":")
        acc = acc_by_id(int(acc_id), True)
        nick = acc["nick"] if acc else "?"
        await edit(f"🗑 Удалить рич аккаунт <b>{nick}</b>?", kb_del_confirm(int(acc_id), int(srv_id), rich=True))

    elif d.startswith("rdelok:"):
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        _, acc_id, srv_id = d.split(":")
        acc_id, srv_id = int(acc_id), int(srv_id)
        acc = acc_by_id(acc_id, True); nick = acc["nick"] if acc else "?"
        DB["rich_accounts"] = [a for a in DB["rich_accounts"] if a["id"] != acc_id]
        save_db(DB)
        accs = accs_of(srv_id, True)
        await edit(f"✅ <code>{nick}</code> удалён из рич.\n\n💎 #{srv_id} {SERVERS[srv_id]} · {len(accs)} акк.",
                   kb_server(srv_id, bool(accs), rich=True))

    elif d.startswith("rown:"):
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        _, acc_id, srv_id, idx = d.split(":")
        acc = acc_by_id(int(acc_id), True)
        cur = acc.get("owner") if acc else None
        cur_txt = f"Сейчас: <b>{cur.capitalize()}</b>" if cur and cur != "none" else "Не назначен"
        await edit(f"👑 Владелец <code>{acc['nick'] if acc else '?'}</code>\n{cur_txt}\n\nВыбери:",
                   kb_owner(int(acc_id), int(srv_id), int(idx), rich=True))

    elif d.startswith("rso:"):
        if not is_rich(uid): await edit("⛔ Нет доступа."); return
        parts = d.split(":")
        acc_id, srv_id, idx, owner = int(parts[1]), int(parts[2]), int(parts[3]), parts[4]
        acc = acc_by_id(acc_id, True)
        if acc: acc["owner"] = None if owner == "none" else owner; save_db(DB)
        accs = accs_of(srv_id, True); idx = max(0, min(idx, len(accs)-1))
        if accs:
            a = accs[idx]
            await edit(text_acc(a, False), kb_acc(srv_id, idx, len(accs), a["id"], False, rich=True))

# ─────────────────────────────────────────────
#  MESSAGE HANDLER
# ─────────────────────────────────────────────
async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    uid = get_uid(update)

    doc = update.message.document
    if doc and doc.file_name and doc.file_name.endswith(".json"):
        await _do_import(update, ctx); return

    state = ctx.user_data.get("state")
    text = (update.message.text or "").strip()
    is_rich_mode = ctx.user_data.get("rich", False)

    # ── Быстрое добавление ────────────────────────────────────────────────────
    if text and not state:
        rich_quick = ctx.user_data.pop("rich_quick", False)
        if rich_quick and not is_rich(uid):
            await update.message.reply_text("⛔ Нет доступа к рич.", reply_markup=kb_menu(uid)); return
        parsed = parse_quick(text, rich=rich_quick)
        if parsed:
            await _quick_add(update, ctx, parsed, uid); return
        return

    if not state or not text: return

    # ── Поиск по нику ─────────────────────────────────────────────────────────
    if state == "search_nick":
        q = text.lower()
        results = [a for a in DB["accounts"] if q in a["nick"].lower()]
        if is_rich(uid):
            results += [a for a in DB["rich_accounts"] if q in a["nick"].lower()]
        ctx.user_data.clear()
        if not results:
            await update.message.reply_text(f"🔍 По «{text}» ничего.", reply_markup=kb_menu(uid))
        else:
            lines = [f"🔍 <b>Найдено по «{text}»</b>:\n"]
            for a in results:
                own = f" · 👑{a['owner'].capitalize()}" if a.get("owner") and a["owner"]!="none" else ""
                rich_mark = " 💎" if a in DB["rich_accounts"] else ""
                lines.append(f"• #{a['serverId']} {SERVERS[a['serverId']]} — <code>{a['nick']}</code> — {fmt_money(a['money'])}{own}{rich_mark}")
            await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=kb_menu(uid))

    # ── Поиск по серверу ──────────────────────────────────────────────────────
    elif state == "search_srv":
        srv_id = find_server(text)
        ctx.user_data.clear()
        if not srv_id:
            await update.message.reply_text(
                f"❌ Сервер «{text}» не найден.\nПопробуй номер или название.",
                reply_markup=kb_menu(uid)); return
        accs = accs_of(srv_id, False)
        srv_name = SERVERS[srv_id]
        if not accs:
            await update.message.reply_text(f"🖥 <b>#{srv_id} {srv_name}</b>\n\nАккаунтов нет.",
                                             parse_mode="HTML", reply_markup=kb_menu(uid)); return
        total_m = sum(a.get("money") or 0 for a in accs)
        lines = [f"🔎 <b>#{srv_id} {srv_name}</b> · {len(accs)} акк. · {fmt_money(total_m)}\n"]
        for a in accs:
            own = f" · 👑{a['owner'].capitalize()}" if a.get("owner") and a["owner"]!="none" else ""
            lines.append(f"• <code>{a['nick']}</code> — {fmt_money(a.get('money',0))}{own}")
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"📂 Открыть #{srv_id}", callback_data=f"srv:{srv_id}"),
            InlineKeyboardButton("◀ Меню", callback_data="menu")
        ]])
        await update.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)

    # ── Добавление аккаунта ───────────────────────────────────────────────────
    elif state == "add_nick":
        ctx.user_data["tmp"]["nick"] = text
        ctx.user_data["state"] = "add_pass"
        back = "rich_menu" if is_rich_mode else "menu"
        await update.message.reply_text("🔑 Введи пароль:", reply_markup=kb_cancel(back))

    elif state == "add_pass":
        ctx.user_data["tmp"]["pass"] = text
        ctx.user_data["state"] = "add_money"
        back = "rich_menu" if is_rich_mode else "menu"
        await update.message.reply_text("💰 Сумма денег (0 если нет):", reply_markup=kb_cancel(back))

    elif state == "add_money":
        try: money = int(text.replace(" ","").replace(".","").replace(",",""))
        except: money = 0
        ctx.user_data["tmp"]["money"] = money
        ctx.user_data["state"] = "add_note"
        back = "rich_menu" if is_rich_mode else "menu"
        await update.message.reply_text("📝 Заметка (или «нет»):", reply_markup=kb_cancel(back))

    elif state == "add_note":
        note = "" if text.lower() in ("нет","no","-","0") else text
        tmp = ctx.user_data["tmp"]; srv = ctx.user_data["srv"]; rich = ctx.user_data.get("rich", False)
        acc = {"id":new_id(),"serverId":srv,"nick":tmp["nick"],"pass":tmp["pass"],
               "money":tmp["money"],"note":note,"owner":None}
        key = "rich_accounts" if rich else "accounts"
        DB[key].append(acc); save_db(DB); ctx.user_data.clear()
        mark = "💎 Рич" if rich else "📋"
        await update.message.reply_text(
            f"✅ {mark} <code>{acc['nick']}</code> добавлен на #{srv} {SERVERS[srv]}!",
            parse_mode="HTML", reply_markup=kb_menu(uid))

    # ── Редактирование ────────────────────────────────────────────────────────
    elif state == "edit_nick":
        tmp = ctx.user_data["tmp"]; rich = ctx.user_data.get("rich", False)
        if text != ".": tmp["nick"] = text
        ctx.user_data["state"] = "edit_pass"
        back = "rich_menu" if rich else "menu"
        await update.message.reply_text(f"🔑 Пароль (или «.» оставить):", reply_markup=kb_cancel(back))

    elif state == "edit_pass":
        if text != ".": ctx.user_data["tmp"]["pass"] = text
        ctx.user_data["state"] = "edit_money"
        rich = ctx.user_data.get("rich", False)
        await update.message.reply_text("💰 Деньги (или «.» оставить):", reply_markup=kb_cancel("rich_menu" if rich else "menu"))

    elif state == "edit_money":
        if text != ".":
            try: ctx.user_data["tmp"]["money"] = int(text.replace(" ","").replace(".","").replace(",",""))
            except: pass
        ctx.user_data["state"] = "edit_note"
        rich = ctx.user_data.get("rich", False)
        await update.message.reply_text("📝 Заметка (или «нет» очистить, «.» оставить):",
                                         reply_markup=kb_cancel("rich_menu" if rich else "menu"))

    elif state == "edit_note":
        tmp = ctx.user_data["tmp"]; rich = ctx.user_data.get("rich", False)
        acc = acc_by_id(tmp["acc_id"], rich)
        if not acc:
            await update.message.reply_text("❌ Не найдено.", reply_markup=kb_menu(uid))
            ctx.user_data.clear(); return
        note = acc.get("note","") if text=="." else ("" if text.lower() in ("нет","no","-") else text)
        acc.update({"nick":tmp["nick"],"pass":tmp["pass"],"money":tmp["money"],"note":note})
        save_db(DB); ctx.user_data.clear()
        await update.message.reply_text(f"✅ <code>{acc['nick']}</code> обновлён!", parse_mode="HTML", reply_markup=kb_menu(uid))

# ─────────────────────────────────────────────
#  ВСПОМОГАТЕЛЬНЫЕ
# ─────────────────────────────────────────────
async def _quick_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE, parsed: dict, uid: int):
    srv_id = parsed['serverId']
    rich = parsed.get('rich', False)
    if srv_id not in SERVERS:
        await update.message.reply_text(f"❌ Сервер #{srv_id} не найден.", reply_markup=kb_menu(uid)); return
    key = "rich_accounts" if rich else "accounts"
    existing = [a for a in DB[key] if a['serverId']==srv_id and a['nick']==parsed['nick']]
    if existing:
        await update.message.reply_text(
            f"⚠️ <code>{parsed['nick']}</code> уже есть на #{srv_id} {SERVERS[srv_id]}!",
            parse_mode="HTML", reply_markup=kb_menu(uid)); return
    order = parsed.get('order','')
    note = f"MoneyTravis · #{order}" if order else "Быстрое добавление"
    acc = {"id":new_id(),"serverId":srv_id,"nick":parsed['nick'],"pass":parsed['pass'],
           "money":parsed['money'],"note":note,"owner":None}
    DB[key].append(acc); save_db(DB)
    total = len(accs_of(srv_id, rich))
    mark = "💎 Рич · " if rich else ""
    await update.message.reply_text(
        f"✅ <b>{mark}Аккаунт добавлен!</b>\n\n"
        f"🖥 Сервер: <b>#{srv_id} {SERVERS[srv_id]}</b>\n"
        f"👤 Ник: <code>{acc['nick']}</code>\n"
        f"🔑 Пароль: <code>{acc['pass']}</code>\n"
        f"💰 Деньги: <b>{fmt_money(acc['money'])}</b>\n\n"
        f"На сервере теперь {total} акк.",
        parse_mode="HTML", reply_markup=kb_menu(uid))

async def _send_export(message):
    raw = json.dumps(DB, ensure_ascii=False, indent=2).encode("utf-8")
    date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    await message.reply_document(document=raw, filename=f"br-vault-{date}.json",
                                  caption=f"✅ Бэкап · {len(DB['accounts'])} обычных · {len(DB['rich_accounts'])} рич")

async def _do_import(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = get_uid(update)
    doc = update.message.document; file = await doc.get_file(); raw = await file.download_as_bytearray()
    try:
        new_db = json.loads(raw.decode("utf-8"))
        if "accounts" not in new_db: raise ValueError
        if "rich_accounts" not in new_db: new_db["rich_accounts"] = []
        DB.clear(); DB.update(new_db); save_db(DB)
        await update.message.reply_text(
            f"✅ Импортировано {len(DB['accounts'])} обычных и {len(DB['rich_accounts'])} рич аккаунтов!",
            reply_markup=kb_menu(uid))
    except:
        await update.message.reply_text("❌ Неверный формат.", reply_markup=kb_menu(uid))
    ctx.user_data.clear()

# ─────────────────────────────────────────────
#  ЗАПУСК
# ─────────────────────────────────────────────
def main():
    if not TOKEN: print("❌ BOT_TOKEN не задан!"); return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.ALL, on_message))
    print("✅ BR Vault Bot v3.0 запущен.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
