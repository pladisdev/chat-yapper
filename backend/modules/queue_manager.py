"""
Queue management for TTS messages and avatar slots.
Handles both avatar slot queuing and parallel message queuing.
"""
import asyncio
import os
import time
from typing import Dict, Any

from modules import logger
from modules.persistent_data import AUDIO_DIR
from modules.tts import get_audio_duration
from modules.avatars import (
    reserve_avatar_slot,
    find_available_slot_for_tts,
    release_avatar_slot,
    get_avatar_assignments_generation_id
)

# Global queue state
avatar_message_queue = []  # Queue for messages when all avatar slots are busy
parallel_message_queue = []  # Queue for messages when parallel limit is reached


def queue_avatar_message(message_data: Dict[str, Any]):
    """Add a message to the avatar queue when all slots are busy"""
    global avatar_message_queue
    
    avatar_message_queue.append({
        "message_data": message_data,
        "queued_time": time.time()
    })
    logger.info(f"Queued message for {message_data.get('user')} (queue length: {len(avatar_message_queue)})")


def queue_parallel_message(message_data: Dict[str, Any]):
    """Add a message to the parallel queue when limit is reached"""
    global parallel_message_queue
    
    parallel_message_queue.append({
        "message_data": message_data,
        "queued_time": time.time()
    })
    logger.info(f"Queued message for {message_data.get('user')} (parallel queue length: {len(parallel_message_queue)})")


def process_parallel_message_queue(app_get_settings_func, process_tts_message_func, 
                                   active_tts_jobs: Dict[str, Any], 
                                   total_active_tts_count: int,
                                   increment_tts_count_func, 
                                   decrement_tts_count_func):
    """
    Process queued messages if parallel slots become available.
    
    Args:
        app_get_settings_func: Function to get current settings
        process_tts_message_func: Async function to process TTS message
        active_tts_jobs: Dict of currently active TTS jobs
        total_active_tts_count: Current count of active TTS jobs
        increment_tts_count_func: Function to increment TTS count
        decrement_tts_count_func: Function to decrement TTS count
    """
    global parallel_message_queue
    
    if not parallel_message_queue:
        return
    
    settings = app_get_settings_func()
    parallel_limit = settings.get("parallelMessageLimit", 5)
    
    # Check if we're under the limit now (or if there's no limit)
    if parallel_limit is None or not isinstance(parallel_limit, (int, float)) or parallel_limit <= 0 or total_active_tts_count < parallel_limit:
        # Try to process the oldest queued message
        queued_item = parallel_message_queue[0]
        message_data = queued_item["message_data"]
        
        # Check if message is too old (ignore messages older than 120 seconds)
        if time.time() - queued_item["queued_time"] > 120:
            parallel_message_queue.pop(0)
            logger.info(f"Discarded old queued parallel message for {message_data.get('user')}")
            # Try to process next message
            if parallel_message_queue:
                process_parallel_message_queue(
                    app_get_settings_func, 
                    process_tts_message_func,
                    active_tts_jobs,
                    total_active_tts_count,
                    increment_tts_count_func,
                    decrement_tts_count_func
                )
            return
        
        # Remove from queue and process
        parallel_message_queue.pop(0)
        
        # Reserve the slot by incrementing counter (check if replacing existing job)
        username = message_data.get('user', 'unknown')
        username_lower = username.lower()
        replacing_existing = username_lower in active_tts_jobs
        
        if not replacing_existing:
            increment_tts_count_func()
        
        limit_text = "unlimited" if not parallel_limit or not isinstance(parallel_limit, (int, float)) or parallel_limit <= 0 else str(int(parallel_limit))
        logger.info(f"Processing queued parallel message for {username} (active: {total_active_tts_count}/{limit_text}, replacing={replacing_existing})")
        
        # Process the queued message
        async def process_queued():
            try:
                await process_tts_message_func(message_data)
            except Exception as e:
                # If processing fails, we need to decrement the counter
                if not replacing_existing:
                    decrement_tts_count_func()
                logger.error(f"Failed to process queued TTS message for {username}: {e}")
        
        asyncio.create_task(process_queued())


def process_avatar_message_queue(process_queued_tts_message_func):
    """
    Process queued messages if avatar slots become available.
    
    Args:
        process_queued_tts_message_func: Async function to process queued TTS message
    """
    global avatar_message_queue
    
    if not avatar_message_queue:
        return
    
    # Try to process the oldest queued message
    queued_item = avatar_message_queue[0]
    message_data = queued_item["message_data"]
    
    # Check if message is too old (ignore messages older than 60 seconds)
    if time.time() - queued_item["queued_time"] > 60:
        avatar_message_queue.pop(0)
        logger.info(f"Discarded old queued message for {message_data.get('user')}")
        # Try to process next message
        if avatar_message_queue:
            process_avatar_message_queue(process_queued_tts_message_func)
        return
    
    # Try to find an available slot
    voice_id = message_data.get("voice", {}).get("id") if message_data.get("voice") else None
    available_slot = find_available_slot_for_tts(voice_id, message_data.get("user"))
    
    if available_slot:
        # Remove from queue and process
        avatar_message_queue.pop(0)
        logger.info(f"Processing queued message for {message_data.get('user')} in slot {available_slot['id']}")
        
        # Process the queued TTS message
        asyncio.create_task(process_queued_tts_message_func(message_data, available_slot))


async def process_queued_tts_message(message_data: Dict[str, Any], target_slot: Dict[str, Any], 
                                     hub, process_avatar_message_queue_func):
    """
    Process a TTS message that was queued due to all slots being busy.
    
    Args:
        message_data: The message data to process
        target_slot: The avatar slot to use
        hub: WebSocket hub for broadcasting
        process_avatar_message_queue_func: Function to process avatar queue on error
    """
    try:
        # Reserve the slot
        audio_url = message_data.get("audioUrl", "")
        user = message_data.get("user", "")
        
        # Try to get audio duration from the file
        audio_duration = None
        if audio_url:
            audio_filename = os.path.basename(audio_url)
            audio_path = os.path.join(AUDIO_DIR, audio_filename)
            if os.path.exists(audio_path):
                audio_duration = get_audio_duration(audio_path)
        
        reserve_avatar_slot(target_slot["id"], user, audio_url, audio_duration)
        
        # Add slot information to the message
        enriched_message = message_data.copy()
        enriched_message.update({
            "targetSlot": {
                "id": target_slot["id"],
                "x_position": target_slot.get("x_position", 50),
                "y_position": target_slot.get("y_position", 50),
                "size": target_slot.get("size", 100)
            },
            "avatarData": target_slot["avatarData"],
            "generationId": get_avatar_assignments_generation_id()
        })
        
        # Broadcast to clients
        await hub.broadcast(enriched_message)
        logger.info(f"Broadcasted queued TTS for {user} in slot {target_slot['id']}")
        
    except Exception as e:
        logger.error(f"Failed to process queued TTS message: {e}")
        # Release the slot on error
        release_avatar_slot(target_slot["id"])
        process_avatar_message_queue_func()


def get_avatar_queue_length() -> int:
    """Get the current length of the avatar message queue"""
    return len(avatar_message_queue)


def get_parallel_queue_length() -> int:
    """Get the current length of the parallel message queue"""
    return len(parallel_message_queue)


def clear_all_queues():
    """Clear both avatar and parallel message queues"""
    global avatar_message_queue, parallel_message_queue
    avatar_message_queue.clear()
    parallel_message_queue.clear()
    logger.info("Cleared all message queues")
