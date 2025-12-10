# Cloudflare Python Workers - Complete Guide

A comprehensive guide to building and deploying Python applications on Cloudflare Workers.

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Quick Start](#quick-start)
4. [Project Structure](#project-structure)
5. [Configuration](#configuration)
6. [Bindings and Services](#bindings-and-services)
7. [Foreign Function Interface (FFI)](#foreign-function-interface-ffi)
8. [Packages and Dependencies](#packages-and-dependencies)
9. [Secrets and Environment Variables](#secrets-and-environment-variables)
10. [Common Patterns](#common-patterns)
11. [Caveats and Gotchas](#caveats-and-gotchas)
12. [Testing](#testing)
13. [Deployment](#deployment)
14. [Examples](#examples)

---

## Overview

Cloudflare Workers now supports Python as a first-class language. Python Workers run on [Pyodide](https://pyodide.org/), a port of CPython to WebAssembly, executing directly in V8 isolates.

**Key Features:**
- Native Python execution (no transpilation)
- Access to pure Python packages from PyPI
- Access to packages included in Pyodide
- Full access to Cloudflare bindings (D1, KV, R2, etc.)
- Foreign Function Interface (FFI) to JavaScript APIs
- Fast cold starts via memory snapshots

---

## How It Works

1. **At Deploy Time:**
   - Your Python code is uploaded to Cloudflare
   - Packages are bundled with your worker
   - Import statements are executed and memory is snapshotted
   - Snapshot is distributed globally

2. **At Runtime:**
   - Memory snapshot is loaded (fast cold start)
   - Your Python code executes in Pyodide
   - JavaScript APIs are accessible via FFI

---

## Quick Start

### Prerequisites

- [Node.js](https://nodejs.org/) v18+
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pywrangler globally
uv tool install workers-py

# Create a new project
mkdir my-python-worker && cd my-python-worker
uv init
uv run pywrangler init
```

### Minimal Worker

**src/entry.py:**
```python
from workers import WorkerEntrypoint, Response

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return Response("Hello from Python!")
```

### Run Locally

```bash
uv run pywrangler dev
```

### Deploy

```bash
uv run pywrangler deploy
```

---

## Project Structure

```
my-python-worker/
├── src/
│   ├── entry.py          # Main entrypoint (required)
│   └── module.py         # Additional modules
├── pyproject.toml        # Python dependencies
├── wrangler.jsonc        # Worker configuration
├── package.json          # npm scripts (optional)
└── .dev.vars             # Local dev environment variables
```

### pyproject.toml

```toml
[project]
name = "my-python-worker"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27.0",       # Your runtime dependencies
]

[dependency-groups]
dev = [
    "workers-py",           # Required for pywrangler CLI
    "workers-runtime-sdk",  # Optional: type hints
    "pytest>=8.0.0",        # Testing
]
```

---

## Configuration

### wrangler.jsonc

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "my-python-worker",
  "main": "src/entry.py",
  "compatibility_date": "2025-12-01",
  "compatibility_flags": ["python_workers"],
  
  // Observability
  "observability": {
    "enabled": true
  },
  
  // Environment variables (non-sensitive)
  "vars": {
    "API_HOST": "api.example.com"
  },
  
  // D1 Database
  "d1_databases": [
    {
      "binding": "DB",
      "database_name": "my-database",
      "database_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    }
  ],
  
  // KV Namespace
  "kv_namespaces": [
    {
      "binding": "KV",
      "id": "xxxxxxxx"
    }
  ],
  
  // R2 Bucket
  "r2_buckets": [
    {
      "binding": "BUCKET",
      "bucket_name": "my-bucket"
    }
  ]
}
```

### Key Configuration Options

| Option | Description |
|--------|-------------|
| `main` | Path to Python entry file |
| `compatibility_date` | API version date |
| `compatibility_flags` | Must include `python_workers` |
| `vars` | Non-sensitive environment variables |
| `d1_databases` | D1 database bindings |
| `kv_namespaces` | KV namespace bindings |
| `r2_buckets` | R2 bucket bindings |

---

## Bindings and Services

Access bindings via `self.env` in your worker class.

### D1 Database

**Configuration:**
```jsonc
"d1_databases": [{
  "binding": "DB",
  "database_name": "my-db",
  "database_id": "xxx"
}]
```

**Usage:**
```python
from workers import WorkerEntrypoint, Response

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # Query
        result = await self.env.DB.prepare(
            "SELECT * FROM users WHERE id = ?"
        ).bind(1).first()
        
        # Insert
        await self.env.DB.prepare(
            "INSERT INTO users (name) VALUES (?)"
        ).bind("John").run()
        
        # All results
        results = await self.env.DB.prepare(
            "SELECT * FROM users"
        ).all()
        
        return Response.json(results)
```

### KV Namespace

**Configuration:**
```jsonc
"kv_namespaces": [{
  "binding": "KV",
  "id": "xxx"
}]
```

**Usage:**
```python
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # Get
        value = await self.env.KV.get("key")
        
        # Put
        await self.env.KV.put("key", "value")
        
        # Delete
        await self.env.KV.delete("key")
        
        return Response(value)
```

### R2 Storage

**Configuration:**
```jsonc
"r2_buckets": [{
  "binding": "BUCKET",
  "bucket_name": "my-bucket"
}]
```

**Usage:**
```python
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # Get object
        obj = await self.env.BUCKET.get("file.txt")
        content = await obj.text()
        
        # Put object
        await self.env.BUCKET.put("file.txt", "content")
        
        return Response(content)
```

---

## Foreign Function Interface (FFI)

Python Workers can call JavaScript APIs directly via Pyodide's FFI.

### Importing JavaScript Globals

```python
from js import console, fetch, Object, JSON, Response as JSResponse
```

### Converting Python to JavaScript

```python
from js import Object
from pyodide.ffi import to_js as _to_js

def to_js(obj):
    """Convert Python dict to JavaScript object."""
    return _to_js(obj, dict_converter=Object.fromEntries)

# Usage
js_obj = to_js({"key": "value"})
```

### Converting JavaScript to Python

```python
import json
from js import JSON

def js_to_py(js_obj):
    """Convert JavaScript object to Python dict."""
    return json.loads(JSON.stringify(js_obj))

# Usage
response = await fetch(url)
js_data = await response.json()
py_data = js_to_py(js_data)  # Now a Python dict
```

### Making HTTP Requests

**Using JS fetch:**
```python
from js import fetch, Object
from pyodide.ffi import to_js

async def make_request():
    response = await fetch(
        "https://api.example.com/data",
        to_js({
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": '{"key": "value"}'
        }, dict_converter=Object.fromEntries)
    )
    
    if response.ok:
        data = await response.json()
        return json.loads(JSON.stringify(data))
```

**Using httpx (recommended for complex requests):**
```python
import httpx

async def make_request():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/data",
            json={"key": "value"}
        )
        return response.json()
```

---

## Packages and Dependencies

### Supported Packages

Python Workers support:
1. **Pure Python packages** from PyPI
2. **Pyodide-compatible packages** (see [list](https://pyodide.org/en/stable/usage/packages-in-pyodide.html))

### Adding Dependencies

**pyproject.toml:**
```toml
[project]
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.0.0",
]
```

**Install locally:**
```bash
uv sync
```

**Deploy (auto-bundles dependencies):**
```bash
uv run pywrangler deploy
```

### HTTP Libraries

Only **async** HTTP libraries work:
- `httpx` (recommended)
- `aiohttp`
- JavaScript `fetch()` via FFI

**Does NOT work:** `requests` (synchronous)

---

## Secrets and Environment Variables

### Environment Variables (Non-Sensitive)

**wrangler.jsonc:**
```jsonc
"vars": {
  "API_HOST": "api.example.com",
  "DEBUG": "false"
}
```

**Access:**
```python
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        host = self.env.API_HOST
        return Response(f"Host: {host}")
```

### Secrets (Sensitive)

**Set via CLI:**
```bash
npx wrangler secret put API_KEY
# Enter value when prompted
```

**Access (same as env vars):**
```python
api_key = self.env.API_KEY
```

### Local Development

Create `.dev.vars` for local secrets:
```
API_KEY=your-dev-key
DB_PASSWORD=local-password
```

**Note:** `.dev.vars` is automatically gitignored.

---

## Common Patterns

### Request Handling

```python
from workers import WorkerEntrypoint, Response
from urllib.parse import urlparse, parse_qs
import json

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(request.url)
        method = request.method
        path = url.path
        
        # Route handling
        if path == "/" and method == "GET":
            return Response.json({"status": "ok"})
        
        if path == "/data" and method == "POST":
            # Parse JSON body (use request.text() then json.loads)
            raw_body = await request.text()
            body = json.loads(raw_body)
            return Response.json({"received": body})
        
        # Query parameters
        if path == "/search":
            params = parse_qs(url.query)
            query = params.get("q", [""])[0]
            return Response(f"Search: {query}")
        
        return Response("Not Found", status=404)
```

### JSON Responses

```python
from js import Object
from pyodide.ffi import to_js

def to_js(obj):
    return to_js(obj, dict_converter=Object.fromEntries)

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        data = {"message": "Hello", "count": 42}
        return Response.json(to_js(data))
```

### Error Handling

```python
class Default(WorkerEntrypoint):
    async def fetch(self, request):
        try:
            result = await self.process_request(request)
            return Response.json(to_js({"data": result}))
        except ValueError as e:
            return Response.json(to_js({"error": str(e)}), status=400)
        except Exception as e:
            console.error(f"Error: {e}")
            return Response.json(to_js({"error": "Internal error"}), status=500)
```

### Logging

```python
from js import console

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        console.log("Info message")
        console.warn("Warning message")
        console.error("Error message")
        return Response("OK")
```

---

## Caveats and Gotchas

### 1. JavaScript Object Iteration

**Problem:** Iterating over JS objects/arrays can cause proxy errors.

```python
# BAD - May cause "borrowed proxy destroyed" error
for item in js_array:
    process(item)

# GOOD - Convert to Python first
py_list = json.loads(JSON.stringify(js_array))
for item in py_list:
    process(item)
```

### 2. Request Body Parsing

**Problem:** `request.json()` returns a JS object, not Python dict.

```python
# BAD
body = await request.json()
value = body["key"]  # May fail

# GOOD
raw_body = await request.text()
body = json.loads(raw_body)
value = body["key"]  # Works
```

### 3. D1 Results

**Problem:** D1 `.first()` returns JS proxy, not Python dict.

```python
# BAD
result = await db.prepare("SELECT * FROM users").first()
if result:  # May be truthy even when no results
    name = result["name"]

# GOOD
result = await db.prepare("SELECT * FROM users").first()
if result is not None:
    result_str = JSON.stringify(result)
    if result_str != "null":
        data = json.loads(result_str)
        name = data["name"]
```

### 4. None vs undefined

**Problem:** Python `None` may not work in JS contexts.

```python
# BAD
await db.prepare("INSERT INTO t VALUES (?)").bind(None).run()

# GOOD - Use empty string or explicit null handling
await db.prepare("INSERT INTO t VALUES (?)").bind("").run()
```

### 5. Synchronous Code

**Problem:** Blocking operations don't work.

```python
# BAD
import requests  # Synchronous - won't work
response = requests.get(url)

# GOOD
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

### 6. File System Access

**Problem:** No traditional file system access.

```python
# BAD
with open("data.txt", "r") as f:
    data = f.read()

# GOOD - Bundled files
from pathlib import Path
file_path = Path(__file__).parent / "data.txt"
data = file_path.read_text()
```

### 7. Environment Variables Type

**Problem:** Env vars from `self.env` are JS strings.

```python
# Convert to Python string explicitly
api_key = str(self.env.API_KEY)
```

---

## Testing

### Setup

**pyproject.toml:**
```toml
[dependency-groups]
dev = [
    "workers-py",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

**pytest.ini:**
```ini
[pytest]
testpaths = tests
asyncio_mode = auto
```

### Test Structure

```
tests/
├── __init__.py
├── test_handlers.py
└── test_utils.py
```

### Example Tests

```python
# tests/test_handlers.py
import pytest
from urllib.parse import urlparse, parse_qs

def test_url_parsing():
    url = "https://example.com/path?key=value"
    parsed = urlparse(url)
    assert parsed.path == "/path"
    params = parse_qs(parsed.query)
    assert params["key"][0] == "value"

@pytest.mark.asyncio
async def test_async_function():
    # Test async code
    result = await some_async_function()
    assert result == expected
```

### Run Tests

```bash
uv run pytest tests/ -v
```

---

## Deployment

### Deploy Commands

```bash
# Development
uv run pywrangler dev

# Deploy to production
uv run pywrangler deploy

# Deploy to specific environment
uv run pywrangler deploy --env staging
```

### CI/CD

**GitHub Actions example:**
```yaml
name: Deploy Worker
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v1
      
      - name: Install Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: |
          npm install
          uv sync
      
      - name: Deploy
        run: uv run pywrangler deploy
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CF_API_TOKEN }}
```

---

## Examples

### Hello World

```python
from workers import WorkerEntrypoint, Response

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return Response("Hello, World!")
```

### JSON API

```python
import json
from js import Object
from pyodide.ffi import to_js
from workers import WorkerEntrypoint, Response

def to_js_obj(obj):
    return to_js(obj, dict_converter=Object.fromEntries)

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        if request.method == "POST":
            body = json.loads(await request.text())
            return Response.json(to_js_obj({
                "received": body,
                "status": "ok"
            }))
        
        return Response.json(to_js_obj({"message": "Send POST"}))
```

### D1 CRUD

```python
import json
from js import Object, JSON
from pyodide.ffi import to_js
from workers import WorkerEntrypoint, Response

def to_js_obj(obj):
    return to_js(obj, dict_converter=Object.fromEntries)

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        db = self.env.DB
        
        # Create
        if request.method == "POST":
            body = json.loads(await request.text())
            await db.prepare(
                "INSERT INTO items (name) VALUES (?)"
            ).bind(body["name"]).run()
            return Response.json(to_js_obj({"created": True}))
        
        # Read
        if request.method == "GET":
            result = await db.prepare("SELECT * FROM items").all()
            items = json.loads(JSON.stringify(result.results))
            return Response.json(to_js_obj({"items": items}))
        
        return Response("Method not allowed", status=405)
```

### External API Call

```python
import json
from js import fetch, Object, JSON
from pyodide.ffi import to_js
from workers import WorkerEntrypoint, Response

def to_js_obj(obj):
    return to_js(obj, dict_converter=Object.fromEntries)

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # Call external API
        api_response = await fetch(
            "https://api.example.com/data",
            to_js_obj({
                "headers": {
                    "Authorization": f"Bearer {self.env.API_KEY}"
                }
            })
        )
        
        if api_response.ok:
            data = json.loads(JSON.stringify(await api_response.json()))
            return Response.json(to_js_obj(data))
        
        return Response("API error", status=502)
```

---

## Resources

- [Official Python Workers Docs](https://developers.cloudflare.com/workers/languages/python/)
- [Pyodide Documentation](https://pyodide.org/en/stable/)
- [Python Workers Examples](https://github.com/cloudflare/python-workers-examples)
- [Wrangler Configuration](https://developers.cloudflare.com/workers/wrangler/configuration/)
- [Cloudflare Workers Discord](https://discord.cloudflare.com/)
