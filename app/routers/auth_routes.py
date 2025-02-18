from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import re
from datetime import timedelta

from app.dependencies import get_db
from app.models import User
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/register", response_class=HTMLResponse)
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "errors": {}, "username": "", "email": ""})

@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    db=Depends(get_db),
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    map_api_key: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    errors = {}
    if not re.match(r'^[a-zA-Z0-9]+$', username):
        errors['username'] = 'Имя пользователя может содержать только буквы и цифры'
    if len(password) < 8:
        errors['password'] = 'Пароль должен содержать минимум 8 символов'
    if password != confirm_password:
        errors['confirm_password'] = 'Пароли не совпадают'

    if errors:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "errors": errors,
                "username": username,
                "email": email,
                "full_name": full_name,
                "map_api_key": map_api_key
            }
        )

    user = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if user:
        errors = {"username": "Имя пользователя или электронная почта уже зарегистрированы"}
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "errors": errors,
                "username": username,
                "email": email,
                "full_name": full_name,
                "map_api_key": map_api_key
            }
        )

    hashed_password = get_password_hash(password)
    new_user = User(
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

@router.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "errors": {}, "username": ""})

@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    db=Depends(get_db),
    username: str = Form(...),
    password: str = Form(...)
):
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

@router.post("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login_required", status_code=302)
    response.delete_cookie("access_token")
    return response

@router.get("/login_required", response_class=HTMLResponse)
async def login_required(request: Request):
    return templates.TemplateResponse("login_required.html", {"request": request})