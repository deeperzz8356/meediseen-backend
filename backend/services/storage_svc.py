import os
from dotenv import load_dotenv

load_dotenv()

def upload_image(local_path: str, destination_blob_name: str) -> str:
    """
    Dispatches upload to either Cloudinary or Firebase based on environment variables.
    """
    use_cloudinary = os.getenv("CLOUDINARY_NAME") and os.getenv("CLOUDINARY_KEY") and os.getenv("CLOUDINARY_SECRET")
    
    if use_cloudinary:
        try:
            from .cloudinary_svc import upload_image as upload_cloudinary
            return upload_cloudinary(local_path, destination_blob_name)
        except ImportError:
            print("⚠️ Cloudinary service not found, falling back to Firebase")
    
    try:
        from .firebase_svc import upload_image as upload_firebase
        return upload_firebase(local_path, destination_blob_name)
    except ImportError:
        print("❌ No storage service available")
        return ""
