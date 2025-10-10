"""
Avatar management router
"""
import asyncio
import os
import time
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, Form, HTTPException
from sqlmodel import Session, select

from .dependencies import (
    logger, engine, PERSISTENT_AVATARS_DIR, PUBLIC_DIR
)
from modules.models import AvatarImage

router = APIRouter()

@router.get("/api/avatars")
async def api_get_avatars():
    """Return list of available avatar images from both built-in and user-uploaded"""
    avatar_files = []
    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    
    # Get built-in avatars from the static directory
    builtin_avatars_dir = os.path.join(PUBLIC_DIR, "voice_avatars")
    if os.path.exists(builtin_avatars_dir):
        try:
            for filename in os.listdir(builtin_avatars_dir):
                if any(filename.lower().endswith(ext) for ext in valid_extensions):
                    avatar_files.append(f"/voice_avatars/{filename}")
        except Exception as e:
            logger.info(f"Error reading built-in avatars: {e}")
    
    # Get user-uploaded avatars from the persistent directory
    if os.path.exists(PERSISTENT_AVATARS_DIR):
        try:
            for filename in os.listdir(PERSISTENT_AVATARS_DIR):
                if any(filename.lower().endswith(ext) for ext in valid_extensions):
                    avatar_files.append(f"/user_avatars/{filename}")
        except Exception as e:
            logger.info(f"Error reading user avatars: {e}")
    
    # Sort for consistent ordering
    avatar_files.sort()
    return {"avatars": avatar_files}

@router.post("/api/avatars/upload")
async def api_upload_avatar(file: UploadFile, avatar_name: str = Form(...), avatar_type: str = Form("default"), avatar_group_id: str = Form(None)):
    """Upload a new avatar image"""
    logger.info(f"API: POST /api/avatars/upload called - name: {avatar_name}, type: {avatar_type}, group: {avatar_group_id}")
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            logger.error(f"Invalid file type uploaded: {file.content_type}")
            return {"error": "File must be an image", "success": False}
        
        # Validate file size (max 5MB)
        if file.size and file.size > 5 * 1024 * 1024:
            return {"error": "File size must be less than 5MB", "success": False}
        
        # Check for existing avatar with same name and type for replacement
        existing_avatar = None
        with Session(engine) as session:
            query = select(AvatarImage).where(
                AvatarImage.name == avatar_name,
                AvatarImage.avatar_type == avatar_type
            )
            existing_avatar = session.exec(query).first()
        
        # Use the persistent avatars directory for uploads
        avatars_dir = PERSISTENT_AVATARS_DIR
        logger.info(f"Saving avatar to persistent directory: {avatars_dir}")
        
        # Generate unique filename or reuse existing if replacing
        file_extension = Path(file.filename or "image.png").suffix
        
        if existing_avatar:
            # Replace existing avatar - reuse filename
            unique_filename = existing_avatar.filename
            file_path = os.path.join(avatars_dir, unique_filename)
        else:
            # New avatar - generate unique filename
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(avatars_dir, unique_filename)
        
        # Read and process image
        content = await file.read()
        
        # Resize image if larger than 200px on any side
        try:
            from PIL import Image
            import io
            
            # Open image from bytes
            image = Image.open(io.BytesIO(content))
            
            # Calculate new size maintaining aspect ratio
            max_size = 200
            if image.width > max_size or image.height > max_size:
                # Calculate resize dimensions
                ratio = min(max_size / image.width, max_size / image.height)
                new_width = int(image.width * ratio)
                new_height = int(image.height * ratio)
                
                # Resize image
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert back to bytes
                output = io.BytesIO()
                # Preserve original format, default to PNG if unknown
                format = image.format or 'PNG'
                if format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                    format = 'PNG'
                image.save(output, format=format, optimize=True, quality=85)
                content = output.getvalue()
            
        except ImportError:
            # Pillow not available, skip resizing
            pass
        except Exception as e:
            logger.info(f"Warning: Failed to resize image: {e}")
            # Continue with original image
        
        # Save processed file
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Save to database (update existing or create new)
        with Session(engine) as session:
            if existing_avatar:
                # Update existing avatar
                existing_avatar.upload_date = str(int(time.time()))
                existing_avatar.file_size = len(content)
                existing_avatar.avatar_group_id = avatar_group_id or existing_avatar.avatar_group_id
                session.add(existing_avatar)
                session.commit()
                session.refresh(existing_avatar)
                avatar = existing_avatar
            else:
                # Create new avatar
                avatar = AvatarImage(
                    name=avatar_name,
                    filename=unique_filename,
                    file_path=f"/user_avatars/{unique_filename}",
                    upload_date=str(int(time.time())),
                    file_size=len(content),
                    avatar_type=avatar_type,
                    avatar_group_id=avatar_group_id
                )
                session.add(avatar)
                session.commit()
                session.refresh(avatar)
        
        # Broadcast refresh message to all connected clients
        # Import here to avoid circular imports
        from app import hub
        asyncio.create_task(hub.broadcast({
            "type": "avatar_updated",
            "message": f"Avatar '{avatar.name}' uploaded"
        }))
        
        return {
            "success": True, 
            "avatar": {
                "id": avatar.id,
                "name": avatar.name,
                "filename": avatar.filename,
                "file_path": avatar.file_path,
                "file_size": avatar.file_size,
                "avatar_type": avatar.avatar_type,
                "avatar_group_id": avatar_group_id
            }
        }
    
    except Exception as e:
        return {"error": str(e), "success": False}

