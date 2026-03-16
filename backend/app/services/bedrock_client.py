import asyncio
import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from app.config import AWS_REGION, NOVA_MODEL_ID, NOVA_PRO_MODEL_ID, NOVA_EMBED_MODEL_ID, BEDROCK_GUARDRAIL_ID, BEDROCK_GUARDRAIL_VERSION

logger = logging.getLogger(__name__)

# Transient error codes worth retrying
_RETRYABLE_ERRORS = ("ThrottlingException", "ServiceUnavailableException", "ModelTimeoutException")
_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds
_MAX_CONCURRENT_BEDROCK = 5  # prevent thundering-herd throttles

# Async-safe concurrency primitives
_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_BEDROCK)
_executor = ThreadPoolExecutor(max_workers=_MAX_CONCURRENT_BEDROCK)


def _retry_with_backoff(fn, max_retries=_MAX_RETRIES):
    """Execute fn with exponential backoff + jitter on transient Bedrock errors."""
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in _RETRYABLE_ERRORS and attempt < max_retries:
                delay = _BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Bedrock transient error ({error_code}), "
                    f"retry {attempt + 1}/{max_retries} in {delay:.1f}s"
                )
                time.sleep(delay)  # OK: runs inside ThreadPoolExecutor, not on event loop
            else:
                raise


