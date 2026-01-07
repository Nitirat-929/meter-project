# ใช้ Python 3.9 แบบ Slim (ขนาดเล็ก เบาเครื่อง)
FROM python:3.9-slim

# ลงโปรแกรมพื้นฐานของ Linux ที่จำเป็นสำหรับ Barcode และ Image Processing
RUN apt-get update && apt-get install -y \
    libzbar0 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ตั้งโฟลเดอร์ทำงานข้างในกล่อง
WORKDIR /app

# ก๊อปปี้ไฟล์รายการ Library ไปลง
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# ก๊อปปี้ไฟล์โค้ดทั้งหมด (factory.py, app.py) เข้าไป
COPY . .

# เปิดพอร์ต 8501 (พอร์ตมาตรฐานของ Streamlit)
EXPOSE 8501

# คำสั่งเริ่มต้น: สั่งรัน factory.py เป็นตัวหลัก
CMD ["streamlit", "run", "factory.py", "--server.address=0.0.0.0"]