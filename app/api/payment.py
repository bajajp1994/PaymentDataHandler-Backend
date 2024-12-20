from fastapi import APIRouter, File, UploadFile, HTTPException
from services.evidence_service import uploading_evidence, get_evidence
from schemas.payment import PaymentCreateRequest, PaymentUpdateRequest, PaymentCreateResponse
from core.database import payments_collection, evidence_collection
from typing import Optional
from datetime import date, datetime
from pymongo import DESCENDING
from fastapi.responses import JSONResponse
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
def get_payments(
    payee_country: Optional[str] = None,
    payee_city: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
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

    # Build query for filtering and searching
    query = {}
    if payee_country:
        query["payee_country"] = payee_country
    if payee_city:
        query["payee_city"] = payee_city
    if search:
        # Define the fields to exclude
        excluded_fields = ["payee_city", "payee_country"]

        # Get all fields in the Payment model except excluded ones
        included_fields = [
            "payee_first_name",
            "payee_last_name",
            "payee_payment_status",
            "payee_added_date_utc",
            "payee_due_date",
            "payee_address_line_1",
            "payee_address_line_2",
            "payee_province_or_state",
            "payee_postal_code",
            "payee_phone_number",
            "payee_email",
            "currency",
            "discount_percent",
            "tax_percent",
            "due_amount",
            "total_due"
        ]

        # Remove excluded fields from the list
        included_fields = [field for field in included_fields if field not in excluded_fields]

        query["$or"] = [
            {field: {"$regex": search, "$options": "i"}} for field in included_fields
        ]

    # Fetch filtered and paginated results
    results = payments_collection.find(query).sort("payee_due_date", DESCENDING).skip(skip).limit(limit)

    # Convert MongoDB results to JSON serializable format
    payments_list = [
        {
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
        for payment in results
    ]

    return JSONResponse(content={"payments": payments_list})