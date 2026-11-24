import base64
import binascii
import bz2
import codecs
import gzip
import json
import lzma
import os
import re
import shutil
import time
import zlib
import telebot
from telebot import types

BOT_TOKEN = "9067356036:AAGH7CmZlnpTJg8PtjqbqKzqqChRVRg9ZMI"
ADMIN_ID = 6623985668
CHANNEL_URL = "https://t.me/ZOM_946"
DEV_USERNAME = "@j1_si"
BOT_BRAND = "ريكسون"
RIGHTS_FOOTER = "تم التشفير من قبل بوت ريكسون"
RIGHTS_UPDATED_FOOTER = "تم التحديث الحقوق من قبل بوتريك"
OUTPUT_RIGHTS_BASE_NAME = "BOT__MVQ_RAXON"
ENC_PREFIX = b"RIXON_ENC_V1:"
VAR_XOR_KEY = 0x5A

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None, threaded=True, num_threads=4)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(BASE_DIR, "work_files")
SEEN_USERS_FILE = os.path.join(BASE_DIR, "seen_users.json")
os.makedirs(WORK_DIR, exist_ok=True)

user_states = {}
user_temp_files = {}
user_rights_data = {}


def load_seen_users():
    if os.path.exists(SEEN_USERS_FILE):
        try:
            with open(SEEN_USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(int(x) for x in data)
        except Exception:
            pass
    return set()


def save_seen_users(seen_set):
    try:
        with open(SEEN_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(seen_set)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


seen_users = load_seen_users()


def setup_bot_commands():
    try:
        bot.set_my_commands([
            types.BotCommand("start", "تشغيل البوت وعرض القائمة الرئيسية")
        ])
    except Exception:
        pass


def get_user_display_name(user):
    first = (user.first_name or "").strip()
    last = (user.last_name or "").strip()
    full_name = f"{first} {last}".strip()
    return full_name if full_name else "غير محدد"


def get_user_username(user):
    if user.username:
        return f"@{user.username}"
    return "لا يوجد يوزر"


def build_welcome_card(user):
    name = get_user_display_name(user)
    username = get_user_username(user)
    uid = user.id
    text = (
        f"⚡ أهلاً بك في بوت {BOT_BRAND} ⚡\n"
        "🛡️ هذا البوت خاص بريكسون لفك التشفير والتشفير ودمج الملفات وتغيير الحقوق 🛡️\n\n"
        "👤 معلومات الحساب:\n"
        f"• الاسم: {name}\n"
        f"• اليوزر: {username}\n"
        f"• الايدي: `{uid}`\n\n"
        "👇 اختر العملية المطلوبة من الأزرار بالأسفل:"
    )
    return text


def build_main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)

    btn_decrypt = types.InlineKeyboardButton("🔓 فك تشفير lua", callback_data="mode_decrypt")
    btn_encrypt = types.InlineKeyboardButton("🔐 تشفير ملف lua", callback_data="mode_encrypt")
    btn_merge = types.InlineKeyboardButton("🧩 دمج lua مع pak", callback_data="mode_merge")
    btn_rights = types.InlineKeyboardButton("✍️ تغيير حقوق", callback_data="mode_rights")

    btn_channel = types.InlineKeyboardButton("📢 قناة المطور", url=CHANNEL_URL)
    btn_dev = types.InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/j1_si")
    btn_start = types.InlineKeyboardButton("🔄 start", callback_data="do_start")

    markup.add(btn_decrypt, btn_encrypt)
    markup.add(btn_merge, btn_rights)
    markup.add(btn_channel, btn_dev)
    markup.add(btn_start)
    return markup


def notify_new_user_once(user):
    if not ADMIN_ID:
        return
    uid = int(user.id)
    if uid in seen_users:
        return

    seen_users.add(uid)
    save_seen_users(seen_users)

    name = get_user_display_name(user)
    username = get_user_username(user)
    msg = (
        f"🆕 مستخدم جديد دخل بوت {BOT_BRAND}!\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 الاسم: {name}\n"
        f"🔗 اليوزر: {username}\n"
        f"🆔 الايدي: `{uid}`\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
    except Exception:
        try:
            bot.send_message(ADMIN_ID, msg.replace("`", ""), parse_mode=None)
        except Exception:
            pass


def extract_scan_items(content):
    urls = sorted(set(re.findall(r"https?://[^\s\"'<>)\]]+", content)))
    usernames = sorted(set(re.findall(r"@[A-Za-z0-9_]{3,}", content)))
    arabic_chunks = re.findall(r"[\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)*", content)
    arabic_names = sorted(set(chunk.strip() for chunk in arabic_chunks if len(chunk.strip()) >= 2))
    return urls, usernames, arabic_names


def scan_lua_content(content):
    urls, usernames, arabic_names = extract_scan_items(content)

    lines = [
        f"📋 تقرير فحص الملف - بوت {BOT_BRAND}",
        "━━━━━━━━━━━━━━━━━━━━",
        "🌐 الروابط:",
    ]
    if urls:
        for u in urls:
            lines.append(f"• {u}")
    else:
        lines.append("• لا يوجد روابط")

    lines.append("")
    lines.append("📝 الأسماء العربية:")
    if arabic_names:
        for a in arabic_names[:50]:
            lines.append(f"• {a}")
        if len(arabic_names) > 50:
            lines.append(f"• والمزيد ({len(arabic_names) - 50} عنصر آخر)")
    else:
        lines.append("• لا يوجد أسماء عربية")

    lines.append("")
    lines.append("👤 اليوزرات:")
    if usernames:
        for un in usernames:
            lines.append(f"• {un}")
    else:
        lines.append("• لا يوجد يوزرات")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"✅ {RIGHTS_FOOTER}")
    return "\n".join(lines)


def looks_like_lua_or_text(data_bytes):
    if not data_bytes or len(data_bytes) < 2:
        return False
    try:
        sample = data_bytes[:200000]
        text = sample.decode("utf-8")
        printable = sum(1 for ch in text if ch.isprintable() or ch in "\r\n\t")
        if len(text) > 0 and (printable / len(text)) > 0.88:
            lua_markers = ["function", "local ", "end", "if ", "then", "return", "gg.", "print(", "require("]
            if any(m in text for m in lua_markers) or (printable / len(text)) > 0.96:
                return True
    except UnicodeDecodeError:
        pass
    return False


def encrypt_bytes_rixon(data_bytes):
    compressed = zlib.compress(data_bytes, level=9)
    xored = bytes(((b ^ ((VAR_XOR_KEY + i) & 0xFF)) for i, b in enumerate(compressed)))
    return ENC_PREFIX + base64.b64encode(xored)


def decrypt_rixon_payload(raw_bytes):
    if not raw_bytes.startswith(ENC_PREFIX):
        return False, None, ""
    try:
        b64_part = re.sub(rb"\s+", b"", raw_bytes[len(ENC_PREFIX):])
        xored = base64.b64decode(b64_part, validate=True)
        compressed = bytes(((b ^ ((VAR_XOR_KEY + i) & 0xFF)) for i, b in enumerate(xored)))
        original = zlib.decompress(compressed)
        return True, original, "فك تشفير ريكسون (RIXON_ENC_V1)"
    except Exception as e:
        return False, None, f"فشل فك تشفير ريكسون: {e}"


def try_decrypt_lua_bytes(raw_bytes):
    # 1. RIXON_ENC_V1
    if raw_bytes.startswith(ENC_PREFIX):
        ok, data, method = decrypt_rixon_payload(raw_bytes)
        if ok and data is not None:
            return True, data, method

    # 2. نص/Lua واضح مباشرة
    if looks_like_lua_or_text(raw_bytes):
        return True, raw_bytes, "نص/Lua مباشر"

    # 3. zlib
    for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS, 16 + zlib.MAX_WBITS):
        try:
            out = zlib.decompress(raw_bytes, wbits)
            if looks_like_lua_or_text(out):
                return True, out, f"zlib ({wbits})"
        except Exception:
            pass

    # 4. gzip / bz2 / lzma
    for dec_func, d_name in ((gzip.decompress, "gzip"), (bz2.decompress, "bz2"), (lzma.decompress, "lzma")):
        try:
            out = dec_func(raw_bytes)
            if looks_like_lua_or_text(out):
                return True, out, d_name
        except Exception:
            pass

    # 5. Base64 قياسي + URL-safe + مزدوج + مع zlib
    for b64_func, b64_name in ((base64.b64decode, "Base64"), (base64.urlsafe_b64decode, "URL-Base64")):
        try:
            stripped = re.sub(rb"\s+", b"", raw_bytes)
            if len(stripped) >= 4:
                padded = stripped + (b"=" * ((-len(stripped)) % 4))
                dec = b64_func(padded)
                if looks_like_lua_or_text(dec):
                    return True, dec, b64_name
                try:
                    dec2 = b64_func(re.sub(rb"\s+", b"", dec))
                    if looks_like_lua_or_text(dec2):
                        return True, dec2, f"Double {b64_name}"
                except Exception:
                    pass
                for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
                    try:
                        dz = zlib.decompress(dec, wbits)
                        if looks_like_lua_or_text(dz):
                            return True, dz, f"{b64_name} + zlib"
                    except Exception:
                        pass
        except Exception:
            pass

    # 6. Base32
    try:
        b32_clean = re.sub(rb"\s+", b"", raw_bytes).upper()
        if len(b32_clean) >= 8:
            b32_dec = base64.b32decode(b32_clean + (b"=" * ((-len(b32_clean)) % 8)))
            if looks_like_lua_or_text(b32_dec):
                return True, b32_dec, "Base32"
    except Exception:
        pass

    # 7. Base85 / ASCII85
    for a85_func, a85_name in ((base64.a85decode, "ASCII85"), (base64.b85decode, "Base85")):
        try:
            a85_dec = a85_func(raw_bytes)
            if looks_like_lua_or_text(a85_dec):
                return True, a85_dec, a85_name
        except Exception:
            pass

    # 8. Hex
    try:
        hex_clean = re.sub(rb"[^0-9a-fA-F]", b"", raw_bytes)
        if len(hex_clean) >= 6 and len(hex_clean) % 2 == 0:
            hex_dec = binascii.unhexlify(hex_clean)
            if looks_like_lua_or_text(hex_dec):
                return True, hex_dec, "Hex"
    except Exception:
        pass

    # 9. XOR بمفاتيح ثابتة ومتغيرة + Byte Shift + ROT13 (للملفات المتوسطة والصغيرة لتجنب بطء الملفات الضخمة)
    if len(raw_bytes) <= 2 * 1024 * 1024:
        xor_keys = [
            0x01, 0x05, 0x07, 0x0D, 0x10, 0x13, 0x17, 0x1A, 0x20, 0x2A, 0x33, 0x37,
            0x42, 0x55, 0x5A, 0x66, 0x77, 0x80, 0x88, 0x99, 0xAA, 0xBB, 0xCC, 0xFF
        ]
        for k in xor_keys:
            x_dec = bytes(b ^ k for b in raw_bytes)
            if looks_like_lua_or_text(x_dec):
                return True, x_dec, f"XOR (0x{k:02X})"

        for start_k in (0x10, 0x20, 0x37, 0x5A, 0x7F, 0xAA):
            r_dec = bytes(((b ^ ((start_k + idx) & 0xFF)) for idx, b in enumerate(raw_bytes)))
            if looks_like_lua_or_text(r_dec):
                return True, r_dec, f"Rolling XOR (0x{start_k:02X})"

        for shift in range(1, 25):
            s_plus = bytes(((b + shift) & 0xFF) for b in raw_bytes)
            if looks_like_lua_or_text(s_plus):
                return True, s_plus, f"Byte Shift (+{shift})"
            s_minus = bytes(((b - shift) & 0xFF) for b in raw_bytes)
            if looks_like_lua_or_text(s_minus):
                return True, s_minus, f"Byte Shift (-{shift})"

    try:
        as_str = raw_bytes.decode("utf-8")
        rot = codecs.encode(as_str, "rot_13").encode("utf-8")
        if looks_like_lua_or_text(rot) and rot != raw_bytes:
            return True, rot, "ROT13"
    except Exception:
        pass

    return False, None, "غير معروف"


