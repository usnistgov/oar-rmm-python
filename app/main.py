
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from pathlib import Path
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
import base64
import logging
import time
from colorama import init, Fore, Style

init()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    startup_event()
    yield
    logger.info("NIST Resource Metadata Management API shutting down...")

app = FastAPI(
    title="NIST Resource Metadata Management API",
    description="These are the set of REST API endpoints which are used to get metadata of various resources especially used to search and discove for Public data repository(PDR). ",
    version="0.0.1",
    docs_url=None,
    lifespan=lifespan,
    contact={
        "name": "Data Support @NIST",
        "url": "https://data.nist.gov/sdp/#/help",
        "email": "datasupport@nist.gov",
    },
    license_info={
        "name": "NIST Software",
        "url": "https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications",
    }
)

ROOT_PREFIX = "/rmm"
APP_DIR = Path(__file__).resolve().parent
DOCS_HTML_PATH = APP_DIR / "index.html"

app.mount(
    "/static",
    StaticFiles(directory=str(APP_DIR / "static")),
    name="static"
)
app.mount(
    f"{ROOT_PREFIX}/static",
    StaticFiles(directory=str(APP_DIR / "static")),
    name="static-root"
)


_DOCS_HTML_CONTENT: str = DOCS_HTML_PATH.read_text(encoding="utf-8")
_DOCS_CONTENT_LENGTH: str = str(len(_DOCS_HTML_CONTENT.encode("utf-8")))


def docs_html_response() -> HTMLResponse:
    return HTMLResponse(content=_DOCS_HTML_CONTENT)


@app.get("/", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    return docs_html_response()

@app.head("/", include_in_schema=False)
async def head_swagger_ui_html():
    return Response(status_code=200, headers={"Content-Length": _DOCS_CONTENT_LENGTH, "Content-Type": "text/html; charset=utf-8"})

@app.get("/rmm/", include_in_schema=False)
async def custom_swagger_ui_html_rmm(request: Request):
    return docs_html_response()

@app.head("/rmm/", include_in_schema=False)
async def head_swagger_ui_html_rmm():
    return Response(status_code=200, headers={"Content-Length": _DOCS_CONTENT_LENGTH, "Content-Type": "text/html; charset=utf-8"})

@app.get("/openapi.json", include_in_schema=False)
async def openapi_schema():
    return JSONResponse(app.openapi())

@app.get("/rmm/openapi.json", include_in_schema=False)
async def openapi_schema_rmm():
    return JSONResponse(app.openapi())

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["servers"] = [{"url": ROOT_PREFIX}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi

app.add_middleware(
    GZipMiddleware,
    minimum_size=int(settings.GZIP_MINIMUM_SIZE)
)

# Router for ``field`` needs to come before ``record`` to avoid field queries to get
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
    
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return Response(content=base64.b64decode(FAVICON_PNG_BASE64), media_type="image/png")

