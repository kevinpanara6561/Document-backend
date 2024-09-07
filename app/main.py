import json
import logging
from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# from fastapi_utils.tasks import repeat_every
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.dependencies import get_db
from app.libs.utils import file_cleanup, generate_id
from app.models import AdminUserModel, CategoryModel, DocumentModel, ExtractedDataModel
from app.routers.admin import api as admin
from app.routers.admin.crud.whatsapp import send_classification_template, send_extract_data_as_excel

app = FastAPI(
    title="DocuLens",
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


# Configure logging
logging.basicConfig(
    filename='logs/access.log',  # Optionally specify a log file
    level=logging.INFO,  # Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log format
    datefmt='%Y-%m-%d %H:%M:%S'  # Format of the timestamps
)