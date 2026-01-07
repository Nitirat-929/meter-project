import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image
import requests
from io import BytesIO
import pandas as pd
import easyocr
import numpy as np

st.set_page_config(page_title="Meter Serial Reader", layout="wide")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

st.title("🔍 ระบบอ่านเลขซีเรียลมิเตอร์ (68xxxxxxx)")
st.info("วางลิงก์รูปมิเตอร์ที่บาร์โค้ดไม่ชัด ระบบจะดึงเลขจากภาพให้แทนครับ")

urls_input = st.text_area("วางลิงก์ภาพที่นี่ (1 ลิงก์ต่อบรรทัด):", height=200)

if st.button("🚀 เริ่มดึงข้อมูล"):
    if urls_input.strip():
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]
        results = []
        progress = st.progress(0)
        
        for idx, url in enumerate(urls):
            try:
                response = requests.get(url, timeout=15)
                img = Image.open(BytesIO(response.content))
                decoded = decode(img)
                found_data = ""
                method = ""
                
                # --- จุดที่แก้ไข 1: Barcode ---
                if decoded:
                    # อ่านค่าเดิมแล้วเติม (Scan) ต่อท้าย
                    raw_serial = decoded[0].data.decode('utf-8')
                    found_data = f"{raw_serial} (Scan)"
                    method = "Barcode"
                # ---------------------------
                else:
                    img_np = np.array(img)
                    ocr_res = reader.readtext(img_np)
                    for (bbox, text, prob) in ocr_res:
                        clean = "".join(filter(str.isdigit, text))
                        # --- จุดที่แก้ไข 2: OCR ---
                        if clean.startswith('68') and 8 <= len(clean) <= 11:
                            found_data = f"{clean} (OCR)" # เติม (OCR) ต่อท้าย
                            method = "OCR (Serial)"
                            break
                        # -----------------------
                
                results.append({
                    "ลำดับ": idx + 1,
                    "เลขซีเรียล": found_data if found_data else "อ่านไม่ได้",
                    "วิธีที่ใช้": method if found_data else "-",
                    "ลิงก์ภาพ": url
                })
            except:
                results.append({"ลำดับ": idx + 1, "เลขซีเรียล": "Error", "วิธีที่ใช้": "โหลดภาพไม่ได้", "ลิงก์ภาพ": url})
            
            progress.progress((idx + 1) / len(urls))

        # แสดงตารางผลลัพธ์
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)

        # เพิ่มปุ่มดาวน์โหลด CSV
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="💾 ดาวน์โหลดผลลัพธ์ (CSV)",
            data=csv,
            file_name="meter_serial_results.csv",
            mime="text/csv",
        )
    else:
        st.warning("กรุณาวางลิงก์ภาพก่อนครับ")