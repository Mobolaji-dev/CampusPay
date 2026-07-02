
import firebase_admin
from firebase_admin import auth
from firebase_admin import credentials
from app.core.config import settings
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import json
import base64
import tempfile

bearer_schema=HTTPBearer()


creds_json = base64.b64decode(os.environ["FIREBASE_CREDENTIALS_BASE64"])
creds_dict = json.loads(creds_json)
firebase_creds = credentials.Certificate(creds_dict)

default_app = firebase_admin.initialize_app(firebase_creds)


def verify_firebase_token(token: str):

    decoded_token = auth.verify_id_token(token)
    return decoded_token

def get_current_firebase_user(creds:HTTPAuthorizationCredentials= Depends(bearer_schema)):

    token=creds.credentials
    try:
        decoded_token = verify_firebase_token(token)
        return decoded_token
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Expired Token"
        ) 


