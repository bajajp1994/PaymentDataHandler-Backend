import pandas as pd
from datetime import date
from models.payment import Payment
from models.evidence import Evidence
from core.database import payments_collection
from schemas.payment import PaymentCreateRequest, PaymentUpdateRequest
from datetime import datetime

def normalize_csv(file_path: str):
    # Step 1: Read the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)

    # Step 2: Normalize the data
    # Ensure the fields are in the correct format (e.g., dates, numbers)
    df['payee_added_date_utc'] = pd.to_datetime(df['payee_added_date_utc'], unit='s').dt.strftime('%b %d, %Y, %I:%M %p')
    df['payee_due_date'] = pd.to_datetime(df['payee_due_date'], format='%Y-%m-%d', errors='coerce')
    df['discount_percent'] = pd.to_numeric(df['discount_percent'], errors='coerce').fillna(0)
    df['tax_percent'] = pd.to_numeric(df['tax_percent'], errors='coerce').fillna(0)
    df['due_amount'] = pd.to_numeric(df['due_amount'], errors='coerce')
    
    # Step 3: Calculate 'total_due' based on discount, tax, and due_amount
    df['total_due'] = df.apply(calculate_total_due, axis=1)
    
    # Step 4: Fill missing or optional fields (handle missing values if necessary)
    df['payee_address_line_2'] = df['payee_address_line_2'].fillna('')
    df['payee_postal_code'] = df['payee_postal_code'].astype(str)
    df['payee_phone_number'] = df['payee_phone_number'].astype(str)
    df['payee_country'] = df['payee_country'].astype(str)
    
    
    # Step 5: Save normalized data into MongoDB
    save_to_normalize_csv_to_db(df)

def save_to_normalize_csv_to_db(df: pd.DataFrame):
    # Convert DataFrame rows to Payment model format and insert into MongoDB
    for _, row in df.iterrows():
        payment_data = row.to_dict()
        payment = Payment(**payment_data)
        payments_collection.insert_one(payment.dict())

def calculate_total_due(row):
    # Apply discount and tax calculations
    discount = row.discount_percent if row.discount_percent else 0
    tax = row.tax_percent if row.tax_percent else 0
    return round(row.due_amount * (1 - discount / 100) * (1 + tax / 100), 2)
