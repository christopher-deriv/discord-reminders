import hashlib
import time
import logging
import asyncio
import base64
import io
import os
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)

# Optional ML solver dependencies
try:
    import numpy as np
    from PIL import Image
    import onnxruntime as ort
    HAS_ML_DEPS = True
except ImportError:
    HAS_ML_DEPS = False

API_BASE_URL = "https://kingshot-giftcode.centurygame.com/api"
SALT = "mN4!pQs6JrYwV9"

# Emulate authentic browser headers from redeemer.py
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://ks-giftcode.centurygame.com",
    "Referer": "https://ks-giftcode.centurygame.com/",
    "Connection": "keep-alive"
}

class KingShotMLSolver:
    def __init__(self, model_path="data/captcha_model.onnx"):
        self.model_path = model_path
        self.session = None
        self.enabled = False
        self.model_metadata = None
        
        if not HAS_ML_DEPS:
            logging.warning("ML Solver disabled: missing required libraries (onnxruntime, numpy, Pillow).")
            return
            
        if not os.path.exists(model_path):
            logging.warning(f"ML Solver disabled: model file not found at {model_path}.")
            return
            
        try:
            # Load metadata if exists
            metadata_path = model_path.replace(".onnx", "_metadata.json")
            if os.path.exists(metadata_path):
                import json
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.model_metadata = json.load(f)
                    
            # Initialize ONNX Inference session on CPU
            self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
            self.enabled = True
            
            # Analyze input layers dynamically
            self.input_name = self.session.get_inputs()[0].name
            
            if self.model_metadata:
                self.height, self.width = self.model_metadata['input_shape'][1:3]
                self.channels = self.model_metadata['input_shape'][0] if len(self.model_metadata['input_shape']) == 3 else 1
            else:
                self.channels = 1
                self.height = 40
                self.width = 150
                
            logging.info(f"ML Solver initialized with model: {model_path}. Dimensions: channels={self.channels}, height={self.height}, width={self.width}")
        except Exception as e:
            logging.error(f"ML Solver failed to load session: {e}")
            self.enabled = False

    def solve(self, base64_img: str) -> str:
        if not self.enabled:
            return ""
            
        try:
            # Clean headers if present in base64 string
            if "," in base64_img:
                base64_img = base64_img.split(",")[1]
                
            # Decode base64 image
            img_data = base64.b64decode(base64_img)
            img = Image.open(io.BytesIO(img_data))
            
            # Preprocess image channels
            if self.channels == 1:
                img = img.convert("L")
            else:
                img = img.convert("RGB")
                
            # Resize to expected dimensions
            img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
            
            # Convert to numpy float32 array
            img_arr = np.array(img, dtype=np.float32)
            
            # Normalize using metadata
            if self.model_metadata and 'normalization' in self.model_metadata:
                mean = self.model_metadata['normalization']['mean'][0]
                std = self.model_metadata['normalization']['std'][0]
                img_arr = (img_arr / 255.0 - mean) / std
            else:
                img_arr = (img_arr / 127.5) - 1.0
                
            # Restructure shape to [batch, channels, height, width]
            if self.channels == 1:
                img_arr = np.expand_dims(img_arr, axis=0) # [1, height, width]
            else:
                img_arr = np.transpose(img_arr, (2, 0, 1)) # [channels, height, width]
                
            img_tensor = np.expand_dims(img_arr, axis=0) # [1, channels, height, width]
            
            # Run inference
            outputs = self.session.run(None, {self.input_name: img_tensor})
            
            # Decode output using metadata map
            predicted_text = ""
            if self.model_metadata and 'idx_to_char' in self.model_metadata:
                idx_to_char = self.model_metadata['idx_to_char']
                for pos in range(4):
                    char_probs = outputs[pos][0]
                    predicted_idx = np.argmax(char_probs)
                    predicted_text += idx_to_char[str(predicted_idx)]
            else:
                vocab = "ABCDEFGHIJKLMNPQRSTUVWXYZ23456789"
                for pos in range(4):
                    char_probs = outputs[pos][0]
                    predicted_idx = np.argmax(char_probs)
                    if predicted_idx < len(vocab):
                        predicted_text += vocab[predicted_idx]
                        
            # Format output to alphanumeric characters only
            predicted_text = "".join([c for c in predicted_text if c.isalnum()]).strip()
            logging.info(f"ML CAPTCHA inference output: '{predicted_text}'")
            return predicted_text
        except Exception as e:
            logging.error(f"ML Solver inference error: {e}")
            return ""

