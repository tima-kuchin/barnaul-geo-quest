from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models import User
from app.auth import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def get_menu(request: Request, user: User = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/login_required", status_code=302)
    return templates.TemplateResponse("menu.html", {"request": request, "user": user})