@router.get("/api/avatars/managed")
async def api_get_managed_avatars():
    """Get list of user-uploaded avatar images"""
    try:
        with Session(engine) as session:
            avatars = session.exec(select(AvatarImage)).all()
            return {
                "avatars": [
                    {
                        "id": avatar.id,
                        "name": avatar.name,
                        "filename": avatar.filename,
                        "file_path": avatar.file_path,
                        "file_size": avatar.file_size,
                        "upload_date": avatar.upload_date,
                        "avatar_type": avatar.avatar_type,
                        "avatar_group_id": avatar.avatar_group_id,
                        "voice_id": avatar.voice_id,
                        "spawn_position": avatar.spawn_position,
                        "disabled": avatar.disabled
                    }
                    for avatar in avatars
                ]
            }
    except Exception as e:
        return {"avatars": [], "error": str(e)}

@router.delete("/api/avatars/{avatar_id}")
async def api_delete_avatar(avatar_id: int):
    """Delete an uploaded avatar image"""
    try:
        with Session(engine) as session:
            avatar = session.get(AvatarImage, avatar_id)
            if not avatar:
                return {"error": "Avatar not found", "success": False}
            
            # Delete file from disk (user-uploaded avatars are in persistent directory)
            full_path = os.path.join(PERSISTENT_AVATARS_DIR, avatar.filename)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"🗑️  Deleted avatar file: {full_path}")
            
            # Delete from database
            session.delete(avatar)
            session.commit()
            
            # Broadcast refresh message to all connected clients
            from app import hub
            asyncio.create_task(hub.broadcast({
                "type": "avatar_updated",
                "message": "Avatar deleted"
            }))
            
            return {"success": True}
    
    except Exception as e:
        return {"error": str(e), "success": False}

@router.delete("/api/avatars/group/{group_id}")
async def api_delete_avatar_group(group_id: str):
    """Delete an entire avatar group (all avatars with the same group_id)"""
    try:
        with Session(engine) as session:
            # Find all avatars in the group
            if group_id.startswith('single_'):
                # Handle single avatars (group_id is like "single_123")
                avatar_id = int(group_id.replace('single_', ''))
                avatars = [session.get(AvatarImage, avatar_id)]
                if not avatars[0]:
                    return {"error": "Avatar not found", "success": False}
            else:
                # Handle grouped avatars
                avatars = session.exec(
                    select(AvatarImage).where(AvatarImage.avatar_group_id == group_id)
                ).all()
                
                if not avatars:
                    return {"error": "Avatar group not found", "success": False}
            
            # Delete files from disk and database
            for avatar in avatars:
                if avatar:  # Check in case of single avatar that might be None
                    full_path = os.path.join(PERSISTENT_AVATARS_DIR, avatar.filename)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        logger.info(f"🗑️  Deleted avatar file: {full_path}")
                    session.delete(avatar)
            
            session.commit()
            
            # Broadcast refresh message to all connected clients
            from app import hub
            asyncio.create_task(hub.broadcast({
                "type": "avatar_updated",
                "message": "Avatar group deleted"
            }))
            
            return {"success": True, "deleted_count": len([a for a in avatars if a])}
    
    except Exception as e:
        return {"error": str(e), "success": False}

