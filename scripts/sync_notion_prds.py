"""
Sync PRDs from Notion to local markdown files for Claude Code access.
This script fetches PRDs from Notion and saves them as markdown files.
"""

import os
import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import requests
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")
    pass

# Configuration - Load from environment variables for security
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
PAGE_ID = os.getenv('NOTION_PAGE_ID')

# Validate required environment variables
if not NOTION_TOKEN:
    raise ValueError("Missing NOTION_TOKEN environment variable. Please set it in .env file.")
if not PAGE_ID:
    raise ValueError("Missing NOTION_PAGE_ID environment variable. Please set it in .env file.")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Local storage
PRD_DIR = Path("docs/prds")
SYNC_LOG = Path("docs/prds/.sync_log.json")
FILE_TRACKING = Path("docs/prds/.file_tracking.json")
CONFLICT_DIR = Path("docs/prds/.conflicts")


class SyncConflictStrategy(Enum):
    """Strategies for handling sync conflicts."""
    NOTION_WINS = "notion_wins"  # Always use Notion version
    LOCAL_WINS = "local_wins"    # Always use local version
    MANUAL = "manual"            # Create conflict files for manual resolution
    MERGE_ATTEMPT = "merge"       # Attempt smart merge, fallback to manual


class FileStatus(Enum):
    """File synchronization status."""
    SYNCED = "synced"           # File is in sync
    LOCAL_MODIFIED = "local_modified"  # Local file modified since last sync
    NOTION_MODIFIED = "notion_modified"  # Notion page modified since last sync
    CONFLICT = "conflict"       # Both local and Notion modified
    LOCAL_ONLY = "local_only"   # File exists only locally
    NOTION_ONLY = "notion_only" # Page exists only in Notion


def clean_page_id(page_id: str) -> str:
    """Clean and format page ID."""
    # Remove any hyphens and ensure proper format
    clean_id = page_id.replace("-", "")
    # Format as 8-4-4-4-12
    if len(clean_id) == 32:
        return f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
    return clean_id


def get_page_content(page_id: str) -> Dict[str, Any]:
    """Fetch page content from Notion."""
    formatted_id = clean_page_id(page_id)
    url = f"https://api.notion.com/v1/pages/{formatted_id}"
    
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error fetching page {formatted_id}: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    return response.json()


def get_page_children(page_id: str) -> List[Dict[str, Any]]:
    """Fetch all child blocks (content) of a page."""
    formatted_id = clean_page_id(page_id)
    url = f"https://api.notion.com/v1/blocks/{formatted_id}/children"
    
    blocks = []
    has_more = True
    start_cursor = None
    
    while has_more:
        params = {"page_size": 100}
        if start_cursor:
            params["start_cursor"] = start_cursor
        
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            print(f"Error fetching children for {formatted_id}: {response.status_code}")
            print(f"Response: {response.text}")
            break
        
        data = response.json()
        blocks.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")
    
    return blocks


def get_database_pages(database_id: str) -> List[Dict[str, Any]]:
    """Fetch all pages from a Notion database."""
    formatted_id = clean_page_id(database_id)
    url = f"https://api.notion.com/v1/databases/{formatted_id}/query"
    
    pages = []
    has_more = True
    start_cursor = None
    
    while has_more:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor
        
        response = requests.post(url, headers=HEADERS, json=payload)
        if response.status_code != 200:
            print(f"Error querying database {formatted_id}: {response.status_code}")
            print(f"Response: {response.text}")
            # Try as a page with children instead
            return None
        
        data = response.json()
        pages.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")
    
    return pages