def process_decrypt(input_path, original_name, user_id):
    base_no_ext = os.path.splitext(original_name)[0]
    user_out_dir = os.path.join(WORK_DIR, f"dec_out_{user_id}")
    os.makedirs(user_out_dir, exist_ok=True)
    out_lua = os.path.join(user_out_dir, f"{base_no_ext}.lua")

    try:
        with open(input_path, "rb") as f:
            raw_bytes = f.read()

        ok, dec_bytes, method = try_decrypt_lua_bytes(raw_bytes)
        if not ok or dec_bytes is None:
            return False, None, f"⚠️ تعذر فك تشفير ملف lua بالخوارزميات المتاحة.\n✅ {RIGHTS_FOOTER}"

        with open(out_lua, "wb") as out:
            out.write(dec_bytes)

        return True, out_lua, f"🔓 تم فك تشفير ملف lua بنجاح ({method}).\n✅ {RIGHTS_FOOTER}"
    except Exception as e:
        return False, None, f"❌ حدث خطأ أثناء فك التشفير: {e}"


def process_encrypt(input_path, original_name, user_id):
    base_no_ext = os.path.splitext(original_name)[0]
    out_path = os.path.join(WORK_DIR, f"encrypted_{user_id}_{base_no_ext}.lua")
    try:
        with open(input_path, "rb") as f:
            data = f.read()

        encoded = encrypt_bytes_rixon(data)
        with open(out_path, "wb") as out:
            out.write(encoded)

        return True, out_path, f"🔐 تم تشفير ملف lua بنجاح.\n✅ {RIGHTS_FOOTER}"
    except Exception as e:
        return False, None, f"❌ تعذر تشفير الملف: {e}"


