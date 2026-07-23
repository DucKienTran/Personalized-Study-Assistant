from sqlalchemy.orm import Session
from passlib.hash import bcrypt

from app.core.database import SessionLocal
from app.models.user_model import Permission, Role, User

ROLES = [
    {
        "name": "admin",
        "description": "Quản trị hệ thống",
    },
    {
        "name": "client",
        "description": "Người dùng hệ thống",
    },
]

PERMISSIONS = [
    {
        "code": "user:manage",
        "name": "Quản lý người dùng",
        "description": "Toàn quyền người dùng",
    },
    {
        "code": "document:create",
        "name": "Tạo tài liệu",
        "description": "",
    },
    {
        "code": "document:read",
        "name": "Đọc tài liệu",
        "description": "",
    },
    {
        "code": "document:update",
        "name": "Cập nhật tài liệu",
        "description": "",
    },
    {
        "code": "document:delete",
        "name": "Xóa tài liệu",
        "description": "",
    },
]

USERS = [
    {
        "username": "Admin_1",
        "email": "admin@gmail.com",
        "password": "Admin@1234",
        "full_name": "System Administrator",
        "role": "admin",
    },
    {
        "username": "Kien_Tran",
        "email": "tranduckien0110@gmail.com",
        "password": "Abcd@1234",
        "full_name": "Kien Tran",
        "role": "client",
    },
]


def seed_roles(db: Session):
    print("Seeding roles...")

    for role_data in ROLES:
        role = db.query(Role).filter_by(name=role_data["name"]).first()

        if role is None:
            db.add(Role(**role_data))
            print(f"  [+] Role: {role_data['name']}")


def seed_permissions(db: Session):
    print("Seeding permissions...")

    for permission_data in PERMISSIONS:
        permission = (
            db.query(Permission).filter_by(code=permission_data["code"]).first()
        )

        if permission is None:
            db.add(Permission(**permission_data))
            print(f"  [+] Permission: {permission_data['code']}")


def seed_role_permissions(db: Session):
    print("Mapping role permissions...")

    admin = db.query(Role).filter_by(name="admin").one()
    client = db.query(Role).filter_by(name="client").one()

    permissions = {p.code: p for p in db.query(Permission).all()}

    # Admin: tất cả quyền
    for permission in permissions.values():
        if permission not in admin.permissions:
            admin.permissions.append(permission)

    # Client
    client_permission_codes = {
        "document:create",
        "document:read",
        "document:update",
        "document:delete",
    }

    for code in client_permission_codes:
        permission = permissions[code]
        if permission not in client.permissions:
            client.permissions.append(permission)


def seed_users(db: Session):
    print("Seeding users...")

    roles = {role.name: role for role in db.query(Role).all()}

    for user_data in USERS:

        exists = db.query(User).filter(User.email == user_data["email"]).first()

        if exists:
            continue

        user = User(
            username=user_data["username"],
            email=user_data["email"],
            password_hash=bcrypt.hash(user_data["password"]),
            full_name=user_data["full_name"],
            role=roles[user_data["role"]],
            is_active=True,
        )

        db.add(user)

        print(f"  [+] User: {user.username}")


def main():
    db = SessionLocal()

    try:
        seed_roles(db)
        db.flush()

        seed_permissions(db)
        db.flush()

        seed_role_permissions(db)

        seed_users(db)

        db.commit()

        print("\n===================================")
        print("Seed completed successfully.")
        print("===================================")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
