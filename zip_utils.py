"""
ZIP Utilities - Extract sessions from bulk ZIP
Complete version with all validation and error handling
"""

import zipfile
import tempfile
import os
import shutil
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

async def extract_sessions_from_bulk(bot, file_id: str, indices: List[int], session_type: str = 'session') -> Tuple[Optional[str], Optional[str]]:
    """
    Extract specific sessions from bulk ZIP and create new ZIP
    
    Args:
        bot: Telegram bot instance
        file_id: Source ZIP file_id
        indices: List of indices to extract [0,1,2,3,4]
        session_type: 'session' or 'tdata'
    
    Returns:
        tuple: (new_file_id, error_message)
    """
    temp_dir = None
    try:
        # 1. Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="bulk_extract_")
        logger.info(f"📁 Created temp dir: {temp_dir}")
        
        # 2. Download source ZIP
        file = await bot.get_file(file_id)
        source_zip_path = os.path.join(temp_dir, 'source.zip')
        await file.download_to_drive(source_zip_path)
        logger.info(f"⬇️ Downloaded source ZIP ({os.path.getsize(source_zip_path) / 1024:.1f} KB)")
        
        # 3. Validate ZIP
        if not zipfile.is_zipfile(source_zip_path):
            return None, "Downloaded file is not a valid ZIP"
        
        # 4. Extract all files
        extract_dir = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(source_zip_path, 'r') as zf:
            # Check for password protection
            for info in zf.infolist():
                if info.flag_bits & 0x1:
                    return None, "ZIP file is password protected"
            zf.extractall(extract_dir)
        
        logger.info(f"📦 Extracted source ZIP")
        
        # 5. List all files based on type
        if session_type == 'session':
            # Get .session files and nested .zip files
            all_files = []
            for item in sorted(os.listdir(extract_dir)):
                item_path = os.path.join(extract_dir, item)
                if os.path.isfile(item_path) and (item.endswith('.session') or item.endswith('.zip')):
                    all_files.append(item)
        else:  # tdata
            # Get tdata folders
            all_files = []
            for item in sorted(os.listdir(extract_dir)):
                item_path = os.path.join(extract_dir, item)
                if os.path.isdir(item_path):
                    all_files.append(item)
        
        logger.info(f"📄 Found {len(all_files)} files/folders")
        
        if len(all_files) == 0:
            return None, f"No {session_type} files found in ZIP"
        
        # 6. Validate indices
        if not indices:
            return None, "No indices provided"
        
        max_index = max(indices)
        if max_index >= len(all_files):
            return None, f"Index {max_index} out of range (max: {len(all_files)-1})"
        
        for idx in indices:
            if idx < 0:
                return None, f"Invalid negative index: {idx}"
        
        # 7. Select files at specified indices
        selected_files = [all_files[i] for i in indices]
        logger.info(f"✅ Selected {len(selected_files)} files: {selected_files[:3]}{'...' if len(selected_files) > 3 else ''}")
        
        # 8. Create output ZIP
        output_zip_path = os.path.join(temp_dir, 'output.zip')
        
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_name in selected_files:
                file_path = os.path.join(extract_dir, file_name)
                
                if os.path.isdir(file_path):
                    # Add entire directory (for tdata)
                    for root, dirs, files in os.walk(file_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_path, extract_dir)
                            zf.write(full_path, arcname=arcname)
                else:
                    # Add single file (for sessions)
                    zf.write(file_path, file_name)
        
        output_size = os.path.getsize(output_zip_path)
        logger.info(f"📦 Created output ZIP ({output_size / 1024:.1f} KB)")
        
        # 9. Validate output ZIP
        if not zipfile.is_zipfile(output_zip_path):
            return None, "Failed to create valid output ZIP"
        
        # 10. Upload to Telegram storage channel
        import config
        with open(output_zip_path, 'rb') as f:
            msg = await bot.send_document(
                chat_id=config.STORAGE_GROUP_ID,
                document=f,
                caption=f"📦 Extracted: {len(indices)} × {session_type}"
            )
        
        new_file_id = msg.document.file_id
        logger.info(f"✅ Uploaded new ZIP, file_id: {new_file_id[:20]}...")
        
        # 11. Cleanup
        shutil.rmtree(temp_dir)
        logger.info(f"🗑️ Cleaned up temp dir")
        
        return new_file_id, None
        
    except Exception as e:
        logger.error(f"❌ Error extracting sessions: {e}")
        import traceback
        traceback.print_exc()
        
        # Cleanup on error
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        return None, f"Extraction error: {str(e)}"


def count_files_in_zip(zip_path: str, session_type: str = 'session') -> int:
    """
    Count files in ZIP
    
    Args:
        zip_path: Path to ZIP file
        session_type: 'session' or 'tdata'
    
    Returns:
        int: Number of sessions found
    """
    try:
        if not os.path.exists(zip_path):
            logger.error(f"ZIP file not found: {zip_path}")
            return 0
        
        if not zipfile.is_zipfile(zip_path):
            logger.error(f"Not a valid ZIP: {zip_path}")
            return 0
        
        temp_dir = tempfile.mkdtemp(prefix="count_")
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_dir)
        
        if session_type == 'session':
            # Count .session and .zip files
            count = len([
                f for f in os.listdir(temp_dir) 
                if os.path.isfile(os.path.join(temp_dir, f)) and 
                (f.endswith('.session') or f.endswith('.zip'))
            ])
        else:  # tdata
            # Count tdata folders
            count = len([
                f for f in os.listdir(temp_dir) 
                if os.path.isdir(os.path.join(temp_dir, f))
            ])
        
        shutil.rmtree(temp_dir)
        return count
        
    except Exception as e:
        logger.error(f"Error counting files: {e}")
        return 0


