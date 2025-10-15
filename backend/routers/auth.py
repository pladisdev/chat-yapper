"""
Authentication and Twitch OAuth router
"""
import asyncio
import secrets
import time
import urllib.parse
from typing import Dict, Any

import aiohttp
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from modules import logger

from modules.persistent_data import (
    get_settings, get_auth, delete_twitch_auth, save_twitch_auth, get_twitch_token,
    TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, TWITCH_REDIRECT_URI, TWITCH_SCOPE, oauth_states
)

router = APIRouter()

# Twitch OAuth Endpoints

@router.get("/auth/twitch")
async def twitch_auth_start():
    """Start Twitch OAuth flow"""
    # Check if Twitch credentials are configured
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        logger.warning("Twitch OAuth attempted but credentials not configured")
        return RedirectResponse(url="/settings?error=twitch_not_configured")
    
    # Generate a random state to prevent CSRF attacks
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {"timestamp": time.time()}
    
    # Build Twitch OAuth URL
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "redirect_uri": TWITCH_REDIRECT_URI,
        "response_type": "code",
        "scope": TWITCH_SCOPE,
        "state": state
    }
    
    auth_url = "https://id.twitch.tv/oauth2/authorize?" + urllib.parse.urlencode(params)
    logger.info(f"Starting Twitch OAuth flow with state: {state}")
    
    return RedirectResponse(url=auth_url)

@router.get("/auth/twitch/callback")
async def twitch_auth_callback(code: str = None, state: str = None, error: str = None):
    """Handle Twitch OAuth callback"""
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"Twitch OAuth error: {error}")
            return RedirectResponse(url="/?error=oauth_denied")
        
        if not code or not state:
            logger.error("Missing code or state in OAuth callback")
            return RedirectResponse(url="/?error=invalid_callback")
        
        # Verify state to prevent CSRF
        if state not in oauth_states:
            logger.error(f"Invalid OAuth state: {state}")
            return RedirectResponse(url="/?error=invalid_state")
        
        # Clean up used state
        del oauth_states[state]
        
        # Exchange code for access token
        token_data = await exchange_code_for_token(code)
        if not token_data:
            return RedirectResponse(url="/?error=token_exchange_failed")
        
        # Get user information
        user_info = await get_twitch_user_info(token_data["access_token"])
        if not user_info:
            return RedirectResponse(url="/?error=user_info_failed")
        
        # Store auth in database
        await store_twitch_auth(user_info, token_data)
        
        logger.info(f"Successfully connected Twitch account: {user_info['login']}")
        return RedirectResponse(url="/settings?twitch=connected")
        
    except Exception as e:
        logger.error(f"Error in Twitch OAuth callback: {e}", exc_info=True)
        return RedirectResponse(url="/?error=callback_error")

@router.get("/api/twitch/status")
async def twitch_auth_status():
    """Get current Twitch connection status"""
    try:
        auth = get_auth()
        if auth:
            return {
                "connected": True,
                "username": auth.username,
                "display_name": auth.display_name,
                "user_id": auth.twitch_user_id
            }
        return {"connected": False}
    except Exception as e:
        logger.error(f"Error checking Twitch status: {e}")
        return {"connected": False, "error": str(e)}

@router.delete("/api/twitch/disconnect")
async def twitch_disconnect():
    """Disconnect Twitch account"""
    try:
        result = delete_twitch_auth()
        if result["success"]:
            logger.info("Twitch account disconnected")
        return result
    except Exception as e:
        logger.error(f"Error disconnecting Twitch: {e}")
        return {"success": False, "error": str(e)}

@router.post("/api/twitch/test")
async def api_test_twitch():
    """Test Twitch connection manually using OAuth"""
    try:
        settings = get_settings()
        twitch_config = settings.get("twitch", {})
        
        if not twitch_config.get("enabled"):
            return {"success": False, "error": "Twitch not enabled in settings"}
        
        # Check OAuth token
        token_info = await get_twitch_token_for_bot()
        if not token_info:
            return {"success": False, "error": "No Twitch account connected. Please connect your account first."}
        
        channel = twitch_config.get("channel") or token_info["username"]
        if not channel:
            return {"success": False, "error": "No channel specified in settings"}
        
        # Import the restart function when needed to avoid circular imports
        from app import restart_twitch_if_needed
        
        # Force restart Twitch connection with OAuth
        await restart_twitch_if_needed(settings)
        
        return {"success": True, "message": f"Twitch connection test initiated for {token_info['username']} -> #{channel}"}
    except Exception as e:
        logger.error(f"Twitch test failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

# Helper functions for OAuth

async def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """Exchange OAuth code for access token"""
    try:
        data = {
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": TWITCH_REDIRECT_URI
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://id.twitch.tv/oauth2/token", data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("Successfully exchanged code for token")
                    return result
                else:
                    logger.error(f"Token exchange failed: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        return None

async def get_twitch_user_info(access_token: str) -> Dict[str, Any]:
    """Get user info from Twitch API"""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Client-Id": TWITCH_CLIENT_ID
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.twitch.tv/helix/users", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    users = result.get("data", [])
                    if users:
                        return users[0]
                    logger.error("No user data returned from Twitch API")
                    return None
                else:
                    logger.error(f"User info request failed: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return None

async def store_twitch_auth(user_info: Dict[str, Any], token_data: Dict[str, Any]):
    """Store Twitch auth in database"""
    try:
        save_twitch_auth(user_info, token_data)
    except Exception as e:
        logger.error(f"Error storing Twitch auth: {e}")
        raise

async def get_twitch_token_for_bot():
    """Get current Twitch token for bot connection"""
    try:
        return get_twitch_token()
    except Exception as e:
        logger.error(f"Error getting Twitch token: {e}")
    
    return None