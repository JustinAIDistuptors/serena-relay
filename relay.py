#!/usr/bin/env python3
"""
Serena Relay Server
This file implements a relay server for the Serena MCP server with streaming support.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.responses import PlainTextResponse
import httpx
import uvicorn

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("serena-relay")

# Get environment variables
UPSTREAM_URL = os.environ.get("UPSTREAM_URL", "https://serena-mcp.fly.dev")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "serena")
KEEP_ALIVE_INTERVAL = 10  # seconds

# Create FastAPI app
app = FastAPI(
    title="Serena Relay",
    description="A relay server for the Serena MCP server with streaming support",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define OpenAPI schema for Serena functions
SERENA_FUNCTIONS = {
    "find_symbol": {
        "description": "Find symbols in code repositories",
        "parameters": {
            "query": {
                "type": "string",
                "description": "Search query for finding symbols"
            },
            "repo_path": {
                "type": "string",
                "description": "Path to the repository to search in"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return"
            }
        },
        "example": {
            "function_call": {
                "name": "find_symbol",
                "parameters": {
                    "query": "function getUser",
                    "repo_path": "/path/to/repo",
                    "limit": 10
                }
            }
        }
    },
    "search_code": {
        "description": "Search for code with semantic understanding",
        "parameters": {
            "query": {
                "type": "string",
                "description": "Natural language query to search for code"
            },
            "repo_path": {
                "type": "string",
                "description": "Path to the repository to search in"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return"
            }
        },
        "example": {
            "function_call": {
                "name": "search_code",
                "parameters": {
                    "query": "how to handle authentication",
                    "repo_path": "/path/to/repo",
                    "limit": 5
                }
            }
        }
    },
    "write_file": {
        "description": "Write content to a file",
        "parameters": {
            "filepath": {
                "type": "string",
                "description": "Path to the file to write"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        },
        "example": {
            "function_call": {
                "name": "write_file",
                "parameters": {
                    "filepath": "/path/to/file.txt",
                    "content": "Hello, world!"
                }
            }
        }
    },
    "read_file": {
        "description": "Read content from a file",
        "parameters": {
            "filepath": {
                "type": "string",
                "description": "Path to the file to read"
            }
        },
        "example": {
            "function_call": {
                "name": "read_file",
                "parameters": {
                    "filepath": "/path/to/file.txt"
                }
            }
        }
    }
}

@app.get("/openapi.json")
async def get_openapi_schema(request: Request):
    """Return OpenAPI schema for Serena functions"""
    schema = {
        "openapi": "3.0.0",
        "info": {
            "title": "Serena API",
            "description": "API for code search and manipulation",
            "version": "1.0.0"
        },
        "security": [{"none": []}],
        "components": {
            "securitySchemes": {
                "none": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "No authentication required. This API is open."
                }
            }
        },
        "paths": {
            f"/proxy/{function_name}": {
                "post": {
                    "summary": function_info["description"],
                    "security": [{"none": []}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "function_call": {
                                            "type": "object",
                                            "properties": {
                                                "name": {
                                                    "type": "string",
                                                    "enum": [function_name]
                                                },
                                                "parameters": {
                                                    "type": "object",
                                                    "properties": function_info["parameters"]
                                                }
                                            },
                                            "required": ["name", "parameters"]
                                        }
                                    },
                                    "required": ["function_call"]
                                },
                                "example": function_info["example"]
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object"
                                    }
                                }
                            }
                        }
                    }
                }
            }
            for function_name, function_info in SERENA_FUNCTIONS.items()
        }
    }
    
    # Check if client prefers text format
    accept_header = request.headers.get("accept", "")
    if "text/" in accept_header:
        return Response(content=json.dumps(schema, indent=2), media_type="text/plain; charset=utf-8")
    else:
        return JSONResponse(content=schema)

@app.get("/openapi.txt")
async def get_openapi_schema_text():
    """Return OpenAPI schema as plain text for LLM tooling"""
    schema = {
        "openapi": "3.0.0",
        "info": {
            "title": "Serena API",
            "description": "API for code search and manipulation",
            "version": "1.0.0"
        },
        "security": [{"none": []}],
        "components": {
            "securitySchemes": {
                "none": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "No authentication required. This API is open."
                }
            }
        },
        "paths": {
            f"/proxy/{function_name}": {
                "post": {
                    "summary": function_info["description"],
                    "security": [{"none": []}],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "function_call": {
                                            "type": "object",
                                            "properties": {
                                                "name": {
                                                    "type": "string",
                                                    "enum": [function_name]
                                                },
                                                "parameters": {
                                                    "type": "object",
                                                    "properties": function_info["parameters"]
                                                }
                                            },
                                            "required": ["name", "parameters"]
                                        }
                                    },
                                    "required": ["function_call"]
                                },
                                "example": function_info["example"]
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object"
                                    }
                                }
                            }
                        }
                    }
                }
            }
            for function_name, function_info in SERENA_FUNCTIONS.items()
        }
    }
    
    # Use chunked encoding for faster initial response
    schema_json = json.dumps(schema, indent=2)
    
    async def generate_chunked_response():
        # Send the first chunk immediately (first 1000 characters)
        first_chunk = schema_json[:1000]
        yield first_chunk.encode()
        
        # Send the rest in chunks
        remaining = schema_json[1000:]
        chunk_size = 1000
        for i in range(0, len(remaining), chunk_size):
            chunk = remaining[i:i+chunk_size]
            yield chunk.encode()
            # Small delay to ensure chunked encoding is used
            await asyncio.sleep(0.01)
    
    return StreamingResponse(
        generate_chunked_response(),
        media_type="text/plain; charset=utf-8",
        headers={"Transfer-Encoding": "chunked"}
    )

@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint"""
    accept_header = request.headers.get("accept", "")
    if "application/health" in accept_header:
        return Response(status_code=204, media_type="application/health+json")
    else:
        return {"ok": True}

