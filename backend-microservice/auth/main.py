from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine
from models import Base
from database import SessionLocal
import models, schemas, utils
import pyotp
from fastapi.security import OAuth2PasswordBearer
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
import qrcode

Base.metadata.create_all(bind=engine)
app = FastAPI()

origins = [
    "http://localhost:3000",  # React development server
    "http://127.0.0.1:3000",
    # Add other origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specific origins or use ["*"] for all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
registration_secrets = {}  # Temporary storage; use a secure method in production

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/register/initiate", response_model=dict)
def initiate_registration(email: EmailStr, db: Session = Depends(get_db)):
    # Check if the email is already registered
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    # Generate a random 2FA secret key
    two_factor_secret = pyotp.random_base32()
    otpauth_url = pyotp.totp.TOTP(two_factor_secret).provisioning_uri(
        name=email, issuer_name="FastAPI"
    )
    # Store the secret temporarily
    registration_secrets[email] = two_factor_secret
    qrcode.make(otpauth_url).save("qr.png")
    return {"otpauth_url": otpauth_url}


@app.post("/register/complete", response_model=schemas.UserOut)
def complete_registration(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Retrieve the stored two_factor_secret
    two_factor_secret = registration_secrets.get(user.email)
    if not two_factor_secret:
        raise HTTPException(status_code=400, detail="Registration not initiated or expired")
    # Verify the OTP code
    totp = pyotp.TOTP(two_factor_secret)
    if not totp.verify(user.otp_code):
        raise HTTPException(status_code=400, detail="Invalid OTP code for 2FA setup")
    # Create the user
    hashed_password = utils.get_password_hash(user.password)
    new_user = models.User(
        user_name = user.user_name,
        email=user.email,
        hashed_password=hashed_password,
        two_factor_secret=two_factor_secret
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    # Remove the secret from temporary storage
    del registration_secrets[user.email]
    return new_user

def authenticate_user(db, email: str, password: str):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not utils.verify_password(password, user.hashed_password):
        return False
    return user

@app.post("/login", response_model=dict)
def login(login_req: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_req.email, login_req.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    # Verify the OTP code
    totp = pyotp.TOTP(user.two_factor_secret)
    if not totp.verify(login_req.otp_code):
        raise HTTPException(status_code=400, detail="Invalid OTP code")
    # Create the access token
    access_token = utils.create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, utils.SECRET_KEY, algorithms=[utils.ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return user

@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user