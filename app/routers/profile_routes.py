from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_db
from app.models import User, GameAttempt
from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/settings", response_class=HTMLResponse)
async def get_settings(request: Request, db=Depends(get_db), user: User = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/login_required", status_code=302)
    return templates.TemplateResponse("settings.html", {"request": request, "user": user, "errors": {}})

@router.post("/settings", response_class=HTMLResponse)
async def update_settings(
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    full_name: str = Form(...),
    map_api_key: str = Form(...)
):
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

@router.get("/history", response_class=HTMLResponse)
async def get_history(request: Request, db=Depends(get_db), user: User = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/login_required", status_code=302)
    attempts = db.query(GameAttempt).filter(GameAttempt.user_id == user.id).order_by(GameAttempt.date.desc()).all()
    total_attempts = len(attempts)
    return templates.TemplateResponse("history.html", {"request": request, "attempts": attempts, "total_attempts": total_attempts})
