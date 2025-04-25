import os
import base64
import websocket
import json
import uuid
import urllib.parse
import urllib.request
from typing import Dict, Any

class ComfyUI:
    def __init__(self, url: str, authentication: str = None):
        self.url = url
        self.authentication = authentication
        self.client_id = str(uuid.uuid4())
        self.headers = {
            "Content-Type": "application/json"
        }
        if authentication:
            self.headers["Authorization"] = authentication

    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        url = f"{self.url}/view?{url_values}"
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            image_bytes = response.read()
            return base64.b64encode(image_bytes).decode("utf-8")

    def get_history(self, prompt_id):
        url = f"{self.url}/history/{prompt_id}"
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    
    def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}/prompt",
            headers=self.headers,
            data=data
        )
        return json.loads(urllib.request.urlopen(req).read())
    
    async def process_workflow(self, workflow_name: str, params: Dict[str, Any], return_url: bool = False):
        workflow_path = os.path.join(os.environ.get("WORKFLOW_DIR", "workflows"), f"{workflow_name}.json")
        if not os.path.exists(workflow_path):
            raise Exception(f"Workflow {workflow_name} not found")

        with open(workflow_path, "r", encoding='utf-8') as f:
            prompt = json.load(f)

        self.update_workflow_params(prompt, params)

        ws = websocket.WebSocket()
        ws_url = f"ws://{os.environ.get("COMFYUI_HOST", "localhost")}:{os.environ.get("COMFYUI_PORT", 8188)}/ws?clientId={self.client_id}"
        
        if self.authentication:
            ws.connect(ws_url, header=[f"Authorization: {self.authentication}"])
        else:
            ws.connect(ws_url)

        try:
            images = self.get_images(ws, prompt, return_url)
            return images
        finally:
            ws.close()

    def get_images(self, ws, prompt, return_url):
        prompt_id = self.queue_prompt(prompt)["prompt_id"]
        output_images = {}
        
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message["type"] == "executing":
                    data = message["data"]
                    if data["node"] is None and data["prompt_id"] == prompt_id:
                        break
            else:
                continue

        history = self.get_history(prompt_id)[prompt_id]
        for node_id in history["outputs"]:
            node_output = history["outputs"][node_id]
            if "images" in node_output:
                if return_url:
                    output_images[node_id] = []
                    for image in node_output["images"]:
                        data = {"filename": image["filename"], "subfolder": image["subfolder"], "type": image["type"]}
                        url_values = urllib.parse.urlencode(data)
                        url = f"{self.url}/view?{url_values}"
                        output_images[node_id].append(url)
                else:
                    output_images[node_id] = [
                        self.get_image(image["filename"], image["subfolder"], image["type"])
                        for image in node_output["images"]
                    ]

        return output_images

    def update_workflow_params(self, prompt, params):
        if not params:
            return

        for node in prompt.values():
            if node["class_type"] == "CLIPTextEncode" and "text" in params:
                if isinstance(node["inputs"]["text"], str):
                    node["inputs"]["text"] = params["text"]
            elif node["class_type"] == "KSampler":
                if "seed" in params:
                    node["inputs"]["seed"] = params["seed"]
                if "steps" in params:
                    node["inputs"]["steps"] = params["steps"]
                if "cfg" in params:
                    node["inputs"]["cfg"] = params["cfg"]
                if "denoise" in params:
                    node["inputs"]["denoise"] = params["denoise"]
            
            elif node["class_type"] == "LoadImage" and "image" in params:
                node["inputs"]["image"] = params["image"]
