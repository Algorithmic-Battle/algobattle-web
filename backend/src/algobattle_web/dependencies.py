from collections.abc import Generator
from dataclasses import dataclass
from typing import Annotated, Literal, Self

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from algobattle_web.models import Team, Tournament, User
from algobattle_web.util import SessionLocal


def get_db() -> Generator[Session]:
    with SessionLocal() as db:
        try:
            yield db
        except:
            db.rollback()
            raise


type Database = Annotated[Session, Depends(get_db)]


def curr_user(
    db: Database, user_token: Annotated[str | None, Depends(APIKeyHeader(name="X-User-Token"))]
) -> User | None:
    return User.decode_token(db, user_token)


type CurrUser = Annotated[User | None, Depends(curr_user)]


@dataclass
class LoginInfo:
    user: User | None

    @property
    def team(self) -> Team | Literal["admin"] | None:
        return self.user.logged_in if self.user else None

    @property
    def tournament(self) -> Tournament | None:
        return self.user.tournament if self.user else None

    @classmethod
    def dependency(cls, user: CurrUser) -> Self:
        if user is not None:
            return cls(user)
        else:
            return cls(None)


LoggedIn = Annotated[LoginInfo, Depends(LoginInfo.dependency)]


def check_if_admin(user: CurrUser):
    if user is None or not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
