import os
import bson
from models.evidence import Evidence
from core.database import evidence_collection, payments_collection
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from io import BytesIO

def uploading_evidence(payment_id: str, file_data: bytes, file_name: str, file_type: str):
    evidence = Evidence(payment_id=payment_id, file_name=file_name, file_data=file_data, file_type=file_type)
    evidence_collection.insert_one(evidence.dict())
    payments_collection.update_one(
        {"_id": ObjectId(payment_id)},  # Match the payment by payment_id
        {"$set": {"payee_payment_status": "completed"}}  # Set the status to "completed"
    )
    return {"file_id": str(evidence.payment_id)}

def get_evidence(payment_id: str):
    evidence = evidence_collection.find_one({"payment_id": payment_id})

    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    if evidence:
        evidence["_id"] = str(evidence["_id"])  # Convert ObjectId to string

    # If file_data is stored as bytes, convert it to a file-like object
    file_data = evidence.get("file_data")
    
    if file_data:
        # Option 1: Save the file temporarily and return its path (for large files)
        temp_file_path = "/tmp/temp_file"
        with open(temp_file_path, "wb") as f:
            f.write(file_data)
        
        return FileResponse(temp_file_path, media_type=evidence["file_type"], headers={"Content-Disposition": f"attachment; filename={evidence['file_name']}"})
    
    raise HTTPException(status_code=400, detail="No file data found") 
