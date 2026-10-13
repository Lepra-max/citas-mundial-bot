import os
import logging
import warnings
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, PreCheckoutQueryHandler,
    ConversationHandler
)
from telegram.request import HTTPXRequest
import db

warnings.filterwarnings("ignore", category=UserWarning)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")


ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))


(
    REG_NAME, REG_AGE, REG_GENDER, REG_LOOKING, REG_COUNTRY, REG_BIO, REG_PHOTO,
    EDIT_CHOICE, EDIT_VALUE,
    CHAT_STATE,
    MODEL_PHOTO1, MODEL_PHOTO2
) = range(12)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

request = HTTPXRequest(
    connect_timeout=60.0, read_timeout=60.0,
    write_timeout=60.0, pool_timeout=30.0,
)


# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = db.get_user(user.id)

    args = context.args
    if args and args[0].startswith("ref_") and not existing:
        try:
            referrer = int(args[0].split("_")[1])
            context.user_data["referred_by"] = referrer
        except Exception:
            pass

    if existing and existing[2]:
        await update.message.reply_text(
            f"¡Hola de nuevo, {existing[2]}! 💖\n\n"
            "🔍 /buscar — Ver perfiles\n"
            "👤 /perfil — Mi perfil\n"
            "💘 /matches — Mis matches\n"
            "💎 /vip — Hacerme VIP\n"
            "👥 /invitar — Invitar amigos\n"
            "❓ /ayuda — Más opciones"
        )
    else:
        keyboard = [
            [InlineKeyboardButton("👤 Crear mi perfil", callback_data="register")],
            [InlineKeyboardButton("👀 Explorar primero", callback_data="explore")]
        ]
        await update.message.reply_text(
            f"¡Hola {user.first_name}! 👋\n\n"
            "Soy *CitasMundialBot* 🌏\n\n"
            "Aquí no eres un número. Encuentra personas reales de todo el mundo que buscan algo genuino.\n\n"
            "✅ Perfiles reales\n"
            "✅ Tú decides quién te habla\n"
            "✅ Conexiones por región\n\n"
            "¿Empezamos? 👇",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ---------- /ayuda ----------
async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Comandos disponibles:*\n\n"
        "🔍 /buscar — Ver perfiles\n"
        "👤 /perfil — Ver mi perfil\n"
        "✏️ /editar — Editar mi perfil\n"
        "💘 /matches — Ver mis matches\n"
        "💎 /vip — Hacerme VIP\n"
        "👥 /invitar — Invitar amigos\n"
        "🚫 /reportar — Reportar usuario\n"
        "❓ /ayuda — Esta ayuda",
        parse_mode="Markdown"
    )


# ---------- REGISTRO ----------
async def registro_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "📝 Vamos a crear tu perfil.\n\n*Paso 1/7:* ¿Cuál es tu nombre?",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "📝 Vamos a crear tu perfil.\n\n*Paso 1/7:* ¿Cuál es tu nombre?",
            parse_mode="Markdown"
        )
    return REG_NAME


async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        f"Genial, {context.user_data['name']} ✨\n\n*Paso 2/7:* ¿Cuántos años tienes? (solo número)",
        parse_mode="Markdown"
    )
    return REG_AGE


