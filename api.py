# api.py
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pyzbar.pyzbar import decode
from PIL import Image, ImageEnhance, ImageOps
import numpy as np
import io

app = FastAPI()

# --- Config CORS (สำคัญมาก ไม่งั้น Vue จะคุยกับ Python ไม่ได้) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ยอมให้ทุกเว็บยิงมาได้ (dev mode)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Logic เดิม (ย่อมา) ---
def process_image_logic(img_bytes):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        
        # Logic การเตรียมภาพแบบเดิมของคุณ
        gray = img.convert('L')
        images_to_check = [
            gray,
            ImageOps.autocontrast(gray),
            ImageEnhance.Contrast(gray).enhance(2.5)
        ]
        
        # 1. Scan Barcode
        for img_ver in images_to_check:
            for angle in [0, -90, 90, 180]:
                rotated = img_ver if angle == 0 else img_ver.rotate(angle, expand=True)
                decoded = decode(rotated)
                if decoded:
                    val = decoded[0].data.decode('utf-8')
                    if len(val) >= 4:
                        return {"serial": val, "method": "Barcode Scan", "status": "Success"}
        
        # 2. Mock OCR (ตัด OCR จริงออกก่อนเพื่อให้โค้ดสั้นลงสำหรับการเทส API)
        # ถ้าจะเอา OCR กลับมา ใส่ code easyocr ตรงนี้ได้เลย
        return {"serial": "Not Found", "method": "Failed", "status": "Failed"}
        
    except Exception as e:
        return {"serial": "Error", "method": str(e), "status": "Error"}

# --- API Endpoint ---
@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    # อ่านไฟล์ที่ Vue ส่งมา
    contents = await file.read()
    result = process_image_logic(contents)
    return result

# วิธีรัน: uvicorn api:app --reload