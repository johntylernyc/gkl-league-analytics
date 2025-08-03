"""
Sync PRDs from Notion to local markdown files for Claude Code access.
This script fetches PRDs from Notion and saves them as markdown files.
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
import requests
from typing import Dict, List, Any

# Configuration
NOTION_TOKEN = "ntn_S71003097902l1oU6HKT2BmEfUBX9wRrQcNSTWLgcj7baT"
PAGE_ID = "2431a736211e80fcbb88fe5de9652180"  # Extracted from URL
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Local storage
PRD_DIR = Path("docs/prds")
SYNC_LOG = Path("docs/prds/.sync_log.json")


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


def save_page_as_markdown(page_id: str, title: str = None) -> str:
    """Save a Notion page as markdown."""
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
    
    filepath.write_text("\n".join(markdown_lines), encoding="utf-8")
    print(f"Saved: {filepath}")
    
    return str(filepath)


def sync_prds():
    """Main sync function."""
    # Create PRD directory
    PRD_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Starting Notion sync...")
    print(f"Page ID: {PAGE_ID}")
    
    # First, try to get the main page
    main_page = get_page_content(PAGE_ID)
    if main_page:
        print(f"Found main page: {get_page_title(main_page)}")
        
        # Save the main page
        save_page_as_markdown(PAGE_ID)
        
        # Get child pages
        children = get_page_children(PAGE_ID)
        child_pages = [b for b in children if b.get("type") == "child_page"]
        child_databases = [b for b in children if b.get("type") == "child_database"]
        
        print(f"Found {len(child_pages)} child pages and {len(child_databases)} child databases")
        
        # Process child pages
        for child in child_pages:
            child_id = child.get("id")
            child_title = child.get("child_page", {}).get("title", "Untitled")
            print(f"Processing child page: {child_title}")
            save_page_as_markdown(child_id, child_title)
        
        # Process child databases
        for child in child_databases:
            db_id = child.get("id")
            db_title = child.get("child_database", {}).get("title", "Untitled")
            print(f"Processing database: {db_title}")
            
            # Get pages from database
            db_pages = get_database_pages(db_id)
            if db_pages:
                for db_page in db_pages:
                    page_id = db_page.get("id")
                    page_title = get_page_title(db_page)
                    print(f"  - Processing database page: {page_title}")
                    save_page_as_markdown(page_id, page_title)
    
    # Try as database if page fetch failed
    else:
        print("Trying as database...")
        pages = get_database_pages(PAGE_ID)
        if pages:
            print(f"Found {len(pages)} pages in database")
            for page in pages:
                page_id = page.get("id")
                title = get_page_title(page)
                print(f"Processing: {title}")
                save_page_as_markdown(page_id, title)
        else:
            print("Could not access as page or database. Please check the ID and permissions.")
    
    # Save sync log
    sync_info = {
        "last_sync": datetime.now().isoformat(),
        "page_id": PAGE_ID,
        "files_synced": len(list(PRD_DIR.glob("*.md")))
    }
    SYNC_LOG.write_text(json.dumps(sync_info, indent=2))
    
    print(f"\nSync complete! {sync_info['files_synced']} files in {PRD_DIR}")


if __name__ == "__main__":
    sync_prds()