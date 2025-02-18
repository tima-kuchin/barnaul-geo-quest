from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.dependencies import get_db
from app.models import GameAttempt, User
from app.auth import get_current_user
from app.game_logic import session

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/play", response_class=HTMLResponse)
async def get_map_coordinates(request: Request, user: User = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/login_required", status_code=302)
    coord = session.get_random_coordinates()
    if not coord:
        return HTMLResponse(content="Нет доступных координат", status_code=404)
    return templates.TemplateResponse("index.html", {"request": request, "coord": coord, "user": user})

@router.get("/next_location", response_class=JSONResponse)
async def get_next_coordinates(user: User = Depends(get_current_user)):
    if user is None:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    coord = session.get_random_coordinates()
    if not coord:
        return JSONResponse(content={"error": "Нет доступных координат"}, status_code=404)
    return JSONResponse(content={"coord": coord})

@router.post("/save_attempt", response_class=JSONResponse)
async def save_attempt(
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    total_distance: int = Form(...),
    total_points: int = Form(...),
    total_time: str = Form(...)
):
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
    except Exception:
        return JSONResponse(content={"error": "Failed to save game attempt"}, status_code=500)
