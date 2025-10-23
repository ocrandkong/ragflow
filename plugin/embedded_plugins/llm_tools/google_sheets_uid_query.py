"""
Google Sheets UID Query Plugin for RAGFlow

This plugin provides a tool for LLM to query user information by UID from Google Sheets.
It connects to Google Sheets API using service account credentials and retrieves user data.
"""

import json
import logging
import os
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    import gspread

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logging.warning("gspread or google-auth library not installed. Google Sheets UID Query plugin will not work.")

from plugin.llm_tool_plugin import LLMToolMetadata, LLMToolPlugin


class GoogleSheetsUIDQueryPlugin(LLMToolPlugin):
    """
    A LLM tool plugin to query user information by UID from Google Sheets.
    
    Configuration:
    - Service account JSON file path: Set via GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE environment variable
    - Sheet ID: Set via GOOGLE_SHEETS_SHEET_ID environment variable
    
    The plugin expects the Google Sheet to have a 'user_id' column.
    """
    _version_ = "1.0.0"
    
    # Configuration from environment variables
    SERVICE_ACCOUNT_FILE = os.environ.get(
        "GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE",
        "/ragflow/mcp/key/plated-epigram-471904-q7-04508ebeae37.json"
    )
    SHEET_ID = os.environ.get(
        "GOOGLE_SHEETS_SHEET_ID",
        "1reki8KLt9UenPTMWTqwNJx9c9dHNGvSdLa7ZXA3dcww"
    )
    
    # Authorization scopes
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    
    # Cache for Google Sheets client to avoid repeated authentication
    _client_cache: Optional[Any] = None
    _sheet_cache: Optional[Any] = None

    @classmethod
    def get_metadata(cls) -> LLMToolMetadata:
        return {
            "name": "google_sheets_uid_query",
            "displayName": "$t:google_sheets_uid_query.name",
            "description": (
                "Query user information by UID from Google Sheets. "
                "This tool connects to a Google Sheets document and retrieves user data "
                "based on the provided user_id (UID). It returns all information associated "
                "with the user, including their rewards and other relevant data."
            ),
            "displayDescription": "$t:google_sheets_uid_query.description",
            "parameters": {
                "uid": {
                    "type": "string",
                    "description": "The user ID (UID) to query. This should be the unique identifier for the user in the Google Sheet.",
                    "displayDescription": "$t:google_sheets_uid_query.params.uid",
                    "required": True
                }
            }
        }

    @classmethod
    def _get_client(cls) -> Any:
        """Get or create cached Google Sheets client"""
        if not GSPREAD_AVAILABLE:
            raise RuntimeError(
                "gspread library is not installed. "
                "Please install it using: pip install gspread google-auth"
            )
        
        if cls._client_cache is None:
            try:
                # Check if service account file exists
                if not os.path.exists(cls.SERVICE_ACCOUNT_FILE):
                    raise FileNotFoundError(
                        f"Service account file not found: {cls.SERVICE_ACCOUNT_FILE}. "
                        f"Please set GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE environment variable "
                        f"or place the file in the expected location."
                    )
                
                # Initialize credentials
                creds = Credentials.from_service_account_file(
                    cls.SERVICE_ACCOUNT_FILE,
                    scopes=cls.SCOPES
                )
                cls._client_cache = gspread.authorize(creds)
                logging.info(f"Google Sheets client initialized successfully with service account: {creds.service_account_email}")
                
            except Exception as e:
                logging.error(f"Failed to initialize Google Sheets client: {e}")
                raise RuntimeError(
                    f"Failed to connect to Google Sheets: {e}. "
                    f"Please ensure:\n"
                    f"1. Service account file exists at: {cls.SERVICE_ACCOUNT_FILE}\n"
                    f"2. Service account has been granted access to the Google Sheet\n"
                    f"3. Sheet ID is correct: {cls.SHEET_ID}"
                )
        
        return cls._client_cache

    @classmethod
    def _get_sheet(cls) -> Any:
        """Get or create cached worksheet"""
        if cls._sheet_cache is None:
            try:
                client = cls._get_client()
                spreadsheet = client.open_by_key(cls.SHEET_ID)
                cls._sheet_cache = spreadsheet.sheet1
                logging.info(f"Successfully connected to Google Sheet: {spreadsheet.title}")
            except gspread.exceptions.APIError as e:
                logging.error(f"Google Sheets API error: {e}")
                raise RuntimeError(
                    f"Failed to access Google Sheet: {e}. "
                    f"This usually means:\n"
                    f"1. The service account doesn't have permission to access the sheet\n"
                    f"2. The Sheet ID is incorrect: {cls.SHEET_ID}\n"
                    f"Please share the Google Sheet with the service account email."
                )
            except Exception as e:
                logging.error(f"Failed to open worksheet: {e}")
                raise RuntimeError(f"Failed to open worksheet: {e}")
        
        return cls._sheet_cache

    def invoke(self, uid: str) -> str:
        """
        Query user information by UID from Google Sheets.
        
        Args:
            uid: The user ID to query
            
        Returns:
            A JSON string containing the user's information, or an error message if not found
        """
        try:
            logging.info(f"Google Sheets UID Query tool invoked with UID: {uid}")
            
            # Get the worksheet
            sheet = self._get_sheet()
            
            # Get all records from the sheet
            all_records = sheet.get_all_records()
            
            # Search for the user by UID
            user_data = None
            for record in all_records:
                # Check if user_id matches (convert both to string for comparison)
                if str(record.get("user_id", "")) == str(uid):
                    user_data = record
                    break
            
            # Return results
            if user_data:
                result = {
                    "success": True,
                    "uid": uid,
                    "data": user_data,
                    "message": f"Successfully found user data for UID: {uid}"
                }
                logging.info(f"Found user data for UID {uid}")
                return json.dumps(result, ensure_ascii=False, indent=2)
            else:
                result = {
                    "success": False,
                    "uid": uid,
                    "data": None,
                    "message": f"No user found with UID: {uid}"
                }
                logging.warning(f"No user found for UID {uid}")
                return json.dumps(result, ensure_ascii=False, indent=2)
                
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error querying Google Sheets for UID {uid}: {error_msg}")
            result = {
                "success": False,
                "uid": uid,
                "error": error_msg,
                "message": f"Failed to query user data: {error_msg}"
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

    @classmethod
    def clear_cache(cls):
        """Clear cached client and sheet (useful for testing or credential updates)"""
        cls._client_cache = None
        cls._sheet_cache = None
        logging.info("Google Sheets client cache cleared")
