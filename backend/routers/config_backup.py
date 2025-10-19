"""
Configuration Export/Import Router
Handles exporting and importing full application configuration including avatars
"""
import asyncio
import io
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from modules import logger
from modules.persistent_data import (
    get_settings, save_settings, get_all_avatars, get_voices,
    add_avatar, add_voice, PERSISTENT_AVATARS_DIR, DB_PATH
)
from modules.models import AvatarImage, Voice

router = APIRouter()

EXPORT_VERSION = "1.0"


@router.get("/api/config/export")
async def export_config():
    """
    Export complete application configuration as a ZIP file.
    Includes settings, voices, avatar metadata, and avatar image files.
    """
    try:
        logger.info("Starting configuration export...")
        
        # Gather all configuration data
        settings = get_settings()
        voices_data = get_voices()
        avatars = get_all_avatars()
        
        # Build export data structure
        export_data = {
            "version": EXPORT_VERSION,
            "exported_at": datetime.now().isoformat(),
            "app_name": "Chat Yapper",
            "settings": settings,
            "voices": [
                {
                    "name": v.name,
                    "voice_id": v.voice_id,
                    "provider": v.provider,
                    "enabled": v.enabled,
                    "avatar_image": v.avatar_image,
                    "avatar_default": v.avatar_default,
                    "avatar_speaking": v.avatar_speaking,
                    "avatar_mode": v.avatar_mode,
                    "created_at": v.created_at
                }
                for v in voices_data.get("voices", []) if isinstance(v, dict)
            ] if voices_data else [],
            "avatars": [
                {
                    "name": a.name,
                    "filename": a.filename,
                    "avatar_type": a.avatar_type,
                    "avatar_group_id": a.avatar_group_id,
                    "voice_id": a.voice_id,
                    "spawn_position": a.spawn_position,
                    "disabled": a.disabled,
                    "upload_date": a.upload_date,
                    "file_size": a.file_size
                }
                for a in avatars
            ]
        }
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add config.json
            config_json = json.dumps(export_data, indent=2)
            zip_file.writestr("config.json", config_json)
            logger.info(f"✓ Added config.json to export")
            
            # Add avatar image files
            avatars_added = 0
            for avatar in avatars:
                avatar_path = os.path.join(PERSISTENT_AVATARS_DIR, avatar.filename)
                if os.path.exists(avatar_path):
                    # Add to avatars/ folder in ZIP
                    zip_file.write(avatar_path, f"avatars/{avatar.filename}")
                    avatars_added += 1
                else:
                    logger.warning(f"Avatar file not found: {avatar.filename}")
            
            logger.info(f"✓ Added {avatars_added} avatar images to export")
        
        # Prepare download
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"chatyapper_config_{timestamp}.zip"
        
        logger.info(f"Export complete: {filename} ({len(zip_buffer.getvalue())} bytes)")
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/api/config/import")
async def import_config(
    file: UploadFile = File(...),
    merge_mode: str = "replace"  # "replace" or "merge"
):
    """
    Import application configuration from a ZIP file.
    
    Args:
        file: ZIP file containing config.json and avatars/ folder
        merge_mode: "replace" (clear existing) or "merge" (add to existing)
    """
    try:
        logger.info(f"Starting configuration import (mode: {merge_mode})...")
        
        # Validate file type
        if not file.filename or not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="File must be a ZIP archive")
        
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            zip_path = os.path.join(temp_dir, "upload.zip")
            content = await file.read()
            with open(zip_path, "wb") as f:
                f.write(content)
            
            logger.info(f"Uploaded file size: {len(content)} bytes")
            
            # Extract ZIP
            extract_dir = os.path.join(temp_dir, "extracted")
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                zip_file.extractall(extract_dir)
            
            # Read config.json
            config_path = os.path.join(extract_dir, "config.json")
            if not os.path.exists(config_path):
                raise HTTPException(status_code=400, detail="Invalid export: config.json not found")
            
            with open(config_path, 'r') as f:
                import_data = json.load(f)
            
            # Validate version
            if import_data.get("version") != EXPORT_VERSION:
                logger.warning(f"Version mismatch: expected {EXPORT_VERSION}, got {import_data.get('version')}")
            
            # Backup current database before import
            backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(DB_PATH, backup_path)
            logger.info(f"Created backup: {backup_path}")
            
            stats = {
                "settings_imported": False,
                "voices_imported": 0,
                "avatars_imported": 0,
                "images_copied": 0,
                "errors": []
            }
            
            try:
                # Import settings
                if "settings" in import_data:
                    save_settings(import_data["settings"])
                    stats["settings_imported"] = True
                    logger.info("Settings imported")
                
                # Import voices
                if "voices" in import_data and merge_mode == "replace":
                    # In replace mode, we'd need to clear existing voices
                    # For now, just add new ones (merge behavior)
                    pass
                
                if "voices" in import_data:
                    for voice_data in import_data["voices"]:
                        try:
                            # Check if voice already exists
                            from modules.persistent_data import check_voice_exists
                            
                            if not check_voice_exists(voice_data["voice_id"], voice_data["provider"]):
                                new_voice = Voice(
                                    name=voice_data["name"],
                                    voice_id=voice_data["voice_id"],
                                    provider=voice_data["provider"],
                                    enabled=voice_data.get("enabled", True),
                                    avatar_image=voice_data.get("avatar_image"),
                                    avatar_default=voice_data.get("avatar_default"),
                                    avatar_speaking=voice_data.get("avatar_speaking"),
                                    avatar_mode=voice_data.get("avatar_mode", "single"),
                                    created_at=voice_data.get("created_at")
                                )
                                add_voice(new_voice)
                                stats["voices_imported"] += 1
                        except Exception as e:
                            error_msg = f"Failed to import voice {voice_data.get('name')}: {str(e)}"
                            stats["errors"].append(error_msg)
                            logger.warning(error_msg)
                    
                    logger.info(f"Imported {stats['voices_imported']} voices")
                
                # Import avatars and their image files
                avatars_dir = os.path.join(extract_dir, "avatars")
                
                if "avatars" in import_data and os.path.exists(avatars_dir):
                    for avatar_data in import_data["avatars"]:
                        try:
                            filename = avatar_data["filename"]
                            source_path = os.path.join(avatars_dir, filename)
                            
                            if not os.path.exists(source_path):
                                stats["errors"].append(f"Avatar image not found: {filename}")
                                continue
                            
                            # Copy image file to persistent directory
                            dest_path = os.path.join(PERSISTENT_AVATARS_DIR, filename)
                            shutil.copy2(source_path, dest_path)
                            stats["images_copied"] += 1
                            
                            # Check if avatar already exists
                            from modules.persistent_data import get_avatar
                            existing = get_avatar(avatar_data["name"], avatar_data["avatar_type"])
                            
                            if not existing or merge_mode == "replace":
                                # Add avatar to database
                                new_avatar = AvatarImage(
                                    name=avatar_data["name"],
                                    filename=filename,
                                    file_path=f"/user_avatars/{filename}",
                                    avatar_type=avatar_data.get("avatar_type", "default"),
                                    avatar_group_id=avatar_data.get("avatar_group_id"),
                                    voice_id=avatar_data.get("voice_id"),
                                    spawn_position=avatar_data.get("spawn_position"),
                                    disabled=avatar_data.get("disabled", False),
                                    upload_date=avatar_data.get("upload_date"),
                                    file_size=avatar_data.get("file_size")
                                )
                                add_avatar(new_avatar)
                                stats["avatars_imported"] += 1
                                
                        except Exception as e:
                            error_msg = f"Failed to import avatar {avatar_data.get('name')}: {str(e)}"
                            stats["errors"].append(error_msg)
                            logger.warning(error_msg)
                    
                    logger.info(f"Imported {stats['avatars_imported']} avatars, copied {stats['images_copied']} images")
                
                # Regenerate avatar slot assignments
                from app import hub, avatar_message_queue
                from modules.avatars import (
                    generate_avatar_slot_assignments, get_active_avatar_slots,
                    get_avatar_slot_assignments, get_avatar_assignments_generation_id
                )
                
                get_active_avatar_slots().clear()
                avatar_message_queue.clear()
                generate_avatar_slot_assignments()
                
                # Broadcast updates
                asyncio.create_task(hub.broadcast({
                    "type": "settings_updated",
                    "settings": import_data.get("settings", {})
                }))
                
                asyncio.create_task(hub.broadcast({
                    "type": "avatar_slots_updated",
                    "slots": get_avatar_slot_assignments(),
                    "generationId": get_avatar_assignments_generation_id()
                }))
                
                logger.info(f"Import complete: {stats}")
                
                return {
                    "success": True,
                    "message": "Configuration imported successfully",
                    "stats": stats,
                    "backup_path": backup_path
                }
                
            except Exception as e:
                # Restore backup on error
                logger.error(f"Import failed, restoring backup: {e}")
                shutil.copy2(backup_path, DB_PATH)
                raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/api/config/info")
async def get_config_info():
    """Get basic information about current configuration (for UI display)"""
    try:
        settings = get_settings()
        voices_data = get_voices()
        avatars = get_all_avatars()
        
        # Calculate avatar storage size
        total_avatar_size = 0
        for avatar in avatars:
            avatar_path = os.path.join(PERSISTENT_AVATARS_DIR, avatar.filename)
            if os.path.exists(avatar_path):
                total_avatar_size += os.path.getsize(avatar_path)
        
        return {
            "success": True,
            "info": {
                "settings_count": len(settings) if settings else 0,
                "voices_count": len(voices_data.get("voices", [])) if voices_data else 0,
                "avatars_count": len(avatars),
                "avatar_storage_mb": round(total_avatar_size / (1024 * 1024), 2),
                "database_path": DB_PATH,
                "avatars_path": PERSISTENT_AVATARS_DIR
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get config info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