def clean_old_merged_lua(pak_bytes):
    return re.sub(
        rb"\n?--RIXON_LUA_PACK_START--.*?--RIXON_LUA_PACK_END--\n?",
        b"",
        pak_bytes,
        flags=re.DOTALL,
    )


def process_merge_lua_pak(lua_path, pak_path, pak_original_name, user_id):
    user_out_dir = os.path.join(WORK_DIR, f"out_{user_id}")
    os.makedirs(user_out_dir, exist_ok=True)
    safe_pak_name = os.path.basename(pak_original_name)
    if not safe_pak_name.lower().endswith(".pak"):
        safe_pak_name = f"{safe_pak_name}.pak"

    out_pak = os.path.join(user_out_dir, safe_pak_name)
    try:
        if not os.path.exists(pak_path) or os.path.getsize(pak_path) == 0:
            return False, None, "❌ ملف pak فارغ أو غير صالح."

        with open(pak_path, "rb") as pf:
            pak_raw = pf.read()

        pak_cleaned = clean_old_merged_lua(pak_raw)

        with open(lua_path, "rb") as lf:
            lua_raw = lf.read()

        encrypted_lua_bytes = encrypt_bytes_rixon(lua_raw)

        merged_bytes = (
            pak_cleaned
            + b"\n--RIXON_LUA_PACK_START--\n"
            + encrypted_lua_bytes
            + b"\n--RIXON_LUA_PACK_END--\n"
        )

        with open(out_pak, "wb") as out:
            out.write(merged_bytes)

        return True, out_pak, f"🧩 تم تشفير ملف lua ودمجه داخل {safe_pak_name} بنفس الاسم بنجاح.\n✅ {RIGHTS_FOOTER}"
    except Exception as e:
        return False, None, f"❌ تعذر دمج الملفات: {e}"


