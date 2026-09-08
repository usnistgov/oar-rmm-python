"""Starlette middleware that records download metrics for record-lookup requests.

NOTE: This middleware is currently defined but **not** registered on the app
(see the commented-out ``app.add_middleware(MetricsMiddleware)`` line in
``app.main``). It also calls ``metrics_crud.record_download(...)``, a method
that is not defined on :class:`~app.crud.metrics.MetricsCRUD` in the current
codebase — enabling this middleware as-is would raise an ``AttributeError``
on every record lookup. Usage metrics are populated by other means in the
current deployment; this module is kept for potential future rework.
"""
import time
import json
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.crud.metrics import metrics_crud
from starlette.responses import Response
import urllib.parse
from datetime import datetime

logger = logging.getLogger(__name__)

class MetricsMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that detects record-lookup requests and logs a download metric.

    Recognizes two request shapes as a "record lookup": path-based
    (``GET /records/{id}`` with no query params) and query-based
    (``GET /records?@id=...``). For those, it reads the response body to
    extract the record's ``ediid`` and forwards a download event to
    :func:`app.crud.metrics.metrics_crud.record_download`. All other requests
    pass through unmodified.
    """

    async def dispatch(self, request: Request, call_next):
        """Intercept a request/response cycle to record metrics for record lookups.

        Args:
            request: The incoming Starlette request.
            call_next: Callable that invokes the next middleware/route handler
                and returns its response.

        Returns:
            Response: The (possibly reconstructed) response to send to the
            client. Reconstruction is necessary because the response body
            stream is consumed while extracting metrics data.
        """
        # Record request start time
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate request duration
        duration = time.time() - start_time
        
        try:
            path = request.url.path
            
            # Check for query parameters
            has_query_params = len(request.query_params) > 0
            
            # Extract user agent and referrer
            user_agent = request.headers.get("user-agent", "")
            referrer = request.headers.get("referer", "")
            
            # Case 1: Direct record path lookup (/records/{id})
            if (path.startswith("/records/") and 
                path.count("/") == 2 and 
                request.method == "GET" and 
                not has_query_params):
                
                # Extract record ID from path (/records/{id})
                record_id = path.split("/")[2]
                
                logger.info(f"Recording metrics for path-based record lookup: {record_id}")
                
                # Process and record metrics
                return await self._process_record_metrics(response, record_id, request.client.host, 
                                                        user_agent, referrer)
                
            # Case 2: Query parameter record lookup (/records?@id=ark:/88434/mds007zd70)  
            elif (path in ["/records", "/records/"] and 
                  request.method == "GET" and 
                  has_query_params and 
                  "@id" in request.query_params):
                
                # Get record ID from query parameter
                record_id = request.query_params["@id"]
                
                logger.info(f"Recording metrics for query-based record lookup: {record_id}")
                
                # Process and record metrics
                return await self._process_record_metrics(response, record_id, request.client.host,
                                                        user_agent, referrer)
                
            else:
                # Debug logging for non-tracked requests
                if path.startswith("/records"):
                    query_params = dict(request.query_params)
                    logger.debug(f"Not tracking metrics for path: {path} with params: {query_params}")
                    
        except Exception as e:
            logger.error(f"Error in metrics middleware: {str(e)}")
            
        return response
        
    async def _process_record_metrics(self, response, record_id, client_ip, user_agent="", referrer=""):
        """Extract metrics from a record-lookup response and forward them for recording.

        Reads and re-assembles the streamed response body in order to parse
        the ``ediid`` out of the JSON payload, then calls
        ``metrics_crud.record_download`` with the collected metadata.

        Args:
            response: The original response produced by the route handler.
            record_id: The record identifier extracted from the request path
                or query string.
            client_ip: IP address of the requesting client.
            user_agent: Value of the ``User-Agent`` request header.
            referrer: Value of the ``Referer`` request header.

        Returns:
            Response: A reconstructed response with the same body, status
            code, headers, and media type as the original — or the original
            response unchanged if metrics processing fails.
        """
        try:
            # Clone the response to read the body
            resp_body = b""
            async for chunk in response.body_iterator:
                resp_body += chunk
            
            # Parse response JSON
            resp_data = json.loads(resp_body.decode())
            
            # Get EDIID from response data
            ediid = None
            if isinstance(resp_data, dict):
                if "ediid" in resp_data:
                    ediid = resp_data.get("ediid", record_id)
                elif "ResultData" in resp_data and isinstance(resp_data["ResultData"], list) and resp_data["ResultData"]:
                    ediid = resp_data["ResultData"][0].get("ediid", record_id)
            
            # Record the download - handle URL encoding in IDs
            pdrid = record_id
            if "ark%3A" in pdrid:
                pdrid = pdrid.replace("ark%3A", "ark:")
                
            # Log what we're recording
            logger.info(f"Recording metrics - PDRID: {pdrid}, EDIID: {ediid or pdrid}")
            
            # Record the download in the original metrics collection
            metrics_crud.record_download(
                pdrid=pdrid,
                ediid=ediid or pdrid,
                ip_address=client_ip,
                user_agent=user_agent,
                referrer=referrer,
                timestamp=datetime.now(),
                download_size=len(resp_body)
            )
            
            # Create a new response with the same content
            return Response(
                content=resp_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
        except Exception as e:
            logger.error(f"Error processing response for metrics: {str(e)}")
            # Return the original response if we can't modify it
            return response