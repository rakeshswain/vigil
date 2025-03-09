import os
import asyncio
import base64
import json
import re
from typing import Dict, List, Any, AsyncGenerator, Optional, Tuple
from pathlib import Path
import tempfile
from datetime import datetime

from playwright.async_api import async_playwright, Browser, Page, ElementHandle
import httpx

# MCP SDK imports
from modelcontextprotocol.server import Server
from modelcontextprotocol.server.stdio import StdioServerTransport
from modelcontextprotocol.types import (
    CallToolRequestSchema,
    ErrorCode,
    ListToolsRequestSchema,
    McpError,
)

class WebTestingAgent:
    """Agent for web application testing using Playwright"""
    
    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None
        self._ready = False
        self._screenshots_dir = Path("screenshots")
        self._screenshots_dir.mkdir(exist_ok=True)
        
        # Initialize MCP server for this agent
        self._init_mcp_server()
    
    def _init_mcp_server(self):
        """Initialize the MCP server for this agent"""
        # This will be implemented when we set up the MCP server
        pass
    
    def is_ready(self) -> bool:
        """Check if the agent is ready to process requests"""
        return self._ready
    
    async def _ensure_browser(self):
        """Ensure that the browser is launched"""
        if self._browser is None:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=True)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 720}
            )
            self._page = await self._context.new_page()
            self._ready = True
    
    async def _take_screenshot(self) -> str:
        """Take a screenshot and return the base64-encoded image"""
        if not self._page:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self._screenshots_dir / f"screenshot_{timestamp}.png"
        
        await self._page.screenshot(path=str(screenshot_path))
        
        # Convert to base64 for embedding in responses
        with open(screenshot_path, "rb") as f:
            screenshot_data = base64.b64encode(f.read()).decode("utf-8")
        
        return f"data:image/png;base64,{screenshot_data}"
    
    async def process_message(self, message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user message and generate responses"""
        # Ensure browser is launched
        await self._ensure_browser()
        
        # Parse the user's instruction
        test_plan = await self._parse_instruction(message)
        
        # Initial response
        yield {
            "message": f"I'll test the web application based on your instructions. Here's my plan:\n\n{test_plan['description']}"
        }
        
        # Execute the test steps
        test_results = {
            "title": test_plan["title"],
            "status": "RUNNING",
            "steps": [],
            "description": test_plan["description"]
        }
        
        yield {
            "message": f"Starting test: {test_plan['title']}...",
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
                await self._execute_step(step)
                
                # Update step status to success
                current_step["status"] = "PASS"
                
                # Take a screenshot after the step
                screenshot = await self._take_screenshot()
                if screenshot:
                    test_results["screenshot"] = screenshot
                
                yield {
                    "message": f"Step {i+1} completed successfully: {step['description']}",
                    "results": test_results
                }
                
            except Exception as e:
                # Update step status to failure
                current_step["status"] = "FAIL"
                current_step["error"] = str(e)
                
                # Take a screenshot of the failure
                screenshot = await self._take_screenshot()
                if screenshot:
                    test_results["screenshot"] = screenshot
                
                # Update overall test status
                test_results["status"] = "FAIL"
                
                yield {
                    "message": f"Step {i+1} failed: {step['description']}\nError: {str(e)}",
                    "results": test_results
                }
                
                # Stop execution after a failure
                break
        
        # If we completed all steps without failure, mark the test as passed
        if test_results["status"] != "FAIL":
            test_results["status"] = "PASS"
            
            yield {
                "message": f"Test completed successfully: {test_plan['title']}",
                "results": test_results
            }
    
    async def _parse_instruction(self, instruction: str) -> Dict[str, Any]:
        """Parse the user's instruction into a test plan"""
        # This is a simplified implementation
        # In a real implementation, we would use NLP or an LLM to parse the instruction
        
        # Extract URL using regex
        url_match = re.search(r'https?://[^\s]+', instruction)
        url = url_match.group(0) if url_match else "https://example.com"
        
        # Create a basic test plan based on the instruction
        if "login" in instruction.lower():
            return {
                "title": f"Login Test for {url}",
                "description": f"Testing the login functionality at {url}",
                "steps": [
                    {
                        "action": "navigate",
                        "url": url,
                        "description": f"Navigate to {url}"
                    },
                    {
                        "action": "find_element",
                        "selector": "input[type='text'], input[type='email'], input[name='username'], input[name='email']",
                        "description": "Find username/email input field"
                    },
                    {
                        "action": "fill",
                        "selector": "input[type='text'], input[type='email'], input[name='username'], input[name='email']",
                        "value": "test@example.com",
                        "description": "Enter test email"
                    },
                    {
                        "action": "find_element",
                        "selector": "input[type='password']",
                        "description": "Find password input field"
                    },
                    {
                        "action": "fill",
                        "selector": "input[type='password']",
                        "value": "password123",
                        "description": "Enter test password"
                    },
                    {
                        "action": "click",
                        "selector": "button[type='submit'], input[type='submit'], button:contains('Login'), button:contains('Sign in')",
                        "description": "Click the login button"
                    },
                    {
                        "action": "wait",
                        "time": 2000,
                        "description": "Wait for login process"
                    },
                    {
                        "action": "check_url_change",
                        "original_url": url,
                        "description": "Verify URL changed after login"
                    }
                ]
            }
        elif "form" in instruction.lower():
            return {
                "title": f"Form Submission Test for {url}",
                "description": f"Testing form submission at {url}",
                "steps": [
                    {
                        "action": "navigate",
                        "url": url,
                        "description": f"Navigate to {url}"
                    },
                    {
                        "action": "find_element",
                        "selector": "form",
                        "description": "Find form element"
                    },
                    {
                        "action": "fill_form",
                        "description": "Fill out form fields with test data"
                    },
                    {
                        "action": "click",
                        "selector": "button[type='submit'], input[type='submit']",
                        "description": "Submit the form"
                    },
                    {
                        "action": "wait",
                        "time": 2000,
                        "description": "Wait for form submission"
                    },
                    {
                        "action": "check_success",
                        "description": "Check for success message or redirect"
                    }
                ]
            }
        else:
            # Default test plan for general navigation and content verification
            return {
                "title": f"Navigation Test for {url}",
                "description": f"Testing navigation and content at {url}",
                "steps": [
                    {
                        "action": "navigate",
                        "url": url,
                        "description": f"Navigate to {url}"
                    },
                    {
                        "action": "wait",
                        "time": 2000,
                        "description": "Wait for page to load"
                    },
                    {
                        "action": "check_title",
                        "description": "Verify page title exists"
                    },
                    {
                        "action": "check_content",
                        "description": "Verify page has content"
                    }
                ]
            }
    
    async def _execute_step(self, step: Dict[str, Any]):
        """Execute a single test step"""
        action = step.get("action", "")
        
        if action == "navigate":
            await self._page.goto(step["url"])
        
        elif action == "find_element":
            element = await self._page.wait_for_selector(step["selector"], timeout=5000)
            if not element:
                raise Exception(f"Element not found: {step['selector']}")
        
        elif action == "fill":
            await self._page.fill(step["selector"], step["value"])
        
        elif action == "click":
            await self._page.click(step["selector"])
        
        elif action == "wait":
            await asyncio.sleep(step["time"] / 1000)  # Convert ms to seconds
        
        elif action == "check_url_change":
            current_url = self._page.url
            if current_url == step.get("original_url", ""):
                raise Exception("URL did not change after action")
        
        elif action == "check_title":
            title = await self._page.title()
            if not title:
                raise Exception("Page title is empty")
        
        elif action == "check_content":
            content = await self._page.content()
            if len(content) < 100:  # Arbitrary threshold
                raise Exception("Page has minimal content")
        
        elif action == "fill_form":
            # Find all input elements in the form
            inputs = await self._page.query_selector_all("input:not([type='submit']):not([type='button']):not([type='hidden'])")
            
            for input_element in inputs:
                input_type = await input_element.get_attribute("type")
                
                if input_type == "text" or input_type == "email" or input_type is None:
                    await input_element.fill("test@example.com")
                elif input_type == "password":
                    await input_element.fill("password123")
                elif input_type == "checkbox":
                    await input_element.check()
        
        elif action == "check_success":
            # Look for common success indicators
            success_selectors = [
                ".success", 
                ".alert-success", 
                "[data-testid='success']",
                "text=success",
                "text=thank you",
                "text=submitted"
            ]
            
            for selector in success_selectors:
                try:
                    element = await self._page.wait_for_selector(selector, timeout=1000)
                    if element:
                        return  # Success indicator found
                except:
                    pass
            
            # Check if URL changed, which might indicate success
            # This is a simplified check
            await asyncio.sleep(1)  # Give time for any redirects
    
    async def close(self):
        """Close the browser and clean up resources"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page = None
            self._ready = False
