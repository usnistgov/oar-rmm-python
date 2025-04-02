from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from app.database import connect_db, create_collection_indexes
from app.routers import paper, record, field, code, patent, api, releaseset, taxonomy, usagemetrics, version
from app.config import settings
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.exceptions import (
    RMMException, ResourceNotFoundException, KeyWordNotFoundException, 
    IllegalArgumentException, GeneralException, InternalServerException, ErrorInfo
)
from pymongo.errors import OperationFailure
import os
import logging
import time
from colorama import init, Fore, Style

init()

logger = logging.getLogger(__name__)

app = FastAPI()
# Router for `field`` needs to come before `record`` to avoid field queries to get
# caught in the `record` router
app.include_router(field.router) 
app.include_router(record.router)
app.include_router(paper.router) 
app.include_router(code.router)
app.include_router(patent.router)
app.include_router(api.router)
app.include_router(releaseset.router)
app.include_router(taxonomy.router)
app.include_router(version.router)
app.include_router(usagemetrics.router, tags=["Metrics"])

# Metrics middleware to record API calls
# app.add_middleware(MetricsMiddleware)

@app.exception_handler(ResourceNotFoundException)
async def resource_not_found_exception_handler(request: Request, exc: ResourceNotFoundException):
    error_info = ErrorInfo(
        url=str(request.url),
        message=str(exc),
        http_status="404"
    )
    return JSONResponse(
        status_code=404,
        content=error_info.to_dict()
    )

@app.exception_handler(KeyWordNotFoundException)
async def keyword_not_found_exception_handler(request: Request, exc: KeyWordNotFoundException):
    error_info = ErrorInfo(
        url=str(request.url),
        message=str(exc),
        http_status="404"
    )
    return JSONResponse(
        status_code=404,
        content=error_info.to_dict()
    )

@app.exception_handler(IllegalArgumentException)
async def illegal_argument_exception_handler(request: Request, exc: IllegalArgumentException):
    error_info = ErrorInfo(
        url=str(request.url),
        message=str(exc),
        http_status="400"
    )
    return JSONResponse(
        status_code=400,
        content=error_info.to_dict()
    )

