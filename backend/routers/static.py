"""
Static file serving and frontend routing
"""
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from modules import logger

from modules.persistent_data import PUBLIC_DIR, PERSISTENT_AVATARS_DIR

router = APIRouter()

@router.get("/favicon.ico")
async def favicon():
    """Serve the favicon.ico file"""
    favicon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    else:
        # Return a 204 No Content if favicon doesn't exist
        return Response(status_code=204)

# Assets endpoint (needs to be defined as a route)
if os.path.isdir(PUBLIC_DIR):
    assets_dir = os.path.join(PUBLIC_DIR, "assets")
    if os.path.isdir(assets_dir):
        @router.get("/assets/{filename}")
        async def serve_assets(filename: str):
            """Serve assets with correct MIME types"""
            file_path = os.path.join(assets_dir, filename)
            logger.info(f"Assets request: {filename} -> {file_path}")
            
            if not os.path.isfile(file_path):
                logger.info(f"Asset file not found: {file_path}")
                raise HTTPException(status_code=404, detail="Asset not found")
            
            # Determine MIME type based on file extension
            media_type = None
            if filename.endswith('.js'):
                media_type = 'application/javascript'
                logger.info(f"Setting JavaScript MIME type for: {filename}")
            elif filename.endswith('.css'):
                media_type = 'text/css'
                logger.info(f"Setting CSS MIME type for: {filename}")
            elif filename.endswith('.map'):
                media_type = 'application/json'
            
            logger.info(f"Serving asset: {filename} with MIME type: {media_type}")
            return FileResponse(file_path, media_type=media_type)

    # Handle specific routes for SPA
    @router.get("/settings")
    async def serve_settings():
        """Serve settings page"""
        index_path = os.path.join(PUBLIC_DIR, "index.html")
        return FileResponse(index_path, media_type='text/html')
    
    @router.get("/yappers")
    async def serve_yappers():
        """Serve yappers page"""
        index_path = os.path.join(PUBLIC_DIR, "index.html")
        return FileResponse(index_path, media_type='text/html')
    
    # Handle vite.svg specifically
    @router.get("/vite.svg")
    async def serve_vite_svg():
        """Serve vite.svg placeholder"""
        svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="m9 12 2 2 4-4"/>
        </svg>'''
        return Response(content=svg_content, media_type="image/svg+xml")
    
    # Handle root path
    @router.get("/")
    async def serve_root():
        """Serve root page"""
        index_path = os.path.join(PUBLIC_DIR, "index.html")
        return FileResponse(index_path, media_type='text/html')

def mount_static_files(app):
    """Mount static file directories after all routes are defined"""
    if os.path.isdir(PUBLIC_DIR):
        logger.info(f"Mounting static files from: {PUBLIC_DIR}")
        
        # Mount built-in voice avatars
        voice_avatars_dir = os.path.join(PUBLIC_DIR, "voice_avatars")
        if os.path.isdir(voice_avatars_dir):
            logger.info(f"Mounting /voice_avatars from: {voice_avatars_dir}")
            app.mount("/voice_avatars", StaticFiles(directory=voice_avatars_dir), name="voice_avatars")
        else:
            logger.info(f"Built-in voice avatars directory not found: {voice_avatars_dir}")
        
        # Mount user-uploaded avatars from persistent directory
        if os.path.isdir(PERSISTENT_AVATARS_DIR):
            logger.info(f"Mounting /user_avatars from: {PERSISTENT_AVATARS_DIR}")
            app.mount("/user_avatars", StaticFiles(directory=PERSISTENT_AVATARS_DIR), name="user_avatars")
        else:
            logger.info(f"User avatars directory not found: {PERSISTENT_AVATARS_DIR}")
    else:
        logger.info(f"Static files directory not found: {PUBLIC_DIR}")