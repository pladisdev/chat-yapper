# Database Migration & Distribution Guide

## Problem
When distributing the Chat Yapper application as an `.exe` to users, they may have an older database with a different schema. This can cause the application to crash or behave incorrectly.

## Solution
The application now includes an **automatic database migration system** that runs on startup. It safely updates old databases to the new schema without losing any data.

## How It Works

### 1. Migration System (`db_migration.py`)
- **Automatically runs** before the application starts
- **Checks existing tables** for missing columns
- **Adds new columns** with appropriate default values
- **Never deletes data** - only adds new fields
- **Logs all changes** for debugging

### 2. Supported Migrations

#### Voice Table
Automatically adds missing columns:
- `avatar_default` (TEXT) - Path to default/idle avatar image
- `avatar_speaking` (TEXT) - Path to speaking avatar image
- `avatar_mode` (TEXT, default: 'single') - Avatar mode (single/dual)
- `created_at` (TEXT) - Timestamp when voice was added

#### AvatarImage Table
Automatically adds missing columns:
- `upload_date` (TEXT) - Upload timestamp
- `file_size` (INTEGER) - File size in bytes
- `avatar_type` (TEXT, default: 'default') - Type: default/speaking
- `avatar_group_id` (TEXT) - Links default and speaking avatars
- `voice_id` (INTEGER) - Links avatar to specific voice
- `spawn_position` (INTEGER) - Fixed spawn position (1-N)

### 3. Database Location
The database is stored in a persistent user directory:

**Windows:** `%LOCALAPPDATA%\ChatYapper\app.db`
- Example: `C:\Users\YourName\AppData\Local\ChatYapper\app.db`

**Linux/Mac:** `~/.chatyapper/app.db`
- Example: `/home/username/.chatyapper/app.db`

## For Developers

### Building a New Version
When you add new database columns to `models.py`:

1. **Update `db_migration.py`** with the new columns:
```python
def migrate_your_table(conn: sqlite3.Connection) -> None:
    migrations = [
        ("new_column_name", "TEXT", "default_value"),
        ("another_column", "INTEGER", None),
    ]
    
    for col_name, col_type, default in migrations:
        add_column_if_missing(conn, "your_table", col_name, col_type, default)
```

2. **Add your migration** to `run_all_migrations()`:
```python
if "your_table" in existing_tables:
    migrate_your_table(conn)
```

3. **Test with an old database**:
   - Copy an old database to the test location
   - Run the application
   - Check logs for migration messages

### Testing Migrations
```python
# Get database info for debugging
from db_migration import get_database_info

db_info = get_database_info("path/to/app.db")
print(f"Tables: {db_info['tables']}")
```

## For Users Having Issues

### Symptoms of Database Issues
- Application crashes on startup
- Missing features or settings
- Errors about missing columns
- "Table not found" errors

### Troubleshooting Steps

#### 1. Check the Logs
Logs are saved in the `logs/` directory next to the executable:
- Look for: `backend_YYYYMMDD_HHMMSS.log`
- Search for: "migration", "error", "database"

#### 2. Use the Debug Endpoint
While the app is running, visit:
```
http://localhost:8000/api/debug/database
```

This shows:
- Database location
- Tables and columns
- Row counts
- Migration status

#### 3. Reset Database (Last Resort)
⚠️ **Warning: This deletes all your voices and avatars!**

To start fresh:
1. Close the application
2. Navigate to: `%LOCALAPPDATA%\ChatYapper` (Windows) or `~/.chatyapper` (Linux/Mac)
3. **Backup** the `app.db` file (just in case!)
4. Delete `app.db`
5. Restart the application - a fresh database will be created

### Manual Migration (Advanced)
If automatic migration fails, you can manually update the database:

```python
import sqlite3

# Connect to database
conn = sqlite3.connect(r'C:\Users\YourName\AppData\Local\ChatYapper\app.db')

# Add missing column example
conn.execute("ALTER TABLE voice ADD COLUMN avatar_mode TEXT DEFAULT 'single'")
conn.commit()
conn.close()
```

## Common Issues

### Issue: "Column already exists"
**Solution:** This is harmless - the migration detected the column already exists and skipped it.

### Issue: "Table doesn't exist"
**Solution:** The table will be created automatically by SQLModel. This is normal for first-time users.

### Issue: "Permission denied" on database file
**Solutions:**
- Close all instances of the application
- Check if another process has the database open
- Run as administrator (Windows)
- Check file permissions

### Issue: Old data missing after migration
**This shouldn't happen!** The migration only adds columns, never removes data.
- Check the backup database file
- Check logs for migration errors
- Contact support with your log file

## Migration Logs

Look for these log messages:

### ✅ Successful Migration
```
INFO - Running database migration check...
INFO - Checking Voice table schema...
INFO - Added column 'avatar_mode' to table 'voice'
INFO - Database migration check completed successfully
```

### ⚠️ Warning (Harmless)
```
INFO - Column 'avatar_mode' already exists in table 'voice'
INFO - Voice table schema is up to date
```

### ❌ Error (Needs Attention)
```
ERROR - Failed to add column 'avatar_mode' to table 'voice': ...
ERROR - Database migration failed: ...
```

## Backup Strategy

### Automatic Backups (Recommended)
Add this to your build script to create automatic backups:

```python
import shutil
from datetime import datetime

def backup_database(db_path):
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
```

### Manual Backup
Users can manually backup their database:
1. Close the application
2. Navigate to `%LOCALAPPDATA%\ChatYapper`
3. Copy `app.db` to `app.db.backup`

## Version Compatibility

| Version | Database Schema | Migration Required |
|---------|----------------|-------------------|
| 1.0.0   | Initial schema | No |
| 1.1.0   | Added avatar_mode, avatar_default, avatar_speaking | Yes ✅ |
| Future  | New columns TBD | Yes ✅ |

## Support

If users encounter database issues:

1. **Ask for the log file** from `logs/backend_*.log`
2. **Ask them to visit** `http://localhost:8000/api/debug/database` and send you the output
3. **Check if migration ran** by searching logs for "migration"
4. **Provide a clean database** if necessary (last resort)

## Future Improvements

Consider implementing:
- [ ] Automatic database backups before migration
- [ ] Rollback capability if migration fails
- [ ] Database version tracking in a metadata table
- [ ] Migration history log
- [ ] User notification when migration is needed
- [ ] Export/import functionality for user data
