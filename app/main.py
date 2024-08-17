from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# from fastapi_utils.tasks import repeat_every

from app.libs.utils import file_cleanup
from app.routers.admin import api as admin

app = FastAPI(
    title="DocumentX",
    description="APIs for DocuX",
    version="1.0.0",
    # docs_url=None,
    redoc_url=None,
)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)


@app.on_event("startup")
# @repeat_every(seconds=86400, wait_first=False)  # Every 24 hours
def startup() -> None:
    file_cleanup()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = exc.errors()[0]
    field = str(error["loc"][1])
    message = error["msg"]
    detail = field + " - " + message.capitalize()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": detail}),
    )