class BedrockClient:
    def __init__(self):
        boto_config = BotoConfig(
            read_timeout=120,
            connect_timeout=10,
            retries={"max_attempts": 0},  # we handle retries ourselves
        )
        self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION, config=boto_config)
        self.model_id = NOVA_MODEL_ID
        self.pro_model_id = NOVA_PRO_MODEL_ID
        self.embed_model_id = NOVA_EMBED_MODEL_ID

    def check_connection(self) -> bool:
        try:
            self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": "hi"}]}],
                inferenceConfig={"maxTokens": 10},
            )
            return True
        except Exception as e:
            logger.warning(f"Bedrock connection check failed: {e}")
            return False

    async def check_connection_async(self) -> bool:
        """Async wrapper for check_connection — runs off the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self.check_connection)

    def converse(
        self,
        messages: list[dict],
        system: str | None = None,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        guardrail: bool = False,
        model_id: str | None = None,
    ) -> dict:
        effective_model = model_id or self.model_id
        kwargs: dict = {
            "modelId": effective_model,
            "messages": messages,
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system:
            kwargs["system"] = [{"text": system}]
        if tools:
            kwargs["toolConfig"] = {"tools": tools}
        if guardrail and BEDROCK_GUARDRAIL_ID:
            kwargs["guardrailConfig"] = {
                "guardrailIdentifier": BEDROCK_GUARDRAIL_ID,
                "guardrailVersion": BEDROCK_GUARDRAIL_VERSION,
                "trace": "enabled",
            }

        start = time.time()
        try:
            response = _retry_with_backoff(lambda: self.client.converse(**kwargs))
            latency = time.time() - start
            request_id = response.get("ResponseMetadata", {}).get("RequestId", "n/a")
            usage = response.get("usage", {})
            logger.info(
                f"Bedrock converse | model={effective_model} "
                f"latency={latency:.2f}s request_id={request_id} "
                f"input_tokens={usage.get('inputTokens', '?')} "
                f"output_tokens={usage.get('outputTokens', '?')}"
            )
            # Check for guardrail intervention
            guardrail_trace = response.get("trace", {}).get("guardrail", {})
            if guardrail_trace:
                logger.info(f"Bedrock guardrail trace | action={guardrail_trace.get('action', 'none')}")
            return response
        except ClientError as e:
            latency = time.time() - start
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", "")
            request_id = e.response.get("ResponseMetadata", {}).get("RequestId", "n/a")
            logger.error(
                f"Bedrock converse FAILED | model={effective_model} "
                f"error={error_code} message={error_msg} latency={latency:.2f}s request_id={request_id}"
            )
            # Fallback: if a non-default model failed, retry with the default (Lite) model
            if effective_model != self.model_id and error_code == "ValidationException":
                logger.warning(f"Falling back from {effective_model} to {self.model_id}")
                kwargs["modelId"] = self.model_id
                try:
                    response = _retry_with_backoff(lambda: self.client.converse(**kwargs))
                    latency = time.time() - start
                    logger.info(f"Bedrock converse FALLBACK OK | model={self.model_id} latency={latency:.2f}s")
                    return response
                except ClientError:
                    pass  # let original error propagate
            raise

    async def converse_async(
        self,
        messages: list[dict],
        system: str | None = None,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        guardrail: bool = False,
        model_id: str | None = None,
    ) -> dict:
        """Async wrapper: runs synchronous converse() in a thread pool to avoid blocking the event loop."""
        async with _semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _executor,
                lambda: self.converse(messages, system, tools, max_tokens, temperature, guardrail, model_id),
            )

    def converse_stream(
        self,
        messages: list[dict],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ):
        """Stream response tokens from Nova via ConverseStream. Yields text chunks."""
        kwargs: dict = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        if system:
            kwargs["system"] = [{"text": system}]

        start = time.time()
        try:
            response = _retry_with_backoff(
                lambda: self.client.converse_stream(**kwargs)
            )
            stream = response.get("stream")
            if stream:
                for event in stream:
                    if "contentBlockDelta" in event:
                        delta = event["contentBlockDelta"].get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            yield text
            latency = time.time() - start
            logger.info(f"Bedrock converse_stream | model={self.model_id} latency={latency:.2f}s")
        except ClientError as e:
            latency = time.time() - start
            error_code = e.response.get("Error", {}).get("Code", "")
            logger.error(f"Bedrock converse_stream FAILED | error={error_code} latency={latency:.2f}s")
            raise

    async def converse_stream_async(
        self,
        messages: list[dict],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        on_chunk=None,
    ):
        """Async streaming: runs converse_stream in a thread, calling on_chunk for each token.

        on_chunk is a sync callable; use this when you need to bridge sync streaming
        into an async context without blocking the event loop.
        Returns the full concatenated text.
        """
        def _run():
            chunks = []
            for chunk in self.converse_stream(messages, system, max_tokens, temperature):
                chunks.append(chunk)
                if on_chunk:
                    on_chunk(chunk)
            return "".join(chunks)

        async with _semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(_executor, _run)

    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector using Nova Embed."""
        body = json.dumps({
            "taskType": "SINGLE_EMBEDDING",
            "singleEmbeddingParams": {
                "embeddingPurpose": "GENERIC_INDEX",
                "embeddingDimension": 384,
                "text": {
                    "truncationMode": "END",
                    "value": text,
                },
            },
        })
        start = time.time()
        try:
            response = _retry_with_backoff(
                lambda: self.client.invoke_model(
                    modelId=self.embed_model_id,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )
            )
            latency = time.time() - start
            logger.info(f"Bedrock embed | model={self.embed_model_id} latency={latency:.2f}s")
            result = json.loads(response["body"].read())
            return result["embeddings"][0]["embedding"]
        except Exception as e:
            latency = time.time() - start
            logger.error(f"Bedrock embed FAILED | model={self.embed_model_id} latency={latency:.2f}s error={e}")
            raise

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts (synchronous, sequential)."""
        return [self.embed(t) for t in texts]

    async def embed_batch_async(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in parallel using asyncio.gather."""
        loop = asyncio.get_event_loop()

        async def _embed_one(text: str) -> list[float]:
            async with _semaphore:
                return await loop.run_in_executor(_executor, self.embed, text)

        return list(await asyncio.gather(*[_embed_one(t) for t in texts]))

    def converse_with_document(
        self,
        pdf_bytes: bytes,
        prompt: str,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        guardrail: bool = False,
    ) -> dict:
        """Send a PDF document to Nova via the Converse API document content block."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "document": {
                            "format": "pdf",
                            "name": "degree_requirements",
                            "source": {"bytes": pdf_bytes},
                        }
                    },
                    {"text": prompt},
                ],
            }
        ]
        return self.converse(messages=messages, tools=tools, max_tokens=max_tokens, guardrail=guardrail)

    async def converse_with_document_async(
        self,
        pdf_bytes: bytes,
        prompt: str,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        guardrail: bool = False,
    ) -> dict:
        """Async wrapper for converse_with_document — runs off the event loop."""
        async with _semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _executor,
                lambda: self.converse_with_document(pdf_bytes, prompt, tools, max_tokens, guardrail),
            )

    def converse_with_image(
        self,
        image_bytes: bytes,
        image_format: str,
        prompt: str,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        guardrail: bool = False,
    ) -> dict:
        """Send an image to Nova via the Converse API image content block (multimodal).

        Supports png, jpeg, webp formats — enables parsing degree audits from
        screenshots, photos, and scanned documents.
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": image_format,
                            "source": {"bytes": image_bytes},
                        }
                    },
                    {"text": prompt},
                ],
            }
        ]
        return self.converse(messages=messages, tools=tools, max_tokens=max_tokens, guardrail=guardrail)

    async def converse_with_image_async(
        self,
        image_bytes: bytes,
        image_format: str,
        prompt: str,
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        guardrail: bool = False,
    ) -> dict:
        """Async multimodal image analysis via Nova's vision capability."""
        async with _semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _executor,
                lambda: self.converse_with_image(image_bytes, image_format, prompt, tools, max_tokens, guardrail),
            )

    def generate_image(self, prompt: str, width: int = 1024, height: int = 1024) -> bytes:
        """Generate an image using Nova Canvas (text-to-image).

        Used to create visual semester roadmap infographics for double major/minor plans
        that students can download and share with their advisor.
        """
        from app.config import NOVA_CANVAS_MODEL_ID
        import json as _json
        body = _json.dumps({
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {"text": prompt},
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "width": width,
                "height": height,
                "quality": "standard",
            },
        })
        start = time.time()
        try:
            response = _retry_with_backoff(
                lambda: self.client.invoke_model(
                    modelId=NOVA_CANVAS_MODEL_ID,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )
            )
            latency = time.time() - start
            logger.info(f"Bedrock Canvas | model={NOVA_CANVAS_MODEL_ID} latency={latency:.2f}s")
            result = _json.loads(response["body"].read())
            import base64
            return base64.b64decode(result["images"][0])
        except Exception as e:
            latency = time.time() - start
            logger.error(f"Bedrock Canvas FAILED | latency={latency:.2f}s error={e}")
            raise

    async def generate_image_async(self, prompt: str, width: int = 1024, height: int = 1024) -> bytes:
        """Async wrapper for Canvas image generation."""
        async with _semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _executor,
                lambda: self.generate_image(prompt, width, height),
            )

    def converse_with_documents(
        self,
        pdf_bytes_1: bytes,
        pdf_bytes_2: bytes,
        prompt: str,
        tools: list[dict] | None = None,
        max_tokens: int = 8192,
        guardrail: bool = False,
    ) -> dict:
        """Send two PDF documents in a single Converse call for side-by-side comparison.

        Used for double major/minor overlap analysis — compares two degree requirement
        PDFs simultaneously so Nova can identify shared courses, equivalent requirements,
        and optimal course-sharing strategies.
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "document": {
                            "format": "pdf",
                            "name": "degree_requirements_1",
                            "source": {"bytes": pdf_bytes_1},
                        }
                    },
                    {
                        "document": {
                            "format": "pdf",
                            "name": "degree_requirements_2",
                            "source": {"bytes": pdf_bytes_2},
                        }
                    },
                    {"text": prompt},
                ],
            }
        ]
        return self.converse(messages=messages, tools=tools, max_tokens=max_tokens, guardrail=guardrail)

    async def converse_with_documents_async(
        self,
        pdf_bytes_1: bytes,
        pdf_bytes_2: bytes,
        prompt: str,
        tools: list[dict] | None = None,
        max_tokens: int = 8192,
        guardrail: bool = False,
    ) -> dict:
        """Async wrapper for multi-document comparison."""
        async with _semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _executor,
                lambda: self.converse_with_documents(pdf_bytes_1, pdf_bytes_2, prompt, tools, max_tokens, guardrail),
            )

    def converse_with_video(
        self,
        video_bytes: bytes,
        video_format: str,
        prompt: str,
        tools: list[dict] | None = None,
        max_tokens: int = 8192,
        guardrail: bool = False,
    ) -> dict:
        """Analyze a video using Nova's video understanding capability.

        Used for parsing degree audits from screen recordings of university portals.
        Students record their screen scrolling through the degree audit page,
        and Nova extracts structured course data from the video frames.
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "video": {
                            "format": video_format,
                            "source": {"bytes": video_bytes},
                        }
                    },
                    {"text": prompt},
                ],
            }
        ]
        return self.converse(messages=messages, tools=tools, max_tokens=max_tokens, guardrail=guardrail)

    async def converse_with_video_async(
        self,
        video_bytes: bytes,
        video_format: str,
        prompt: str,
        tools: list[dict] | None = None,
        max_tokens: int = 8192,
        guardrail: bool = False,
    ) -> dict:
        """Async video analysis via Nova's video understanding."""
        async with _semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                _executor,
                lambda: self.converse_with_video(video_bytes, video_format, prompt, tools, max_tokens, guardrail),
            )

    async def embed_async(self, text: str) -> list[float]:
        """Async wrapper for embed — runs off the event loop."""
        async with _semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(_executor, self.embed, text)

    def extract_text_response(self, response: dict) -> str:
        """Extract text from a Converse API response."""
        output = response.get("output", {})
        message = output.get("message", {})
        for block in message.get("content", []):
            if "text" in block:
                return block["text"]
        return ""

    def extract_tool_use(self, response: dict) -> dict | None:
        """Extract tool use input from a Converse API response."""
        output = response.get("output", {})
        message = output.get("message", {})
        for block in message.get("content", []):
            if "toolUse" in block:
                return block["toolUse"].get("input", {})
        return None


# Singleton — use MockBedrockClient in demo mode for deterministic local operation
def _create_client():
    from app.config import DEMO_MODE
    if DEMO_MODE:
        from app.services.mock_bedrock import MockBedrockClient
        return MockBedrockClient()
    return BedrockClient()

bedrock = _create_client()
