
import random
import time

from modules import logger
from modules.persistent_data import get_avatars
from modules.persistent_data import get_settings

avatar_slot_assignments = []  # List of slot objects with avatar assignments
active_avatar_slots = {}  # slot_id -> {"user": str, "start_time": float, "audio_url": str, "audio_duration": float}

avatar_assignments_generation_id = 0  # Increments when assignments are regenerated

def get_max_avatar_positions():
    """Calculate the maximum number of avatar positions from settings"""
    settings = get_settings()
    avatar_rows = settings.get("avatarRows", 2)
    avatar_row_config = settings.get("avatarRowConfig", [6, 6])
    # Sum up avatars across all configured rows
    max_positions = sum(avatar_row_config[:avatar_rows])
    return max_positions

def get_available_avatars():
    """Get all enabled avatar configurations from database"""
    from modules.models import AvatarImage
    
    try:
        
            # Get all enabled avatars from database
        avatars = get_avatars()
        
        if not avatars:
            # Fallback to default avatars if no managed avatars
            return [
                {
                    "name": "Default Avatar 1",
                    "defaultImage": "/voice_avatars/ava.png",
                    "speakingImage": "/voice_avatars/ava.png",
                    "isSingleImage": True,
                    "spawn_position": None,
                    "voice_id": None
                },
                {
                    "name": "Default Avatar 2", 
                    "defaultImage": "/voice_avatars/liam.png",
                    "speakingImage": "/voice_avatars/liam.png",
                    "isSingleImage": True,
                    "spawn_position": None,
                    "voice_id": None
                }
            ]
        
        # Group avatars by avatar_group_id or create single groups
        grouped = {}
        for avatar in avatars:
            key = avatar.avatar_group_id or f"single_{avatar.id}"
            if key not in grouped:
                grouped[key] = {
                    "name": avatar.name,
                    "images": {},
                    "spawn_position": avatar.spawn_position,
                    "voice_id": avatar.voice_id
                }
            else:
                # Update spawn_position and voice_id if not null
                if avatar.spawn_position is not None:
                    grouped[key]["spawn_position"] = avatar.spawn_position
                if avatar.voice_id is not None:
                    grouped[key]["voice_id"] = avatar.voice_id
            
            # Ensure file path is properly formatted for frontend access
            file_path = avatar.file_path
            if not file_path.startswith('http') and not file_path.startswith('/'):
                file_path = f"/{file_path}"
            grouped[key]["images"][avatar.avatar_type] = file_path
        
        # Convert to avatar objects
        avatar_groups = []
        for group in grouped.values():
            avatar_groups.append({
                "name": group["name"],
                "defaultImage": group["images"].get("default", group["images"].get("speaking", "/voice_avatars/ava.png")),
                "speakingImage": group["images"].get("speaking", group["images"].get("default", "/voice_avatars/ava.png")),
                "isSingleImage": not group["images"].get("speaking") or not group["images"].get("default") or group["images"].get("speaking") == group["images"].get("default"),
                "spawn_position": group["spawn_position"],  # None = random, number = specific slot
                "voice_id": group["voice_id"]  # None = random voice
            })
        
        return avatar_groups
            
    except Exception as e:
        logger.error(f"Failed to load avatars: {e}")
        # Return default avatars on error
        return [
            {
                "name": "Default Avatar 1",
                "defaultImage": "/voice_avatars/ava.png",
                "speakingImage": "/voice_avatars/ava.png", 
                "isSingleImage": True,
                "spawn_position": None,
                "voice_id": None
            }
        ]

def generate_avatar_slot_assignments():
    """Generate randomized avatar assignments for all slots based on settings"""
    global avatar_slot_assignments, avatar_assignments_generation_id
    
    settings = get_settings()
    avatar_rows = settings.get("avatarRows", 2)
    avatar_row_config = settings.get("avatarRowConfig", [6, 6])
    
    # Debug logging for settings
    logger.info(f"🔧 Avatar settings from backend: avatarRows={avatar_rows}, avatarRowConfig={avatar_row_config}")
    
    available_avatars = get_available_avatars()
    if not available_avatars:
        logger.warning("No avatars available for assignment")
        avatar_slot_assignments = []
        return
    
    total_slots = sum(avatar_row_config[:avatar_rows])
    logger.info(f"🎭 Generating avatar assignments for {total_slots} slots with {len(available_avatars)} avatars")
    logger.info(f"📸 Available avatars: {[{'name': a['name'], 'defaultImage': a['defaultImage'][:50] + '...' if len(a['defaultImage']) > 50 else a['defaultImage']} for a in available_avatars]}")
    
    assignments = []
    
    # Handle avatars with specific spawn positions first
    slot_index = 0
    slots = []
    
    # Create all slots first
    for row_index in range(avatar_rows):
        avatars_in_row = avatar_row_config[row_index] if row_index < len(avatar_row_config) else 6
        logger.debug(f"🔧 Creating row {row_index} with {avatars_in_row} avatars")
        for col_index in range(avatars_in_row):
            slots.append({
                "id": f"slot_{slot_index}",
                "row": row_index,
                "col": col_index,
                "totalInRow": avatars_in_row,
                "avatarData": None,  # Will be assigned
                "isActive": False
            })
            slot_index += 1
    
    logger.info(f"🔧 Total slots created: {len(slots)}")
    
    # First pass: Handle avatars with specific spawn positions
    assigned_slots = set()
    for avatar in available_avatars:
        if avatar["spawn_position"] is not None:
            spawn_pos = avatar["spawn_position"] - 1  # Convert to 0-based index
            if 0 <= spawn_pos < len(slots) and spawn_pos not in assigned_slots:
                slots[spawn_pos]["avatarData"] = avatar.copy()
                assigned_slots.add(spawn_pos)
                logger.info(f"🎯 Assigned {avatar['name']} to specific position {spawn_pos + 1}")
    
    # Second pass: Randomly assign remaining avatars to unassigned slots
    unassigned_slots = [i for i in range(len(slots)) if i not in assigned_slots]
    
    # Create assignment pool - ensure each avatar appears at least once if we have enough slots
    assignment_pool = []
    if len(unassigned_slots) >= len(available_avatars):
        # Add each avatar at least once
        assignment_pool.extend(available_avatars)
        # Fill remaining with random avatars
        remaining = len(unassigned_slots) - len(available_avatars)
        for _ in range(remaining):
            assignment_pool.append(random.choice(available_avatars))
    else:
        # More avatars than slots, randomly select
        for _ in range(len(unassigned_slots)):
            assignment_pool.append(random.choice(available_avatars))
    
    # Shuffle the assignment pool
    random.shuffle(assignment_pool)
    
    # Assign to unassigned slots
    for i, slot_idx in enumerate(unassigned_slots):
        if i < len(assignment_pool):
            slots[slot_idx]["avatarData"] = assignment_pool[i].copy()
            logger.info(f"🎲 Randomly assigned {assignment_pool[i]['name']} to slot {slot_idx}")
    
    avatar_slot_assignments = slots
    avatar_assignments_generation_id += 1
    
    logger.info(f"✅ Generated {len(avatar_slot_assignments)} avatar slot assignments (gen #{avatar_assignments_generation_id})")
    
    # Log a sample of what will be sent to frontend for debugging
    if avatar_slot_assignments:
        sample_slot = avatar_slot_assignments[0]
        logger.info(f"📤 Sample slot data being sent to frontend: {sample_slot}")

    return avatar_slot_assignments

