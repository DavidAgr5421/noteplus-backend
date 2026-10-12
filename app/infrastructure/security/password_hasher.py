import bcrypt


class BcryptPasswordHasher:
    def hash(self, plain: str) -> str:
        # bcrypt cost 12
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:
            return False