async def reg_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text.strip())
        if age < 18 or age > 99:
            raise ValueError
        context.user_data["age"] = age
        keyboard = [
            [InlineKeyboardButton("👩 Mujer", callback_data="g_f"),
             InlineKeyboardButton("👨 Hombre", callback_data="g_m")],
            [InlineKeyboardButton("🌈 Otro", callback_data="g_o")]
        ]
        await update.message.reply_text(
            "*Paso 3/7:* ¿Cuál es tu género?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return REG_GENDER
    except ValueError:
        await update.message.reply_text("⚠️ Debes tener entre 18 y 99 años. Escribe solo el número.")
        return REG_AGE


async def reg_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mapping = {"g_f": "Mujer", "g_m": "Hombre", "g_o": "Otro"}
    context.user_data["gender"] = mapping[query.data]

    keyboard = [
        [InlineKeyboardButton("👩 Mujeres", callback_data="lf_f"),
         InlineKeyboardButton("👨 Hombres", callback_data="lf_m")],
        [InlineKeyboardButton("🌈 Me da igual", callback_data="lf_a")]
    ]
    await query.edit_message_text(
        f"Género: {context.user_data['gender']} ✅\n\n*Paso 4/7:* ¿A quién buscas?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return REG_LOOKING


async def reg_looking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mapping = {"lf_f": "Mujer", "lf_m": "Hombre", "lf_a": "Todos"}
    context.user_data["looking_for"] = mapping[query.data]

    # Mapear "Todos" a un valor que la BD entienda
    if context.user_data["looking_for"] == "Todos":
        context.user_data["looking_for_db"] = None  # significa que ve ambos
    else:
        context.user_data["looking_for_db"] = context.user_data["looking_for"]

    await query.edit_message_text(
        f"Buscas: {context.user_data['looking_for']} ✅\n\n"
        "*Paso 5/7:* ¿En qué país vives? (escrito, ej: Cuba)",
        parse_mode="Markdown"
    )
    return REG_COUNTRY


async def reg_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["country"] = update.message.text.strip()
    await update.message.reply_text(
        "*Paso 6/7:* Cuéntanos algo sobre ti (una frase corta).",
        parse_mode="Markdown"
    )
    return REG_BIO


async def reg_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["bio"] = update.message.text.strip()
    context.user_data["photo_count"] = 0
    await update.message.reply_text(
        "*Paso 7/7:* Envíame tu primera foto 📸\n\n"
        "Puedes enviar hasta 3 fotos. Cuando termines, envía /listo",
        parse_mode="Markdown"
    )
    return REG_PHOTO


async def reg_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text.strip() == "/listo":
        if context.user_data.get("photo_count", 0) == 0:
            await update.message.reply_text("⚠️ Necesitas al menos 1 foto para terminar.")
            return REG_PHOTO
        return await finalize_register(update, context)

    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ Envíame una foto, o envía /listo para terminar."
        )
        return REG_PHOTO

    count = context.user_data.get("photo_count", 0)
    if count >= 3:
        await update.message.reply_text("Ya tienes 3 fotos. Envía /listo para terminar.")
        return REG_PHOTO

    photo_id = update.message.photo[-1].file_id
    user_id = update.effective_user.id

    db.add_media(user_id, photo_id, "photo", count + 1)
    context.user_data["photo_count"] = count + 1

    if count + 1 < 3:
        await update.message.reply_text(
            f"✅ Foto {count + 1}/3 guardada.\n\n"
            "Envía otra foto o /listo para terminar."
        )
    else:
        await update.message.reply_text(
            "✅ 3 fotos guardadas. Envía /listo para terminar."
        )
    return REG_PHOTO


async def finalize_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referred_by = context.user_data.get("referred_by")

    db.save_user(
        user.id, user.username or "",
        context.user_data["name"],
        context.user_data["age"],
        context.user_data["gender"],
        context.user_data["looking_for_db"],
        context.user_data["country"],
        referred_by
    )
    db.update_bio(user.id, context.user_data["bio"])

    if referred_by:
        try:
            await context.bot.send_message(
                chat_id=referred_by,
                text="🎁 ¡Alguien se registró con tu enlace!"
            )
        except Exception:
            pass

    await update.message.reply_text(
        "🎉 *¡Tu perfil está listo!*\n\n"
        f"👤 {context.user_data['name']}, {context.user_data['age']}\n"
        f"🌍 {context.user_data['country']}\n\n"
        "Usa /buscar para empezar a conocer gente 💘",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado. Usa /start para volver.")
    return ConversationHandler.END


# ---------- PERFIL ----------
async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user or not user[2]:
        await update.message.reply_text("Aún no tienes perfil. Usa /registro")
        return

    # Dar VIP automático al admin
    if user_id == ADMIN_ID and not db.check_vip_expired(user_id):
        db.set_vip(user_id, 3650)
        user = db.get_user(user_id)

    is_vip = db.check_vip_expired(user[0])
    vip_tag = "💎 VIP" if is_vip else "🆓 Gratis"

    media = db.get_user_media(user[0])
    photos = [m[0] for m in media if m[1] == "photo"]

    caption = (
        f"👤 *Tu perfil*\n\n"
        f"Nombre: {user[2]}\n"
        f"Edad: {user[3]}\n"
        f"Género: {user[4]}\n"
        f"Busca: {user[5]}\n"
        f"País: {user[6]}\n"
        f"Bio: {user[7] or 'Sin bio'}\n"
        f"Estado: {vip_tag}\n"
        f"Likes restantes: {user[10]}\n"
    )

    if photos:
        await update.message.reply_photo(photo=photos[0], caption=caption, parse_mode="Markdown")
    else:
        await update.message.reply_text(caption, parse_mode="Markdown")


# ---------- BUSCAR ----------
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user or not user[2]:
        await update.message.reply_text("Primero crea tu perfil con /registro")
        return

    is_vip = db.check_vip_expired(user[0])
    likes_left = user[10]

    if likes_left <= 0 and not is_vip:
        keyboard = [[InlineKeyboardButton("💎 Hacerme VIP", callback_data="vip_buy")]]
        await update.message.reply_text(
            "Te quedaste sin likes 😢\n\nHazte VIP para likes ilimitados.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    looking = user[5] or "Todos"
    country = user[6]

    if looking == "Todos":
        # Buscar cualquiera
        profile = None
        for gender_option in ["Mujer", "Hombre", "Otro"]:
            profile = db.get_random_profile(update.effective_user.id, gender_option, country, is_vip)
            if profile:
                break
    else:
        profile = db.get_random_profile(update.effective_user.id, looking, country, is_vip)

    if not profile:
        await update.message.reply_text(
            "No hay más perfiles por ahora 😢\n\n"
            "Invita a tus amigos con /invitar para que el bot crezca."
        )
        return

    pid, pname, page, pgender, pcountry, pbio, pvip = profile

    keyboard = [
        [InlineKeyboardButton("❤️ Me gusta", callback_data=f"like_{pid}"),
         InlineKeyboardButton("👎 Pasar", callback_data=f"dislike_{pid}")],
        [InlineKeyboardButton("💬 Enviar mensaje", callback_data=f"msg_{pid}")],
        [InlineKeyboardButton("🚫 Reportar", callback_data=f"report_{pid}")]
    ]

    vip_tag = "💎" if pvip else ""
    caption = (
        f"👤 *{pname}* {vip_tag}\n"
        f"{page} años · {pgender}\n"
        f"🌍 {pcountry}\n"
        f"📝 {pbio or 'Sin descripción'}\n\n"
        f"Likes restantes: {likes_left if not is_vip else '∞'}"
    )

    media = db.get_user_media(pid)
    photos = [m[0] for m in media if m[1] == "photo"]

    if photos:
        await update.message.reply_photo(
            photo=photos[0], caption=caption,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            caption, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ---------- MATCHES ----------
async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = db.get_matches(update.effective_user.id)
    if not rows:
        await update.message.reply_text(
            "Aún no tienes matches 💔\n\nUsa /buscar para encontrar gente."
        )
        return

    text = "💘 *Tus matches:*\n\n"
    keyboard = []
    for uid, name, age, country in rows:
        text += f"• {name}, {age} ({country})\n"
        keyboard.append([InlineKeyboardButton(f"💬 Chatear con {name}", callback_data=f"chat_{uid}")])

    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------- EDITAR ----------
async def editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Bio", callback_data="edit_bio")],
        [InlineKeyboardButton("🌍 País", callback_data="edit_country")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="edit_cancel")]
    ]
    await update.message.reply_text(
        "✏️ ¿Qué quieres editar?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------- INVITAR ----------
async def invitar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = (await context.bot.get_me()).username
    user_id = update.effective_user.id
# ---------- REPORTAR ----------
async def reportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚫 Para reportar usa el botón *Reportar* que aparece en cada perfil.",
        parse_mode="Markdown"
    )


# ---------- STATS (ADMIN) ----------
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    import sqlite3
    conn = sqlite3.connect("citas.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE banned = 0")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = DATE('now')")
    hoy = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = DATE('now', '-1 day')")
    ayer = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_model = 1")
    modelos = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
    vips = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM matches")
    matches = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages")
    mensajes = c.fetchone()[0]
    conn.close()
    crec = f"+{hoy - ayer}" if hoy >= ayer else f"{hoy - ayer}"
    await update.message.reply_text(
        f"📊 *Panel de Admin*\n\n"
        f"👥 *Total usuarios:* {total}\n"
        f"🆕 *Hoy:* {hoy}\n"
        f"📅 *Ayer:* {ayer}\n"
        f"📈 *Crecimiento:* {crec}\n\n"
        f"🌹 *Modelos activas:* {modelos}\n"
        f"💎 *VIPs:* {vips}\n"
        f"💘 *Matches:* {matches}\n"
        f"💬 *Mensajes:* {mensajes}",
        parse_mode="Markdown"
    )


# ---------- VIP ----------
async def vip_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 VIP 30 días (250 ⭐)", callback_data="vip_buy")]
    ]
    await update.message.reply_text(
        "💎 *CitasMundial VIP*\n\n"
        "Con VIP obtienes:\n\n"
        "✅ Likes *ilimitados*\n"
        "✅ Tu perfil se muestra en *todas las regiones*\n"
        "✅ Apareces primero en las búsquedas\n"
        "✅ Insignia VIP en tu perfil\n\n"
        "Precio: *250 Stars* / 30 días\n\n"
        "Pulsa el botón para comprar 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def send_vip_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="VIP CitasMundial - 30 días",
        description="Likes ilimitados + perfil visible en todas las regiones",
        payload="vip_30d",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice("VIP 30 días", 250)],
        start_parameter="vip-30d"
    )