def find_available_slot_for_tts(voice_id=None, user=None):
    """Find the best available slot for TTS based on voice matching and availability"""
    global active_avatar_slots
    
    if not avatar_slot_assignments:
        logger.warning("No avatar slot assignments available")
        return None
    
    # Get current timestamp for cleanup
    current_time = time.time()
    
    # Clean up expired active slots (safety mechanism in case frontend doesn't report end)
    expired_slots = []
    for slot_id, slot_info in active_avatar_slots.items():
        # Use audio duration + 5 second buffer, or fallback to 30 seconds if duration unknown
        audio_duration = slot_info.get("audio_duration", 30)
        expiry_time = audio_duration + 5  # Add 5 second buffer for network/processing delays
        if current_time - slot_info.get("start_time", 0) > expiry_time:
            expired_slots.append(slot_id)
            logger.info(f"🕐 Slot {slot_id} expired after {expiry_time}s (audio: {audio_duration}s + 5s buffer)")
    
    for slot_id in expired_slots:
        logger.info(f"🧹 Cleaning up expired active slot: {slot_id}")
        del active_avatar_slots[slot_id]
    
    # Find slots that match the voice_id if specified
    matching_slots = []
    available_slots = []
    
    for slot in avatar_slot_assignments:
        slot_id = slot["id"]
        avatar_data = slot["avatarData"]
        
        is_active = slot_id in active_avatar_slots
        
        if not is_active:
            available_slots.append(slot)
            
            # Check if this avatar matches the voice_id
            if voice_id and avatar_data and avatar_data.get("voice_id") == voice_id:
                matching_slots.append(slot)
    
    # Prefer voice-matched slots if available
    if matching_slots:
        selected_slot = random.choice(matching_slots)
        logger.info(f"🎯 Selected voice-matched slot {selected_slot['id']} for voice {voice_id}")
        return selected_slot
    
    # Use any available slot
    if available_slots:
        selected_slot = random.choice(available_slots)
        logger.info(f"🎲 Selected random available slot {selected_slot['id']} (no voice match)")
        return selected_slot
    
    # No available slots
    logger.info("⏳ All avatar slots are busy, message will be queued")
    return None

def reserve_avatar_slot(slot_id, user, audio_url, audio_duration=None):
    """Reserve an avatar slot for TTS playback"""
    global active_avatar_slots
    
    active_avatar_slots[slot_id] = {
        "user": user,
        "start_time": time.time(),
        "audio_url": audio_url,
        "audio_duration": audio_duration or 30  # Default to 30s if duration not provided
    }
    duration_info = f" (duration: {audio_duration}s)" if audio_duration else " (duration: unknown, using 30s default)"
    logger.info(f"🔒 Reserved slot {slot_id} for user {user}{duration_info} (active slots: {len(active_avatar_slots)})")

def release_avatar_slot(slot_id):
    """Release an avatar slot when TTS playback ends"""
    global active_avatar_slots
    
    if slot_id in active_avatar_slots:
        user = active_avatar_slots[slot_id]["user"]
        del active_avatar_slots[slot_id]
        logger.info(f"🔓 Released slot {slot_id} for user {user} (active slots: {len(active_avatar_slots)})")
    else:
        logger.warning(f"Attempted to release slot {slot_id} that wasn't reserved")


# Getter functions to access global state (avoids import reference issues)
def get_avatar_slot_assignments():
    """Get the current avatar slot assignments list."""
    return avatar_slot_assignments


def get_active_avatar_slots():
    """Get the current active avatar slots dictionary."""
    return active_avatar_slots


def get_avatar_assignments_generation_id():
    """Get the current avatar assignments generation ID."""
    return avatar_assignments_generation_id