class KingShotClient:
    def __init__(self, model_path="data/captcha_model.onnx"):
        self.solver = KingShotMLSolver(model_path)
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=HEADERS)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def generate_signature(self, params: dict) -> str:
        sorted_keys = sorted(params.keys())
        param_pairs = []
        for key in sorted_keys:
            param_pairs.append(f"{key}={params[key]}")
        param_string = "&".join(param_pairs)
        string_to_hash = f"{param_string}{SALT}"
        return hashlib.md5(string_to_hash.encode("utf-8")).hexdigest()

    async def make_post_request(self, endpoint: str, data: dict) -> dict:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(headers=HEADERS)
            
        url = f"{API_BASE_URL}/{endpoint}"
        
        if "time" not in data:
            data["time"] = str(int(time.time() * 1000))
        if "sign" not in data:
            data["sign"] = self.generate_signature(data)
            
        try:
            async with self.session.post(url, data=data) as response:
                if response.status == 429:
                    logging.warning("HTTP 429 Rate Limit encountered from KingShot API.")
                    return {"code": 429, "msg": "Rate limited by server"}
                if response.status != 200:
                    text = await response.text()
                    logging.error(f"HTTP Error {response.status}: {text}")
                    return {"code": -1, "msg": f"HTTP Error {response.status}"}
                
                res_data = await response.json()
                return res_data
        except Exception as e:
            logging.error(f"Error during KingShot POST request: {e}")
            return {"code": -1, "msg": str(e)}

    async def verify_player(self, fid: str) -> dict:
        payload = {"fid": str(fid)}
        return await self.make_post_request("player", payload)

    async def get_config(self) -> dict:
        return await self.make_post_request("gift_code_config", {})

    async def fetch_captcha(self, fid: str) -> dict:
        payload = {
            "fid": str(fid),
            "init": "0"
        }
        return await self.make_post_request("get_captcha", payload)

    async def redeem_code(self, fid: str, cdk: str, captcha_code: str = "") -> dict:
        payload = {
            "fid": str(fid),
            "cdk": str(cdk),
            "captcha_code": captcha_code
        }
        return await self.make_post_request("gift_code", payload)

    async def redeem_with_captcha_solver(self, fid: str, cdk: str) -> dict:
        """
        Attempts to redeem a gift code. Handles automated ML solver cycle and fallbacks.
        """
        res = await self.redeem_code(fid, cdk)
        
        code = res.get("code")
        err_code = res.get("err_code")
        msg = str(res.get("msg", "")).upper()
        
        # 40007 is the standard Century Games CAPTCHA required code, or TIME ERROR message
        is_captcha = (code == 1 and err_code == 40007) or "TIME ERROR" in msg or "CAPTCHA" in msg
        
        if is_captcha:
            if self.solver.enabled:
                logging.info(f"CAPTCHA challenge detected for player {fid}. Fetching CAPTCHA image...")
                captcha_res = await self.fetch_captcha(fid)
                captcha_data = captcha_res.get("data") or {}
                captcha_base64 = captcha_data.get("img")
                
                if captcha_base64:
                    logging.info(f"CAPTCHA image fetched successfully. Running ML solver...")
                    # Run CPU inference in thread to keep event loop fully non-blocking
                    solved_code = await asyncio.to_thread(self.solver.solve, captcha_base64)
                    
                    if solved_code:
                        logging.info(f"Resubmitting redemption for player {fid} with solved CAPTCHA: '{solved_code}'")
                        res = await self.redeem_code(fid, cdk, captcha_code=solved_code)
                    else:
                        logging.warning(f"ML Solver returned empty CAPTCHA string. Skipping player {fid}.")
                else:
                    err_msg = captcha_res.get("msg", "Unknown error")
                    logging.warning(f"Failed to fetch CAPTCHA image (msg: {err_msg}). Skipping player {fid}.")
            else:
                logging.warning(f"CAPTCHA required for player {fid} but ML Solver is disabled. Skipping player.")
                
        return res
