import random
from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=12
)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, secret_key: str, algorithm: str, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def get_random_coordinates() -> [float, float]:
    # Координаты города
    lower_corner = (83.533018, 53.186965)
    upper_corner = (83.907624, 53.481861)

    random_lon = lower_corner[0] + random.random() * (upper_corner[0] - lower_corner[0])
    random_lat = lower_corner[1] + random.random() * (upper_corner[1] - lower_corner[1])

    return [random_lat, random_lon]
