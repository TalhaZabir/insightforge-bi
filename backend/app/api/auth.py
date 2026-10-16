"""Auth routes: login (rate-limited), logout, me, admin user list."""

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.auth.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.entities import AuditLog, User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise _unauthorized()
    if not user.is_active:
        raise _unauthorized()
    db.add(AuditLog(user_id=user.id, action="login", entity="user", entity_id=user.id))
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role))


def _unauthorized():
    from fastapi import HTTPException, status

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
    )


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Stateless JWT: server records the event; client discards the token.
    db.add(AuditLog(user_id=user.id, action="logout", entity="user", entity_id=user.id))
    db.commit()
    return {"status": "logged_out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(_admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.email).all()
