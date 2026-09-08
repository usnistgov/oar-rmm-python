
"""Application entry point for the NIST Resource Metadata Management (RMM) API.

This module builds and configures the FastAPI ``app`` instance that is served by
Uvicorn/Gunicorn (see docker/entrypoint.sh and start.sh). It is responsible for:

- Wiring up all resource routers (records, fields, papers, code, patents, APIs,
  release sets, taxonomy, versions, usage metrics, facets).
- Serving a custom static Swagger/Redoc documentation page (index.html) instead
  of FastAPI's default docs UI, at both ``/`` and the ``/rmm`` root path prefix.
- Registering global exception handlers that translate internal exceptions
  (see app.middleware.exceptions) and MongoDB errors into JSON error responses
  with a consistent shape.
- Configuring cross-cutting middleware (GZip compression, optional CORS).
- Printing a startup banner and verifying database connectivity on boot.

Run directly (e.g. ``python -m app.main`` is not supported); the app is served via
an ASGI server that imports the module-level ``app`` object.
"""
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
from app.routers import paper, record, field, code, patent, api, releaseset, taxonomy, usagemetrics, version, facets
from app.config import settings
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.exceptions import (
    RMMException, ResourceNotFoundException, KeyWordNotFoundException, 
    IllegalArgumentException, GeneralException, InternalServerException, ErrorInfo
)

from pymongo.errors import OperationFailure
from app.logging_setup import setup_logging
import os
import base64
import logging
import time
from colorama import init, Fore, Style

init()

logger = logging.getLogger(__name__)

