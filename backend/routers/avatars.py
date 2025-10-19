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
from modules.persistent_data import (
    PUBLIC_DIR, PERSISTENT_AVATARS_DIR,
    delete_avatar, get_avatar, get_avatars, get_all_avatars, add_avatar, update_avatar,
    delete_avatar_group, update_avatar_group_position, toggle_avatar_group_disabled
)
from modules.models import AvatarImage
from modules import logger
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
        # Validate file type (accept PNG, JPG, JPEG, GIF, WebP)
        allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp']
        if not file.content_type or file.content_type not in allowed_types:
            logger.error(f"Invalid file type uploaded: {file.content_type}")
            return {"error": "File must be an image (PNG, JPG, GIF, or WebP)", "success": False}
        
        # Validate file size (max 5MB)
        if file.size and file.size > 5 * 1024 * 1024:
            return {"error": "File size must be less than 5MB", "success": False}
        
        # Check for existing avatar with same name and type for replacement
        existing_avatar = get_avatar(avatar_name, avatar_type)
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
        
        # Resize image if larger than 200px on any side (skip GIFs and animated WebP to preserve animation)
        is_animated_format = file.content_type in ['image/gif', 'image/webp']
        
        if not is_animated_format:
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
                    if format not in ['JPEG', 'PNG', 'WEBP']:
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
       
        if existing_avatar:
            # Update existing avatar
            existing_avatar.upload_date = str(int(time.time()))
            existing_avatar.file_size = len(content)
            existing_avatar.avatar_group_id = avatar_group_id or existing_avatar.avatar_group_id
            
            avatar = existing_avatar
            update_avatar(avatar)
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
            add_avatar(avatar)
        
        # Broadcast refresh message to all connected clients and regenerate slot assignments
        # Import here to avoid circular imports
        from app import hub, avatar_message_queue
        from modules.avatars import (generate_avatar_slot_assignments, get_active_avatar_slots,
                                     get_avatar_slot_assignments, get_avatar_assignments_generation_id)
        
        # Regenerate avatar slot assignments since available avatars changed
        get_active_avatar_slots().clear()
        avatar_message_queue.clear()
        generate_avatar_slot_assignments()
        
        # Broadcast avatar slots update to yappers page
        asyncio.create_task(hub.broadcast({
            "type": "avatar_slots_updated",
            "slots": get_avatar_slot_assignments(),
            "generationId": get_avatar_assignments_generation_id()
        }))
        
        # Also broadcast avatar update message for settings page
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
        avatars = get_all_avatars()      
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
        delete_avatar(avatar_id)
        
        # Broadcast refresh message and regenerate slot assignments
        from app import hub, avatar_message_queue
        from modules.avatars import (generate_avatar_slot_assignments, get_active_avatar_slots,
                                     get_avatar_slot_assignments, get_avatar_assignments_generation_id)
        
        # Regenerate avatar slot assignments since available avatars changed
        get_active_avatar_slots().clear()
        avatar_message_queue.clear()
        generate_avatar_slot_assignments()
        
        # Broadcast avatar slots update to yappers page
        asyncio.create_task(hub.broadcast({
            "type": "avatar_slots_updated",
            "slots": get_avatar_slot_assignments(),
            "generationId": get_avatar_assignments_generation_id()
        }))
        
        # Also broadcast avatar update message for settings page
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
        result = delete_avatar_group(group_id)
        from app import hub, avatar_message_queue
        from modules.avatars import (generate_avatar_slot_assignments, get_active_avatar_slots,
                                     get_avatar_slot_assignments, get_avatar_assignments_generation_id)
        get_active_avatar_slots().clear()
        avatar_message_queue.clear()
        generate_avatar_slot_assignments()
        # Broadcast avatar slots update to yappers page
        asyncio.create_task(hub.broadcast({
            "type": "avatar_slots_updated",
            "slots": get_avatar_slot_assignments(),
            "generationId": get_avatar_assignments_generation_id()
        }))
        # Also broadcast avatar update message for settings page
        asyncio.create_task(hub.broadcast({
            "type": "avatar_updated",
            "message": "Avatar group deleted"
        }))
        return result
    except Exception as e:
        return {"error": str(e), "success": False}

@router.put("/api/avatars/group/{group_id}/position")
async def api_update_avatar_position(group_id: str, position_data: dict):
    """Update spawn position assignment for an avatar group"""
    try:
        spawn_position = position_data.get("spawn_position")
        result = update_avatar_group_position(group_id, spawn_position)
        
        from app import hub, avatar_message_queue
        from modules.avatars import (generate_avatar_slot_assignments, get_active_avatar_slots,
                                     get_avatar_slot_assignments, get_avatar_assignments_generation_id)
        get_active_avatar_slots().clear()
        avatar_message_queue.clear()
        generate_avatar_slot_assignments()
        # Broadcast avatar slots update to yappers page
        asyncio.create_task(hub.broadcast({
            "type": "avatar_slots_updated",
            "slots": get_avatar_slot_assignments(),
            "generationId": get_avatar_assignments_generation_id()
        }))
        # Also broadcast avatar update message for settings page
        asyncio.create_task(hub.broadcast({
            "type": "avatar_updated",
            "message": "Avatar spawn position updated"
        }))
        return result
    except Exception as e:
        return {"error": str(e), "success": False}