def block_to_markdown(block: Dict[str, Any]) -> str:
    """Convert a Notion block to markdown."""
    block_type = block.get("type")
    
    if block_type == "paragraph":
        return rich_text_to_markdown(block.get("paragraph", {}).get("rich_text", []))
    
    elif block_type == "heading_1":
        text = rich_text_to_markdown(block.get("heading_1", {}).get("rich_text", []))
        return f"# {text}"
    
    elif block_type == "heading_2":
        text = rich_text_to_markdown(block.get("heading_2", {}).get("rich_text", []))
        return f"## {text}"
    
    elif block_type == "heading_3":
        text = rich_text_to_markdown(block.get("heading_3", {}).get("rich_text", []))
        return f"### {text}"
    
    elif block_type == "bulleted_list_item":
        text = rich_text_to_markdown(block.get("bulleted_list_item", {}).get("rich_text", []))
        return f"- {text}"
    
    elif block_type == "numbered_list_item":
        text = rich_text_to_markdown(block.get("numbered_list_item", {}).get("rich_text", []))
        return f"1. {text}"
    
    elif block_type == "code":
        code = rich_text_to_markdown(block.get("code", {}).get("rich_text", []))
        language = block.get("code", {}).get("language", "")
        return f"```{language}\n{code}\n```"
    
    elif block_type == "quote":
        text = rich_text_to_markdown(block.get("quote", {}).get("rich_text", []))
        return f"> {text}"
    
    elif block_type == "divider":
        return "---"
    
    elif block_type == "child_page":
        title = block.get("child_page", {}).get("title", "Untitled")
        return f"[Child Page: {title}]"
    
    elif block_type == "child_database":
        title = block.get("child_database", {}).get("title", "Untitled")
        return f"[Child Database: {title}]"
    
    else:
        return f"[Unsupported block type: {block_type}]"


def rich_text_to_markdown(rich_text_array: List[Dict[str, Any]]) -> str:
    """Convert Notion rich text to markdown."""
    result = []
    
    for text_obj in rich_text_array:
        text = text_obj.get("plain_text", "")
        annotations = text_obj.get("annotations", {})
        
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("code"):
            text = f"`{text}`"
        if annotations.get("strikethrough"):
            text = f"~~{text}~~"
        
        if text_obj.get("href"):
            text = f"[{text}]({text_obj['href']})"
        
        result.append(text)
    
    return "".join(result)


def get_page_title(page: Dict[str, Any]) -> str:
    """Extract title from a Notion page."""
    properties = page.get("properties", {})
    
    # Try different common title property names
    for prop_name in ["title", "Title", "Name", "name"]:
        if prop_name in properties:
            title_prop = properties[prop_name]
            if title_prop.get("type") == "title":
                title_array = title_prop.get("title", [])
                if title_array:
                    return title_array[0].get("plain_text", "Untitled")
    
    # If no title property found, check all properties
    for prop_name, prop_value in properties.items():
        if prop_value.get("type") == "title":
            title_array = prop_value.get("title", [])
            if title_array:
                return title_array[0].get("plain_text", "Untitled")
    
    return "Untitled"


def get_page_last_edited(page: Dict[str, Any]) -> datetime:
    """Extract last edited time from a Notion page."""
    last_edited = page.get("last_edited_time")
    if last_edited:
        return datetime.fromisoformat(last_edited.replace('Z', '+00:00'))
    return datetime.now(timezone.utc)


def calculate_content_hash(content: str) -> str:
    """Calculate hash of content for change detection."""
    # Remove sync metadata lines for hash calculation
    lines = content.split('\n')
    filtered_lines = []
    skip_next = False
    
    for line in lines:
        if line.startswith('*Synced from Notion on'):
            skip_next = True
            continue
        if skip_next and line.startswith('*Page ID:'):
            skip_next = False
            continue
        if skip_next and line.strip() == '---':
            skip_next = False
            continue
        if not skip_next:
            filtered_lines.append(line)
    
    clean_content = '\n'.join(filtered_lines).strip()
    return hashlib.sha256(clean_content.encode('utf-8')).hexdigest()


def extract_page_id_from_file(filepath: Path) -> Optional[str]:
    """Extract Notion page ID from markdown file metadata."""
    try:
        content = filepath.read_text(encoding='utf-8')
        for line in content.split('\n'):
            if line.startswith('*Page ID:'):
                return line.replace('*Page ID:', '').replace('*', '').strip()
    except Exception:
        pass
    return None


def load_file_tracking() -> Dict[str, Any]:
    """Load file tracking metadata."""
    if FILE_TRACKING.exists():
        try:
            return json.loads(FILE_TRACKING.read_text())
        except Exception:
            pass
    return {"files": {}, "last_full_sync": None}


def save_file_tracking(tracking_data: Dict[str, Any]):
    """Save file tracking metadata."""
    FILE_TRACKING.write_text(json.dumps(tracking_data, indent=2))