@app.exception_handler(InternalServerException)
async def internal_server_exception_handler(request: Request, exc: InternalServerException):
    error_info = ErrorInfo(
        url=str(request.url),
        message=str(exc),
        http_status="500"
    )
    return JSONResponse(
        status_code=500,
        content=error_info.to_dict()
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_info = ErrorInfo(
        url=str(request.url),
        message=str(exc),
        http_status="400"
    )
    return JSONResponse(
        status_code=400,
        content=error_info.to_dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    error_info = ErrorInfo(
        url=str(request.url),
        message="Internal server error",
        http_status="500"
    )
    return JSONResponse(
        status_code=500,
        content=error_info.to_dict()
    )

@app.exception_handler(OperationFailure)
async def mongodb_operation_failure_handler(request: Request, exc: OperationFailure):
    # Check for null byte error
    if "null byte" in str(exc).lower():
        error_info = ErrorInfo(
            url=str(request.url),
            message="Invalid character in query: null bytes are not allowed",
            http_status="400"
        )
        return JSONResponse(
            status_code=400,
            content=error_info.to_dict()
        )
    # Other MongoDB errors
    error_info = ErrorInfo(
        url=str(request.url),
        message="Invalid database query",
        http_status="400"
    )
    return JSONResponse(
        status_code=400,
        content=error_info.to_dict()
    )

@app.on_event("startup")
def startup_event():
    # Save config source for display in banner
    config_source = settings.show_config_source()
    
    # Clear terminal (works on most terminals)
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # ASCII Art Banner with animation
    ascii_banner = f"""
        {Fore.CYAN}
            ███╗   ██╗██╗███████╗████████╗    ██████╗ ███╗   ███╗███╗   ███╗
            ████╗  ██║██║██╔════╝╚══██╔══╝    ██╔══██╗████╗ ████║████╗ ████║
            ██╔██╗ ██║██║███████╗   ██║       ██████╔╝██╔████╔██║██╔████╔██║
            ██║╚██╗██║██║╚════██║   ██║       ██╔══██╗██║╚██╔╝██║██║╚██╔╝██║
            ██║ ╚████║██║███████║   ██║       ██║  ██║██║ ╚═╝ ██║██║ ╚═╝ ██║
            ╚═╝  ╚═══╝╚═╝╚══════╝   ╚═╝       ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝     ╚═╝
        {Style.RESET_ALL}
        {Fore.GREEN}  🚀 Resource Metadata Management Service - Ready for Requests 🚀{Style.RESET_ALL}
            ───────────────────────────────────────────────────────────────
    """
    # Print each line with a small delay for animation effect
    for line in ascii_banner.split('\n'):
        print(line)
        time.sleep(0.1)
    
    # Server details
    print(f"{Fore.YELLOW}    🔌 Server Status:{Style.RESET_ALL} {Fore.GREEN}Online{Style.RESET_ALL}")
    
    # Configuration source
    source_color = Fore.GREEN if "remote" in config_source else Fore.YELLOW
    print(f"{Fore.YELLOW}    ⚙️  Config Source:{Style.RESET_ALL} {source_color}{config_source}{Style.RESET_ALL}")
    
    # Database connection
    try:
        db = connect_db()
        print(f"{Fore.YELLOW}    🗄️  Database:{Style.RESET_ALL} {Fore.GREEN}Connected{Style.RESET_ALL} ({db.name})")
        
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        print(f"{Fore.YELLOW}    🗄️  Database:{Style.RESET_ALL} {Fore.RED}Connection Failed{Style.RESET_ALL}")
        print(f"{Fore.RED}    ⚠️  Error: {str(e)}{Style.RESET_ALL}")
    
    # Endpoints
    print(f"{Fore.YELLOW}    🛣️  Routes:{Style.RESET_ALL} {Fore.CYAN}/papers, /records, /fields, /code, /patents, /apis, /releasesets, /taxonomy, /versions{Style.RESET_ALL}")
    
    # Footer
    print(f"\n{Fore.BLUE}    📝 {time.strftime('%Y-%m-%d %H:%M:%S')} - NIST RMM API Started{Style.RESET_ALL}")
    print(f"{Fore.BLUE}    ───────────────────────────────────────────────────────────────{Style.RESET_ALL}\n")
    
    # Re-display important config info after the banner (won't be cleared)
    logger.info(f"Configuration source: {config_source}")
    logger.info(f"Database: {settings.DB_NAME} at {settings.MONGO_HOST}")
    logger.info(f"Metrics DB: {settings.METRICS_DB_NAME}")
    logger.info("NIST Resource Metadata Management API started successfully!")


@app.get("/debug/record-collection")
async def debug_record_collection():
    """Debug endpoint to test record collection directly"""
    from app.database import db
    from app.config import settings
    import json
    
    try:
        collection_name = settings.RECORDS_COLLECTION
        result = {
            "collection_name": collection_name,
            "exists": collection_name in db.list_collection_names(),
            "document_count": db[collection_name].count_documents({}),
            "collections": db.list_collection_names()
        }
        
        # Get sample document
        sample = db[collection_name].find_one({})
        if sample:
            # Convert ObjectId to string for JSON serialization
            sample["_id"] = str(sample["_id"])
            result["sample_document"] = sample
            
        return result
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        # Construct the absolute path to the index.html file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(base_dir, "index.html")
        
        # Read the HTML file with proper error handling
        try:
            with open(html_path, "r") as file:
                html_content = file.read()
        except FileNotFoundError:
            logger.error(f"Index.html file not found at path: {html_path}")
            raise ResourceNotFoundException(f"Homepage template not found")
        except Exception as e:
            logger.error(f"Error reading index.html: {e}")
            raise InternalServerException(f"Error reading homepage template: {str(e)}")
        
        return HTMLResponse(content=html_content)
    except (ResourceNotFoundException, InternalServerException):
        # Let the exception handlers handle these
        raise
    except Exception as e:
        logger.error(f"Unexpected error serving homepage: {e}")
        raise InternalServerException(f"Unexpected error serving homepage: {str(e)}")