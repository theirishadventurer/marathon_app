from fastapi import APIRouter
from starlette.responses import JSONResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def post_chat():
    return JSONResponse(status_code=501, content={"detail": "Chat not implemented — session 3"})


@router.get("")
async def get_chat():
    return JSONResponse(status_code=501, content={"detail": "Chat not implemented — session 3"})
