import json

from fastapi import APIRouter, File, UploadFile, HTTPException
from services.evidence_service import uploading_evidence, get_evidence
from schemas.payment import PaymentCreateRequest, PaymentUpdateRequest, PaymentCreateResponse
from core.database import payments_collection, evidence_collection
from typing import Optional
from datetime import date, datetime
from pymongo import DESCENDING
from fastapi.responses import JSONResponse, FileResponse
from bson import ObjectId

router = APIRouter()

"""
    Create a new payment record in the database.

    This endpoint accepts a `PaymentCreateRequest` object and creates a new payment entry 
    in the payments collection. The `payee_added_date_utc` and `payee_due_date` fields 
    are converted into the required formats before insertion.

    - **payment**: The payment data to be inserted, provided as a JSON body.

    Returns:
        - **payment_id**: The ID of the newly created payment.

    Raises:
        - HTTPException: If there is an error during the creation process.
"""

@router.post("/create", response_model=PaymentCreateResponse)
async def create_payment(payment: PaymentCreateRequest):
    # Prepare the payment data for insertion
    payment_data = payment.dict()

    if isinstance(payment.payee_added_date_utc, datetime):
        payment_data['payee_added_date_utc'] = payment.payee_added_date_utc.strftime("%b %d, %Y, %I:%M %p")

    if isinstance(payment.payee_due_date, date):
        payment_data['payee_due_date'] = datetime.combine(payment.payee_due_date, datetime.min.time())  
    # Insert payment into the payments collection
    try:
        result = payments_collection.insert_one(payment_data)
        # Return the ID of the newly created payment as a string
        return {"payment_id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating payment: {str(e)}")
    pass

"""
    Update an existing payment record.

    This endpoint updates the payment status and related fields for an existing payment 
    identified by `payment_id`.

    - **payment_id**: The ID of the payment to be updated (in URL path).
    - **payment**: The payment update data to be applied.

    Returns:
        - **message**: Confirmation message indicating the payment was updated.

    Raises:
        - HTTPException: If there is an error during the update process.
"""

@router.put("/update/{payment_id}")
async def update_payment(payment_id: str, payment: PaymentUpdateRequest):
    # Prepare the payment data for update
    payment_data = payment.dict()

    if isinstance(payment.payee_added_date_utc, datetime):
        payment_data['payee_added_date_utc'] = payment.payee_added_date_utc.strftime("%b %d, %Y, %I:%M %p")

    if isinstance(payment.payee_due_date, date):
        payment_data['payee_due_date'] = datetime.combine(payment.payee_due_date, datetime.min.time())  
    # Insert payment into the payments collection
    try:
        result = payments_collection.update_one({"_id": ObjectId(payment_id)}, {"$set": payment_data})
        return {"message":  "Payment updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating payment: {str(e)}")
    pass