def build_pre_rights_cliche(file_name, content):
    urls, usernames, _ = extract_scan_items(content)
    urls_text = "\n".join(f"  • {u}" for u in urls) if urls else "  • لا يوجد روابط حالياً"
    users_text = "\n".join(f"  • {un}" for un in usernames) if usernames else "  • لا يوجد يوزرات حالياً"

    return (
        f"📋 كليشة بيانات الملف قبل تغيير الحقوق - بوت {BOT_BRAND}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 اسم الملف: {file_name}\n"
        f"🌐 الروابط الموجودة:\n{urls_text}\n"
        f"👤 اليوزرات الموجودة:\n{users_text}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📢 أرسل الآن لينك قناتك:"
    )


def build_final_rights_cliche(out_file_name, channel_link, username_val):
    return (
        f"✍️ كليشة تغيير الحقوق - بوت {BOT_BRAND}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 اسم الملف: {out_file_name}\n"
        f"📢 لينك القناة الجديد: {channel_link}\n"
        f"👤 اليوزر الجديد: {username_val}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ {RIGHTS_UPDATED_FOOTER}"
    )


def fit_replacement_to_length(replacement_str, target_byte_len):
    rep_bytes = replacement_str.encode("utf-8", errors="ignore")
    if len(rep_bytes) == target_byte_len:
        return replacement_str
    if len(rep_bytes) < target_byte_len:
        return replacement_str + (" " * (target_byte_len - len(rep_bytes)))
    trimmed = rep_bytes[:target_byte_len]
    while trimmed:
        try:
            return trimmed.decode("utf-8")
        except UnicodeDecodeError:
            trimmed = trimmed[:-1]
    return ""


