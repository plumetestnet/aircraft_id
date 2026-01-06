"""
TData Converter - Convert Telethon sessions to TData format
Based on your friend's code, integrated for the bot
"""

import os
import asyncio
import zipfile
import shutil
import tempfile
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
try:
    from opentele.api import UseCurrentSession
    OPENTELE_AVAILABLE = True
except ImportError:
    OPENTELE_AVAILABLE = False
    logging.warning("⚠️ opentele not installed - TData conversion disabled")

import config

logger = logging.getLogger(__name__)

# Disable Telethon's connection logging
logging.getLogger('telethon.network.mtprotosender').setLevel(logging.CRITICAL)
logging.getLogger('telethon.client.telegrambaseclient').setLevel(logging.CRITICAL)


async def convert_session_to_tdata(session_string: str, phone_number: str, output_dir: str = None) -> str:
    """
    Convert a single session string to TData format
    
    Args:
        session_string: Telethon session string
        phone_number: Phone number for naming
        output_dir: Output directory (temp if None)
    
    Returns:
        Path to TData zip file
    """
    if not OPENTELE_AVAILABLE:
        raise Exception("opentele library not installed. Run: pip install opentele")
    
    # Create temp directory if not specified
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="tdata_")
    
    tdata_path = os.path.join(output_dir, f"{phone_number}_tdata")
    os.makedirs(tdata_path, exist_ok=True)
    
    client = None
    try:
        logger.info(f"🔄 Converting session for {phone_number} to TData...")
        
        # Create Telethon client from string session
        client = TelegramClient(
            StringSession(session_string),
            config.API_ID,
            config.API_HASH
        )
        
        # Connect
        await client.connect()
        
        # Check if authorized
        if not await client.is_user_authorized():
            logger.error(f"❌ Session not authorized for {phone_number}")
            return None
        
        # Convert to TDesktop using opentele
        tdesk = await client.ToTDesktop(flag=UseCurrentSession)
        
        # Save TData
        tdata_folder = os.path.join(tdata_path, "tdata")
        os.makedirs(tdata_folder, exist_ok=True)
        tdesk.SaveTData(tdata_folder)
        
        logger.info(f"✅ TData saved to {tdata_folder}")
        
        # Create ZIP file
        zip_path = os.path.join(output_dir, f"{phone_number}_tdata.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(tdata_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, tdata_path)
                    zipf.write(file_path, arcname=arcname)
        
        logger.info(f"✅ TData ZIP created: {zip_path}")
        
        # Cleanup tdata folder (keep only zip)
        shutil.rmtree(tdata_path)
        
        return zip_path
        
    except Exception as e:
        logger.error(f"❌ Error converting to TData: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        if client and client.is_connected():
            try:
                await client.disconnect()
            except:
                pass


async def convert_multiple_sessions_to_tdata(sessions_data: list, output_dir: str = None) -> str:
    """
    Convert multiple sessions to TData and create a single ZIP
    
    Args:
        sessions_data: List of dicts with 'session_string' and 'phone_number'
        output_dir: Output directory (temp if None)
    
    Returns:
        Path to combined ZIP file
    """
    if not OPENTELE_AVAILABLE:
        raise Exception("opentele library not installed")
    
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="tdata_batch_")
    
    tdata_base = os.path.join(output_dir, "tdata")
    os.makedirs(tdata_base, exist_ok=True)
    
    successful = []
    failed = []
    
    for i, session_data in enumerate(sessions_data, 1):
        session_string = session_data.get('session_string')
        phone_number = session_data.get('phone_number', f'session_{i}')
        
        logger.info(f"📦 Converting {i}/{len(sessions_data)}: {phone_number}")
        
        try:
            # Convert individual session
            zip_path = await convert_session_to_tdata(
                session_string,
                phone_number,
                tdata_base
            )
            
            if zip_path:
                successful.append(phone_number)
            else:
                failed.append(phone_number)
                
        except Exception as e:
            logger.error(f"❌ Failed to convert {phone_number}: {e}")
            failed.append(phone_number)
    
    if not successful:
        logger.error("❌ No sessions converted successfully")
        return None
    
    # Create combined ZIP
    import time
    timestamp = int(time.time())
    combined_zip = os.path.join(output_dir, f"TData_batch_{timestamp}.zip")
    
    with zipfile.ZipFile(combined_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(tdata_base):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, tdata_base)
                zipf.write(file_path, arcname=arcname)
    
    logger.info(f"✅ Batch conversion complete: {len(successful)}/{len(sessions_data)}")
    logger.info(f"📦 Combined ZIP: {combined_zip}")
    
    return combined_zip


def extract_session_from_tdata(tdata_zip_path: str) -> str:
    """
    Extract session string from TData ZIP (reverse conversion)
    Note: This requires the TData to be valid and may not always work
    
    Args:
        tdata_zip_path: Path to TData ZIP file
    
    Returns:
        Session string or None
    """
    # This is complex and may not always be possible
    # For now, return None - admin should upload .session files
    logger.warning("⚠️ TData to session conversion not implemented yet")
    return None


async def verify_tdata(tdata_zip_path: str) -> bool:
    """
    Verify if TData ZIP is valid
    
    Args:
        tdata_zip_path: Path to TData ZIP file
    
    Returns:
        True if valid, False otherwise
    """
    try:
        with zipfile.ZipFile(tdata_zip_path, 'r') as zipf:
            # Check if it contains tdata folder structure
            files = zipf.namelist()
            
            # Basic validation - should contain key files
            required_files = ['key_datas', 'settings0', 'maps0']
            
            has_required = any(
                any(req in f for req in required_files)
                for f in files
            )
            
            return has_required
            
    except Exception as e:
        logger.error(f"❌ Error verifying TData: {e}")
        return False


# Utility function for bot integration
async def prepare_tdata_for_user(session_string: str, phone_number: str) -> dict:
    """
    Prepare TData for user download
    Returns dict with both .session and .tdata.zip
    
    Args:
        session_string: Telethon session string
        phone_number: Phone number
    
    Returns:
        Dict with 'session_file', 'tdata_file', 'success'
    """
    result = {
        'success': False,
        'session_file': None,
        'tdata_file': None,
        'error': None
    }
    
    temp_dir = tempfile.mkdtemp(prefix="user_download_")
    
    try:
        # 1. Create .session file
        session_file = os.path.join(temp_dir, f"{phone_number}.session")
        with open(session_file, 'w') as f:
            f.write(session_string)
        result['session_file'] = session_file
        
        # 2. Try to create TData (if opentele available)
        if OPENTELE_AVAILABLE:
            try:
                tdata_zip = await convert_session_to_tdata(
                    session_string,
                    phone_number,
                    temp_dir
                )
                result['tdata_file'] = tdata_zip
            except Exception as e:
                logger.warning(f"⚠️ Could not create TData: {e}")
                # Not critical - user still gets .session
        
        result['success'] = True
        
    except Exception as e:
        logger.error(f"❌ Error preparing files: {e}")
        result['error'] = str(e)
    
    return result


def cleanup_temp_files(file_paths: list):
    """Clean up temporary files and directories"""
    for path in file_paths:
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            logger.debug(f"Cleanup: {e}")