"""
    Delete an existing payment record and related evidence.

    This endpoint deletes a payment record identified by `payment_id` and also removes any 
    related evidence from the evidence collection if it exists.

    - **payment_id**: The ID of the payment to be deleted (in URL path).

    Returns:
        - **message**: Confirmation message indicating the payment was deleted.

    Raises:
        - HTTPException: If there is an error during the deletion process or if the payment does not exist.
"""
@router.delete("/delete/{payment_id}")
async def delete_payment(payment_id: str):
    # Validate the payment_id is in the correct format
    try:
        # Convert the payment_id to an ObjectId
        payment_object_id = ObjectId(payment_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payment ID format")
    
    # Check if the payment exists in the database
    payment = payments_collection.find_one({"_id": payment_object_id})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    # Delete related evidence from the evidence collection (if any)
    evidence = evidence_collection.find_one({"payment_id": payment_id})
    if evidence:
        evidence_collection.delete_many({"payment_id": payment_id})
    
    # Now delete the payment from the payments collection
    result = payments_collection.delete_one({"_id": payment_object_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {"message": "Payment and related evidence deleted successfully"}


"""
    Upload evidence related to a payment.

    This endpoint uploads a file as evidence for a payment identified by `payment_id`.

    - **payment_id**: The ID of the payment for which evidence is being uploaded.
    - **file**: The file to be uploaded, passed as a form-data.

    Returns:
        - **message**: A confirmation message indicating the upload was successful.

    Raises:
        - HTTPException: If there is an error during the file upload process.
"""
@router.post("/upload_evidence/{payment_id}")
async def upload_evidence(payment_id: str, file: UploadFile = File(...)):
    file_data = await file.read()
    return uploading_evidence(payment_id, file_data, file.filename, file.content_type)

"""
    Download evidence related to a payment.

    This endpoint retrieves and serves the evidence associated with a payment identified by `payment_id`.

    - **payment_id**: The ID of the payment for which evidence is being requested.

    Returns:
        - The file content for the evidence associated with the payment.

    Raises:
        - HTTPException: If no evidence exists for the specified payment.
"""
@router.get("/download_evidence/{payment_id}")
async def download_evidence(payment_id: str):
    return get_evidence(payment_id)

"""
    Fetch a list of payments, optionally filtered by country, city, or search query.

    This endpoint retrieves a list of payments from the database with support for filtering 
    by `payee_country`, `payee_city`, or a search query. It also supports pagination with 
    `skip` and `limit` parameters.

    - **payee_country**: Filter payments by the country of the payee (optional).
    - **payee_city**: Filter payments by the city of the payee (optional).
    - **search**: Search by payee's first name, last name, or email (optional).
    - **skip**: Number of records to skip for pagination (default 0).
    - **limit**: Number of records to return (default 10).

    Returns:
        - A JSON object containing the filtered list of payments with relevant details.

    Raises:
        - HTTPException: If there is an error during the retrieval process.
"""
@router.get("/get_payments")
@router.get("/get_payments")
def get_payments(
    payee_first_name: Optional[str] = None,
    payee_last_name: Optional[str] = None,
    payee_payment_status: Optional[str] = None,
    payee_address_line_1: Optional[str] = None,
    payee_address_line_2: Optional[str] = None,
    payee_city: Optional[str] = None,
    payee_country: Optional[str] = None,
    payee_province_or_state: Optional[str] = None,
    payee_postal_code: Optional[str] = None,
    payee_phone_number: Optional[str] = None,
    payee_email: Optional[str] = None,
    currency: Optional[str] = None,
    skip: int = 1,
    limit: int = 10,
):
    today = datetime.combine(date.today(), datetime.min.time())

    # Update `payee_payment_status` based on `payee_due_date`
    payments_collection.update_many(
        {"payee_due_date": {"$eq": today}},
        {"$set": {"payee_payment_status": "due_now"}}
    )
    payments_collection.update_many(
        {"payee_due_date": {"$lt": today}},
        {"$set": {"payee_payment_status": "overdue"}}
    )

    # Calculate `total_due` for all records
    payments = payments_collection.find()
    for payment in payments:
        discount = payment.get("discount_percent", 0) or 0
        tax = payment.get("tax_percent", 0) or 0
        due_amount = payment["due_amount"]
        total_due = due_amount - (due_amount * discount / 100) + (due_amount * tax / 100)
        payments_collection.update_one(
            {"_id": payment["_id"]},
            {"$set": {"total_due": round(total_due, 2)}}
        )

    # Build the query based on the fields passed from the frontend (only text fields)
    query = {}
    if payee_first_name:
        query["payee_first_name"] = {"$regex": payee_first_name, "$options": "i"}
    if payee_last_name:
        query["payee_last_name"] = {"$regex": payee_last_name, "$options": "i"}
    if payee_payment_status:
        query["payee_payment_status"] = {"$regex": payee_payment_status, "$options": "i"}
    if payee_address_line_1:
        query["payee_address_line_1"] = {"$regex": payee_address_line_1, "$options": "i"}
    if payee_address_line_2:
        query["payee_address_line_2"] = {"$regex": payee_address_line_2, "$options": "i"}
    if payee_city:
        query["payee_city"] = {"$regex": payee_city, "$options": "i"}
    if payee_country:
        query["payee_country"] = {"$regex": payee_country, "$options": "i"}
    if payee_province_or_state:
        query["payee_province_or_state"] = {"$regex": payee_province_or_state, "$options": "i"}
    if payee_postal_code:
        query["payee_postal_code"] = {"$regex": payee_postal_code, "$options": "i"}
    if payee_phone_number:
        query["payee_phone_number"] = {"$regex": payee_phone_number, "$options": "i"}
    if payee_email:
        query["payee_email"] = {"$regex": payee_email, "$options": "i"}
    if currency:
        query["currency"] = {"$regex": currency, "$options": "i"}

    # Pagination calculation
    calculate_skip = (skip - 1) * limit
    # Fetch filtered and paginated results
    results = payments_collection.find(query).sort("payee_due_date", -1).skip(calculate_skip).limit(limit)

    total_count = payments_collection.count_documents(query)

    # Convert MongoDB results to JSON serializable format
    payments_list = []
    for payment in results:
        payment_data = {
            **{
                key: (str(value) if key == "_id" else value)
                for key, value in payment.items()
                if key != "payee_due_date"  # Exclude payee_due_date temporarily
            },
            "payee_due_date": (
                payment["payee_due_date"].isoformat().split("T")[0]
                if isinstance(payment["payee_due_date"], datetime)
                else payment["payee_due_date"]
            ),
        }

        # Call `get_evidence` with the payment's payment_id (_id)
        payment_id = str(payment["_id"])
        evidence_response = get_evidence(payment_id)  # You can adjust this if needed for async calls

        if isinstance(evidence_response, FileResponse):
            # If file data is found, include it
            payment_data["evidence_file"] = {
                "file_found": True,
                "file_name": evidence_response.headers["Content-Disposition"].split("=")[-1],
            }
        else:
            # If no file data is found, include a message
            evidence_data = evidence_response.body.decode()  # Decode the response body into a string
            evidence_data = json.loads(evidence_data)  # Convert the JSON string into a Python dictionary
            payment_data["evidence_file"] = {
                "file_found": False,
                "message": evidence_data.get("message", "No file data available"),  # Safely extract message
            }

        payments_list.append(payment_data)

    return JSONResponse(content={"payments": payments_list, "totalCount": total_count})