@router.put("/api/avatars/group/{group_id}/position")
async def api_update_avatar_position(group_id: str, position_data: dict):
    """Update spawn position assignment for an avatar group"""
    try:
        spawn_position = position_data.get("spawn_position")  # None means random, 1-6 means specific slot
        
        with Session(engine) as session:
            # Find all avatars in the group
            if group_id.startswith('single_'):
                # Handle single avatars
                avatar_id = int(group_id.replace('single_', ''))
                avatars = [session.get(AvatarImage, avatar_id)]
                if not avatars[0]:
                    return {"error": "Avatar not found", "success": False}
            else:
                # Handle grouped avatars
                avatars = session.exec(
                    select(AvatarImage).where(AvatarImage.avatar_group_id == group_id)
                ).all()
                
                if not avatars:
                    return {"error": "Avatar group not found", "success": False}
            
            # Update spawn_position for all avatars in the group
            for avatar in avatars:
                if avatar:
                    avatar.spawn_position = spawn_position
                    session.add(avatar)
            
            session.commit()
            
            # Broadcast refresh message to all connected clients
            from app import hub
            asyncio.create_task(hub.broadcast({
                "type": "avatar_updated",
                "message": "Avatar spawn position updated"
            }))
            
            return {"success": True, "updated_count": len([a for a in avatars if a])}
    
    except Exception as e:
        return {"error": str(e), "success": False}

@router.put("/api/avatars/{avatar_id}/toggle-disabled")
async def api_toggle_avatar_disabled(avatar_id: int):
    """Toggle the disabled status of an avatar"""
    try:
        with Session(engine) as session:
            avatar = session.get(AvatarImage, avatar_id)
            if not avatar:
                return {"error": "Avatar not found", "success": False}
            
            # Toggle the disabled status
            avatar.disabled = not avatar.disabled
            session.add(avatar)
            session.commit()
            
            # Broadcast refresh message to all connected clients
            from app import hub
            asyncio.create_task(hub.broadcast({
                "type": "avatar_updated",
                "message": f"Avatar {'disabled' if avatar.disabled else 'enabled'}"
            }))
            
            return {
                "success": True,
                "avatar_id": avatar_id,
                "disabled": avatar.disabled,
                "message": f"Avatar {'disabled' if avatar.disabled else 'enabled'}"
            }
    
    except Exception as e:
        return {"error": str(e), "success": False}

@router.put("/api/avatars/group/{group_id}/toggle-disabled")
async def api_toggle_avatar_group_disabled(group_id: str):
    """Toggle the disabled status of an entire avatar group"""
    try:
        with Session(engine) as session:
            # Find all avatars in the group
            if group_id.startswith('single_'):
                # Handle single avatars (group_id is like "single_123")
                avatar_id = int(group_id.replace('single_', ''))
                avatars = [session.get(AvatarImage, avatar_id)]
                if not avatars[0]:
                    return {"error": "Avatar not found", "success": False}
            else:
                # Handle grouped avatars (pairs)
                avatars = session.exec(
                    select(AvatarImage).where(AvatarImage.avatar_group_id == group_id)
                ).all()
                
                if not avatars:
                    return {"error": "Avatar group not found", "success": False}
            
            # Check current disabled status - if any avatar is enabled, we disable all
            # If all are disabled, we enable all
            any_enabled = any(not avatar.disabled for avatar in avatars if avatar)
            new_disabled_status = any_enabled  # If any enabled, disable all; if all disabled, enable all
            
            # Update disabled status for all avatars in the group
            updated_count = 0
            for avatar in avatars:
                if avatar:
                    avatar.disabled = new_disabled_status
                    session.add(avatar)
                    updated_count += 1
            
            session.commit()
            
            # Broadcast refresh message to all connected clients
            from app import hub
            asyncio.create_task(hub.broadcast({
                "type": "avatar_updated",
                "message": f"Avatar group {'disabled' if new_disabled_status else 'enabled'}"
            }))
            
            return {
                "success": True,
                "group_id": group_id,
                "disabled": new_disabled_status,
                "updated_count": updated_count,
                "message": f"Avatar group {'disabled' if new_disabled_status else 'enabled'}"
            }
    
    except Exception as e:
        return {"error": str(e), "success": False}

@router.post("/api/avatars/re-randomize")
async def api_re_randomize_avatars():
    """Trigger avatar re-randomization on the Yappers page"""
    try:
        # Broadcast a message to all WebSocket clients to re-randomize avatars
        from app import hub
        asyncio.create_task(hub.broadcast({
            "type": "re_randomize_avatars",
            "message": "Avatar assignments re-randomized"
        }))
        
        logger.info("Avatar re-randomization triggered")
        return {"success": True, "message": "Avatar assignments will be re-randomized"}
    except Exception as e:
        logger.error(f"Avatar re-randomization failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}