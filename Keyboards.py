from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛡️ Admin Panel", callback_data="admin_panel")
    kb.button(text="🚫 Ban Manager", callback_data="ban_manager")
    kb.button(text="⚙️ Settings", callback_data="settings")
    kb.button(text="❓ Help", callback_data="help")
    kb.adjust(2, 2)
    return kb.as_markup()


def back_menu(target="main_menu"):
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Back", callback_data=target)
    return kb.as_markup()


def admin_actions(user_id):
    kb = InlineKeyboardBuilder()
    kb.button(text="➖ Remove Admin", callback_data=f"remove_admin:{user_id}")
    kb.button(text="🚫 Ban User", callback_data=f"ban_user:{user_id}")
    kb.button(text="⬅️ Back", callback_data="admin_panel")
    kb.adjust(1, 1, 1)
    return kb.as_markup()


def confirm_action(action, user_id, target="admin_panel"):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Yes", callback_data=f"confirm:{action}:{user_id}")
    kb.button(text="❌ No", callback_data=target)
    kb.adjust(2)
    return kb.as_markup()
