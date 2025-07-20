from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
import logging

logger = logging.getLogger(__name__)

class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that retrieves token from either
    the Authorization header or an HTTP-only cookie.
    """

    def authenticate(self, request):
        try:
            # Attempt to get JWT token from Authorization header
            header = self.get_header(request)

            if header is None:
                # Fallback to secure HTTP-only cookie
                raw_token = request.COOKIES.get(settings.AUTH_COOKIE)
                if not raw_token:
                    return None  # No token found in either source
            else:
                raw_token = self.get_raw_token(header)

            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)

            # Check if user is active (required by your document)
            if not user.is_active:
                logger.warning(f"Inactive user tried to authenticate: {user.username}")
                raise AuthenticationFailed("User account is inactive.")

            logger.info(f"User '{user.username}' authenticated via JWT.")
            return user, validated_token

        except AuthenticationFailed as auth_fail:
            logger.warning(f"Authentication failed: {str(auth_fail)}")
            raise auth_fail  # Let DRF handle failed auths properly

        except Exception as e:
            logger.error(f"Unexpected error in CustomJWTAuthentication: {str(e)}", exc_info=True)
            return None