def process_change_rights(input_path, original_name, channel_link, username_val, user_id):
    ext = os.path.splitext(original_name)[1] or ".lua"
    out_file_name = f"{OUTPUT_RIGHTS_BASE_NAME}{ext}"
    user_out_dir = os.path.join(WORK_DIR, f"rights_out_{user_id}")
    os.makedirs(user_out_dir, exist_ok=True)
    out_path = os.path.join(user_out_dir, out_file_name)

    try:
        with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        clean_username = username_val if username_val.startswith("@") else f"@{username_val.lstrip('@')}"
        if not username_val.strip():
            clean_username = "غير محدد"

        def replace_url_match(match):
            matched_str = match.group(0)
            target_len = len(matched_str.encode("utf-8", errors="ignore"))
            return fit_replacement_to_length(channel_link, target_len)

        def replace_user_match(match):
            matched_str = match.group(0)
            if clean_username == "غير محدد":
                return matched_str
            target_len = len(matched_str.encode("utf-8", errors="ignore"))
            return fit_replacement_to_length(clean_username, target_len)

        updated_content = re.sub(r"https?://[^\s\"'<>)\]]+", replace_url_match, content)
        if clean_username != "غير محدد":
            updated_content = re.sub(r"@[A-Za-z0-9_]{3,}", replace_user_match, updated_content)

        orig_len = len(content.encode("utf-8", errors="ignore"))
        curr_len = len(updated_content.encode("utf-8", errors="ignore"))
        if curr_len < orig_len:
            updated_content += " " * (orig_len - curr_len)
        elif curr_len > orig_len:
            diff = curr_len - orig_len
            trailing_spaces = len(updated_content) - len(updated_content.rstrip(" "))
            if trailing_spaces > 0:
                rem = min(diff, trailing_spaces)
                updated_content = updated_content[:-rem]

        with open(out_path, "w", encoding="utf-8") as out:
            out.write(updated_content)

        cliche_text = build_final_rights_cliche(out_file_name, channel_link, clean_username)
        return True, out_path, cliche_text
    except Exception as e:
        return False, None, f"❌ تعذر تغيير الحقوق: {e}"


def send_start_menu(chat_id, user):
    user_states[user.id] = None
    user_temp_files[user.id] = {}
    user_rights_data[user.id] = {}

    notify_new_user_once(user)

    card_text = build_welcome_card(user)
    markup = build_main_keyboard()

    try:
        bot.send_message(chat_id, card_text, reply_markup=markup, parse_mode="Markdown")
    except Exception:
        bot.send_message(chat_id, card_text.replace("`", ""), reply_markup=markup, parse_mode=None)


@bot.message_handler(commands=["start"])
def handle_start(message):
    try:
        send_start_menu(message.chat.id, message.from_user)
    except Exception as e:
        print(f"[START_ERR] {e}")


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        user = call.from_user
        uid = user.id
        chat_id = call.message.chat.id if call.message else uid
        data = (call.data or "").strip()

        notify_new_user_once(user)

        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass

        if data == "do_start":
            send_start_menu(chat_id, user)

        elif data == "mode_decrypt":
            user_states[uid] = "waiting_decrypt_file"
            user_temp_files[uid] = {}
            bot.send_message(chat_id, "أرسل ملف lua المراد فك تشفيره\n🔓⚡")

        elif data == "mode_encrypt":
            user_states[uid] = "waiting_encrypt_file"
            user_temp_files[uid] = {}
            bot.send_message(chat_id, "أرسل ملف lua المراد تشفيره\n🔐⚡")

        elif data == "mode_merge":
            user_states[uid] = "waiting_merge_lua"
            user_temp_files[uid] = {}
            bot.send_message(chat_id, "أرسل ملف lua أولاً\n🧩⚡")

        elif data == "mode_rights":
            user_states[uid] = "waiting_rights_file"
            user_temp_files[uid] = {}
            user_rights_data[uid] = {}
            bot.send_message(chat_id, "أرسل ملف lua المراد تغيير حقوقه\n✍️⚡")
    except Exception as e:
        print(f"[CALLBACK_ERR] {e}")


