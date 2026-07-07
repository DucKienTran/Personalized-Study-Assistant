from sqlalchemy.orm import Session

from app.core.mysql import SessionLocal
from app.models.user_model import Permission, Role

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


def seed_roles(db: Session):
    print("Seeding roles...")

    for role_data in ROLES:
        role = db.query(Role).filter(Role.name == role_data["name"]).first()

        if role is None:
            db.add(Role(**role_data))
            print(f"  [+] {role_data['name']}")

    db.commit()


def seed_permissions(db: Session):
    print("Seeding permissions...")

    for permission_data in PERMISSIONS:
        permission = db.query(Permission).filter(Permission.code == permission_data["code"]).first()

        if permission is None:
            db.add(Permission(**permission_data))
            print(f"  [+] {permission_data['code']}")

    db.commit()


def seed_role_permissions(db: Session):
    print("Mapping permissions...")

    admin = db.query(Role).filter(Role.name == "admin").first()
    client = db.query(Role).filter(Role.name == "client").first()

    permissions = db.query(Permission).all()

    # Admin có toàn quyền
    for permission in permissions:
        if permission not in admin.permissions:
            admin.permissions.append(permission)

    # Client chỉ được thao tác document
    client_permission_codes = {
        "document:create",
        "document:read",
        "document:update",
        "document:delete",
    }

    for permission in permissions:
        if permission.code in client_permission_codes and permission not in client.permissions:
            client.permissions.append(permission)

    db.commit()


def main():
    db = SessionLocal()

    try:
        seed_roles(db)
        seed_permissions(db)
        seed_role_permissions(db)

        print("\nSeed completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