def get_file_info(filepath: Path) -> Dict[str, Any]:
    """Get comprehensive file information."""
    if not filepath.exists():
        return None
    
    stat = filepath.stat()
    content = filepath.read_text(encoding='utf-8')
    
    return {
        "path": str(filepath),
        "modified_time": stat.st_mtime,
        "size": stat.st_size,
        "content_hash": calculate_content_hash(content),
        "notion_page_id": extract_page_id_from_file(filepath)
    }


def detect_file_status(filepath: Path, notion_page: Dict[str, Any], tracking_data: Dict[str, Any]) -> FileStatus:
    """Detect the synchronization status of a file."""
    file_info = get_file_info(filepath)
    page_id = notion_page.get('id') if notion_page else None
    notion_modified = get_page_last_edited(notion_page) if notion_page else None
    
    # Get tracking info for this file
    file_key = str(filepath.relative_to(PRD_DIR))
    tracked_info = tracking_data["files"].get(file_key, {})
    
    # File doesn't exist locally
    if not file_info:
        return FileStatus.NOTION_ONLY if notion_page else FileStatus.SYNCED
    
    # No Notion page
    if not notion_page:
        return FileStatus.LOCAL_ONLY
    
    # First time tracking this file
    if not tracked_info:
        return FileStatus.NOTION_MODIFIED
    
    # Check if local file changed
    local_changed = (
        file_info["content_hash"] != tracked_info.get("content_hash") or
        file_info["modified_time"] != tracked_info.get("modified_time")
    )
    
    # Check if Notion page changed
    last_notion_sync = tracked_info.get("last_notion_modified")
    notion_changed = False
    if last_notion_sync and notion_modified:
        last_sync_time = datetime.fromisoformat(last_notion_sync)
        notion_changed = notion_modified > last_sync_time
    elif not last_notion_sync:
        notion_changed = True
    
    # Determine status
    if local_changed and notion_changed:
        return FileStatus.CONFLICT
    elif local_changed:
        return FileStatus.LOCAL_MODIFIED
    elif notion_changed:
        return FileStatus.NOTION_MODIFIED
    else:
        return FileStatus.SYNCED


def update_notion_page(page_id: str, content: str) -> bool:
    """Update a Notion page with markdown content."""
    formatted_id = clean_page_id(page_id)
    
    # Convert markdown back to Notion blocks
    blocks = markdown_to_notion_blocks(content)
    
    # First, get existing children to delete them
    existing_blocks = get_page_children(page_id)
    
    # Delete existing content
    for block in existing_blocks:
        delete_url = f"https://api.notion.com/v1/blocks/{block['id']}"
        requests.delete(delete_url, headers=HEADERS)
    
    # Add new content
    url = f"https://api.notion.com/v1/blocks/{formatted_id}/children"
    payload = {"children": blocks}
    
    response = requests.patch(url, headers=HEADERS, json=payload)
    if response.status_code == 200:
        print(f"Updated Notion page: {page_id}")
        return True
    else:
        print(f"Error updating Notion page {page_id}: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def markdown_to_notion_blocks(content: str) -> List[Dict[str, Any]]:
    """Convert markdown content to Notion blocks."""
    lines = content.split('\n')
    blocks = []
    
    # Skip metadata lines
    content_start = 0
    for i, line in enumerate(lines):
        if line.strip() == '---' and i > 0:
            content_start = i + 1
            break
    
    i = content_start
    while i < len(lines):
        line = lines[i].rstrip()
        
        if not line:
            i += 1
            continue
        
        # Headers
        if line.startswith('# '):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        elif line.startswith('## '):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        elif line.startswith('### '):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                }
            })
        # Lists
        elif line.startswith('- '):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        elif re.match(r'^\d+\. ', line):
            content = re.sub(r'^\d+\. ', '', line)
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                }
            })
        # Code blocks
        elif line.startswith('```'):
            language = line[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": '\n'.join(code_lines)}}],
                    "language": language if language else "plain text"
                }
            })
        # Quotes
        elif line.startswith('> '):
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        # Dividers
        elif line.strip() == '---':
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        # Regular paragraphs
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                }
            })
        
        i += 1
    
    return blocks


