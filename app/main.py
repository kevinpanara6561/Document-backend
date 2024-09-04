import json
import logging
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# from fastapi_utils.tasks import repeat_every

from app.database import SessionLocal
from app.libs.utils import file_cleanup, generate_id
from app.models import AdminUserModel, CategoryModel, DocumentModel, ExtractedDataModel
from app.routers.admin import api as admin
from app.routers.admin.crud.whatsapp import send_classification_template

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


# Configure logging
logging.basicConfig(
    filename='logs/access.log',  # Optionally specify a log file
    level=logging.INFO,  # Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log format
    datefmt='%Y-%m-%d %H:%M:%S'  # Format of the timestamps
)

db = SessionLocal()

socket = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    host = websocket.query_params.get("host", "default_host")
    logging.info(f"path: {host}")
    logging.info("websocket message")
    await websocket.accept()
    socket.add(websocket)
    
    try:
        logging.info("in try")
        while True:
            data = await websocket.receive_text()
            logging.info(f"Received data: {data}")
            
            # Parse JSON data
            json_data = json.loads(data)
            logging.info(f"Parsed JSON data: {json_data}")

            db_category = db.query(CategoryModel).filter(CategoryModel.name == json_data['category'], CategoryModel.is_deleted == False).first()
            db_sub_category = db.query(CategoryModel).filter(CategoryModel.name == json_data['sub_category'], CategoryModel.is_deleted == False).first()
            db_document = db.query(DocumentModel).filter(DocumentModel.id == json_data['document_id'], DocumentModel.is_deleted == False).first()
            db_admin_user = db.query(AdminUserModel).filter(AdminUserModel.id == db_document.admin_user_id, AdminUserModel.is_deleted == False).first()
            
            if not db_category:
                new_category = CategoryModel(
                    id = generate_id(),
                    name = json_data['category'],
                    parent_id = None,
                    admin_user_id = json_data['admin_user_id']
                )
                db.add(new_category)
                db.commit()
                
                new_sub_catgory = CategoryModel(
                    id = generate_id(),
                    name = json_data['sub_category'],
                    parent_id = new_category.id,
                    admin_user_id = json_data['admin_user_id']
                )
                
                db.add(new_sub_catgory)
                db.commit()
                
                db_document.category_id = new_sub_catgory.id
                db_document.status = json_data['status']
                db.commit()
                                
            else:
                if not db_sub_category:
                    new_sub_catgory = CategoryModel(
                        id = generate_id(),
                        name = json_data['sub_category'],
                        parent_id = db_category.id,
                        admin_user_id = json_data['admin_user_id']
                    )
                    
                    db.add(new_sub_catgory)
                    db.commit()
                    
                    db_document.category_id = new_sub_catgory.id
                    db_document.status = json_data['status']
                    db.commit()
                    
                else:
                    db_document.category_id = db_sub_category.id
                    db_document.status = json_data['status']
                    db.commit()
            
            # Create a new entry in the database
            new_data = ExtractedDataModel(
                id=generate_id(),
                data=json_data,
                classification_result=json_data['sub_category'],
                document_id=json_data['document_id'],
            )
            
            db.add(new_data)
            db.commit()
            
            try:
                logging.info("in whatsapp try")
                send_classification_template(db_admin_user.phone, json_data['sub_category'], json_data['category'], json_data['sub_category'])
            except Exception as e:
                logging.error(e)
            
            for conn in socket:
                if conn.query_params.get("host", "default_host") == "local":
                    logging.info(f"Sending data to local client: {data}")
                    await conn.send_text(f"Message text was: {data}")

    except WebSocketDisconnect:
        logging.info(f"Client disconnected from host: {host}")
        socket.discard(websocket)