
from datetime import datetime, timedelta, timezone

import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from starlette.config import Config as StarletteConfig

from app.api.dependencies import get_db
from app.core.config import Config
from app.db.session import User

auth_router = APIRouter()

# Setup OAuth
starlette_config = StarletteConfig(environ={
    "GOOGLE_CLIENT_ID": Config.GOOGLE_CLIENT_ID or "",
    "GOOGLE_CLIENT_SECRET": Config.GOOGLE_CLIENT_SECRET or ""
})
oauth = OAuth(starlette_config)
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@auth_router.get("/login/google")
async def login_google(request: Request):
    if not Config.GOOGLE_CLIENT_ID:
        return HTMLResponse("<h3>Error: GOOGLE_CLIENT_ID not set in environment.</h3>", status_code=500)
    redirect_uri = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@auth_router.get("/auth")
async def auth(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    if not code:
        return HTMLResponse("<h3>Auth Error: No authorization code received</h3>", status_code=400)

    import requests
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": Config.GOOGLE_CLIENT_ID,
        "client_secret": Config.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": str(request.url_for('auth'))
    }
    
    try:
        resp = requests.post(token_url, data=data, timeout=15)
        resp.raise_for_status()
        token_data = resp.json()
    except Exception as e:
        err_msg = str(e)
        if 'resp' in locals():
            err_msg += f" | Details: {resp.text}"
        return HTMLResponse(f"<h3>Auth Error (Token Exchange): {err_msg}</h3>", status_code=400)

    access_token = token_data.get("access_token")
    if not access_token:
        return HTMLResponse("<h3>Auth Error: Failed to obtain access token.</h3>", status_code=400)

    try:
        user_resp = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", 
                                 headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        user_resp.raise_for_status()
        user_info = user_resp.json()
    except Exception as e:
        return HTMLResponse(f"<h3>Auth Error (User Info): {e!s}</h3>", status_code=400)

    if not user_info:
        return HTMLResponse("<h3>Auth Error: Failed to retrieve user info.</h3>", status_code=400)

    email = user_info['email']
    name = user_info.get('name', '')
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
        
    # Generate JWT
    expiration = datetime.now(timezone.utc) + timedelta(minutes=Config.JWT_EXPIRATION_MINUTES)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": expiration
    }
    token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)
        
    frontend_url = Config.FRONTEND_URL.split(",")[0].strip() if Config.FRONTEND_URL else "http://localhost:5173"
    return RedirectResponse(url=f'{frontend_url}/?token={token}')

@auth_router.get("/logout")
async def logout(request: Request):
    request.session.pop('user_id', None)
    request.session.pop('user_email', None)
    return RedirectResponse(url='http://localhost:5173/')

@auth_router.get("/api/me")
async def get_me(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not logged in or missing Bearer token")
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
        user_id = payload.get("sub")
    except jwt.ExpiredSignatureError:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid token")

    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not logged in")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {"id": user.id, "name": user.name, "email": user.email}
