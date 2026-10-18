import bcrypt
from .database import engine, Base, SessionLocal
from .models import User, Zone

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def init_database():
    print("Создание таблиц БД...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Проверяем, есть ли уже пользователи
        if not db.query(User).filter(User.username == "admin").first():
            print("Создание тестовых учетных записей...")
            admin_user = User(
                username="admin",
                email="admin@medsecure.local",
                hashed_password=hash_password("admin123"),
                role="admin"
            )
            doctor_user = User(
                username="dr_ivanov",
                email="ivanov@medsecure.local",
                hashed_password=hash_password("doctor123"),
                role="doctor"
            )
            db.add_all([admin_user, doctor_user])
            db.commit()
            db.refresh(admin_user)

            print("Создание начальных зон безопасности клиники...")
            initial_zones = [
                Zone(
                    name="Приемный покой и общий коридор",
                    clearance_level=1,
                    status="В норме",
                    description="Зона свободного перемещения пациентов и персонала.",
                    created_by=admin_user.id
                ),
                Zone(
                    name="Операционный блок №1",
                    clearance_level=3,
                    status="В норме",
                    description="Стерильная зона хирургического отделения.",
                    created_by=admin_user.id
                ),
                Zone(
                    name="Хранилище наркотических препаратов",
                    clearance_level=4,
                    status="Спецконтроль",
                    description="Особо охраняемое помещение. Доступ по правилу двух лиц.",
                    created_by=admin_user.id
                )
            ]
            db.add_all(initial_zones)
            db.commit()
            print("База данных успешно инициализирована!")
        else:
            print("База данных уже содержит начальные данные.")
    finally:
        db.close()

if __name__ == "__main__":
    init_database()