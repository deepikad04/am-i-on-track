import asyncio
import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Assigns a UUID4 request ID to every request and logs request details."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "method=%s path=%s status_code=%s duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-user concurrency limiter using asyncio.Semaphore."""

    def __init__(self, app, max_concurrent: int = 5):
        super().__init__(app)
        self.max_concurrent = max_concurrent
        # token_string -> (semaphore, last_seen_timestamp)
        self._semaphores: dict[str, tuple[asyncio.Semaphore, float]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = 300  # 5 minutes
        self._cleanup_task: asyncio.Task | None = None

    async def dispatch(self, request: Request, call_next):
        # Lazily start the cleanup task
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

        token = self._extract_token(request)
        if token is None:
            # No auth header -- let the request through without concurrency limiting
            return await call_next(request)

        semaphore = await self._get_semaphore(token)

        # Non-blocking acquire: reject immediately if at capacity
        if semaphore._value <= 0:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many concurrent requests. Please wait."},
            )
        await semaphore.acquire()  # guaranteed not to block since _value > 0

        try:
            response = await call_next(request)
            return response
        finally:
            semaphore.release()

    @staticmethod
    def _extract_token(request: Request) -> str | None:
        auth = request.headers.get("authorization")
        if not auth:
            return None
        # Strip "Bearer " prefix if present, otherwise use the raw value
        parts = auth.split(None, 1)
        return parts[1] if len(parts) > 1 else parts[0]

    async def _get_semaphore(self, token: str) -> asyncio.Semaphore:
        async with self._lock:
            now = time.monotonic()
            if token in self._semaphores:
                sem, _ = self._semaphores[token]
                self._semaphores[token] = (sem, now)
                return sem
            sem = asyncio.Semaphore(self.max_concurrent)
            self._semaphores[token] = (sem, now)
            return sem

    async def _periodic_cleanup(self):
        """Remove semaphores for users not seen in the last 5 minutes."""
        while True:
            await asyncio.sleep(self._cleanup_interval)
            now = time.monotonic()
            async with self._lock:
                stale = [
                    token
                    for token, (_, last_seen) in self._semaphores.items()
                    if now - last_seen > self._cleanup_interval
                ]
                for token in stale:
                    del self._semaphores[token]
                if stale:
                    logger.info("Cleaned up %d stale rate-limit semaphores", len(stale))
