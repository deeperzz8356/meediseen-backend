import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_NAME"),
    api_key=os.getenv("CLOUDINARY_KEY"),
    api_secret=os.getenv("CLOUDINARY_SECRET"),
    secure=True
)

def upload_image(local_path: str, destination_blob_name: str) -> str:
    """
    Uploads a file to Cloudinary and returns the secure URL.
    This signature matches the firebase_svc.upload_image for easy swapping.
    """
    try:
        # We use the destination_blob_name to create a unique public_id if possible
        # but Cloudinary handles uniqueness well with default settings too.
        # destination_blob_name example: uploads/session_id/original.jpg
        
        # Remove extension for public_id
        public_id = os.path.splitext(destination_blob_name)[0]
        
        response = cloudinary.uploader.upload(
            local_path,
            public_id=public_id,
            folder="mediseen"
        )
        url = response.get("secure_url", "")
        print(f"✅ Cloudinary upload success: {url}")
        return url
    except Exception as e:
        print(f"❌ Cloudinary upload error: {e}")
        return ""
