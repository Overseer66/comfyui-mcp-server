# ComfyUI MCP Server

## 1. Overview

- A server implementation for integrating ComfyUI with MCP.
- ⚠️ IMPORTANT: This server requires a running ComfyUI server.
    - You must either host your own ComfyUI server,
    - or have access to an existing ComfyUI server address.

---

## 2. Debugging

  ### 2.1 ComfyUI Debugging

  ```bash
  python src/test_comfyui.py
  ```

  ### 2.2 MCP Debugging

  ```bash
  mcp dev src/server.py
  ```

---

## 3. Installation and Configuration

  ### 3.1 ComfyUI Configuration

  - Edit `src/.env` to set ComfyUI host and port:

      ```env
      COMFYUI_HOST=localhost
      COMFYUI_PORT=8188
      ```

  ### 3.2 Adding Custom Workflows

  - To add new tools, place your workflow JSON files in the `workflows` directory and declare them as new tools in the system.

---

## 4. Built-in Tools

  - **text_to_image**

    - Returns only the URL of the generated image.
    - To get the actual image:
        - Use the `download_image` tool, or
        - Access the URL directly in your browser.

  - **download_image**

    - Downloads images generated by other tools (like `text_to_image`) using the image URL.

  - **run_workflow_with_file**

    - Run a workflow by providing the path to a workflow JSON file.

        ```
        # You should ask to agent like this.
        Run comfyui workflow with text_to_image.json
        ```

    - example image of CursorAI
      ![](resources/run_workflow_from_file_demo.png)

  - **run_workflow_with_json**

    - Run a workflow by providing the workflow JSON data directly.

        ```
        # You should ask to agent like this.
        Run comfyui workflow with this 
        {
          "3": {
              "inputs": {
                  "seed": 156680208700286,
                  "steps": 20,
            ... (workflow JSON example)
        }
        ```

---

## 5. How to Run

  ### 5.1 Using UV (Recommended)

  - Example `mcp.json`:

      ```json
      {
        "mcpServers": {
          "comfyui": {
            "command": "uv",
            "args": [
              "--directory",
              "PATH/MCP/comfyui",
              "run",
              "--with",
              "mcp",
              "--with",
              "websocket-client",
              "--with",
              "python-dotenv",
              "mcp",
              "run",
              "src/server.py:mcp"
            ]
          }
        }
      }
      ```

  ### 5.2 Using Docker

  - Downloading images to a local folder with `download_image` may be difficult since the Docker container does not share the host filesystem.
  - When using Docker, consider:
      1. Set `RETURN_URL=false` in `.env` to receive image data as bytes.
      2. Set `COMFYUI_HOST` in `.env` to the appropriate address (e.g., `host.docker.internal` or your server's IP).
      3. Note: Large image payloads may exceed response limits when using binary data.

  #### 5.2.1 Build Docker Image

  ```bash
  # First build image
  docker image build -t mcp/comfyui .
  ```

  ```json
  {
    "mcpServers": {
      "comfyui": {
        "command": "docker",
        "args": [
          "run",
          "-i",
          "--rm",
          "-p",
          "3001:3000",
          "mcp/comfyui"
        ]
      }
    }
  }
  ```

  #### 5.2.2 Using Existing Images

  Also you can use prebuilt image.

  ```json
  {
    "mcpServers": {
      "comfyui": {
        "command": "docker",
        "args": [
          "run",
          "-i",
          "--rm",
          "-p",
          "3001:3000",
          "overseer66/mcp-comfyui"
        ]
      }
    }
  }
  ```

  #### 5.2.3 Using SSE Transport

  1. Run the SSE server with Docker:

      ```bash
      docker run -i --rm -p 8001:8000 overseer66/mcp-comfyui-sse
      ```

  2. Configure `mcp.json` (change localhost to your IP or domain if needed):

      ```json
      {
        "mcpServers": {
          "comfyui": {
            "url": "http://localhost:8001/sse" 
          }
        }
      }
      ```

  > NOTE: When adding new workflows as tools, you need to rebuild and redeploy the Docker images to make them available.

---
