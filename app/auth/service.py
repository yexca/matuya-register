from werkzeug.security import check_password_hash, generate_password_hash

from .repository import UserRepository


class AuthService:
    def __init__(self, db):
        self.repo = UserRepository(db)

    def ensure_initial_admin(self, username, password):
        password_hash = generate_password_hash(password, method="pbkdf2:sha256")
        return self.repo.create_or_update(username, password_hash)

    def login(self, username, password):
        user = self.repo.get_by_username(username)
        if user is None:
            return None
        if not check_password_hash(user.password_hash, password):
            return None
        return user

    def get_current_user(self, user_id):
        if user_id is None:
            return None
        return self.repo.get_by_id(user_id)