def detect_session_type(zip_path: str) -> Tuple[Optional[str], int]:
    """
    Detect if ZIP contains .session files or tdata folders
    
    Args:
        zip_path: Path to ZIP file
    
    Returns:
        tuple: (session_type, count) or (None, 0)
    """
    try:
        if not zipfile.is_zipfile(zip_path):
            return None, 0
        
        temp_dir = tempfile.mkdtemp(prefix="detect_")
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_dir)
        
        # Check for .session files
        session_files = [
            f for f in os.listdir(temp_dir) 
            if os.path.isfile(os.path.join(temp_dir, f)) and 
            (f.endswith('.session') or f.endswith('.zip'))
        ]
        
        # Check for tdata folders
        tdata_folders = [
            f for f in os.listdir(temp_dir) 
            if os.path.isdir(os.path.join(temp_dir, f))
        ]
        
        shutil.rmtree(temp_dir)
        
        # Priority: session files > tdata folders
        if len(session_files) > 0:
            return ('session', len(session_files))
        elif len(tdata_folders) > 0:
            return ('tdata', len(tdata_folders))
        else:
            return (None, 0)
            
    except Exception as e:
        logger.error(f"Error detecting session type: {e}")
        return (None, 0)


async def validate_bulk_zip(bot, file_id: str) -> Tuple[Optional[str], int, Optional[str]]:
    """
    Validate bulk ZIP file
    
    Args:
        bot: Bot instance
        file_id: File ID
    
    Returns:
        tuple: (session_type, count, error_message)
    """
    temp_dir = None
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="validate_")
        
        # Download file
        file = await bot.get_file(file_id)
        zip_path = os.path.join(temp_dir, 'validate.zip')
        await file.download_to_drive(zip_path)
        
        # Check file size
        file_size = os.path.getsize(zip_path)
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            shutil.rmtree(temp_dir)
            return None, 0, f"File too large: {file_size / 1024 / 1024:.1f} MB (max 50MB)"
        
        if file_size < 100:  # Too small to be valid
            shutil.rmtree(temp_dir)
            return None, 0, "File too small to contain sessions"
        
        # Check if valid ZIP
        if not zipfile.is_zipfile(zip_path):
            shutil.rmtree(temp_dir)
            return None, 0, "Not a valid ZIP file"
        
        # Check for corruption
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                bad_file = zf.testzip()
                if bad_file:
                    shutil.rmtree(temp_dir)
                    return None, 0, f"Corrupted file in ZIP: {bad_file}"
        except zipfile.BadZipFile:
            shutil.rmtree(temp_dir)
            return None, 0, "ZIP file is corrupted"
        
        # Detect type and count
        session_type, count = detect_session_type(zip_path)
        
        shutil.rmtree(temp_dir)
        
        if count == 0:
            return None, 0, "No session files or tdata folders found in ZIP"
        
        if count > 1000:
            return None, 0, f"Too many sessions: {count} (max 1000 per bulk)"
        
        logger.info(f"✅ Validated: {session_type} × {count}")
        return session_type, count, None
        
    except Exception as e:
        logger.error(f"Validation error: {e}")
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        return None, 0, f"Validation error: {str(e)}"


def get_zip_info(zip_path: str) -> dict:
    """
    Get detailed information about ZIP file
    
    Args:
        zip_path: Path to ZIP
    
    Returns:
        dict with ZIP info
    """
    try:
        if not zipfile.is_zipfile(zip_path):
            return {"error": "Not a valid ZIP"}
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            info = {
                "file_count": len(zf.namelist()),
                "total_size": sum(f.file_size for f in zf.infolist()),
                "compressed_size": sum(f.compress_size for f in zf.infolist()),
                "compression_ratio": 0,
                "files": [f.filename for f in zf.infolist()[:10]]  # First 10 files
            }
            
            if info["total_size"] > 0:
                info["compression_ratio"] = (1 - info["compressed_size"] / info["total_size"]) * 100
            
            return info
            
    except Exception as e:
        return {"error": str(e)}


async def test_extract_one(bot, file_id: str, session_type: str = 'session') -> Tuple[bool, Optional[str]]:
    """
    Test extraction by extracting just the first session
    
    Args:
        bot: Bot instance
        file_id: Source ZIP file_id
        session_type: 'session' or 'tdata'
    
    Returns:
        tuple: (success, error_message)
    """
    try:
        result_file_id, error = await extract_sessions_from_bulk(
            bot, file_id, [0], session_type
        )
        
        if error:
            return False, error
        
        if result_file_id:
            return True, None
        
        return False, "Unknown error"
        
    except Exception as e:
        return False, str(e)