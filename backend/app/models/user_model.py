from sqlalchemy import TIMESTAMP, Boolean, Column, ForeignKey, String, Table
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.mysql import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    role_id = Column(
        BIGINT(unsigned=True), ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )

    full_name = Column(String(150), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    role = relationship("Role", back_populates="users")
    documents = relationship("Document", back_populates="user")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else None


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        BIGINT(unsigned=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        BIGINT(unsigned=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    code = Column(String(100), unique=True, index=True, nullable=False)  # e.g. "document:create"
    description = Column(String(255), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Quan hệ n-n với Roles
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")


class Role(Base):
    __tablename__ = "roles"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), unique=True, index=True, nullable=False)  # e.g. "admin", "client"
    description = Column(String(255), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        BIGINT(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    jti = Column(String(128), unique=True, index=True, nullable=False)  # Token ID (JWT ID)
    revoked = Column(TINYINT(1), default=0, nullable=False)

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    expired_at = Column(TIMESTAMP, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")
