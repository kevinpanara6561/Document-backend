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



socket = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    db_session = SessionLocal()
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
            if json_data['template'] == "classification":
                if json_data['parent_id']:
                    new_document = DocumentModel(
                        id = json_data["document_id"],
                        name = json_data['file_name'],
                        file_path = json_data['file_path'],
                        file_type = json_data['file_type'],
                        admin_user_id = json_data['admin_user_id'],
                        parent_id = json_data['parent_id'],
                        upload_by = True,
                        is_whatsapp = json_data['is_whatsapp']
                    )
                    db_session.add(new_document)
                    db_session.commit()
                    db_session.refresh(new_document)
                    
                
            db_admin_user = db_session.query(AdminUserModel).filter(AdminUserModel.id == json_data['admin_user_id'], AdminUserModel.is_deleted == False).first()
            if json_data['template'] == "classification":

                db_category = db_session.query(CategoryModel).filter(CategoryModel.name == json_data['category'], CategoryModel.admin_user_id == json_data['admin_user_id'], CategoryModel.is_deleted == False).first()
                db_sub_category = db_session.query(CategoryModel).filter(CategoryModel.name == json_data['sub_category'],CategoryModel.admin_user_id == json_data['admin_user_id'],  CategoryModel.is_deleted == False).first()
                db_document = db_session.query(DocumentModel).filter(DocumentModel.id == json_data['document_id'], DocumentModel.admin_user_id == json_data['admin_user_id'], DocumentModel.is_deleted == False).first()
                
                if not db_category:
                    new_category = CategoryModel(
                        id = generate_id(),
                        name = json_data['category'],
                        parent_id = None,
                        admin_user_id = json_data['admin_user_id']
                    )
                    db_session.add(new_category)
                    db_session.commit()
                    db_session.refresh(new_category)
                    
                    new_sub_catgory = CategoryModel(
                        id = generate_id(),
                        name = json_data['sub_category'],
                        parent_id = new_category.id,
                        admin_user_id = json_data['admin_user_id']
                    )
                    
                    db_session.add(new_sub_catgory)
                    db_session.commit()
                    db_session.refresh(new_sub_catgory)
                    
                    # db_document = db_session.query(DocumentModel).filter(DocumentModel.id == json_data['document_id'], DocumentModel.admin_user_id == json_data['admin_user_id'], DocumentModel.is_deleted == False).first()
                    
                    db_document.category_id = new_sub_catgory.id
                    db_document.status = json_data['status']
                    db_session.commit()
                                    
                else:
                    if not db_sub_category:
                        new_sub_catgory = CategoryModel(
                            id = generate_id(),
                            name = json_data['sub_category'],
                            parent_id = db_category.id,
                            admin_user_id = json_data['admin_user_id']
                        )
                        
                        db_session.add(new_sub_catgory)
                        db_session.commit()
                        db_session.refresh(new_sub_catgory)
                        
                        # db_document = db_session.query(DocumentModel).filter(DocumentModel.id == json_data['document_id'], DocumentModel.admin_user_id == json_data['admin_user_id'], DocumentModel.is_deleted == False).first()
                        
                        db_document.category_id = new_sub_catgory.id
                        db_document.status = json_data['status']
                        db_session.commit()
                        
                    else:
                        
                        # db_document = db_session.query(DocumentModel).filter(DocumentModel.id == json_data['document_id'], DocumentModel.admin_user_id == json_data['admin_user_id'], DocumentModel.is_deleted == False).first()
                        
                        db_document.category_id = db_sub_category.id
                        db_document.status = json_data['status']
                        db_session.commit()
                
                # # Create a new entry in the database
                new_data = ExtractedDataModel(
                    id=generate_id(),
                    classification_result=json_data['sub_category'],
                    document_id=json_data['document_id'],
                )
                
                db_session.add(new_data)
                db_session.commit()
                db_session.refresh(new_data)
                
                try:
                    if db_document.is_whatsapp == True:
                        send_classification_template(db_admin_user.phone, json_data['sub_category'], json_data['category'], json_data['sub_category'])
                except Exception as e:
                    logging.error(e)
                
                for conn in socket:
                    if conn.query_params.get("host", "default_host") == "local":
                        logging.info(f"Sending data to local client: {data}")
                        await conn.send_json(json_data)
                        
                        
            else:
                try:
                    
                    send_extract_data_as_excel(db_admin_user.phone, json_data)
                    
                except Exception as e:
                    logging.error(e)

                for conn in socket:
                    if conn.query_params.get("host", "default_host") == "local":
                        logging.info(f"Sending data to local client: {data}")
                        await conn.send_json(json_data)
                        
                db_exreact_data = db_session.query(ExtractedDataModel).filter(ExtractedDataModel.document_id == json_data['document_id']).first()
                
                dumps_data = json.dumps(json_data['extract_data'])
                db_exreact_data.data = dumps_data
                db_session.commit()
                
            db_session.close()

    except WebSocketDisconnect:
        logging.info(f"Client disconnected from host: {host}")
        socket.discard(websocket)