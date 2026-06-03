"""Authentication helpers and routes (JWT with httpOnly cookies)."""
import os
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel, EmailStr
from bson import ObjectId
import uuid

JWT_ALGORITHM = "HS256"


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "access",
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 3600,
        path="/",
    )


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def build_auth_router(db):
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    async def get_current_user(request: Request) -> dict:
        token = request.cookies.get("access_token")
        if not token:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                token = auth[7:]
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user

    @router.post("/register")
    async def register(data: RegisterIn, response: Response):
        email = data.email.lower()
        if await db.users.find_one({"email": email}):
            raise HTTPException(status_code=400, detail="Email gia' registrata")
        user_id = str(uuid.uuid4())
        doc = {
            "id": user_id,
            "email": email,
            "name": data.name or email.split("@")[0],
            "password_hash": hash_password(data.password),
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(doc)
        token = create_access_token(user_id, email)
        set_auth_cookie(response, token)
        return {"id": user_id, "email": email, "name": doc["name"], "role": "user", "token": token}

    @router.post("/login")
    async def login(data: LoginIn, response: Response):
        email = data.email.lower()
        user = await db.users.find_one({"email": email})
        if not user or not verify_password(data.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Credenziali non valide")
        token = create_access_token(user["id"], email)
        set_auth_cookie(response, token)
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "role": user.get("role", "user"),
            "token": token,
        }

    @router.post("/logout")
    async def logout(response: Response):
        response.delete_cookie("access_token", path="/")
        return {"ok": True}

    @router.get("/me")
    async def me(user: dict = Depends(get_current_user)):
        return user

    return router, get_current_user


async def seed_admin(db):
    email = os.environ.get("ADMIN_EMAIL", "admin@dubita.it").lower()
    pw = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": email})
    if not existing:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": email,
            "name": "Admin",
            "password_hash": hash_password(pw),
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    elif not verify_password(pw, existing.get("password_hash", "")):
        await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(pw)}})
