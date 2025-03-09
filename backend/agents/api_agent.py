import os
import asyncio
import json
import re
import uuid
from typing import Dict, List, Any, AsyncGenerator, Optional, Tuple
from pathlib import Path
from datetime import datetime
import inspect

import httpx
from pydantic import BaseModel, Field, ValidationError

# MCP SDK imports
from modelcontextprotocol.server import Server
from modelcontextprotocol.server.stdio import StdioServerTransport
from modelcontextprotocol.types import (
    CallToolRequestSchema,
    ErrorCode,
    ListToolsRequestSchema,
    McpError,
)

class ApiTestingAgent:
    """Agent for API testing"""
    
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        self._ready = True
        self._results_dir = Path("api_results")
        self._results_dir.mkdir(exist_ok=True)
        
        # Initialize MCP server for this agent
        self._init_mcp_server()
    
    def _init_mcp_server(self):
        """Initialize the MCP server for this agent"""
        # This will be implemented when we set up the MCP server
        pass
    
    def is_ready(self) -> bool:
        """Check if the agent is ready to process requests"""
        return self._ready
    
    async def process_message(self, message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user message and generate responses"""
        # Parse the user's instruction
        test_plan = await self._parse_instruction(message)
        
        # Initial response
        yield {
            "message": f"I'll test the API based on your instructions. Here's my plan:\n\n{test_plan['description']}"
        }
        
        # Execute the test steps
        test_results = {
            "title": test_plan["title"],
            "status": "RUNNING",
            "steps": [],
            "description": test_plan["description"]
        }
        
        yield {
            "message": f"Starting API test: {test_plan['title']}...",
            "results": test_results
        }
        
        # Execute each test step
        for i, step in enumerate(test_plan["steps"]):
            try:
                # Update status
                current_step = {
                    "description": step["description"],
                    "status": "RUNNING"
                }
                test_results["steps"].append(current_step)
                
                yield {
                    "message": f"Executing step {i+1}/{len(test_plan['steps'])}: {step['description']}...",
                    "results": test_results
                }
                
                # Execute the step
                result = await self._execute_step(step)
                
                # Update step with result details
                current_step["status"] = "PASS"
                current_step["details"] = result
                
                yield {
                    "message": f"Step {i+1} completed successfully: {step['description']}\n```json\n{json.dumps(result, indent=2)}\n```",
                    "results": test_results
                }
                
            except Exception as e:
                # Update step status to failure
                current_step["status"] = "FAIL"
                current_step["error"] = str(e)
                
                # Update overall test status
                test_results["status"] = "FAIL"
                
                yield {
                    "message": f"Step {i+1} failed: {step['description']}\nError: {str(e)}",
                    "results": test_results
                }
                
                # Don't stop execution after a failure for API tests
                # We'll continue with the next steps
        
        # If we completed all steps without failure, mark the test as passed
        if test_results["status"] != "FAIL":
            test_results["status"] = "PASS"
            
            yield {
                "message": f"API test completed successfully: {test_plan['title']}",
                "results": test_results
            }
        
        # Generate additional test cases if requested
        if test_plan.get("generate_additional_tests", False):
            yield {
                "message": "Generating additional test cases based on the API response..."
            }
            
            additional_tests = await self._generate_additional_tests(test_results)
            
            if additional_tests:
                for test in additional_tests:
                    yield {
                        "message": f"Additional test case: {test['title']}\n{test['description']}",
                        "results": test
                    }
            else:
                yield {
                    "message": "No additional test cases could be generated."
                }
    
    async def _parse_instruction(self, instruction: str) -> Dict[str, Any]:
        """Parse the user's instruction into a test plan"""
        # This is a simplified implementation
        # In a real implementation, we would use NLP or an LLM to parse the instruction
        
        # Extract URL using regex
        url_match = re.search(r'https?://[^\s]+', instruction)
        url = url_match.group(0) if url_match else "https://jsonplaceholder.typicode.com/posts"
        
        # Determine HTTP method
        method = "GET"  # Default method
        if "post" in instruction.lower():
            method = "POST"
        elif "put" in instruction.lower():
            method = "PUT"
        elif "delete" in instruction.lower():
            method = "DELETE"
        elif "patch" in instruction.lower():
            method = "PATCH"
        
        # Create a basic test plan based on the instruction
        if method == "GET":
            return {
                "title": f"GET Request Test for {url}",
                "description": f"Testing GET request to {url}",
                "generate_additional_tests": True,
                "steps": [
                    {
                        "action": "request",
                        "method": "GET",
                        "url": url,
                        "description": f"Send GET request to {url}"
                    },
                    {
                        "action": "validate_status",
                        "expected_status": 200,
                        "description": "Validate response status code is 200"
                    },
                    {
                        "action": "validate_response",
                        "description": "Validate response format is JSON"
                    },
                    {
                        "action": "measure_performance",
                        "description": "Measure response time"
                    }
                ]
            }
        elif method == "POST":
            return {
                "title": f"POST Request Test for {url}",
                "description": f"Testing POST request to {url}",
                "generate_additional_tests": True,
                "steps": [
                    {
                        "action": "request",
                        "method": "POST",
                        "url": url,
                        "headers": {
                            "Content-Type": "application/json"
                        },
                        "data": {
                            "title": "Test Post",
                            "body": "This is a test post",
                            "userId": 1
                        },
                        "description": f"Send POST request to {url}"
                    },
                    {
                        "action": "validate_status",
                        "expected_status": 201,
                        "description": "Validate response status code is 201 (Created)"
                    },
                    {
                        "action": "validate_response",
                        "description": "Validate response format is JSON"
                    },
                    {
                        "action": "validate_field",
                        "field": "id",
                        "description": "Validate response contains an ID field"
                    },
                    {
                        "action": "measure_performance",
                        "description": "Measure response time"
                    }
                ]
            }
        elif method == "PUT":
            return {
                "title": f"PUT Request Test for {url}",
                "description": f"Testing PUT request to {url}",
                "generate_additional_tests": True,
                "steps": [
                    {
                        "action": "request",
                        "method": "PUT",
                        "url": url,
                        "headers": {
                            "Content-Type": "application/json"
                        },
                        "data": {
                            "id": 1,
                            "title": "Updated Test",
                            "body": "This is an updated test",
                            "userId": 1
                        },
                        "description": f"Send PUT request to {url}"
                    },
                    {
                        "action": "validate_status",
                        "expected_status": 200,
                        "description": "Validate response status code is 200"
                    },
                    {
                        "action": "validate_response",
                        "description": "Validate response format is JSON"
                    },
                    {
                        "action": "measure_performance",
                        "description": "Measure response time"
                    }
                ]
            }
        elif method == "DELETE":
            return {
                "title": f"DELETE Request Test for {url}",
                "description": f"Testing DELETE request to {url}",
                "generate_additional_tests": False,
                "steps": [
                    {
                        "action": "request",
                        "method": "DELETE",
                        "url": url,
                        "description": f"Send DELETE request to {url}"
                    },
                    {
                        "action": "validate_status",
                        "expected_status": 200,
                        "description": "Validate response status code is 200"
                    },
                    {
                        "action": "measure_performance",
                        "description": "Measure response time"
                    }
                ]
            }
        else:  # PATCH or other methods
            return {
                "title": f"{method} Request Test for {url}",
                "description": f"Testing {method} request to {url}",
                "generate_additional_tests": True,
                "steps": [
                    {
                        "action": "request",
                        "method": method,
                        "url": url,
                        "headers": {
                            "Content-Type": "application/json"
                        },
                        "data": {
                            "title": "Patched Test"
                        },
                        "description": f"Send {method} request to {url}"
                    },
                    {
                        "action": "validate_status",
                        "expected_status": 200,
                        "description": "Validate response status code is 200"
                    },
                    {
                        "action": "validate_response",
                        "description": "Validate response format is JSON"
                    },
                    {
                        "action": "measure_performance",
                        "description": "Measure response time"
                    }
                ]
            }
    
    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test step"""
        action = step.get("action", "")
        
        if action == "request":
            start_time = datetime.now()
            
            method = step.get("method", "GET")
            url = step.get("url", "")
            headers = step.get("headers", {})
            params = step.get("params", {})
            data = step.get("data", None)
            
            # Convert data to JSON if it's a dict
            json_data = None
            if isinstance(data, dict):
                json_data = data
                data = None
            
            # Make the request
            response = await self._client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
                follow_redirects=True
            )
            
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Try to parse response as JSON
            try:
                response_json = response.json()
                response_body = response_json
            except:
                response_body = response.text
            
            # Save the response for later steps
            self._last_response = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "duration_ms": duration_ms
            }
            
            return self._last_response
        
        elif action == "validate_status":
            expected_status = step.get("expected_status", 200)
            
            if self._last_response["status_code"] != expected_status:
                raise Exception(f"Expected status code {expected_status}, got {self._last_response['status_code']}")
            
            return {
                "expected": expected_status,
                "actual": self._last_response["status_code"],
                "result": "PASS"
            }
        
        elif action == "validate_response":
            # Check if response body is JSON
            if not isinstance(self._last_response["body"], (dict, list)):
                raise Exception("Response body is not valid JSON")
            
            return {
                "format": "JSON",
                "result": "PASS"
            }
        
        elif action == "validate_field":
            field = step.get("field", "")
            
            if not isinstance(self._last_response["body"], dict):
                raise Exception("Response body is not a JSON object")
            
            if field not in self._last_response["body"]:
                raise Exception(f"Field '{field}' not found in response")
            
            return {
                "field": field,
                "value": self._last_response["body"][field],
                "result": "PASS"
            }
        
        elif action == "measure_performance":
            duration_ms = self._last_response["duration_ms"]
            
            # Arbitrary threshold for demonstration
            performance_rating = "Excellent" if duration_ms < 100 else "Good" if duration_ms < 500 else "Fair" if duration_ms < 1000 else "Poor"
            
            return {
                "duration_ms": duration_ms,
                "rating": performance_rating,
                "result": "PASS"
            }
        
        else:
            raise Exception(f"Unknown action: {action}")
    
    async def _generate_additional_tests(self, test_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate additional test cases based on the API response"""
        additional_tests = []
        
        # This is a simplified implementation
        # In a real implementation, we would analyze the API response and generate more sophisticated tests
        
        # Get the last response from the test results
        last_response = None
        for step in test_results["steps"]:
            if step.get("details") and "body" in step["details"]:
                last_response = step["details"]
        
        if not last_response:
            return additional_tests
        
        # Generate tests based on the response type
        response_body = last_response["body"]
        
        if isinstance(response_body, list):
            # Test for empty array
            additional_tests.append({
                "title": "Test API with query that returns empty array",
                "status": "SUGGESTED",
                "description": "Test the API with query parameters that should return an empty array",
                "steps": [
                    {
                        "description": "Send request with invalid query parameters",
                        "status": "SUGGESTED"
                    },
                    {
                        "description": "Verify response is an empty array",
                        "status": "SUGGESTED"
                    }
                ]
            })
            
            # Test for pagination if the array is large
            if len(response_body) > 10:
                additional_tests.append({
                    "title": "Test API pagination",
                    "status": "SUGGESTED",
                    "description": "Test the API's pagination functionality",
                    "steps": [
                        {
                            "description": "Send request with page=1&limit=5 parameters",
                            "status": "SUGGESTED"
                        },
                        {
                            "description": "Verify response contains 5 items",
                            "status": "SUGGESTED"
                        },
                        {
                            "description": "Send request with page=2&limit=5 parameters",
                            "status": "SUGGESTED"
                        },
                        {
                            "description": "Verify response contains next 5 items",
                            "status": "SUGGESTED"
                        }
                    ]
                })
        
        elif isinstance(response_body, dict):
            # Test for required fields
            additional_tests.append({
                "title": "Test API required fields validation",
                "status": "SUGGESTED",
                "description": "Test the API's validation of required fields",
                "steps": [
                    {
                        "description": "Send request with missing required fields",
                        "status": "SUGGESTED"
                    },
                    {
                        "description": "Verify response indicates missing fields error",
                        "status": "SUGGESTED"
                    }
                ]
            })
            
            # Test for field validation
            additional_tests.append({
                "title": "Test API field validation",
                "status": "SUGGESTED",
                "description": "Test the API's validation of field formats and values",
                "steps": [
                    {
                        "description": "Send request with invalid field formats",
                        "status": "SUGGESTED"
                    },
                    {
                        "description": "Verify response indicates validation errors",
                        "status": "SUGGESTED"
                    }
                ]
            })
        
        # Add authentication test if headers indicate auth is used
        if "authorization" in last_response["headers"] or "x-api-key" in last_response["headers"]:
            additional_tests.append({
                "title": "Test API authentication",
                "status": "SUGGESTED",
                "description": "Test the API's authentication requirements",
                "steps": [
                    {
                        "description": "Send request without authentication",
                        "status": "SUGGESTED"
                    },
                    {
                        "description": "Verify response indicates authentication error",
                        "status": "SUGGESTED"
                    },
                    {
                        "description": "Send request with invalid authentication",
                        "status": "SUGGESTED"
                    },
                    {
                        "description": "Verify response indicates authentication error",
                        "status": "SUGGESTED"
                    }
                ]
            })
        
        return additional_tests
    
    async def close(self):
        """Close the client and clean up resources"""
        await self._client.aclose()
        self._ready = False
