# Bài tập: Chạy chatbot Pygame + Google Gemini (source có sẵn)

Dự án gồm `main.py` (cửa sổ **AI Chat**), `requirements.txt`. Bài tập là làm theo từng bước để lấy code, lấy API key, chạy chương trình, nhập key và thử chat.

---

## Bước 1 — Lấy source code về máy

1. Sao chép **toàn bộ thư mục dự án** về máy (có ít nhất `main.py` và `requirements.txt`) — ví dụ: tải ZIP, `git clone`, hoặc copy từ giảng viên.
2. Mở terminal tại **thư mục gốc** của dự án (cùng cấp với `main.py`).

**Kiểm tra:** Trong thư mục thấy được `main.py` và `requirements.txt`.

---

## Bước 2 — Cài thư viện Python

Cần Python 3.10 trở lên (khuyến nghị).

```bash
pip install -r requirements.txt
```

Hoặc:

```bash
pip install pygame google-generativeai pyperclip
```

**Lưu ý:** Ứng dụng dùng gói `google-generativeai` (trong code: `import google.generativeai as genai`).

---

## Bước 3 — Lấy API key (Google AI Studio)

1. Mở trình duyệt: [Google AI Studio — API keys](https://aistudio.google.com/apikey).
2. Đăng nhập Google.
3. Tạo **API key** mới (hoặc dùng key đã có).
4. **Sao chép** key (thường bắt đầu bằng `AIza...`).

**Bảo mật:** Không đăng key lên mạng xã hội hoặc repo công khai. Trong bài tập này bạn **dán key trong ô trên giao diện**, không cần sửa trực tiếp trong file `.py`.

---

## Bước 4 — Chạy chương trình

Trong thư mục dự án:

```bash
python main.py
```

Cửa sổ **AI Chat** hiện ra. Nếu báo thiếu module, quay lại Bước 2 (đúng môi trường Python đang dùng lệnh `python`).

---

## Bước 5 — Gắn API key và thử chat

1. Click vào ô **API Key** (dòng có chữ “API Key:”), **dán** key đã copy.
2. Nhấn **Enter** hoặc nút **Lưu**.  
   - Có thông báo “API key đã được lưu!”  
   - Chấm tròn cạnh tiêu đề chuyển **xanh** khi đã có key.  
   - Có nút **show** / **hide** để xem hoặc ẩn key khi cần.
3. Click ô nhập **phía dưới**, gõ câu hỏi (ví dụ: *Xin chào, bạn là ai?*).
4. Nhấn **Enter** hoặc nút **Gửi**.
5. Đợi phản hồi trong khung chat. Có thể **đổi model Gemini** bằng mũi tên ◀ ▶ trên thanh tiêu đề (danh sách nằm trong biến `FREE_MODELS` trong `main.py`).

**Mẹo trong app:** Chuột phải lên một bubble tin nhắn để **copy** nội dung (cần `pyperclip`).

---

## Checklist nộp bài / tự kiểm tra

- [ ] Đã có source đầy đủ và mở terminal đúng thư mục.
- [ ] `pip install -r requirements.txt` chạy xong không lỗi.
- [ ] Đã tạo/lấy API key từ AI Studio.
- [ ] `python main.py` mở được cửa sổ chat.
- [ ] Lưu API key thành công; gửi ít nhất một câu và nhận được trả lời từ AI (hoặc đọc được thông báo lỗi rõ nếu key/mạng lỗi).

---

## Xử lý sự cố thường gặp

| Hiện tượng | Gợi ý |
|------------|--------|
| `ModuleNotFoundError` | Cài lại Bước 2; kiểm tra đúng phiên bản `python` / `pip`. |
| “Vui lòng nhập và lưu API key trước!” | Dán key và bấm **Lưu** (hoặc Enter khi đang gõ trong ô API). |
| Bubble `[Lỗi] ...` | Key sai, hết quota, hoặc API chưa bật; kiểm tra AI Studio và kết nối mạng. |
| Không copy được bằng chuột phải | Cài `pyperclip`; trên một số OS cần quyền clipboard. |

---

## File khác trong repo

- `bai_tap.md` — bài tập / bài giải mẫu theo hướng **tự code** chatbot đơn giản (khác cấu trúc với `main.py` hiện tại).
- File **này** (`bai_tap_huong_dan_chat_pygame.md`) chỉ hướng dẫn **dùng sẵn** ứng dụng chat Pygame trong thư mục này.
