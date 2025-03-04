import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image

def save_photo(photo_file, max_size=(300, 300)):
    """
    Save and process a photo upload.
    
    Args:
        photo_file: FileStorage object from form
        max_size: Tuple for maximum dimensions (width, height)
        
    Returns:
        Filename of saved photo or None if saving failed
    """
    if not photo_file:
        return None
    
    # Create a unique filename
    filename = secure_filename(photo_file.filename)
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    
    # Get the upload path
    upload_path = current_app.config['UPLOAD_PATH']
    filepath = os.path.join(upload_path, unique_filename)
    
    try:
        # Save and process the image
        img = Image.open(photo_file)
        
        # Convert to RGB if needed (in case of PNG with transparency)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize while maintaining aspect ratio
        img.thumbnail(max_size, Image.LANCZOS)
        
        # Save the processed image
        img.save(filepath, quality=85, optimize=True)
        return unique_filename
    except Exception as e:
        current_app.logger.error(f"Error saving photo: {str(e)}")
        return None

def delete_photo(filename):
    """Delete a photo by filename."""
    if not filename:
        return False
    
    filepath = os.path.join(current_app.config['UPLOAD_PATH'], filename)
    
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        return True
    except Exception as e:
        current_app.logger.error(f"Error deleting photo: {str(e)}")
        return False