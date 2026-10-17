import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN
from database import (
    delete_promoted_admin,
    init_db,
    is_bot_promoted,
    save_promoted_admin,
)
from keyboards import (
    admin_actions,
    back_menu,
    confirm_action,
    main_menu,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
router = Router()


# ---------- Helpers ----------
async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        return m.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
    except Exception:
        return False


def get_target(message: Message, command: CommandObject):
    if message.reply_to_message:
        return message.reply_to_message.from_user.id
    if command.args:
        try:
            return int(command.args.split()[0])
        except ValueError:
            return None
    return None


# ---------- Commands ----------
@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type == ChatType.PRIVATE:
        await message.answer(
            "👋 <b>Welcome to Admin Manager Bot!</b>\n\n"
            "I manage your groups & channels with full power:\n\n"
            "• 🛡️ Promote / Demote admins\n"
            "• 🚫 Ban / Unban / Mute users\n"
            "• 🔄 Track promoted admins & auto-remove\n"
            "• ⚙️ Full group management UI\n\n"
            "➕ <b>Add me to your group</b> and make me <b>admin</b> with:\n"
            "• Add New Admins\n"
            "• Ban Users\n"
            "• Delete Messages\n\n"
            "Then open the panel with /panel.",
            reply_markup=main_menu(),
        )
    else:
        await message.answer(
            "🤖 <b>I'm online!</b>\nAdmins can use /panel here.",
            reply_markup=main_menu(),
        )


@router.message(Command("panel"))
async def cmd_panel(message: Message):
    if message.chat.type == ChatType.PRIVATE:
        await message.answer("⚠️ Use this command inside a group/channel.")
        return
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        await message.answer("🚫 Only admins can use this panel.")
        return
    await message.answer(
        f"🛡️ <b>Admin Control Panel</b>\n\n"
        f"📍 Chat: <b>{message.chat.title}</b>\n\n"
        f"Choose an option below:",
        reply_markup=main_menu(),
    )


# ---------- Callbacks ----------
@router.callback_query(F.data == "main_menu")
async def cb_main(call: CallbackQuery):
    await call.message.edit_text(
        f"🛡️ <b>Admin Control Panel</b>\n\n"
        f"📍 Chat: <b>{call.message.chat.title}</b>",
        reply_markup=main_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(call: CallbackQuery):
    if not await is_admin(call.bot, call.message.chat.id, call.from_user.id):
        await call.answer("🚫 Admins only!", show_alert=True)
        return

    admins = await call.bot.get_chat_administrators(call.message.chat.id)
    kb = InlineKeyboardBuilder()
    text = "🛡️ <b>Admins in this chat</b>\n\n"

    for adm in admins:
        if adm.user.is_bot:
            continue
        role = "👑 Owner" if adm.status == ChatMemberStatus.CREATOR else "🛡️ Admin"
        text += f"{role} — {adm.user.full_name}\n"
        kb.button(
            text=f"⚙️ {adm.user.full_name}",
            callback_data=f"admin_actions:{adm.user.id}",
        )

    kb.button(text="⬅️ Back", callback_data="main_menu")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("admin_actions:"))
async def cb_admin_actions(call: CallbackQuery):
    if not await is_admin(call.bot, call.message.chat.id, call.from_user.id):
        await call.answer("🚫 Admins only!", show_alert=True)
        return

    user_id = int(call.data.split(":")[1])
    try:
        m = await call.bot.get_chat_member(call.message.chat.id, user_id)
        name = m.user.full_name
        role = m.status
    except Exception:
        name, role = "Unknown", "unknown"

    tracked = await is_bot_promoted(call.message.chat.id, user_id)
    note = (
        "✅ <i>Promoted via this bot — auto-remove works</i>"
        if tracked
        else "⚠️ <i>Promoted by someone else — auto-remove may fail</i>"
    )

    await call.message.edit_text(
        f"👤 <b>{name}</b>\n"
        f"🆔 <code>{user_id}</code>\n"
        f"📌 Status: <b>{role}</b>\n\n{note}",
        reply_markup=admin_actions(user_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("remove_admin:"))
async def cb_remove_admin(call: CallbackQuery):
    if not await is_admin(call.bot, call.message.chat.id, call.from_user.id):
        await call.answer("🚫 Admins only!", show_alert=True)
        return
    user_id = int(call.data.split(":")[1])
    await call.message.edit_text(
        f"⚠️ <b>Confirm Removal</b>\n\n"
        f"Remove admin rights from <code>{user_id}</code>?",
        reply_markup=confirm_action("remove_admin", user_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("ban_user:"))
async def cb_ban_user(call: CallbackQuery):
    if not await is_admin(call.bot, call.message.chat.id, call.from_user.id):
        await call.answer("🚫 Admins only!", show_alert=True)
        return
    user_id = int(call.data.split(":")[1])
    await call.message.edit_text(
        f"⚠️ <b>Confirm Ban</b>\n\nBan <code>{user_id}</code>?",
        reply_markup=confirm_action("ban_user", user_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("confirm:"))
async def cb_confirm(call: CallbackQuery):
    _, action, user_id = call.data.split(":")
    user_id = int(user_id)
    chat_id = call.message.chat.id

    if not await is_admin(call.bot, chat_id, call.from_user.id):
        await call.answer("🚫 Admins only!", show_alert=True)
        return

    try:
        if action == "remove_admin":
            await call.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
            )
            await delete_promoted_admin(chat_id, user_id)
            await call.message.edit_text(
                f"✅ <b>Admin Removed</b>\n\n<code>{user_id}</code> is no longer an admin.",
                reply_markup=back_menu("admin_panel"),
            )
        elif action == "ban_user":
            await call.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await call.message.edit_text(
                f"🚫 <b>User Banned</b>\n\n<code>{user_id}</code> has been banned.",
                reply_markup=back_menu("admin_panel"),
            )
    except Exception as e:
        await call.message.edit_text(
            f"❌ <b>Failed</b>\n\n<code>{e}</code>",
            reply_markup=back_menu("admin_panel"),
        )
    await call.answer()


@router.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery):
    await call.message.edit_text(
        "❓ <b>Help</b>\n\n"
        "<b>Commands (admins):</b>\n"
        "/panel — open control panel\n"
        "/promote — reply + promote\n"
        "/demote — reply + demote\n"
        "/ban — reply + ban\n"
        "/unban — reply + unban\n"
        "/mute — reply + mute\n\n"
        "<b>Auto-remove:</b>\n"
        "When the bot promotes someone, it tracks them.\n"
        "If you remove them via the panel, they're auto-demoted.",
        reply_markup=back_menu("main_menu"),
    )
    await call.answer()


@router.callback_query(F.data == "ban_manager")
async def cb_ban_manager(call: CallbackQuery):
    await call.message.edit_text(
        "🚫 <b>Ban Manager</b>\n\n"
        "Use these commands by replying to a user:\n\n"
        "• /ban — Ban a user\n"
        "• /unban — Unban a user\n"
        "• /mute — Mute a user\n\n"
        "Or use the <b>Admin Panel → Ban User</b> button.",
        reply_markup=back_menu("main_menu"),
    )
    await call.answer()


@router.callback_query(F.data == "settings")
async def cb_settings(call: CallbackQuery):
    await call.message.edit_text(
        "⚙️ <b>Settings</b>\n\n"
        "Bot automatically tracks promotions.\n"
        "More settings coming soon!",
        reply_markup=back_menu("main_menu"),
    )
    await call.answer()


# ---------- Auto tracking ----------
@router.chat_member()
async def on_chat_member(event: ChatMemberUpdated):
    chat_id = event.chat.id
    user_id = event.new_chat_member.user.id

    was_admin = event.old_chat_member.status in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    )
    is_now_admin = event.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR

    if is_now_admin and not was_admin:
        await save_promoted_admin(chat_id, user_id, event.from_user.id)
    elif was_admin and not is_now_admin:
        await delete_promoted_admin(chat_id, user_id)


# ---------- Slash commands ----------
@router.message(Command("promote"))
async def cmd_promote(message: Message, command: CommandObject):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return
    target = get_target(message, command)
    if not target:
        await message.reply("ℹ️ Reply to a user or use <code>/promote USER_ID</code>")
        return
    try:
        await message.bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_change_info=False,
            can_promote_members=False,
        )
        await save_promoted_admin(message.chat.id, target, message.from_user.id)
        await message.reply(f"✅ Promoted <code>{target}</code> to admin.")
    except Exception as e:
        await message.reply(f"❌ {e}")