@router.put("/api/avatars/group/{group_id}/toggle-disabled")
async def api_toggle_avatar_group_disabled(group_id: str):
    """Toggle the disabled status of an entire avatar group"""
    try:
        result = toggle_avatar_group_disabled(group_id)
        from app import hub, avatar_message_queue
        from modules.avatars import (generate_avatar_slot_assignments, get_active_avatar_slots,
                                     get_avatar_slot_assignments, get_avatar_assignments_generation_id)
        get_active_avatar_slots().clear()
        avatar_message_queue.clear()
        generate_avatar_slot_assignments()
        # Broadcast avatar slots update to yappers page
        asyncio.create_task(hub.broadcast({
            "type": "avatar_slots_updated",
            "slots": get_avatar_slot_assignments(),
            "generationId": get_avatar_assignments_generation_id()
        }))
        # Also broadcast avatar update message for settings page
        asyncio.create_task(hub.broadcast({
            "type": "avatar_updated",
            "message": f"Avatar group {'disabled' if result.get('disabled') else 'enabled'}"
        }))
        return result
    except Exception as e:
        return {"error": str(e), "success": False}

@router.post("/api/avatars/re-randomize")
@router.post("/api/avatar-slots/regenerate")
async def api_regenerate_avatar_slots():
    """Force regeneration of avatar slot assignments (re-randomize avatars)"""
    try:
        from app import hub, avatar_message_queue
        from modules.avatars import (generate_avatar_slot_assignments, get_active_avatar_slots,
                                     get_avatar_slot_assignments, get_avatar_assignments_generation_id)
        
        # Clear any active slots to avoid conflicts
        get_active_avatar_slots().clear()
        avatar_message_queue.clear()
        
        # Regenerate assignments
        generate_avatar_slot_assignments()
        
        # Broadcast to all clients to update their assignments
        await hub.broadcast({
            "type": "avatar_slots_updated",
            "slots": get_avatar_slot_assignments(),
            "generationId": get_avatar_assignments_generation_id()
        })
        
        logger.info(f"Avatar slots regenerated (generation #{get_avatar_assignments_generation_id()})")
        
        return {
            "success": True,
            "slots": get_avatar_slot_assignments(),
            "generationId": get_avatar_assignments_generation_id(),
            "message": "Avatar slots regenerated"
        }
    except Exception as e:
        logger.error(f"Failed to regenerate avatar slots: {e}")
        return {"success": False, "error": str(e)}

@router.post("/api/avatar-slots/{slot_id}/release")
async def api_release_avatar_slot(slot_id: str):
    """Manually release an avatar slot (for debugging/management)"""
    try:
        from modules.avatars import release_avatar_slot, get_active_avatar_slots
        
        active_avatar_slots = get_active_avatar_slots()
        if slot_id in active_avatar_slots:
            user = active_avatar_slots[slot_id]["user"]
            release_avatar_slot(slot_id)
            return {
                "success": True,
                "message": f"Released slot {slot_id} (was used by {user})"
            }
        else:
            return {
                "success": False,
                "message": f"Slot {slot_id} was not active"
            }
    except Exception as e:
        logger.error(f"Failed to release slot {slot_id}: {e}")
        return {"success": False, "error": str(e)}

@router.get("/api/avatar-slots/queue")
async def api_get_avatar_queue():
    """Get current avatar message queue status"""
    try:
        from app import avatar_message_queue
        from modules.avatars import get_active_avatar_slots, get_avatar_slot_assignments
        
        active_avatar_slots = get_active_avatar_slots()
        avatar_slot_assignments = get_avatar_slot_assignments()
        
        queue_info = []
        for i, item in enumerate(avatar_message_queue):
            queue_info.append({
                "position": i + 1,
                "user": item["message_data"].get("user", "unknown"),
                "text": item["message_data"].get("text", "")[:50] + "..." if len(item["message_data"].get("text", "")) > 50 else item["message_data"].get("text", ""),
                "queued_time": item["queued_time"],
                "wait_time": time.time() - item["queued_time"]
            })
        
        return {
            "queue": queue_info,
            "length": len(avatar_message_queue),
            "active_slots": len(active_avatar_slots),
            "total_slots": len(avatar_slot_assignments)
        }
    except Exception as e:
        logger.error(f"Failed to get avatar queue: {e}")
        return {"queue": [], "length": 0, "active_slots": 0, "total_slots": 0}