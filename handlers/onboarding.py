import logging
from handlers.menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)

# Re-export ONBOARDING_BALANCE for backwards compatibility
ONBOARDING_BALANCE = 3

def get_onboarding_conversation_handler():
    # Deprecated: Onboarding is now integrated into get_auth_conversation_handler()
    return None
