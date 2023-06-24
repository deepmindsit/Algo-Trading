from jose import JWTError, jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime, timedelta

from utils.app_utils import AppUtils


class AuthHandler():
    security = HTTPBearer()
    secret = AppUtils.getSettings().SECRET_KEY

    def encode_token(self, user_id):
        payload = {
            'exp': datetime.utcnow() + timedelta(days=AppUtils.getSettings().ACCESS_TOKEN_EXPIRE),
            'iat': datetime.utcnow(),
            'sub': user_id
        }
        return jwt.encode(
            payload,
            self.secret,
            algorithm=AppUtils.getSettings().ALGORITHM
        )

    def decode_token(self, token):
        try:
            payload = jwt.decode(token, self.secret, algorithms=[
                                 AppUtils.getSettings().ALGORITHM])
            return payload['sub']
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401, detail='Signature has expired')
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail='Invalid token')

    def auth_wrapper(self, auth: HTTPAuthorizationCredentials = Security(security)):
        return self.decode_token(auth.credentials)

    def decode_ws_token(self, token):
        try:
            payload = jwt.decode(token, self.secret, algorithms=['HS256'])
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 1
        except Exception as ex:
            return 2
