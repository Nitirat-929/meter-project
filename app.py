import streamlit as st
from pyzbar.pyzbar import decode
from PIL import Image, UnidentifiedImageError, ImageEnhance, ImageOps
import requests
from requests.exceptions import RequestException
from io import BytesIO
import pandas as pd
import easyocr
import numpy as np
import base64

# ==========================================
# 1. ฟังก์ชัน Logic (แก้ไส้ในใหม่ให้อ่านบาร์โค้ดโหดขึ้น)
# ==========================================
def process_image_logic(img, reader_obj):
    # --- เตรียมภาพ (Resize) ---
    max_dim = 1500 # เพิ่มความละเอียดขึ้นหน่อยเผื่อบาร์โค้ดเล็ก
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    # แปลงเป็นขาวดำ
    gray = img.convert('L')

    # --- สร้างภาพหลายเวอร์ชั่นเพื่อดักจับบาร์โค้ด (สูตรแก้บาร์โค้ดตายยาก) ---
    images_to_check = []
    
    # 1. ภาพ Original ขาวดำ
    images_to_check.append(gray)
    
    # 2. ภาพ Auto Contrast (แก้แสงจ้า/มืดเกิน)
    auto = ImageOps.autocontrast(gray)
    images_to_check.append(auto)
    
    # 3. ภาพ High Contrast (เข้มจัด)
    enhancer = ImageEnhance.Contrast(gray)
    high_contrast = enhancer.enhance(2.5) # เพิ่มเป็น 2.5
    images_to_check.append(high_contrast)
    
    # 4. ภาพ Binary (Threshold แบบ Adaptive - ช่วยภาพที่มีเงาบัง)
    # ใช้ numpy ช่วยทำ Threshold แบบง่ายๆ แต่ได้ผลดีกว่า fix ค่า 100
    np_img = np.array(gray)
    thresh_val = np.mean(np_img) # ใช้ค่าเฉลี่ยแสงของภาพเป็นตัวตัด
    binary = gray.point(lambda x: 0 if x < thresh_val - 20 else 255, '1')
    images_to_check.append(binary)

    # --- วนลูปหมุนภาพ + สแกน Barcode ---
    angles = [0, -90, 90, 180] # เพิ่ม 180 องศา (กลับหัว)
    
    for img_ver in images_to_check:
        for angle in angles:
            if angle != 0:
                rotated = img_ver.rotate(angle, expand=True)
            else:
                rotated = img_ver
            
            # ยิง Barcode
            decoded = decode(rotated)
            if decoded:
                for d in decoded:
                    raw_val = d.data.decode('utf-8')
                    # กรองขยะ: เอาเฉพาะที่ยาวเกิน 4 ตัว
                    if len(raw_val) >= 4:
                        return raw_val, "Barcode"

    # --- ถ้า Barcode ไม่เจอจริงๆ ให้ใช้ OCR (Logic เดิมของคุณ) ---
    img_np = np.array(gray) # ใช้ภาพขาวดำปกติส่ง OCR
    ocr_res = reader_obj.readtext(img_np, detail=0) 
    
    candidates = []
    for text in ocr_res:
        clean = "".join(c for c in text if c.isalnum())
        if len(clean) >= 5:
            score = len(clean)
            if clean.isdigit(): score += 50 # เพิ่มคะแนนตัวเลขให้เยอะขึ้น (จาก 20 เป็น 50)
            else: score += sum(c.isdigit() for c in clean)
            candidates.append((score, clean))
    
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1], "OCR"
        
    return "ไม่พบข้อมูล", "Error"

def image_to_base64(img):
    buffered = BytesIO()
    img.convert('RGB').save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

# ฟังก์ชันสำหรับกดปุ่ม Clear
def clear_data():
    st.session_state.clear()
    st.rerun()

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

# ==========================================
# 2. ส่วนหน้าจอ (UI เดิมเป๊ะๆ)
# ==========================================
st.set_page_config(page_title="Universal Barcode Reader", layout="wide")

# --- ส่วนหัวและปุ่มเคลียร์ ---
col_title, col_clear = st.columns([3, 1])
with col_title:
    st.title("🔍 ʙᴀʀᴄᴏᴅᴇ ʀᴇᴀᴅᴇʀ  ⛶")
