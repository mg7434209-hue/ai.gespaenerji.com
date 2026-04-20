"""FastAPI auth dependency'leri."""
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.auth.security import decode_token


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Cookie veya Authorization header'dan token alıp user döndürür."""
    # Önce cookie'ye bak
    token = request.cookies.get("access_token")

    # Yoksa Authorization header
    if not token:
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum bulunamadı",
        )

    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz token",
        )

    user = db.query(User).filter(User.email == payload["sub"], User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı bulunamadı")

    return user