def save_page_as_markdown(page_id: str, title: str = None, tracking_data: Dict[str, Any] = None) -> str:
    """Save a Notion page as markdown with tracking."""
    page = get_page_content(page_id)
    if not page:
        return None
    
    if not title:
        title = get_page_title(page)
    
    # Get page content blocks
    blocks = get_page_children(page_id)
    
    # Convert to markdown
    markdown_lines = [f"# {title}\n"]
    markdown_lines.append(f"*Synced from Notion on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    markdown_lines.append(f"*Page ID: {page_id}*\n")
    markdown_lines.append("---\n")
    
    for block in blocks:
        md = block_to_markdown(block)
        if md:
            markdown_lines.append(md)
            markdown_lines.append("")
    
    # Save to file
    filename = re.sub(r'[^\w\s-]', '', title.lower())
    filename = re.sub(r'[-\s]+', '-', filename)
    filepath = PRD_DIR / f"{filename}.md"
    
    content = "\n".join(markdown_lines)
    filepath.write_text(content, encoding="utf-8")
    print(f"Saved: {filepath}")
    
    # Update tracking data
    if tracking_data is not None:
        file_key = str(filepath.relative_to(PRD_DIR))
        file_info = get_file_info(filepath)
        tracking_data["files"][file_key] = {
            **file_info,
            "last_notion_modified": get_page_last_edited(page).isoformat(),
            "notion_page_id": page_id
        }
    
    return str(filepath)


def attempt_smart_merge(local_content: str, notion_content: str) -> Optional[str]:
    """Attempt to merge local and Notion content intelligently."""
    local_lines = local_content.split('\n')
    notion_lines = notion_content.split('\n')
    
    # Remove metadata from both versions for comparison
    local_clean = []
    notion_clean = []
    
    # Process local content
    skip_metadata = False
    for line in local_lines:
        if line.startswith('*Synced from Notion on') or line.startswith('*Page ID:'):
            skip_metadata = True
            continue
        if skip_metadata and line.strip() == '---':
            skip_metadata = False
            continue
        if not skip_metadata:
            local_clean.append(line)
    
    # Process Notion content
    skip_metadata = False
    for line in notion_lines:
        if line.startswith('*Synced from Notion on') or line.startswith('*Page ID:'):
            skip_metadata = True
            continue
        if skip_metadata and line.strip() == '---':
            skip_metadata = False
            continue
        if not skip_metadata:
            notion_clean.append(line)
    
    # Simple merge heuristics
    local_text = '\n'.join(local_clean).strip()
    notion_text = '\n'.join(notion_clean).strip()
    
    # If one is a superset of the other, use the larger one
    if local_text in notion_text:
        return notion_content
    elif notion_text in local_text:
        return local_content
    
    # If they're very similar (small diff), prefer the longer one
    local_words = set(local_text.split())
    notion_words = set(notion_text.split())
    
    if local_words and notion_words:
        similarity = len(local_words & notion_words) / len(local_words | notion_words)
        if similarity > 0.8:  # 80% similarity
            return local_content if len(local_text) > len(notion_text) else notion_content
    
    # Can't merge safely
    return None


def handle_conflict(filepath: Path, notion_page: Dict[str, Any], strategy: SyncConflictStrategy, tracking_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Handle sync conflicts based on strategy."""
    CONFLICT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if strategy == SyncConflictStrategy.NOTION_WINS:
        # Backup local version, use Notion
        backup_path = CONFLICT_DIR / f"{filepath.stem}_local_backup_{timestamp}.md"
        if filepath.exists():
            backup_path.write_text(filepath.read_text())
        
        # Save Notion version
        title = get_page_title(notion_page)
        page_id = notion_page.get('id')
        save_page_as_markdown(page_id, title, tracking_data)
        
        return True, f"Using Notion version, local backed up to {backup_path}"
    
    elif strategy == SyncConflictStrategy.LOCAL_WINS:
        # Upload local version to Notion
        if filepath.exists():
            content = filepath.read_text()
            page_id = extract_page_id_from_file(filepath)
            if page_id and update_notion_page(page_id, content):
                # Update tracking
                file_key = str(filepath.relative_to(PRD_DIR))
                file_info = get_file_info(filepath)
                tracking_data["files"][file_key] = {
                    **file_info,
                    "last_notion_modified": datetime.now(timezone.utc).isoformat(),
                    "notion_page_id": page_id
                }
                return True, "Updated Notion with local version"
        return False, "Failed to upload local version to Notion"
    
    elif strategy == SyncConflictStrategy.MERGE_ATTEMPT:
        # Try smart merge first
        local_content = filepath.read_text() if filepath.exists() else ""
        
        # Get Notion content
        title = get_page_title(notion_page)
        page_id = notion_page.get('id')
        blocks = get_page_children(page_id)
        
        markdown_lines = [f"# {title}\n"]
        markdown_lines.append(f"*Synced from Notion on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        markdown_lines.append(f"*Page ID: {page_id}*\n")
        markdown_lines.append("---\n")
        
        for block in blocks:
            md = block_to_markdown(block)
            if md:
                markdown_lines.append(md)
                markdown_lines.append("")
        
        notion_content = "\n".join(markdown_lines)
        
        merged_content = attempt_smart_merge(local_content, notion_content)
        
        if merged_content:
            # Successful merge
            filepath.write_text(merged_content)
            
            # Update Notion if merged content differs from Notion
            if merged_content != notion_content:
                update_notion_page(page_id, merged_content)
            
            # Update tracking
            file_key = str(filepath.relative_to(PRD_DIR))
            file_info = get_file_info(filepath)
            tracking_data["files"][file_key] = {
                **file_info,
                "last_notion_modified": datetime.now(timezone.utc).isoformat(),
                "notion_page_id": page_id
            }
            
            return True, "Successfully merged local and Notion changes"
        else:
            # Fall back to manual resolution
            return handle_conflict(filepath, notion_page, SyncConflictStrategy.MANUAL, tracking_data)
    
    elif strategy == SyncConflictStrategy.MANUAL:
        # Create conflict files for manual resolution
        
        # Save local version
        local_conflict = CONFLICT_DIR / f"{filepath.stem}_local_{timestamp}.md"
        if filepath.exists():
            local_conflict.write_text(filepath.read_text())
        
        # Save Notion version
        notion_conflict = CONFLICT_DIR / f"{filepath.stem}_notion_{timestamp}.md"
        title = get_page_title(notion_page)
        page_id = notion_page.get('id')
        
        # Generate Notion content
        blocks = get_page_children(page_id)
        markdown_lines = [f"# {title}\n"]
        markdown_lines.append(f"*Synced from Notion on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        markdown_lines.append(f"*Page ID: {page_id}*\n")
        markdown_lines.append("---\n")
        
        for block in blocks:
            md = block_to_markdown(block)
            if md:
                markdown_lines.append(md)
                markdown_lines.append("")
        
        notion_content = "\n".join(markdown_lines)
        notion_conflict.write_text(notion_content)
        
        # Create merge template
        merge_template = CONFLICT_DIR / f"{filepath.stem}_merge_template_{timestamp}.md"
        template_content = f"""# MERGE CONFLICT RESOLUTION
# File: {filepath.name}
# Resolve conflicts and save the final version back to: {filepath}

# LOCAL VERSION (your changes):
# {'-' * 50}

{filepath.read_text() if filepath.exists() else '(no local content)'}

# NOTION VERSION (remote changes):
# {'-' * 50}

{notion_content}

# INSTRUCTIONS:
# 1. Review both versions above
# 2. Create your merged version below
# 3. Copy the merged content to {filepath}
# 4. Re-run the sync

# YOUR MERGED VERSION:
# {'-' * 50}

# (Create your merged version here)
"""
        merge_template.write_text(template_content)
        
        message = f"""Manual resolution required:
  Local version: {local_conflict}
  Notion version: {notion_conflict}
  Merge template: {merge_template}
  Target file: {filepath}"""
        
        return False, message
    
    return False, "Unknown conflict strategy"


def sync_prds(conflict_strategy: SyncConflictStrategy = SyncConflictStrategy.MANUAL, 
              bidirectional: bool = True):
    """Enhanced sync function with conflict resolution."""
    # Create directories
    PRD_DIR.mkdir(parents=True, exist_ok=True)
    CONFLICT_DIR.mkdir(exist_ok=True)
    
    print(f"Starting enhanced Notion sync...")
    print(f"Page ID: {PAGE_ID}")
    print(f"Conflict strategy: {conflict_strategy.value}")
    print(f"Bidirectional: {bidirectional}")
    
    # Load tracking data
    tracking_data = load_file_tracking()
    
    # Collect all Notion pages
    notion_pages = {}
    local_files = {}
    
    # Get existing local files
    for filepath in PRD_DIR.glob("*.md"):
        if not filepath.name.startswith('.'):
            page_id = extract_page_id_from_file(filepath)
            local_files[str(filepath.relative_to(PRD_DIR))] = {
                'path': filepath,
                'page_id': page_id
            }
    
    # Fetch Notion pages
    main_page = get_page_content(PAGE_ID)
    if main_page:
        print(f"Found main page: {get_page_title(main_page)}")
        notion_pages[PAGE_ID] = main_page
        
        # Get child pages
        children = get_page_children(PAGE_ID)
        child_pages = [b for b in children if b.get("type") == "child_page"]
        child_databases = [b for b in children if b.get("type") == "child_database"]
        
        print(f"Found {len(child_pages)} child pages and {len(child_databases)} child databases")
        
        # Collect child pages
        for child in child_pages:
            child_id = child.get("id")
            child_page = get_page_content(child_id)
            if child_page:
                notion_pages[child_id] = child_page
        
        # Collect database pages
        for child in child_databases:
            db_id = child.get("id")
            db_pages = get_database_pages(db_id)
            if db_pages:
                for db_page in db_pages:
                    page_id = db_page.get("id")
                    notion_pages[page_id] = db_page
    else:
        # Try as database
        print("Trying as database...")
        pages = get_database_pages(PAGE_ID)
        if pages:
            for page in pages:
                page_id = page.get("id")
                notion_pages[page_id] = page
    
    # Create page_id to filename mapping
    page_to_file = {}
    for file_key, file_info in local_files.items():
        if file_info['page_id']:
            page_to_file[file_info['page_id']] = file_key
    
    # Process each file/page combination
    conflicts = []
    synced_count = 0
    
    # Process Notion pages
    for page_id, page in notion_pages.items():
        title = get_page_title(page)
        filename = re.sub(r'[^\w\s-]', '', title.lower())
        filename = re.sub(r'[-\s]+', '-', filename) + '.md'
        filepath = PRD_DIR / filename
        
        # Detect status
        status = detect_file_status(filepath, page, tracking_data)
        print(f"File: {filename} - Status: {status.value}")
        
        if status == FileStatus.SYNCED:
            synced_count += 1
            continue
        
        elif status == FileStatus.NOTION_MODIFIED or status == FileStatus.NOTION_ONLY:
            # Download from Notion
            save_page_as_markdown(page_id, title, tracking_data)
            synced_count += 1
        
        elif status == FileStatus.LOCAL_MODIFIED:
            if bidirectional:
                # Upload to Notion
                content = filepath.read_text()
                if update_notion_page(page_id, content):
                    # Update tracking
                    file_key = str(filepath.relative_to(PRD_DIR))
                    file_info = get_file_info(filepath)
                    tracking_data["files"][file_key] = {
                        **file_info,
                        "last_notion_modified": datetime.now(timezone.utc).isoformat(),
                        "notion_page_id": page_id
                    }
                    synced_count += 1
                    print(f"Uploaded local changes to Notion: {filename}")
            else:
                print(f"Local file modified but bidirectional sync disabled: {filename}")
        
        elif status == FileStatus.CONFLICT:
            conflicts.append((filepath, page, status))
            success, message = handle_conflict(filepath, page, conflict_strategy, tracking_data)
            print(f"  Conflict resolution: {message}")
            if success:
                synced_count += 1
    
    # Process local-only files
    for file_key, file_info in local_files.items():
        if not file_info['page_id']:
            print(f"Local-only file (no Notion page ID): {file_key}")
    
    # Update tracking timestamp
    tracking_data["last_full_sync"] = datetime.now().isoformat()
    save_file_tracking(tracking_data)
    
    # Save sync log
    sync_info = {
        "last_sync": datetime.now().isoformat(),
        "page_id": PAGE_ID,
        "files_synced": synced_count,
        "conflicts_detected": len(conflicts),
        "conflict_strategy": conflict_strategy.value,
        "bidirectional": bidirectional,
        "total_notion_pages": len(notion_pages),
        "total_local_files": len(local_files)
    }
    SYNC_LOG.write_text(json.dumps(sync_info, indent=2))
    
    # Enhanced logging summary
    print(f"\n{'='*60}")
    print(f"SYNC COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"  Files synced successfully: {synced_count}")
    print(f"  Conflicts detected: {len(conflicts)}")
    print(f"  Total Notion pages: {len(notion_pages)}")
    print(f"  Total local files: {len(local_files)}")
    print(f"  Conflict strategy: {conflict_strategy.value}")
    print(f"  Bidirectional sync: {'Enabled' if bidirectional else 'Disabled'}")
    
    if conflicts:
        print(f"\nCONFLICTS REQUIRING ATTENTION:")
        for filepath, page, status in conflicts:
            print(f"    - {filepath.name}: {status.value}")
        
        if conflict_strategy == SyncConflictStrategy.MANUAL:
            print(f"\nManual resolution steps:")
            print(f"    1. Review conflict files in: {CONFLICT_DIR}")
            print(f"    2. Resolve conflicts manually")
            print(f"    3. Re-run sync to continue")
    
    # Log any file tracking issues
    orphaned_files = [f for f, info in local_files.items() if not info['page_id']]
    if orphaned_files:
        print(f"\nLocal files without Notion page IDs:")
        for file_key in orphaned_files:
            print(f"    - {file_key}")
        print(f"    These files are not synced with Notion")
    
    print(f"\nDetailed sync log: {SYNC_LOG}")
    print(f"File tracking data: {FILE_TRACKING}")
    
    if CONFLICT_DIR.exists() and any(CONFLICT_DIR.iterdir()):
        print(f"Conflict files: {CONFLICT_DIR}")


def print_usage_examples():
    """Print usage examples for the enhanced sync."""
    print("\nUSAGE EXAMPLES:")
    print("\n  Basic sync (manual conflict resolution):")
    print("    python sync_notion_prds.py")
    print("\n  Auto-resolve conflicts (Notion wins):")
    print("    python sync_notion_prds.py --strategy notion_wins")
    print("\n  Auto-resolve conflicts (Local wins):")
    print("    python sync_notion_prds.py --strategy local_wins")
    print("\n  Attempt smart merge with manual fallback:")
    print("    python sync_notion_prds.py --strategy merge")
    print("\n  Download-only mode (no uploads to Notion):")
    print("    python sync_notion_prds.py --no-bidirectional")
    print("\n  Check status without making changes:")
    print("    python sync_notion_prds.py --dry-run")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enhanced Notion PRD sync with bidirectional sync and conflict resolution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python sync_notion_prds.py                           # Basic sync with manual conflict resolution
  python sync_notion_prds.py --strategy notion_wins    # Auto-resolve conflicts (prefer Notion)
  python sync_notion_prds.py --strategy local_wins     # Auto-resolve conflicts (prefer local)
  python sync_notion_prds.py --strategy merge          # Attempt smart merge
  python sync_notion_prds.py --no-bidirectional        # Download-only mode
  python sync_notion_prds.py --dry-run                 # Check status without changes"""
    )
    
    parser.add_argument("--strategy", 
                       choices=[s.value for s in SyncConflictStrategy],
                       default=SyncConflictStrategy.MANUAL.value,
                       help="Conflict resolution strategy (default: manual)")
    parser.add_argument("--no-bidirectional", action="store_true",
                       help="Disable uploading local changes to Notion")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be synced without making changes")
    parser.add_argument("--examples", action="store_true",
                       help="Show usage examples")
    
    args = parser.parse_args()
    
    if args.examples:
        print_usage_examples()
        exit(0)
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print("This feature is not yet implemented.")
        print("For now, run without --dry-run to see actual sync status.")
        exit(0)
    
    strategy = SyncConflictStrategy(args.strategy)
    bidirectional = not args.no_bidirectional
    
    try:
        sync_prds(strategy, bidirectional)
    except KeyboardInterrupt:
        print("\n\nSync interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nSync failed with error: {e}")
        print(f"Check {SYNC_LOG} for details")
        exit(1)