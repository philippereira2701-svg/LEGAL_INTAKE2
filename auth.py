import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from flask import request, g, jsonify
from functools import wraps
import uuid

SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("FLASK_SECRET_KEY", "lexbridge-jwt-dev"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440 # 24 hours

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a bcrypt hashed password"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    """Generate a signed JWT token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def require_auth(f):
    """Decorator to enforce JWT authentication and set global tenant context"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('access_token') or request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        if not token:
            return jsonify({"msg": "Token is missing"}), 401
            
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            g.tenant_id = payload.get("tenant_id")
            g.user_id = payload.get("user_id")
            g.role = payload.get("role")
            if not g.tenant_id or not g.user_id:
                return jsonify({"msg": "Token is invalid"}), 401
        except (JWTError, ValueError):
            return jsonify({"msg": "Token is invalid"}), 401
            
        return f(*args, **kwargs)
    return decorated

def require_role(role: str):
    """Decorator to enforce specific user roles"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if g.role != role and g.role != 'admin':
                return jsonify({"msg": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