async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    amount = update.message.successful_payment.total_amount

    if payload == "vip_30d":
        db.set_vip(user_id, 30)
        msg = "🎉 ¡Ahora eres VIP por 30 días! 💎\n\nDisfruta de likes ilimitados y visibilidad global."
    elif payload.startswith("unlock_photo_"):
        model_id = int(payload.split("_")[2])
        db.unlock_photo(user_id, model_id)
        db.register_payment(user_id, model_id, 50, "photo")
        msg = "📸 ¡Foto desbloqueada! Usa /modelos para verla completa."
    elif payload.startswith("unlock_chat_"):
        model_id = int(payload.split("_")[2])
        db.unlock_chat(user_id, model_id)
        db.register_payment(user_id, model_id, 300, "chat")
        msg = "💬 ¡Chat desbloqueado! Ya puedes escribirle a la modelo."
    else:
        msg = "✅ ¡Pago recibido!"

    await update.message.reply_text(msg)

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"💰 *Nuevo pago*\n\n"
                 f"👤 {update.effective_user.first_name}\n"
                 f"🆔 `{user_id}`\n"
                 f"📦 {payload}\n"
                 f"⭐ {amount} Stars",
            parse_mode="Markdown"
        )
    except Exception:
        pass


# ---------- BOTONES ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data == "register":
        await query.edit_message_text(
            "📝 Vamos a crear tu perfil.\n\n*Paso 1/7:* ¿Cuál es tu nombre?",
            parse_mode="Markdown"
        )
        return

    if data == "explore":
        await query.edit_message_text("Usa /buscar para ver perfiles 👀")
        return

    if data == "modelo_si":
        await modelo_si(update, context)
        return
    if data == "modelo_no":
        await modelo_no(update, context)
        return

    if data == "vip_buy":
        await send_vip_invoice(update, context)
        return

    if data == "admin_ingresos":
        if user_id != ADMIN_ID:
            return
        await ingresos(update, context)
        return

    if data == "admin_reportes":
        if user_id != ADMIN_ID:
            return
        await admin_reportes(update, context)
        return

    if data == "admin_broadcast":
        if user_id != ADMIN_ID:
            return
        await admin_broadcast(update, context)
        return

    if data == "admin_refresh":
        if user_id != ADMIN_ID:
            return
        await query.edit_message_text("🔄 Actualiza con /admin")
        return

    if data == "admin_back":
        await query.edit_message_text("Usa /admin para volver al panel")
        return

    if data.startswith("unlock_photo_"):
        await unlock_photo_payment(update, context)
        return

    if data.startswith("unlock_chat_"):
        await unlock_chat_payment(update, context)
        return

    if data == "none":
        await query.answer("Ya tienes todo desbloqueado ✅")
        return

    if data.startswith("aprobar_"):
        if user_id != ADMIN_ID:
            return
        target = int(data.split("_")[1])
        db.approve_model(target)
        await query.edit_message_caption("✅ Modelo aprobada.")
        try:
            await context.bot.send_message(
                chat_id=target,
                text="🎉 *¡Felicidades!* Has sido aprobada como modelo de CitasMundial.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return

    if data.startswith("rechazar_"):
        if user_id != ADMIN_ID:
            return
        target = int(data.split("_")[1])
        db.reject_model(target)
        await query.edit_message_caption("❌ Solicitud rechazada.")
        try:
            await context.bot.send_message(
                chat_id=target,
                text="❌ Tu solicitud de modelo no fue aprobada."
            )
        except Exception:
            pass
        return

    if data.startswith("like_"):
        user_check = db.get_user(user_id)
        if user_check and user_check[13] == "approved":
            await query.edit_message_text("❌ Las modelos no pueden dar likes.")
            return
        target = int(data.split("_")[1])
        user = db.get_user(user_id)
        is_vip = db.check_vip_expired(user_id)
        if not is_vip and not db.use_like(user_id):
            keyboard = [[InlineKeyboardButton("💎 Hacerme VIP", callback_data="vip_buy")]]
            await query.edit_message_text(
                "Te quedaste sin likes 😢\n\nHazte VIP para ilimitados.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        db.save_like(user_id, target)
        if db.check_match(user_id, target):
            db.create_match(user_id, target)
            await query.edit_message_text("🎉 *¡ES UN MATCH!* 💘", parse_mode="Markdown")
            try:
                await context.bot.send_message(
                    chat_id=target,
                    text="🎉 *¡Tienes un nuevo match!* 💘\n\nUsa /matches para verlo.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        else:
            await query.edit_message_text("❤️ Like enviado. Usa /buscar para seguir.")
        return

    if data.startswith("dislike_"):
        await query.edit_message_text("👎 Pasaste. Usa /buscar para ver otro.")
        return

    if data.startswith("msg_") or data.startswith("chat_"):
        target = int(data.split("_")[1])
        context.user_data["chat_with"] = target
        context.user_data["in_chat"] = True
        await query.edit_message_text("💬 Escribe tu mensaje. (Para cancelar, /cancelar)")
        return

    if data.startswith("report_"):
        target = int(data.split("_")[1])
        db.report_user(user_id, target, "Reportado desde perfil")
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚨 *Reporte*\nUsuario `{user_id}` reportó a `{target}`",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await query.edit_message_text("✅ Reporte enviado. Gracias.")
        return

    if data.startswith("block_"):
        target = int(data.split("_")[1])
        db.block_user(user_id, target)
        await query.edit_message_text("⛔ Usuario bloqueado.")
        return

    if data == "edit_bio":
        context.user_data["edit_field"] = "bio"
        await query.edit_message_text("📝 Envía tu nueva bio:")
        return

    if data == "edit_country":
        context.user_data["edit_field"] = "country"
        await query.edit_message_text("🌍 Envía tu nuevo país:")
        return

    if data == "edit_cancel":
        await query.edit_message_text("❌ Edición cancelada.")
        return


# ---------- MANEJADOR DE TEXTO ----------
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.user_data.get("admin_broadcast"):
        if user_id != ADMIN_ID:
            return
        context.user_data["admin_broadcast"] = False
        text = update.message.text.strip()

        if text == "/cancelar":
            await update.message.reply_text("❌ Broadcast cancelado.")
            return

        import sqlite3
        conn = sqlite3.connect("citas.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE banned = 0")
        users = c.fetchall()
        conn.close()

        enviados = 0
        for (uid,) in users:
            try:
                await context.bot.send_message(chat_id=uid, text=f"📢 *Aviso:*\n\n{text}", parse_mode="Markdown")
                enviados += 1
            except Exception:
                pass

        await update.message.reply_text(f"✅ Mensaje enviado a {enviados} usuarios.")
        return
# ---------- MAIN ----------

async def modelo_si(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # Enviar mensaje al admin (tú)
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🌹 *Nueva solicitud de modelo*\n\n"
                 f"👤 {user.first_name}\n"
                 f"🆔 `{user.id}`\n"
                 f"📛 Usuario: @{user.username or 'sin_username'}\n\n"
                 f"Escríbele para coordinar las fotos.",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Error avisando al admin: {e}")

    await query.edit_message_text(
        "🎉 *¡Excelente decisión!*\n\n"
        "Hemos avisado al admin de tu interés.\n"
        "Él se pondrá en contacto contigo muy pronto.\n\n"
        "Mientras tanto, puedes ir preparando:\n"
        "1️⃣ Foto con la mano en la cara 🤳\n"
        "2️⃣ Foto con un papel que diga *CitasMundial* 📝\n\n"
        "Si quieres adelantar, escríbele tú directamente: @manu_alejandro",
        parse_mode="Markdown"
    )


async def modelo_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Sin problema. Usa /ser_modelo si cambias de opinión.")




async def blur_and_send(update, context, photo_id, caption, keyboard=None):
    """Descarga la foto, la difumina y la envía."""
    import io
    from PIL import Image, ImageFilter

    try:
        file = await context.bot.get_file(photo_id)
        file_bytes = await file.download_as_bytearray()

        img = Image.open(io.BytesIO(file_bytes))
        img = img.filter(ImageFilter.GaussianBlur(radius=25))

        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)

        await update.effective_chat.send_photo(
            photo=output,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error difuminando: {e}")
        await update.effective_chat.send_message(
            f"👤 {caption}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def modelos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra las modelos del mes con fotos difuminadas."""
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Primero crea tu perfil con /registro")
        return

    if user[3] == "Mujer":
        await update.message.reply_text(
            "🌹 Esta sección es para los caballeros. \n\n"
            "Si quieres ser modelo, usa /ser_modelo"
        )
        return

    models = db.get_active_models()
    if not models:
        await update.message.reply_text(
            "🌹 Aún no hay modelos disponibles. Vuelve pronto."
        )
        return

    await update.message.reply_text(
        f"🌹 *Modelos del Mes*\n\n"
        f"Hay *{len(models)}* modelos disponibles.\n"
        f"Desbloquea sus fotos por *50 Stars* o escríbeles por *300 Stars*.\n\n"
        f"👇 Aquí tienes la primera:",
        parse_mode="Markdown"
    )

    for model_id, name, age, country, photo1 in models:
        unlocked_photo = db.has_unlocked_photo(update.effective_user.id, model_id)
        unlocked_chat = db.has_unlocked_chat(update.effective_user.id, model_id)

        keyboard = []
        if not unlocked_photo:
            keyboard.append([InlineKeyboardButton("📸 Desbloquear foto (50 ⭐)", callback_data=f"unlock_photo_{model_id}")])
        if not unlocked_chat:
            keyboard.append([InlineKeyboardButton("💬 Escribir a la modelo (300 ⭐)", callback_data=f"unlock_chat_{model_id}")])
        
        if not keyboard:
            keyboard.append([InlineKeyboardButton("✅ Todo desbloqueado", callback_data="none")])

        caption = (
            f"🌹 *{name}*, {age} años\n"
            f"🌍 {country}\n\n"
            f"{'📸 Foto desbloqueada ✅' if unlocked_photo else '🔒 Foto bloqueada'}\n"
            f"{'💬 Chat desbloqueado ✅' if unlocked_chat else '🔒 Chat bloqueado'}"
        )

        if unlocked_photo and photo1:
            await update.message.reply_photo(
                photo=photo1,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif photo1:
            await blur_and_send(
                update, context, photo1, caption,
                InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                caption,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


async def unlock_photo_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el pago para desbloquear una foto."""
    query = update.callback_query
    await query.answer()
    model_id = int(query.data.split("_")[2])

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="Desbloquear foto de modelo",
        description="Ver la foto completa de esta modelo",
        payload=f"unlock_photo_{model_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice("Foto de modelo", 50)],
        start_parameter="unlock-photo"
    )


async def unlock_chat_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el pago para desbloquear el chat con una modelo."""
    query = update.callback_query
    await query.answer()
    model_id = int(query.data.split("_")[2])

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="Escribir a la modelo",
        description="Enviar un mensaje privado a esta modelo",
        payload=f"unlock_chat_{model_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice("Chat con modelo", 300)],
        start_parameter="unlock-chat"
    )


async def mi_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel para que las modelos vean sus ganancias."""
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Primero crea tu perfil con /registro")
        return

    if user[13] != "approved":
        await update.message.reply_text(
            "🌹 Este panel es solo para modelos aprobadas.\n\n"
            "Si quieres ser modelo, usa /ser_modelo"
        )
        return

    stats = db.get_model_stats(user[0])
    total = stats["total"]
    her_cut = stats["her_cut"]

    await update.message.reply_text(
        f"🌹 *Tu Panel de Modelo*\n\n"
        f"👁️ *Fotos vistas:* {stats['photos']}\n"
        f"💬 *Chats abiertos:* {stats['chats']}\n\n"
        f"💰 *Total generado:* {total} Stars\n"
        f"💵 *Tu 50%:* {her_cut} Stars\n"
        f"🏦 *Mi 50%:* {stats['your_cut']} Stars\n\n"
        f"📌 Los pagos se procesan semanalmente.\n"
        f"Contacta al admin para coordinar.",
        parse_mode="Markdown"
    )


async def ingresos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel de admin con los ingresos de todas las modelos."""
    if update.effective_user.id != ADMIN_ID:
        return

    rows = db.get_all_model_payments()
    if not rows:
        await update.message.reply_text("Aún no hay ingresos de modelos.")
        return

    texto = "💰 *Ingresos de Modelos*\n\n"
    total_general = 0
    total_a_pagar = 0

    for name, uid, total, photos, chats in rows:
        her_cut = total // 2
        total_general += total
        total_a_pagar += her_cut
        texto += (
            f"🌹 *{name}*\n"
            f"   📸 {photos} fotos | 💬 {chats} chats\n"
            f"   💰 {total} Stars (ella: {her_cut})\n\n"
        )

    texto += (
        f"━━━━━━━━━━━━━━━\n"
        f"📊 *Total general:* {total_general} Stars\n"
        f"💵 *A pagar a modelos:* {total_a_pagar} Stars\n"
        f"🏦 *Tu ganancia:* {total_general - total_a_pagar} Stars"
    )

    await update.message.reply_text(texto, parse_mode="Markdown")


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel de administración completo."""
    if update.effective_user.id != ADMIN_ID:
        return

    import sqlite3
    conn = sqlite3.connect("citas.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users WHERE banned = 0")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = DATE('now')")
    hoy = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = DATE('now', '-1 day')")
    ayer = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE is_model = 1")
    modelos = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
    vips = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM matches")
    matches = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM messages")
    mensajes = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM reports")
    reportes = c.fetchone()[0]

    c.execute("SELECT COALESCE(SUM(amount), 0) FROM model_payments")
    ingresos = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
    baneados = c.fetchone()[0]

    conn.close()

    crecimiento = f"+{hoy - ayer}" if hoy >= ayer else f"{hoy - ayer}"

    texto = (
        f"👑 *PANEL DE ADMIN*\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📊 *Estadísticas de usuarios*\n"
        f"👥 Total: *{total}*\n"
        f"🆕 Hoy: *{hoy}*\n"
        f"📅 Ayer: *{ayer}*\n"
        f"📈 Crecimiento: *{crecimiento}*\n\n"
        f"💎 VIPs: *{vips}*\n"
        f"🌹 Modelos: *{modelos}*\n"
        f"🚫 Baneados: *{baneados}*\n\n"
        f"💘 Matches: *{matches}*\n"
        f"💬 Mensajes: *{mensajes}*\n"
        f"🚨 Reportes: *{reportes}*\n\n"
        f"💰 *Ingresos totales:* *{ingresos} Stars*\n"
    )

    keyboard = [
        [InlineKeyboardButton("💰 Ver ingresos por modelo", callback_data="admin_ingresos")],
        [InlineKeyboardButton("🚨 Ver reportes", callback_data="admin_reportes")],
        [InlineKeyboardButton("📢 Enviar mensaje masivo", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 Actualizar", callback_data="admin_refresh")]
    ]

    await update.message.reply_text(
        texto,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prepara el envío de un mensaje masivo."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📢 *Enviar mensaje masivo*\n\n"
        "Envía el mensaje que quieres mandar a TODOS los usuarios.\n"
        "Escribe /cancelar para cancelar.",
        parse_mode="Markdown"
    )
    context.user_data["admin_broadcast"] = True


async def admin_reportes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los reportes pendientes."""
    query = update.callback_query
    await query.answer()

    import sqlite3
    conn = sqlite3.connect("citas.db")
    c = conn.cursor()
    c.execute("""SELECT r.reporter_id, r.reported_id, r.reason, r.created_at,
                 u.name FROM reports r
                 LEFT JOIN users u ON u.user_id = r.reported_id
                 ORDER BY r.created_at DESC LIMIT 10""")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await query.edit_message_text("✅ No hay reportes pendientes.")
        return

    texto = "🚨 *Últimos reportes:*\n\n"
    for rep_id, reported_id, reason, date, name in rows:
        texto += (
            f"👤 Reportado: *{name or reported_id}*\n"
            f"🆔 `{reported_id}`\n"
            f"📝 Razón: {reason}\n"
            f"🕐 {date}\n\n"
        )

    keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data="admin_back")]]
    await query.edit_message_text(
        texto,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def main():
    db.init_db()
    print("🤖 Iniciando CitasMundialBot...")
    # Dar VIP automático al admin
    admin = db.get_user(ADMIN_ID)
    if admin:
        db.set_vip(ADMIN_ID, 3650)
        print(f"✅ Admin ({ADMIN_ID}) configurado como VIP por 10 años")
    else:
        print(f"⚠️ Admin ({ADMIN_ID}) aún no tiene perfil. Regístrate primero con /registro")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(request)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("registro", registro_start),
            CommandHandler("ser_modelo", ser_modelo),
            CallbackQueryHandler(registro_start, pattern="^register$"),
        ],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_age)],
            REG_GENDER: [CallbackQueryHandler(reg_gender, pattern="^g_")],
            REG_LOOKING: [CallbackQueryHandler(reg_looking, pattern="^lf_")],
            REG_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_country)],
            REG_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_bio)],
            REG_PHOTO: [
                MessageHandler(filters.PHOTO, reg_photo),
                CommandHandler("listo", reg_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_photo),
            ],
            MODEL_PHOTO1: [MessageHandler(filters.PHOTO, model_photo1)],
            MODEL_PHOTO2: [MessageHandler(filters.PHOTO, model_photo2)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("perfil", perfil))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler("matches", matches))
    app.add_handler(CommandHandler("editar", editar))
    app.add_handler(CommandHandler("invitar", invitar))
    app.add_handler(CommandHandler("reportar", reportar))
    app.add_handler(CommandHandler("vip", vip_info))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("ser_modelo", ser_modelo))
    app.add_handler(CommandHandler("modelos_pendientes", modelos_pendientes))
    app.add_handler(CommandHandler("modelos", modelos))
    app.add_handler(CommandHandler("mi_panel", mi_panel))
    app.add_handler(CommandHandler("ingresos", ingresos))

    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("✅ Bot corriendo. Ctrl+C para detener.")
    app.run_polling()


