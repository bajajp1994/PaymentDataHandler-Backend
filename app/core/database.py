from pymongo import MongoClient
from .config import settings
from bson.son import SON

class MongoDB:
    def __init__(self, uri: str = settings.mongodb_uri, db_name: str = settings.database_name):
        """
        Initialize MongoDB connection and database.
        """
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def get_collection(self, collection_name: str):
        """
        Dynamically get the specified collection from the database.
        """
        return self.db[collection_name]

    def close(self):
        """
        Close the MongoDB client connection.
        """
        self.client.close()


# Example usage
db = MongoDB()

# For payments collection
payments_collection = db.get_collection("payments")

# For evidence collection
evidence_collection = db.get_collection("evidence")