with col_clear:
    st.write("") 
    st.write("")
    if st.button("🗑️ ล้างหน้าจอ (Clear All)", type="secondary", use_container_width=True):
        clear_data()

tab1, tab2 = st.tabs(["🔗 วางลิงก์ภาพ (URL)", "📂 อัปโหลดไฟล์ (File)"])

urls = []
uploaded_files = []

with tab1:
    urls_input = st.text_area("วางลิงก์ภาพ (1 ลิงก์ต่อบรรทัด):", height=150, key="url_input")
    if urls_input.strip():
        urls = [url.strip() for url in urls_input.split('\n') if url.strip()]

with tab2:
    uploaded_files = st.file_uploader("เลือกไฟล์รูปภาพ", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, key="file_input")

if st.button("🚀 เริ่มประมวลผล", type="primary"):
    results = []
    total = len(urls) + len(uploaded_files)
    
    if total > 0:
        bar = st.progress(0)
        idx_count = 0
        headers = {'User-Agent': 'Mozilla/5.0'}

        # --- Process URL ---
        for url in urls:
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                img = Image.open(BytesIO(resp.content))
                val, method_type = process_image_logic(img, reader)
                
                if method_type == "Barcode":
                    serial_display = f"{val} (Scan)"
                    method_display = "Barcode"
                elif method_type == "OCR":
                    serial_display = f"{val} (OCR)"
                    method_display = "OCR (Serial)" 
                else:
                    serial_display = "อ่านไม่ได้"
                    method_display = "-"

                results.append({
                    "preview": image_to_base64(img.resize((50,50))),
                    "ลำดับ": 0,
                    "เลขซีเรียล": serial_display,
                    "วิธีที่ใช้": method_display,
                    "ลิงก์ภาพ": url
                })
            except Exception as e:
                results.append({
                    "preview": None,
                    "ลำดับ": 0,
                    "เลขซีเรียล": "Error",
                    "วิธีที่ใช้": "Error",
                    "ลิงก์ภาพ": url
                })
            idx_count += 1
            bar.progress(idx_count / total)

        # --- Process File ---
        for up_file in uploaded_files:
            try:
                img = Image.open(up_file)
                val, method_type = process_image_logic(img, reader)
                
                if method_type == "Barcode":
                    serial_display = f"{val} (Scan)"
                    method_display = "Barcode"
                elif method_type == "OCR":
                    serial_display = f"{val} (OCR)"
                    method_display = "OCR (Serial)"
                else:
                    serial_display = "อ่านไม่ได้"
                    method_display = "-"

                results.append({
                    "preview": image_to_base64(img.resize((50,50))),
                    "ลำดับ": 0,
                    "เลขซีเรียล": serial_display,
                    "วิธีที่ใช้": method_display,
                    "ลิงก์ภาพ": up_file.name
                })
            except Exception as e:
                results.append({
                    "preview": None,
                    "ลำดับ": 0,
                    "เลขซีเรียล": "Error",
                    "วิธีที่ใช้": "Error",
                    "ลิงก์ภาพ": up_file.name
                })
            idx_count += 1
            bar.progress(idx_count / total)

        bar.empty()
        
        # --- สร้าง DataFrame และจัดเรียง ---
        if results:
            df = pd.DataFrame(results)
            df['ลำดับ'] = range(1, len(df) + 1)
            
            final_df = df[['ลำดับ', 'เลขซีเรียล', 'วิธีที่ใช้', 'ลิงก์ภาพ']]

            st.subheader("✅ ผลลัพธ์การอ่านค่า")
            
            display_df = df[['preview', 'ลำดับ', 'เลขซีเรียล', 'วิธีที่ใช้', 'ลิงก์ภาพ']]
            st.data_editor(
                display_df,
                column_config={
                    "preview": st.column_config.ImageColumn("รูป"),
                    "ลิงก์ภาพ": st.column_config.TextColumn("ลิงก์/ชื่อไฟล์", width="large"),
                },
                hide_index=True,
                use_container_width=True
            )

            csv = final_df.to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="💾 ดาวน์โหลด CSV ",
                data=csv,
                file_name="meter_serial_results_clean.csv",
                mime="text/csv",
                type="primary"
            )
    else:
        st.warning("⚠️ กรุณาใส่ลิงก์ หรือ อัปโหลดไฟล์ก่อนกดปุ่มครับ")