async def ser_modelo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Primero crea tu perfil con /registro")
        return
    if user[3] != "Mujer":
        await update.message.reply_text("Esta opción es solo para mujeres.")
        return
    if user[13] == "approved":
        await update.message.reply_text("✅ Ya eres modelo activa.")
        return
    keyboard = [
        [InlineKeyboardButton("💎 Sí, quiero ser modelo", callback_data="modelo_si")],
        [InlineKeyboardButton("❌ No, gracias", callback_data="modelo_no")]
    ]
    await update.message.reply_text(
        "🌹 *Conviértete en Modelo CitasMundial*\n\n"
        "¿Sabías que las modelos de nuestro bot están entre las mujeres más vistas del mundo? 🔥\n\n"
        "*Esto es lo que obtienes:*\n\n"
        "✨ *Perfil destacado en TODAS las regiones*\n"
        "✨ *Aparece en la sección Modelos del Mes*\n"
        "✨ *Gana dinero real por cada hombre que vea tu perfil*\n"
        "✨ *Gana dinero real por cada chat privado que recibas*\n"
        "✨ *Tú decides cuándo y con quién hablar*\n"
        "✨ *Sin obligación de dar likes ni matches*\n"
        "✨ *Solo chateas si tú quieres, cuando tú quieras*\n\n"
        "*Requisitos:*\n"
        "• Ser mujer verificada (2 fotos con poses específicas)\n"
        "• Ser mayor de edad\n"
        "• Compromiso de 1 mes mínimo\n\n"
        "*Ganancias:*\n"
        "• 50% para ti de cada interacción\n"
        "• Pagos semanales o mensuales (a convenir)\n"
        "• Transferencia por el método que prefieras\n\n"
        "*¿Te interesa?* Pulsa el botón 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def model_photo1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠️ Envía una foto.")
        return MODEL_PHOTO1
    context.user_data["model_photo1"] = update.message.photo[-1].file_id
    await update.message.reply_text("*Paso 2/2:* Envía tu segunda foto con un papel que diga 'CitasMundial' 📝")
    return MODEL_PHOTO2


async def model_photo2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠️ Envía una foto.")
        return MODEL_PHOTO2
    photo2 = update.message.photo[-1].file_id
    photo1 = context.user_data["model_photo1"]
    user_id = update.effective_user.id
async def modelos_pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    pending = db.get_pending_models()
    if not pending:
        await update.message.reply_text("No hay solicitudes pendientes.")
        return
    for user_id, name, age, country, photo1, photo2 in pending:
        keyboard = [[
            InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar_{user_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_{user_id}")
        ]]
        await update.message.reply_photo(
            photo=photo1,
            caption=f"👤 *{name}*, {age}\n🌍 {country}\n🆔 `{user_id}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


if __name__ == "__main__":
    main()


