"""
Google Sheets UID Query Plugin for RAGFlow

This plugin provides a tool for LLM to query user information by UID from Google Sheets.
It connects to Google Sheets API using service account credentials and retrieves user data.
"""

import json
import logging
import os
from typing import Optional, Any

from plugin.llm_tool_plugin import LLMToolMetadata, LLMToolPlugin

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    gspread = None  # type: ignore
    Credentials = None  # type: ignore
    GSPREAD_AVAILABLE = False
    logging.warning("gspread or google-auth library not installed. Google Sheets UID Query plugin will not work.")


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
    _sheet_cache: dict[str, Any] = {}  # Cache multiple sheets by exact name

    @classmethod
    def get_metadata(cls) -> LLMToolMetadata:
        return {
            "name": "google_sheets_uid_query",
            "displayName": "$t:google_sheets_uid_query.name",
            "description": (
                "Query user information by UID from Google Sheets. "
                "This tool uses predefined classification categories to determine which sheet to query. "
                "IMPORTANT: You MUST provide both uid and query_context parameters. "
                "The query_context should contain the classification category such as: "
                "'查询个人活动奖励类' (for reward data), '查询黑牌用户类' (for riskcontrol data), "
                "or '查询问题类' (for general inquiries). "
                "The system will automatically map the category to the correct data sheet."
            ),
            "displayDescription": "$t:google_sheets_uid_query.description",
            "parameters": {
                "uid": {
                    "type": "string",
                    "description": "The user ID (UID) to query. This should be the unique identifier for the user in the Google Sheet.",
                    "displayDescription": "$t:google_sheets_uid_query.params.uid",
                    "required": True
                },
                "query_context": {
                    "type": "string",
                    "description": (
                        "The classification category that determines which sheet to query. "
                        "RECOMMENDED: Pass the exact category from your classification system (e.g., {Categorize:LuckyChickenRhyme@category_name}). "
                        "Supported categories: "
                        "'查询个人活动奖励类' → reward sheet, "
                        "'查询黑牌用户类' → riskcontrol sheet, "
                        "'查询问题类' → riskcontrol sheet. "
                        "If not provided, the system will try to infer from the user's question keywords, but providing the category ensures more accurate routing."
                    ),
                    "displayDescription": "$t:google_sheets_uid_query.params.query_context",
                    "required": False,
                    "default": ""
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
    def _get_sheet(cls, sheet_name: str = "reward") -> Any:
        """Get or create cached worksheet by exact name"""
        # Use exact sheet name as cache key (case-sensitive)
        if sheet_name not in cls._sheet_cache:
            try:
                client = cls._get_client()
                spreadsheet = client.open_by_key(cls.SHEET_ID)
                
                # Try to get the worksheet by exact title
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                    cls._sheet_cache[sheet_name] = worksheet
                    logging.info(f"Successfully connected to Google Sheet: {spreadsheet.title}, worksheet: {worksheet.title}")
                    
                except Exception as ws_error:
                    # List available worksheets for debugging
                    available_sheets = [ws.title for ws in spreadsheet.worksheets()]
                    raise ValueError(
                        f"Worksheet '{sheet_name}' not found. "
                        f"Available worksheets: {', '.join(available_sheets)}. "
                        f"Note: Sheet names are case-sensitive."
                    )
                    
            except Exception as e:
                # Check if this is a gspread API error
                error_type = type(e).__name__
                logging.error(f"Google Sheets error ({error_type}): {e}")
                
                if "APIError" in error_type or "permission" in str(e).lower():
                    raise RuntimeError(
                        f"Failed to access Google Sheet: {e}. "
                        f"This usually means:\n"
                        f"1. The service account doesn't have permission to access the sheet\n"
                        f"2. The Sheet ID is incorrect: {cls.SHEET_ID}\n"
                        f"Please share the Google Sheet with the service account email."
                    )
                else:
                    raise RuntimeError(f"Failed to open worksheet: {e}")
        
        return cls._sheet_cache[sheet_name]

    @classmethod
    def _determine_sheet_name(cls, query_context: str) -> str:
        """
        Determine which sheet to query based on the classification category.
        
        Args:
            query_context: The classification category from the prompt (e.g., "查询黑牌用户类", "查询个人活动奖励类")
            
        Returns:
            The sheet name to query
        """
        query_lower = query_context.lower()
        
        # Direct category to sheet mapping - exact matching first
        category_sheet_map = {
            # 黑牌用户类 -> riskcontrol
            "查询黑牌用户类": "riskcontrol",
            "黑牌用户类": "riskcontrol",
            "黑牌用户": "riskcontrol",
            
            # 个人活动奖励类 -> reward
            "查询个人活动奖励类": "reward",
            "个人活动奖励类": "reward",
            "活动奖励类": "reward",
            "奖励类": "reward",
            
            # 问题类 -> 可以根据实际情况映射
            # "查询问题类": "riskcontrol",  # 假设问题类查询风控
            # "问题类": "riskcontrol",
        }
        
        # First try exact category matching (case-insensitive)
        for category, sheet_name in category_sheet_map.items():
            if category in query_lower:
                logging.info(f"Matched category '{category}' -> sheet '{sheet_name}' (context: {query_context})")
                return sheet_name
        
        # Fallback: keyword matching for flexibility
        sheet_keywords = {
            "riskcontrol": [
                # 风控相关
                "risk", "风险", "riskcontrol", "风控", "control",
                # 黑名单相关
                "黑牌", "黑名单", "blacklist", "blocked", "封禁", "banned",
                # 提现/账户问题相关
                "提现", "withdraw", "无法提现", "不能提现", "提款", 
                "账户", "account", "冻结", "frozen", "限制", "restricted",
                # 异常相关
                "异常", "问题", "issue", "problem"
            ],
            "reward": [
                "reward", "奖励", "bonus", "红利", "积分", "points",
                "活动", "activity", "促销", "promotion", "返水", "rebate"
            ],
        }
        
        # Check for keyword matches
        for sheet_name, keywords in sheet_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                logging.info(f"Matched keyword -> sheet '{sheet_name}' (context: {query_context})")
                return sheet_name
        
        # Default to 'reward' if no match found
        logging.info(f"No category or keyword match found, defaulting to 'reward' sheet (context: {query_context})")
        return "reward"

    def invoke(self, uid: str, query_context: str = "") -> str:
        """
        Query user information by UID from Google Sheets.
        The system automatically determines which sheet to query based on the query context.
        
        Args:
            uid: The user ID to query
            query_context: The user's original question (used to determine which sheet to query)
            
        Returns:
            A JSON string containing the user's information, or an error message if not found
        """
        try:
            # Automatically determine which sheet to query
            sheet_name = self._determine_sheet_name(query_context)
            
            logging.info(f"Google Sheets UID Query tool invoked with UID: {uid}, determined sheet: {sheet_name} (context: {query_context})")
            
            # Get the worksheet
            sheet = self._get_sheet(sheet_name)
            
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
                    "sheet": sheet_name,
                    "data": user_data,
                    "message": f"Successfully found user data for UID: {uid} in sheet '{sheet_name}'"
                }
                logging.info(f"Found user data for UID {uid} in sheet {sheet_name}")
                return json.dumps(result, ensure_ascii=False, indent=2)
            else:
                result = {
                    "success": False,
                    "uid": uid,
                    "sheet": sheet_name,
                    "data": None,
                    "message": f"No user found with UID: {uid} in sheet '{sheet_name}'"
                }
                logging.warning(f"No user found for UID {uid} in sheet {sheet_name}")
                return json.dumps(result, ensure_ascii=False, indent=2)
                
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error querying Google Sheets for UID {uid} in sheet {sheet_name}: {error_msg}")
            result = {
                "success": False,
                "uid": uid,
                "sheet": sheet_name,
                "error": error_msg,
                "message": f"Failed to query user data: {error_msg}"
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

    @classmethod
    def clear_cache(cls):
        """Clear cached client and sheet (useful for testing or credential updates)"""
        cls._client_cache = None
        cls._sheet_cache = {}
        logging.info("Google Sheets client cache cleared")
