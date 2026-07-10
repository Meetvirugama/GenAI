from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig
from sqlalchemy.orm import Session
from core.config import Config
from core.db import User
from api.dependencies import get_db

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
        "redirect_uri": "http://localhost:7860/auth"
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
        return HTMLResponse(f"<h3>Auth Error (User Info): {str(e)}</h3>", status_code=400)

    if user_info:
        email = user_info['email']
        name = user_info.get('name', '')
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, name=name)
            db.add(user)
            db.commit()
            db.refresh(user)
            
        request.session['user_id'] = user.id
        request.session['user_email'] = user.email
        
    return RedirectResponse(url='http://localhost:5173/')

@auth_router.get("/logout")
async def logout(request: Request):
    request.session.pop('user_id', None)
    request.session.pop('user_email', None)
    return RedirectResponse(url='http://localhost:5173/')

@auth_router.get("/api/me")
async def get_me(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get('user_id')
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not logged in")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {"id": user.id, "name": user.name, "email": user.email}