async def stream_with_keepalive(response_stream, keep_alive_interval=KEEP_ALIVE_INTERVAL):
    """Stream response with keep-alive messages to prevent timeouts"""
    try:
        async for chunk in response_stream:
            yield chunk
            
        # After the main content is streamed, send keep-alive messages
        while True:
            # Send an empty comment as keep-alive
            yield b"\n"  # Send a newline as keep-alive
            await asyncio.sleep(keep_alive_interval)
    except asyncio.CancelledError:
        # Handle client disconnection gracefully
        logger.info("Client disconnected, stopping stream")
        raise

@app.post("/proxy/{endpoint:path}")
async def proxy(endpoint: str, request: Request):
    """
    Proxy requests to the upstream Serena MCP server.
    Handles both regular and streaming responses.
    """
    try:
        # Get request body
        body = await request.body()
        
        # Parse request headers
        headers = dict(request.headers.items())
        
        # Remove any Authorization header to ensure we don't leak credentials
        headers.pop("authorization", None)
        headers.pop("Authorization", None)
        
        # Set content type if not present
        if "content-type" not in headers:
            headers["content-type"] = "application/json"
            
        # Get upstream URL
        upstream_url = f"{UPSTREAM_URL}/{endpoint}"
        logger.info(f"Proxying request to {upstream_url}")
        
        # Determine if this is a streaming endpoint (search_code)
        is_streaming = False
        try:
            body_json = json.loads(body)
            if "function_call" in body_json and body_json["function_call"].get("name") == "search_code":
                is_streaming = True
                logger.info("Detected streaming endpoint (search_code)")
        except:
            pass
            
        # Create auth tuple for basic auth
        auth = ("serena", os.environ.get("SERENA_PASSWORD", "password123"))
        
        # Create async client
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5-minute timeout
            if is_streaming:
                # For streaming endpoints, use streaming response
                response = await client.post(
                    upstream_url,
                    content=body,
                    headers=headers,
                    auth=auth,
                    timeout=300.0,  # 5-minute timeout
                    stream=True
                )
                
                # Set up response headers
                response_headers = dict(response.headers.items())
                response_headers["Access-Control-Allow-Origin"] = "*"
                response_headers["Access-Control-Allow-Credentials"] = "false"
                
                # Return streaming response with keep-alive
                return StreamingResponse(
                    stream_with_keepalive(response.aiter_bytes()),
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type", "application/json")
                )
            else:
                # For regular endpoints, use normal response
                response = await client.post(
                    upstream_url,
                    content=body,
                    headers=headers,
                    auth=auth,
                    timeout=60.0  # 1-minute timeout for regular requests
                )
                
                # Get response content
                content = None
                try:
                    content = response.json()
                except:
                    content = {"raw_response": response.text}
                
                # Set up response headers
                response_headers = dict(response.headers.items())
                response_headers["Access-Control-Allow-Origin"] = "*"
                response_headers["Access-Control-Allow-Credentials"] = "false"
                
                return JSONResponse(
                    content=content if content else {},
                    status_code=response.status_code,
                    headers=response_headers
                )
    except httpx.RequestError as e:
        logger.error(f"Error forwarding request: {str(e)}")
        return JSONResponse(
            content={"error": f"Error forwarding request: {str(e)}"},
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "false"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(
            content={"error": f"Unexpected error: {str(e)}"},
            status_code=500,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "false"
            }
        )

@app.options("/proxy/{endpoint:path}")
async def options_proxy(endpoint: str):
    """Handle OPTIONS requests for CORS preflight"""
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "false",
            "Access-Control-Max-Age": "86400"  # 24 hours
        }
    )

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint that returns HTML documentation"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Serena Relay API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            h1 { color: #333; }
            h2 { color: #444; margin-top: 30px; }
            pre { background-color: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
            a { color: #0066cc; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .endpoint { margin-bottom: 20px; }
            .description { margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <h1>Serena Relay API</h1>
        <p>This API provides a relay to the Serena MCP server for code search and manipulation.</p>
        
        <h2>API Documentation</h2>
        <p>View the full API documentation:</p>
        <ul>
            <li><a href="/openapi.json">OpenAPI Specification (JSON)</a></li>
            <li><a href="/openapi.txt">OpenAPI Specification (Text)</a></li>
        </ul>
        
        <h2>Health Check</h2>
        <div class="endpoint">
            <p class="description">Check if the API is healthy:</p>
            <pre>curl -X GET https://serena-relay.fly.dev/health</pre>
        </div>
        
        <h2>Available Functions</h2>
    """
    
    for function_name, function_info in SERENA_FUNCTIONS.items():
        example = json.dumps(function_info["example"], indent=4)
        html_content += f"""
        <div class="endpoint">
            <h3>{function_name}</h3>
            <p class="description">{function_info["description"]}</p>
            <pre>curl -X POST https://serena-relay.fly.dev/proxy/{function_name} \
    -H "Content-Type: application/json" \
    -d '{json.dumps(function_info["example"])}'</pre>
        </div>
        """
    
    html_content += """
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content, media_type="text/html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    logger.info(f"Starting Serena Relay on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