@bot.message_handler(content_types=["document"])
def handle_document(message):
    user = message.from_user
    uid = user.id
    chat_id = message.chat.id

    try:
        notify_new_user_once(user)
        doc = message.document
        file_name = doc.file_name or "file.lua"
        ext = os.path.splitext(file_name)[1].lower()
        saved_path = os.path.join(WORK_DIR, f"{uid}_{file_name}")

        bot.send_message(chat_id, "⏳ جاري استلام ومعالجة الملف...")

        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(saved_path, "wb") as f:
            f.write(downloaded)

        state = user_states.get(uid)

        if state == "waiting_decrypt_file":
            ok, out_lua, msg = process_decrypt(saved_path, file_name, uid)
            user_states[uid] = None
            if ok and out_lua and os.path.exists(out_lua):
                with open(out_lua, "rb") as lf:
                    bot.send_document(chat_id, lf, caption=msg)
            else:
                bot.send_message(chat_id, msg)
            return

        if state == "waiting_encrypt_file":
            ok, out_path, msg = process_encrypt(saved_path, file_name, uid)
            user_states[uid] = None
            if ok and out_path:
                with open(out_path, "rb") as ef:
                    bot.send_document(chat_id, ef, caption=msg)
            else:
                bot.send_message(chat_id, msg)
            return

        if state == "waiting_merge_lua":
            user_temp_files.setdefault(uid, {})["lua_path"] = saved_path
            user_temp_files[uid]["lua_name"] = file_name
            user_states[uid] = "waiting_merge_pak"
            bot.send_message(chat_id, "أرسل ملف pak الآن\n🧩⚡")
            return

        if state == "waiting_merge_pak":
            lua_path = user_temp_files.get(uid, {}).get("lua_path")
            if not lua_path or not os.path.exists(lua_path):
                user_states[uid] = "waiting_merge_lua"
                bot.send_message(chat_id, "أرسل ملف lua أولاً\n🧩⚡")
                return
            ok, out_pak, msg = process_merge_lua_pak(lua_path, saved_path, file_name, uid)
            user_states[uid] = None
            user_temp_files[uid] = {}
            if ok and out_pak:
                with open(out_pak, "rb") as mf:
                    bot.send_document(chat_id, mf, caption=msg)
            else:
                bot.send_message(chat_id, msg)
            return

        if state == "waiting_rights_file":
            user_temp_files.setdefault(uid, {})["rights_path"] = saved_path
            user_temp_files[uid]["rights_name"] = file_name
            user_rights_data[uid] = {}
            user_states[uid] = "waiting_rights_channel"

            try:
                with open(saved_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                content = ""

            pre_cliche = build_pre_rights_cliche(file_name, content)
            bot.send_message(chat_id, pre_cliche)
            return

        if ext == ".lua" or file_name.lower().endswith(".lua"):
            with open(saved_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            result_text = scan_lua_content(content)
            bot.send_message(chat_id, result_text)
        else:
            bot.send_message(chat_id, "👇 اختر العملية المطلوبة من قائمة start:")

    except Exception as e:
        print(f"[DOC_ERR] {e}")
        try:
            bot.send_message(chat_id, f"❌ حدث خطأ أثناء معالجة الملف: {e}")
        except Exception:
            pass


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user = message.from_user
    uid = user.id
    chat_id = message.chat.id

    try:
        notify_new_user_once(user)
        text = (message.text or "").strip()
        state = user_states.get(uid)

        if state == "waiting_rights_channel":
            user_rights_data.setdefault(uid, {})["channel"] = text
            user_states[uid] = "waiting_rights_username"
            bot.send_message(chat_id, "👤 أرسل الآن اليوزر:")
            return

        if state == "waiting_rights_username":
            r_data = user_rights_data.get(uid, {})
            channel_link = r_data.get("channel", CHANNEL_URL)
            username_val = text

            target_file = user_temp_files.get(uid, {}).get("rights_path")
            target_name = user_temp_files.get(uid, {}).get("rights_name", "script.lua")

            user_states[uid] = None
            user_temp_files[uid] = {}
            user_rights_data[uid] = {}

            if target_file and os.path.exists(target_file):
                ok, out_path, cliche_or_err = process_change_rights(
                    target_file, target_name, channel_link, username_val, uid
                )
                if ok and out_path:
                    bot.send_message(chat_id, cliche_or_err)
                    with open(out_path, "rb") as rf:
                        bot.send_document(
                            chat_id,
                            rf,
                            caption=f"✅ {RIGHTS_UPDATED_FOOTER}"
                        )
                else:
                    bot.send_message(chat_id, cliche_or_err)
            else:
                bot.send_message(chat_id, "⚠️ الملف غير موجود، ابدأ من زر تغيير الحقوق مرة أخرى.")
            return

        bot.send_message(chat_id, "👇 استخدم زر start لعرض القائمة الرئيسية.")
    except Exception as e:
        print(f"[TEXT_ERR] {e}")


if __name__ == "__main__":
    setup_bot_commands()
    print(f"{BOT_BRAND} bot is running...")
    while True:
        try:
            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=20,
                allowed_updates=["message", "callback_query"]
            )
        except Exception as e:
            print(f"[POLLING_ERR] {e}")
            time.sleep(2)