FAVICON_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager that runs startup/shutdown hooks.

    On startup, configures logging and runs :func:`startup_event` (which prints
    the banner and verifies the database connection). On shutdown, logs a
    shutdown message. Registered via ``FastAPI(lifespan=lifespan)``.

    Args:
        app: The FastAPI application instance being started (unused directly,
            required by the lifespan context manager signature).

    Yields:
        None. Control is yielded back to FastAPI while the app serves requests;
        code after the ``yield`` runs during shutdown.
    """
    setup_logging()
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
    """Build the HTML response serving the pre-rendered API documentation page.

    The page content is read once at import time from ``app/index.html`` and
    cached in ``_DOCS_HTML_CONTENT`` to avoid a disk read on every request.

    Returns:
        HTMLResponse: The static documentation page content.
    """
    return HTMLResponse(content=_DOCS_HTML_CONTENT)


@app.get("/", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    """Serve the custom documentation page at the site root (``/``).

    Args:
        request: The incoming request (unused, required by FastAPI's route
            signature convention).

    Returns:
        HTMLResponse: The static documentation page content.
    """
    return docs_html_response()

@app.head("/", include_in_schema=False)
async def head_swagger_ui_html():
    """Respond to HEAD requests at ``/`` with the same headers as the GET route.

    Returns:
        Response: An empty-body 200 response carrying the ``Content-Length``
        and ``Content-Type`` headers that a GET to ``/`` would return, so HEAD
        clients can check availability without downloading the full page.
    """
    return Response(status_code=200, headers={"Content-Length": _DOCS_CONTENT_LENGTH, "Content-Type": "text/html; charset=utf-8"})

@app.get("/rmm/", include_in_schema=False)
async def custom_swagger_ui_html_rmm(request: Request):
    """Serve the custom documentation page under the ``/rmm/`` root prefix.

    Mirrors :func:`custom_swagger_ui_html` for deployments where the API is
    reverse-proxied behind the ``/rmm`` path prefix.

    Args:
        request: The incoming request (unused).

    Returns:
        HTMLResponse: The static documentation page content.
    """
    return docs_html_response()

@app.head("/rmm/", include_in_schema=False)
async def head_swagger_ui_html_rmm():
    """Respond to HEAD requests at ``/rmm/`` with the same headers as the GET route.

    Returns:
        Response: An empty-body 200 response with ``Content-Length`` and
        ``Content-Type`` headers matching the GET ``/rmm/`` response.
    """
    return Response(status_code=200, headers={"Content-Length": _DOCS_CONTENT_LENGTH, "Content-Type": "text/html; charset=utf-8"})

@app.get("/openapi.json", include_in_schema=False)
async def openapi_schema():
    """Return the generated OpenAPI schema as JSON at the default path.

    Returns:
        JSONResponse: The OpenAPI schema produced by :func:`custom_openapi`.
    """
    return JSONResponse(app.openapi())

@app.get("/rmm/openapi.json", include_in_schema=False)
async def openapi_schema_rmm():
    """Return the generated OpenAPI schema as JSON under the ``/rmm`` prefix.

    Returns:
        JSONResponse: The OpenAPI schema produced by :func:`custom_openapi`.
    """
    return JSONResponse(app.openapi())

def custom_openapi():
    """Generate (and cache) the OpenAPI schema, overriding ``app.openapi``.

    Builds the schema on first call via ``fastapi.openapi.utils.get_openapi``,
    injects a ``servers`` entry pointing at ``ROOT_PREFIX`` so that generated
    client requests are correctly prefixed with ``/rmm``, and caches the result
    on ``app.openapi_schema`` so subsequent calls are free. Assigned to
    ``app.openapi`` below to replace FastAPI's default schema generator.

    Returns:
        dict: The OpenAPI schema document.
    """
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

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Router for ``field`` needs to come before ``record`` to avoid field queries to get
# caught in the `record` router
app.include_router(field.router) 
app.include_router(record.router)
app.include_router(facets.router)
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
    """Translate :class:`~app.middleware.exceptions.ResourceNotFoundException` into a 404 JSON response.

    Args:
        request: The request that triggered the exception (used for the ``url`` field).
        exc: The raised exception instance.

    Returns:
        JSONResponse: HTTP 404 with an :class:`ErrorInfo` payload.
    """
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
    """Translate :class:`~app.middleware.exceptions.KeyWordNotFoundException` into a 404 JSON response.

    Args:
        request: The request that triggered the exception.
        exc: The raised exception instance.

    Returns:
        JSONResponse: HTTP 404 with an :class:`ErrorInfo` payload.
    """
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
    """Translate :class:`~app.middleware.exceptions.IllegalArgumentException` into a 400 JSON response.

    Args:
        request: The request that triggered the exception.
        exc: The raised exception instance.

    Returns:
        JSONResponse: HTTP 400 with an :class:`ErrorInfo` payload.
    """
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
    """Translate :class:`~app.middleware.exceptions.InternalServerException` into a 500 JSON response.

    Args:
        request: The request that triggered the exception.
        exc: The raised exception instance.

    Returns:
        JSONResponse: HTTP 500 with an :class:`ErrorInfo` payload.
    """
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
    """Translate FastAPI/pydantic request validation errors into a 400 JSON response.

    Overrides FastAPI's default validation error handler so that malformed
    request parameters return the application's standard :class:`ErrorInfo`
    shape instead of the default ``{"detail": [...]}`` structure.

    Args:
        request: The request that failed validation.
        exc: The validation error raised by FastAPI.

    Returns:
        JSONResponse: HTTP 400 with an :class:`ErrorInfo` payload.
    """
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
    """Catch-all handler for any unhandled exception, returning a generic 500 response.

    Acts as a safety net so unexpected errors never leak stack traces or
    internal details to clients; the real error is expected to already have
    been logged by the code that raised it.

    Args:
        request: The request being processed when the exception occurred.
        exc: The unhandled exception.

    Returns:
        JSONResponse: HTTP 500 with a generic "Internal server error" message.
    """
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
    """Translate raw pymongo :class:`~pymongo.errors.OperationFailure` errors into JSON responses.

    MongoDB operation errors (e.g. malformed queries, invalid characters such
    as null bytes) would otherwise surface as unhandled 500s via the generic
    handler; this gives a more specific 400 response for the common
    null-byte-in-query case and a general 400 for other query errors.

    Args:
        request: The request that triggered the database error.
        exc: The pymongo operation failure.

    Returns:
        JSONResponse: HTTP 400 with an :class:`ErrorInfo` payload describing
        an invalid query.
    """
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
    """Run application startup diagnostics: print the banner and verify the database.

    Clears the terminal, prints an ASCII-art banner with server/config/database
    status, attempts a database connection via :func:`app.database.connect_db`
    (logging and printing a failure notice if it cannot connect, without
    aborting startup), and logs a summary of the effective configuration.
    Invoked once from :func:`lifespan` during application startup.
    """
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
    """Diagnostic endpoint reporting the state of the records collection.

    Intended for manual troubleshooting during development/deployment (not
    part of the public API surface — not documented in the OpenAPI schema
    beyond its default inclusion). Reports whether the configured records
    collection exists, its document count, the list of all collections in the
    database, and one sample document (with its ``_id`` stringified).

    Returns:
        dict: Diagnostic info, or ``{"error": str}`` if the query fails.
    """
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
    """Serve a favicon from an embedded base64-encoded PNG rather than a static file.

    Returns:
        Response: The decoded PNG image bytes with ``image/png`` media type.
    """
    return Response(content=base64.b64decode(FAVICON_PNG_BASE64), media_type="image/png")

