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
    user = db.get_user(update.effective_user.id)
    if not user or not user[2]:
        await update.message.reply_text("Aún no tienes perfil. Usa /registro")
        return

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
    total = db.count_users()
    vips = db.count_vips()
    await update.message.reply_text(
        f"📊 *Estadísticas*\n\n"
        f"👥 Usuarios: {total}\n"
        f"💎 VIPs: {vips}",
        parse_mode="Markdown"
    )


# ---------- VIP ----------
async def vip_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 VIP 30 días (100 ⭐)", callback_data="vip_buy")]
    ]
    await update.message.reply_text(
        "💎 *CitasMundial VIP*\n\n"
        "Con VIP obtienes:\n\n"
        "✅ Likes *ilimitados*\n"
        "✅ Tu perfil se muestra en *todas las regiones*\n"
        "✅ Apareces primero en las búsquedas\n"
        "✅ Insignia VIP en tu perfil\n\n"
        "Precio: *100 Stars* / 30 días\n\n"
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
        prices=[LabeledPrice("VIP 30 días", 100)],
        start_parameter="vip-30d"
    )


async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
# ---------- BOTONES ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
# ---------- MANEJADOR DE TEXTO ----------
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
# ---------- MAIN ----------
def main():
    db.init_db()
    print("🤖 Iniciando CitasMundialBot...")

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
    app.add_handler(CommandHandler("ser_modelo", ser_modelo))
    app.add_handler(CommandHandler("modelos_pendientes", modelos_pendientes))

    app.add_handler(PreCheckoutQueryHandler(precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("✅ Bot corriendo. Ctrl+C para detener.")
    app.run_polling()


if __name__ == "__main__":
    main()


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
    await update.message.reply_text(
        "🌹 *Postúlate como Modelo*\n\nEnvía /cancelar si no quieres seguir.\n\n*Paso 1/2:* Envía tu primera foto con la mano en la cara 🤳",
        parse_mode="Markdown"
    )
    return MODEL_PHOTO1


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
