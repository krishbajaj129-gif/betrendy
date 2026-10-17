"""
Database models for BeTrendy.
Includes User and Favourite models with secure password hashing and relationship mapping.
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def utc_now():
    """Helper to return current UTC datetime."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """
    User model representing registered users.
    Stores credentials securely using Werkzeug's modern password hashing.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # One-to-many relationship: One user can have many saved favourites
    favourites = db.relationship(
        'Favourite',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def set_password(self, password: str) -> None:
        """Hash plain text password with scrypt/pbkdf2 before saving to database."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify plain text password against stored secure hash."""
        return check_password_hash(self.password_hash, password)

    def is_favourite(self, item_name: str) -> bool:
        """Check whether the user has favourited an item (case-insensitive)."""
        return self.favourites.filter(
            db.func.lower(Favourite.item_name) == item_name.strip().lower()
        ).first() is not None

    def __repr__(self):
        return f"<User {self.username}>"


class Favourite(db.Model):
    """
    Favourite model representing saved fashion items.
    Tied to a specific user via a foreign key with a unique constraint.
    """
    __tablename__ = 'favourites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    item_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='general')  # men / women / custom
    created_at = db.Column(db.DateTime, default=utc_now)

    # Prevent duplicate saves of the same item for the same user
    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_name', name='uq_user_item'),
    )

    def to_dict(self):
        """Serialize model to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'item_name': self.item_name,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Favourite user={self.user_id} item='{self.item_name}'>"
