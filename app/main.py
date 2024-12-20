from fastapi import FastAPI
from api.payment import router as payment_router
from dotenv import load_dotenv
import os
from services.normalize_csv_service import normalize_csv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# CSV file path from environment variable (can be adjusted if needed)
CSV_FILE_PATH = os.getenv("CSV_FILE_PATH", "./payment_information.csv")

@app.on_event("startup")
async def startup_event():
    """
    This function is executed when the application starts up.
    It will normalize the data from the CSV file and save it to MongoDB.
    """
    print(f"Normalizing data from {CSV_FILE_PATH}...")
    normalize_csv(CSV_FILE_PATH)  # Normalize and save to MongoDB
    print("Normalization completed.")

app.include_router(payment_router, prefix="/payments", tags=["Payments"])
