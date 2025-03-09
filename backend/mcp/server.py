#!/usr/bin/env python3
import os
import json
import asyncio
import base64
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from modelcontextprotocol.server import Server
from modelcontextprotocol.server.stdio import StdioServerTransport
from modelcontextprotocol.types import (
    CallToolRequestSchema,
    ErrorCode,
    ListResourcesRequestSchema,
    ListResourceTemplatesRequestSchema,
    ListToolsRequestSchema,
    McpError,
    ReadResourceRequestSchema,
)

class TestingMcpServer:
    """MCP server for testing agents"""
    
    def __init__(self, agent_type: str = "web"):
        """Initialize the MCP server
        
        Args:
            agent_type: Type of agent ("web" or "api")
        """
        self.agent_type = agent_type
        self.server = Server(
            {
                "name": f"{agent_type}-testing-agent",
                "version": "0.1.0",
            },
            {
                "capabilities": {
                    "resources": {},
                    "tools": {},
                }
            }
        )
        
        # Set up handlers
        self._setup_tool_handlers()
        self._setup_resource_handlers()
        
        # Error handling
        self.server.onerror = lambda error: print(f"[MCP Error] {error}")
    
    def _setup_tool_handlers(self):
        """Set up tool handlers based on agent type"""
        self.server.setRequestHandler(ListToolsRequestSchema, self._handle_list_tools)
        self.server.setRequestHandler(CallToolRequestSchema, self._handle_call_tool)
    
    def _setup_resource_handlers(self):
        """Set up resource handlers based on agent type"""
        self.server.setRequestHandler(ListResourcesRequestSchema, self._handle_list_resources)
        self.server.setRequestHandler(ListResourceTemplatesRequestSchema, self._handle_list_resource_templates)
        self.server.setRequestHandler(ReadResourceRequestSchema, self._handle_read_resource)
    
    async def _handle_list_tools(self, request):
        """Handle list tools request"""
        if self.agent_type == "web":
            return {
                "tools": [
                    {
                        "name": "navigate_to_url",
                        "description": "Navigate to a URL in the browser",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "URL to navigate to"
                                }
                            },
                            "required": ["url"]
                        }
                    },
                    {
                        "name": "click_element",
                        "description": "Click an element on the page",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "selector": {
                                    "type": "string",
                                    "description": "CSS selector for the element to click"
                                }
                            },
                            "required": ["selector"]
                        }
                    },
                    {
                        "name": "fill_form",
                        "description": "Fill a form with data",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "form_selector": {
                                    "type": "string",
                                    "description": "CSS selector for the form"
                                },
                                "fields": {
                                    "type": "object",
                                    "description": "Field names and values to fill"
                                }
                            },
                            "required": ["form_selector", "fields"]
                        }
                    },
                    {
                        "name": "take_screenshot",
                        "description": "Take a screenshot of the current page",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "full_page": {
                                    "type": "boolean",
                                    "description": "Whether to capture the full page or just the viewport"
                                }
                            }
                        }
                    },
                    {
                        "name": "run_test",
                        "description": "Run a predefined test on a web page",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "URL to test"
                                },
                                "test_type": {
                                    "type": "string",
                                    "description": "Type of test to run (login, form, navigation)",
                                    "enum": ["login", "form", "navigation"]
                                }
                            },
                            "required": ["url", "test_type"]
                        }
                    }
                ]
            }
        else:  # API agent
            return {
                "tools": [
                    {
                        "name": "send_request",
                        "description": "Send an HTTP request to an API endpoint",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "method": {
                                    "type": "string",
                                    "description": "HTTP method",
                                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
                                },
                                "url": {
                                    "type": "string",
                                    "description": "URL to send the request to"
                                },
                                "headers": {
                                    "type": "object",
                                    "description": "HTTP headers"
                                },
                                "params": {
                                    "type": "object",
                                    "description": "Query parameters"
                                },
                                "data": {
                                    "type": "object",
                                    "description": "Request body data"
                                }
                            },
                            "required": ["method", "url"]
                        }
                    },
                    {
                        "name": "validate_response",
                        "description": "Validate an API response",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "expected_status": {
                                    "type": "integer",
                                    "description": "Expected HTTP status code"
                                },
                                "expected_format": {
                                    "type": "string",
                                    "description": "Expected response format",
                                    "enum": ["json", "xml", "text"]
                                },
                                "expected_fields": {
                                    "type": "array",
                                    "description": "Expected fields in the response",
                                    "items": {
                                        "type": "string"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "name": "run_api_test",
                        "description": "Run a predefined test on an API endpoint",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "API endpoint URL"
                                },
                                "test_type": {
                                    "type": "string",
                                    "description": "Type of test to run",
                                    "enum": ["get", "post", "put", "delete", "auth"]
                                }
                            },
                            "required": ["url", "test_type"]
                        }
                    },
                    {
                        "name": "generate_test_cases",
                        "description": "Generate additional test cases for an API",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "API endpoint URL"
                                },
                                "response_type": {
                                    "type": "string",
                                    "description": "Type of response",
                                    "enum": ["object", "array", "primitive"]
                                }
                            },
                            "required": ["url"]
                        }
                    }
                ]
            }
    
    async def _handle_call_tool(self, request):
        """Handle call tool request"""
        tool_name = request.params.name
        arguments = request.params.arguments
        
        # This is a simplified implementation
        # In a real implementation, we would actually execute the tool
        
        if self.agent_type == "web":
            if tool_name == "navigate_to_url":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Navigated to {arguments.get('url', 'unknown URL')}"
                        }
                    ]
                }
            elif tool_name == "click_element":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Clicked element with selector: {arguments.get('selector', 'unknown selector')}"
                        }
                    ]
                }
            elif tool_name == "fill_form":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Filled form with selector: {arguments.get('form_selector', 'unknown form')} with data: {json.dumps(arguments.get('fields', {}))}"
                        }
                    ]
                }
            elif tool_name == "take_screenshot":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Took screenshot with full_page={arguments.get('full_page', False)}"
                        }
                    ]
                }
            elif tool_name == "run_test":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Ran {arguments.get('test_type', 'unknown')} test on {arguments.get('url', 'unknown URL')}"
                        }
                    ]
                }
            else:
                raise McpError(
                    ErrorCode.MethodNotFound,
                    f"Unknown tool: {tool_name}"
                )
        else:  # API agent
            if tool_name == "send_request":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Sent {arguments.get('method', 'GET')} request to {arguments.get('url', 'unknown URL')}"
                        }
                    ]
                }
            elif tool_name == "validate_response":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Validated response with expected status {arguments.get('expected_status', 200)}"
                        }
                    ]
                }
            elif tool_name == "run_api_test":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Ran {arguments.get('test_type', 'unknown')} test on {arguments.get('url', 'unknown URL')}"
                        }
                    ]
                }
            elif tool_name == "generate_test_cases":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Generated test cases for {arguments.get('url', 'unknown URL')}"
                        }
                    ]
                }
            else:
                raise McpError(
                    ErrorCode.MethodNotFound,
                    f"Unknown tool: {tool_name}"
                )
    
    async def _handle_list_resources(self, request):
        """Handle list resources request"""
        if self.agent_type == "web":
            return {
                "resources": [
                    {
                        "uri": "web-testing://screenshots/latest",
                        "name": "Latest Screenshot",
                        "mimeType": "image/png",
                        "description": "The most recent screenshot taken during testing"
                    },
                    {
                        "uri": "web-testing://results/latest",
                        "name": "Latest Test Results",
                        "mimeType": "application/json",
                        "description": "Results from the most recent web test"
                    }
                ]
            }
        else:  # API agent
            return {
                "resources": [
                    {
                        "uri": "api-testing://results/latest",
                        "name": "Latest API Test Results",
                        "mimeType": "application/json",
                        "description": "Results from the most recent API test"
                    }
                ]
            }
    
    async def _handle_list_resource_templates(self, request):
        """Handle list resource templates request"""
        if self.agent_type == "web":
            return {
                "resourceTemplates": [
                    {
                        "uriTemplate": "web-testing://screenshots/{timestamp}",
                        "name": "Screenshot by Timestamp",
                        "mimeType": "image/png",
                        "description": "Screenshot taken at a specific timestamp"
                    },
                    {
                        "uriTemplate": "web-testing://results/{test_id}",
                        "name": "Test Results by ID",
                        "mimeType": "application/json",
                        "description": "Results from a specific web test"
                    }
                ]
            }
        else:  # API agent
            return {
                "resourceTemplates": [
                    {
                        "uriTemplate": "api-testing://results/{test_id}",
                        "name": "API Test Results by ID",
                        "mimeType": "application/json",
                        "description": "Results from a specific API test"
                    },
                    {
                        "uriTemplate": "api-testing://endpoints/{url}",
                        "name": "API Endpoint Information",
                        "mimeType": "application/json",
                        "description": "Information about a specific API endpoint"
                    }
                ]
            }
    
    async def _handle_read_resource(self, request):
        """Handle read resource request"""
        uri = request.params.uri
        
        # This is a simplified implementation
        # In a real implementation, we would actually fetch the resource
        
        if uri.startswith("web-testing://screenshots/"):
            # Return a placeholder screenshot
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "image/png",
                        "text": "Base64-encoded screenshot would go here"
                    }
                ]
            }
        elif uri.startswith("web-testing://results/"):
            # Return placeholder test results
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps({
                            "title": "Sample Web Test",
                            "status": "PASS",
                            "steps": [
                                {"description": "Navigate to URL", "status": "PASS"},
                                {"description": "Fill login form", "status": "PASS"},
                                {"description": "Submit form", "status": "PASS"},
                                {"description": "Verify redirect", "status": "PASS"}
                            ]
                        }, indent=2)
                    }
                ]
            }
        elif uri.startswith("api-testing://results/"):
            # Return placeholder API test results
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps({
                            "title": "Sample API Test",
                            "status": "PASS",
                            "steps": [
                                {"description": "Send GET request", "status": "PASS"},
                                {"description": "Validate status code", "status": "PASS"},
                                {"description": "Validate response format", "status": "PASS"},
                                {"description": "Measure performance", "status": "PASS"}
                            ]
                        }, indent=2)
                    }
                ]
            }
        elif uri.startswith("api-testing://endpoints/"):
            # Return placeholder endpoint information
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps({
                            "url": uri.replace("api-testing://endpoints/", ""),
                            "methods": ["GET", "POST", "PUT", "DELETE"],
                            "parameters": ["id", "name", "status"],
                            "authentication": "Bearer token"
                        }, indent=2)
                    }
                ]
            }
        else:
            raise McpError(
                ErrorCode.InvalidRequest,
                f"Unknown resource URI: {uri}"
            )
    
    async def run(self):
        """Run the MCP server"""
        transport = StdioServerTransport()
        await self.server.connect(transport)
        print(f"{self.agent_type.capitalize()} Testing MCP server running on stdio", file=os.sys.stderr)
        
        # Keep the server running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.server.close()
    
    async def close(self):
        """Close the MCP server"""
        await self.server.close()

if __name__ == "__main__":
    # Determine agent type from command line arguments
    import sys
    agent_type = sys.argv[1] if len(sys.argv) > 1 else "web"
    
    # Run the server
    server = TestingMcpServer(agent_type)
    asyncio.run(server.run())
