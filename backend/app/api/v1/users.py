from fastapi import APIRouter, status

from app.api.deps import AdminUser, ClientIp, SessionDep
from app.schemas.user import UserCreate, UserOut
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate, admin: AdminUser, session: SessionDep, ip: ClientIp
) -> UserOut:
    user = await user_service.create_user(session, admin, body, ip)
    return UserOut.model_validate(user)


@router.get("", response_model=list[UserOut])
async def list_users(admin: AdminUser, session: SessionDep) -> list[UserOut]:
    users = await user_service.list_users(session, admin.organization_id)
    return [UserOut.model_validate(u) for u in users]
