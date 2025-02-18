import re

def validate_username(username: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9]+$', username))

# Здесь можно добавить другие утилиты по необходимости.
