import logging
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, Zone
from .schemas import (
    UserCreate, UserOut, UserLogin, Token,
    ZoneCreate, ZoneUpdate, ZoneOut, PaginatedZones
)
from .auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, require_admin
)

# Настройка логирования сервера
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("medsecure_api")

app = FastAPI(
    title="MedSecure API",
    description="REST API системы комплексной безопасности клиники (Вариант №18)",
    version="1.0.0"
)

# Настройка CORS для взаимодействия с React SPA (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальный перехватчик и логирование ошибок 500
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Необработанная ошибка сервера: {exc} на пути {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера безопасности. Обратитесь к администратору."}
    )

# ==========================================
# 1. АУТЕНТИФИКАЦИЯ И ПРОФИЛЬ
# ==========================================

@app.post("/api/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, tags=["Auth"])
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового сотрудника клиники"""
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже зарегистрирован")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже зарегистрирован")

    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role or "doctor"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"Зарегистрирован новый пользователь: {new_user.username} (Роль: {new_user.role})")
    return new_user

@app.post("/api/auth/login", response_model=Token, tags=["Auth"])
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Вход сотрудника и получение JWT Bearer-токена"""
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    logger.info(f"Успешный вход в систему: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=UserOut, tags=["Auth"])
def get_me(current_user: User = Depends(get_current_user)):
    """Получение профиля текущего авторизованного пользователя"""
    return current_user

# ==========================================
# 2. CRUD-ОПЕРАЦИИ С ЗОНАМИ БЕЗОПАСНОСТИ
# ==========================================

@app.get("/api/zones", response_model=PaginatedZones, tags=["Zones"])
def get_zones(
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=50, description="Количество записей на страницу"),
    search: Optional[str] = Query(None, description="Поиск по названию или описанию"),
    status: Optional[str] = Query(None, description="Фильтрация по статусу"),
    min_clearance: Optional[int] = Query(None, ge=1, le=4, description="Минимальный уровень допуска"),
    db: Session = Depends(get_db)
):
    """Получение списка зон клиники с пагинацией и фильтрацией"""
    query = db.query(Zone)

    # Применение фильтров
    if search:
        query = query.filter(Zone.name.ilike(f"%{search}%") | Zone.description.ilike(f"%{search}%"))
    if status:
        query = query.filter(Zone.status == status)
    if min_clearance:
        query = query.filter(Zone.clearance_level >= min_clearance)

    total = query.count()
    items = query.order_by(Zone.id.asc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": items
    }

@app.get("/api/zones/{zone_id}", response_model=ZoneOut, tags=["Zones"])
def get_zone_by_id(zone_id: int, db: Session = Depends(get_db)):
    """Получение детальной информации о конкретной зоне"""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Зона безопасности #{zone_id} не найдена")
    return zone

@app.post("/api/zones", response_model=ZoneOut, status_code=status.HTTP_201_CREATED, tags=["Zones"])
def create_zone(
    zone_in: ZoneCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создание нового объекта безопасности (требуется авторизация)"""
    new_zone = Zone(
        name=zone_in.name,
        clearance_level=zone_in.clearance_level,
        status=zone_in.status,
        description=zone_in.description,
        created_by=current_user.id
    )
    db.add(new_zone)
    db.commit()
    db.refresh(new_zone)
    logger.info(f"Пользователь {current_user.username} создал зону #{new_zone.id}: {new_zone.name}")
    return new_zone

@app.put("/api/zones/{zone_id}", response_model=ZoneOut, tags=["Zones"])
def update_zone(
    zone_id: int,
    zone_update: ZoneUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновление параметров зоны (требуется авторизация)"""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Зона безопасности #{zone_id} не найдена")

    update_data = zone_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(zone, field, val)

    db.commit()
    db.refresh(zone)
    logger.info(f"Пользователь {current_user.username} обновил параметры зоны #{zone.id}")
    return zone

@app.delete("/api/zones/{zone_id}", status_code=status.HTTP_200_OK, tags=["Zones"])
def delete_zone(
    zone_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Удаление зоны безопасности (только администратор)"""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail=f"Зона безопасности #{zone_id} не найдена")

    db.delete(zone)
    db.commit()
    logger.warning(f"Администратор {current_user.username} удалил зону #{zone_id}")
    return {"message": f"Зона безопасности #{zone_id} успешно удалена"}