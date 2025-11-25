
import random
import time

from modules import logger
from modules.persistent_data import get_enabled_avatars
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
        avatars = get_enabled_avatars()
        
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
    """Generate avatar assignments from configured slots in database"""
    global avatar_slot_assignments, avatar_assignments_generation_id
    
    from modules.persistent_data import get_avatar_slots
    
    # Get configured slots from database
    configured_slots = get_avatar_slots()
    
    if not configured_slots:
        # No configured slots - return empty list
        logger.info("No configured avatar slots found - avatar crowd will be empty")
        avatar_slot_assignments = []
        avatar_assignments_generation_id += 1
        return avatar_slot_assignments
    
    # Get available avatars
    available_avatars = get_available_avatars()
    if not available_avatars:
        logger.warning("No avatars available for assignment")
        avatar_slot_assignments = []
        avatar_assignments_generation_id += 1
        return avatar_slot_assignments
    
    # Create avatar lookup by group_id matching frontend logic
    # Frontend uses: avatar.avatar_group_id || `single_${avatar.id}`
    from modules.persistent_data import get_enabled_avatars
    raw_avatars = get_enabled_avatars()
    
    avatar_group_lookup = {}
    for avatar_db in raw_avatars:
        group_id = avatar_db.avatar_group_id or f"single_{avatar_db.id}"
        if group_id not in avatar_group_lookup:
            avatar_group_lookup[group_id] = {
                "name": avatar_db.name,
                "images": {},
                "voice_id": avatar_db.voice_id,
                "spawn_position": avatar_db.spawn_position
            }
        # Ensure file path is properly formatted
        file_path = avatar_db.file_path
        if not file_path.startswith('http') and not file_path.startswith('/'):
            file_path = f"/{file_path}"
        avatar_group_lookup[group_id]["images"][avatar_db.avatar_type] = file_path
    
    # Convert to avatar data format
    avatar_data_by_group = {}
    for group_id, group_data in avatar_group_lookup.items():
        default_img = group_data["images"].get("default", group_data["images"].get("speaking"))
        speaking_img = group_data["images"].get("speaking", group_data["images"].get("default"))
        avatar_data_by_group[group_id] = {
            "name": group_data["name"],
            "defaultImage": default_img,
            "speakingImage": speaking_img,
            "isSingleImage": default_img == speaking_img or not (default_img and speaking_img),
            "voice_id": group_data["voice_id"],
            "spawn_position": group_data["spawn_position"]
        }
    
    assignments = []
    
    # Get list of all avatar group IDs for random selection
    available_avatar_groups = list(avatar_data_by_group.keys())
    
    for slot_config in configured_slots:
        slot_data = {
            "id": slot_config['id'],  # Use database primary key for unique ID
            "slot_index": slot_config['slot_index'],  # Keep slot_index for ordering/display
            "x_position": slot_config["x_position"],
            "y_position": slot_config["y_position"],
            "size": slot_config["size"],
            "voice_id": slot_config.get("voice_id"),  # Voice assignment for this slot (None = random)
            "avatarData": None,
            "isActive": False
        }
        
        # Assign avatar if one is configured for this slot
        if slot_config.get("avatar_group_id") and slot_config["avatar_group_id"] in avatar_data_by_group:
            # Specific avatar assigned
            avatar_data = avatar_data_by_group[slot_config["avatar_group_id"]].copy()
            slot_data["avatarData"] = avatar_data
            logger.info(f"Assigned {avatar_data['name']} to slot {slot_config['slot_index']} at ({slot_config['x_position']}%, {slot_config['y_position']}%)")
        elif available_avatar_groups:
            # No specific avatar assigned (null) - randomly select one
            import random
            random_group_id = random.choice(available_avatar_groups)
            avatar_data = avatar_data_by_group[random_group_id].copy()
            slot_data["avatarData"] = avatar_data
            logger.info(f"Randomly assigned {avatar_data['name']} to slot {slot_config['slot_index']} at ({slot_config['x_position']}%, {slot_config['y_position']}%)")
        
        assignments.append(slot_data)
    
    avatar_slot_assignments = assignments
    avatar_assignments_generation_id += 1
    
    logger.info(f"Generated {len(avatar_slot_assignments)} avatar slot assignments from configured slots (gen #{avatar_assignments_generation_id})")
    
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
            logger.info(f"Slot {slot_id} expired after {expiry_time}s (audio: {audio_duration}s + 5s buffer)")
    
    for slot_id in expired_slots:
        logger.info(f"Cleaning up expired active slot: {slot_id}")
        del active_avatar_slots[slot_id]
    
    # Get list of valid voice IDs for validation
    from modules.persistent_data import get_voices
    voices_data = get_voices()
    voices_list = voices_data.get("voices", [])
    valid_voice_ids = {voice["id"] for voice in voices_list if voice.get("enabled", False)}
    
    # Find slots that match the voice_id if specified
    matching_slots = []
    available_slots = []
    
    for slot in avatar_slot_assignments:
        slot_id = slot["id"]
        slot_voice_id = slot.get("voice_id")
        
        is_active = slot_id in active_avatar_slots
        
        if not is_active:
            available_slots.append(slot)
            
            # Check if this slot matches the voice_id
            # slot_voice_id can be:
            # - None (random - matches any voice)
            # - A valid voice ID (must match the requested voice)
            # - An invalid/deleted voice ID (treated as random)
            if voice_id:
                if slot_voice_id is None:
                    # Random slot - matches any voice
                    matching_slots.append(slot)
                elif slot_voice_id == voice_id and slot_voice_id in valid_voice_ids:
                    # Exact match with valid voice
                    matching_slots.append(slot)
                elif slot_voice_id not in valid_voice_ids:
                    # Voice was deleted - treat as random
                    matching_slots.append(slot)
    
    # Prefer voice-matched slots if available
    if matching_slots:
        selected_slot = random.choice(matching_slots)
        logger.info(f"Selected voice-matched slot {selected_slot['id']} for voice {voice_id}")
        return selected_slot
    
    # Use any available slot
    if available_slots:
        selected_slot = random.choice(available_slots)
        logger.info(f"Selected random available slot {selected_slot['id']} (no voice match)")
        return selected_slot
    
    # No available slots
    logger.info("All avatar slots are busy, message will be queued")
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
    logger.info(f"Reserved slot {slot_id} for user {user}{duration_info} (active slots: {len(active_avatar_slots)})")

def release_avatar_slot(slot_id):
    """Release an avatar slot when TTS playback ends"""
    global active_avatar_slots
    
    if slot_id in active_avatar_slots:
        user = active_avatar_slots[slot_id]["user"]
        del active_avatar_slots[slot_id]
        logger.info(f"Released slot {slot_id} for user {user} (active slots: {len(active_avatar_slots)})")
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
