from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

client: AsyncIOMotorClient = None


def get_client() -> AsyncIOMotorClient:
    return client


def get_database():
    return client[settings.mongodb_db_name]


async def connect_to_mongo():
    global client
    try:
        client = AsyncIOMotorClient(settings.mongodb_url)
        # Ping to confirm connection
        await client.admin.command("ping")
        logger.info("✅ Connected to MongoDB")

        db = get_database()
        # Create indexes
        await db.users.create_index([("email", ASCENDING)], unique=True)
        await db.documents.create_index([("department", ASCENDING)])
        await db.documents.create_index([("uploaded_by", ASCENDING)])
        await db.chat_history.create_index([("user_id", ASCENDING)])
        await db.chat_history.create_index([("created_at", ASCENDING)])
        await db.analytics.create_index([("timestamp", ASCENDING)])
        logger.info("✅ MongoDB indexes created")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise


async def close_mongo_connection():
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")
