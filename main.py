import os
import random
import json
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__default_rounds=12
)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Загрузка координат из JSON файла
if os.path.exists('valid_coordinates.json'):
    with open('valid_coordinates.json', 'r') as f:
        coordinates = json.load(f)
else:
    coordinates = []


class GameSession:
    def __init__(self):
        self.used_coordinates = []

    def get_random_coordinates(self):
        available_coords = [coord for coord in coordinates if coord not in self.used_coordinates]
        if not available_coords:
            self.used_coordinates = []
            available_coords = coordinates.copy()
        coord = random.choice(available_coords)
        self.used_coordinates.append(coord)
        return coord


session = GameSession()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    full_name = Column(String)
    map_api_key = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    session_token = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)


class GameAttempt(Base):
    __tablename__ = "game_attempts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    date = Column(DateTime, default=datetime.utcnow)
    total_distance = Column(Integer)
    total_points = Column(Integer)
    total_time = Column(String)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None


@app.post("/register", response_class=HTMLResponse)
async def register(request: Request, db: Session = Depends(get_db),
                   username: str = Form(...), email: str = Form(...),
                   full_name: str = Form(...), map_api_key: str = Form(...),
                   password: str = Form(...), confirm_password: str = Form(...)):
    errors = {}
    if not re.match(r'^[a-zA-Z0-9]+$', username):
        errors['username'] = 'Имя пользователя может содержать только буквы и цифры'
    if len(password) < 8:
        errors['password'] = 'Пароль должен содержать минимум 8 символов'
    if password != confirm_password:
        errors['confirm_password'] = 'Пароли не совпадают'

    if errors:
        return templates.TemplateResponse("register.html",
                                          {"request": request, "errors": errors, "username": username, "email": email,
                                           "full_name": full_name, "map_api_key": map_api_key})

    user = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if user:
        errors = {"username": "Имя пользователя или электронная почта уже зарегистрированы"}
        return templates.TemplateResponse("register.html",
                                          {"request": request, "errors": errors, "username": username, "email": email,
                                           "full_name": full_name, "map_api_key": map_api_key})

    hashed_password = get_password_hash(password)
    new_user = User(username=username, email=email, password_hash=hashed_password, full_name=full_name,
                    map_api_key=map_api_key)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return RedirectResponse(url="/login", status_code=302)


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, db: Session = Depends(get_db),
                username: str = Form(...), password: str = Form(...)):
    errors = {}
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        errors = {"username": "Неверное имя пользователя или пароль"}
        return templates.TemplateResponse("login.html", {"request": request, "errors": errors, "username": username})

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response


@app.get("/settings", response_class=HTMLResponse)
async def get_settings(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/login_required", status_code=302)
    return templates.TemplateResponse("settings.html", {"request": request, "user": user, "errors": {}})


@app.post("/settings", response_class=HTMLResponse)
async def update_settings(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user),
                          full_name: str = Form(...), map_api_key: str = Form(...)):
    if user is None:
        return RedirectResponse(url="/login_required", status_code=302)

    errors = {}
    if not full_name:
        errors['full_name'] = 'Полное имя обязательно'
    if not map_api_key:
        errors['map_api_key'] = 'API ключ Яндекс карт обязателен'

    if errors:
        return templates.TemplateResponse("settings.html", {"request": request, "user": user, "errors": errors})

    user.full_name = full_name
    user.map_api_key = map_api_key
    db.commit()
    return RedirectResponse(url="/", status_code=302)

@app.post("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login_required", status_code=302)
    response.delete_cookie("access_token")
    return response


@app.get("/register", response_class=HTMLResponse)
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "errors": {}, "username": "", "email": ""})


@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "errors": {}, "username": ""})


@app.get("/login_required", response_class=HTMLResponse)
async def login_required(request: Request):
    return templates.TemplateResponse("login_required.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
async def get_menu(request: Request, user: User = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/login_required", status_code=302)
    return templates.TemplateResponse("menu.html", {"request": request, "user": user})


@app.get("/play", response_class=HTMLResponse)
async def get_map_coordinates(request: Request, user: User = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/login_required", status_code=302)
    coord = session.get_random_coordinates()
    if not coord:
        return HTMLResponse(content="Нет доступных координат", status_code=404)
    return templates.TemplateResponse("index.html", {"request": request, "coord": coord, "user": user})


@app.get("/next_location", response_class=JSONResponse)
async def get_next_coordinates(user: User = Depends(get_current_user)):
    if user is None:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    coord = session.get_random_coordinates()
    if not coord:
        return JSONResponse(content={"error": "Нет доступных координат"}, status_code=404)
    return JSONResponse(content={"coord": coord})


@app.post("/save_attempt", response_class=JSONResponse)
async def save_attempt(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user),
                       total_distance: int = Form(...), total_points: int = Form(...), total_time: str = Form(...)):
    if user is None:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)

    try:
        game_attempt = GameAttempt(
            user_id=user.id,
            total_distance=total_distance,
            total_points=total_points,
            total_time=total_time
        )
        db.add(game_attempt)
        db.commit()
        return JSONResponse(content={"message": "Game attempt saved successfully"})
    except Exception as e:
        return JSONResponse(content={"error": "Failed to save game attempt"}, status_code=500)


@app.get("/history", response_class=HTMLResponse)
async def get_history(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/login_required", status_code=302)

    attempts = db.query(GameAttempt).filter(GameAttempt.user_id == user.id).order_by(GameAttempt.date.desc()).all()
    total_attempts = len(attempts)

    return templates.TemplateResponse("history.html",
                                      {"request": request, "attempts": attempts, "total_attempts": total_attempts})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)