@router.message(Command("demote"))
async def cmd_demote(message: Message, command: CommandObject):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return
    target = get_target(message, command)
    if not target:
        await message.reply("ℹ️ Reply to a user or use <code>/demote USER_ID</code>")
        return
    try:
        await message.bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False,
        )
        await delete_promoted_admin(message.chat.id, target)
        await message.reply(f"✅ Demoted <code>{target}</code>.")
    except Exception as e:
        await message.reply(f"❌ {e}")


@router.message(Command("ban"))
async def cmd_ban(message: Message, command: CommandObject):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return
    target = get_target(message, command)
    if not target:
        await message.reply("ℹ️ Reply to a user or use <code>/ban USER_ID</code>")
        return
    try:
        await message.bot.ban_chat_member(message.chat.id, target)
        await message.reply(f"🚫 Banned <code>{target}</code>.")
    except Exception as e:
        await message.reply(f"❌ {e}")


@router.message(Command("unban"))
async def cmd_unban(message: Message, command: CommandObject):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return
    target = get_target(message, command)
    if not target:
        await message.reply("ℹ️ Reply to a user or use <code>/unban USER_ID</code>")
        return
    try:
        await message.bot.unban_chat_member(message.chat.id, target)
        await message.reply(f"✅ Unbanned <code>{target}</code>.")
    except Exception as e:
        await message.reply(f"❌ {e}")


@router.message(Command("mute"))
async def cmd_mute(message: Message, command: CommandObject):
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        return
    target = get_target(message, command)
    if not target:
        await message.reply("ℹ️ Reply to a user or use <code>/mute USER_ID</code>")
        return
    try:
        await message.bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target,
            permissions=ChatPermissions(can_send_messages=False),
        )
        await message.reply(f"🔇 Muted <code>{target}</code>.")
    except Exception as e:
        await message.reply(f"❌ {e}")


# ---------- Main ----------
async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    logging.info("🤖 Bot started on Railway. Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
