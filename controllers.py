import re
from datetime import timedelta

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import jwt, JWTError
from sqlalchemy.orm import sessionmaker

import entities
from utils import get_random_coordinates, get_password_hash, create_access_token, verify_password


def run_controllers(access_token_expire_minutes: int,
                    secret_key: str,
                    session_local: sessionmaker):
    app = FastAPI()
    algorithm = 'HS256'

    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")

    def get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    def get_current_user(request: Request, db: entities.Session = Depends(get_db)):
        token = request.cookies.get("access_token")
        if not token:
            return None
        try:
            payload = jwt.decode(token.split(" ")[1], secret_key, algorithms=[algorithm])
            username = payload.get("sub")
            if username is None:
                return None
            user = (
                db.query(entities.User)
                .filter(entities.User.username == username)
                .first()
            )
            return user
        except JWTError:
            return None

    @app.post("/register", response_class=HTMLResponse)
    async def register(request: Request, db: entities.Session = Depends(get_db),
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
                                              {"request": request, "errors": errors, "username": username,
                                               "email": email,
                                               "full_name": full_name, "map_api_key": map_api_key})

        user = (
            db.query(entities.User)
            .filter((entities.User.username == username) | (entities.User.email == email))
            .first()
        )
        if user:
            errors = {"username": "Имя пользователя или электронная почта уже зарегистрированы"}
            return templates.TemplateResponse("register.html",
                                              {"request": request, "errors": errors, "username": username,
                                               "email": email,
                                               "full_name": full_name, "map_api_key": map_api_key})

        hashed_password = get_password_hash(password)
        new_user = entities.User(
            username=username,
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            map_api_key=map_api_key
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return RedirectResponse(url="/login", status_code=302)

    @app.post("/login", response_class=HTMLResponse)
    async def login(request: Request, db: entities.Session = Depends(get_db),
                    username: str = Form(...), password: str = Form(...)):
        user = db.query(entities.User).filter(entities.User.username == username).first()
        if not user or not verify_password(password, user.password_hash):
            errors = {"username": "Неверное имя пользователя или пароль"}
            return templates.TemplateResponse("login.html",
                                              {"request": request, "errors": errors, "username": username})

        access_token_expires = timedelta(minutes=access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username},
            secret_key=secret_key,
            algorithm=algorithm,
            expires_delta=access_token_expires
        )
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
        return response

    @app.get("/settings", response_class=HTMLResponse)
    async def get_settings(request: Request, user: entities.User = Depends(get_current_user)):
        if user is None:
            return RedirectResponse(url="/login_required", status_code=302)
        return templates.TemplateResponse("settings.html", {"request": request, "user": user, "errors": {}})

    @app.post("/settings", response_class=HTMLResponse)
    async def update_settings(request: Request,
                              db: entities.Session = Depends(get_db),
                              user: entities.User = Depends(get_current_user),
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
    async def logout():
        response = RedirectResponse(url="/login_required", status_code=302)
        response.delete_cookie("access_token")
        return response

    @app.get("/register", response_class=HTMLResponse)
    async def get_register(request: Request):
        return templates.TemplateResponse("register.html",
                                          {"request": request, "errors": {}, "username": "", "email": ""})

    @app.get("/login", response_class=HTMLResponse)
    async def get_login(request: Request):
        return templates.TemplateResponse("login.html", {"request": request, "errors": {}, "username": ""})

    @app.get("/login_required", response_class=HTMLResponse)
    async def login_required(request: Request):
        return templates.TemplateResponse("login_required.html", {"request": request})

    @app.get("/", response_class=HTMLResponse)
    async def get_menu(request: Request, user: entities.User = Depends(get_current_user)):
        if user is None:
            return RedirectResponse(url="/login_required", status_code=302)
        return templates.TemplateResponse("menu.html", {"request": request, "user": user})

    @app.get("/play", response_class=HTMLResponse)
    async def get_map_coordinates(request: Request, user: entities.User = Depends(get_current_user)):
        if user is None:
            return RedirectResponse(url="/login_required", status_code=302)
        coord = get_random_coordinates()
        if not coord:
            return HTMLResponse(content="Нет доступных координат", status_code=404)
        return templates.TemplateResponse("index.html", {"request": request, "coord": coord, "user": user})

    @app.get("/next_location", response_class=JSONResponse)
    async def get_next_coordinates(user: entities.User = Depends(get_current_user)):
        if user is None:
            return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
        coord = get_random_coordinates()
        if not coord:
            return JSONResponse(content={"error": "Нет доступных координат"}, status_code=404)
        return JSONResponse(content={"coord": coord})

    @app.post("/save_attempt", response_class=JSONResponse)
    async def save_attempt(db: entities.Session = Depends(get_db),
                           user: entities.User = Depends(get_current_user),
                           total_distance: int = Form(...),
                           total_points: int = Form(...),
                           total_time: str = Form(...)):
        if user is None:
            return JSONResponse(content={"error": "Unauthorized"}, status_code=401)

        try:
            game_attempt = entities.GameAttempt(
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
    async def get_history(request: Request,
                          db: entities.Session = Depends(get_db),
                          user: entities.User = Depends(get_current_user)):
        if user is None:
            return RedirectResponse(url="/login_required", status_code=302)

        attempts = (db.query(entities.GameAttempt)
                    .filter(entities.GameAttempt.user_id == user.id)
                    .order_by(entities.GameAttempt.date.desc())
                    .all())
        total_attempts = len(attempts)

        return templates.TemplateResponse("history.html",
                                          {"request": request, "attempts": attempts, "total_attempts": total_attempts})

    return app
