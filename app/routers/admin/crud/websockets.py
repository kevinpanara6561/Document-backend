# import json
# import logging

# from fastapi import WebSocket, WebSocketDisconnect
# from app.database import SessionLocal
# from app.libs.utils import generate_id
# from app.models import ExtractedDataModel
# from app.main import app


# db = SessionLocal()

# socket = set()

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     host = websocket.query_params.get("host", "default_host")
#     logging.info(f"path: {host}")
#     logging.info("websocket message")
    
#     await websocket.accept()
#     socket.add(websocket)
    
#     try:
#         while True:
#             data = await websocket.receive_text()
#             logging.info(f"Received data: {data}")
            
#             # Parse JSON data
#             json_data = json.loads(data)
#             logging.info(f"Parsed JSON data: {json_data}")

#             # Extract relevant information from the parsed JSON
#             score = json_data.get("score")
#             label = json_data.get("label")
#             pdf_id = json_data.get("pdf_id")

#             # Create a new entry in the database
#             new_data = ExtractedDataModel(
#                 id=generate_id(),
#                 data=json_data,
#                 classification_result=label,
#                 invoice_id=pdf_id,
#                 is_deleted=False
#             )
            
#             db.add(new_data)
#             db.commit()

#             for i in socket:
#                 if i.query_params.get("host", "default_host") == "local":
#                     logging.info(f"Sending data to local client: {data}")
#                     await i.send_text(f"Message text was: {data}")

#     except WebSocketDisconnect:
#         logging.info(f"Client disconnected from host: {host}")
#         socket.discard(websocket)