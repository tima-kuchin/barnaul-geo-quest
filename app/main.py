from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from app.database import engine
from app.models import Base
# Импорт маршрутизаторов (если они реализованы в пакете app/routers)
from app.routers import auth_routes, game_routes, profile_routes, main_routes
# Импорт обработчика ошибок
from app.routers.error_handlers import register_exception_handlers

app = FastAPI()

# Монтирование статических файлов и шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Создание таблиц в БД
Base.metadata.create_all(bind=engine)

# Подключение обработчика ошибок
register_exception_handlers(app)

# Подключение маршрутов
app.include_router(auth_routes.router)
app.include_router(game_routes.router)
app.include_router(profile_routes.router)
app.include_router(main_routes.router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)