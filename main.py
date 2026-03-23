import sys, threading, textwrap
import pygame
import pyperclip
import google.generativeai as genai

# Free tier models (không cần billing):
#   gemini-2.5-flash      – nhanh, thông minh, miễn phí
#   gemini-2.5-flash-lite – nhanh nhất, nhẹ nhất, miễn phí
#   gemini-2.5-pro        – mạnh nhất nhưng giới hạn thấp hơn
FREE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
]
MODEL    = FREE_MODELS[0]   # mặc định: gemini-2.5-flash
W, H     = 880, 680
TOP_H    = 50
APIKEY_H = 56
INPUT_H  = 64
SIDE_PAD = 14

pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("AI Chat")
clock = pygame.time.Clock()

font       = pygame.font.SysFont("Segoe UI", 16)
font_bold  = pygame.font.SysFont("Segoe UI", 17, bold=True)
font_small = pygame.font.SysFont("Segoe UI", 13)

BG       = (243, 244, 248)
WHITE    = (255, 255, 255)
BLUE     = (60, 110, 230)
GREEN    = (34, 170, 90)
GRAY     = (148, 153, 165)
LGRAY    = (208, 210, 220)
BLACK    = (28, 28, 38)
TOAST_BG = (38, 38, 52)
RED_SOFT = (200, 80, 80)
SEL_BG   = (180, 210, 255)

# ── TextInput class ────────────────────────────────────────────────────────────
class TextInput:
    """Input field với cursor đầy đủ: ←/→, Home/End, Del, Ctrl+A/C/V/X."""

    def __init__(self, placeholder="", password=False, allow_newline=False):
        self.text          = ""
        self.cursor        = 0
        self.sel_start     = None   # None = không có selection
        self.placeholder   = placeholder
        self.password      = password
        self.allow_newline = allow_newline
        self._scroll_px    = 0      # pixel offset để giữ cursor nhìn thấy

    # ── keyboard ──────────────────────────────────────────────────────────────
    def handle_key(self, event):
        mods = pygame.key.get_mods()
        ctrl = bool(mods & pygame.KMOD_CTRL)
        shift = bool(mods & pygame.KMOD_SHIFT)

        # ── Ctrl shortcuts ────────────────────────────────────────────────────
        if ctrl:
            if event.key == pygame.K_a:
                self.sel_start = 0
                self.cursor    = len(self.text)
                return
            if event.key == pygame.K_c:
                sel = self._selected_text()
                if sel:
                    try: pyperclip.copy(sel)
                    except Exception: pass
                return
            if event.key == pygame.K_x:
                sel = self._selected_text()
                if sel:
                    try: pyperclip.copy(sel)
                    except Exception: pass
                    self._delete_selection()
                return
            if event.key == pygame.K_v:
                try:
                    raw   = pyperclip.paste() or ""
                    clean = raw if self.allow_newline else raw.replace("\n", " ").replace("\r", "")
                    clean = "".join(c for c in clean if c.isprintable() or (self.allow_newline and c == "\n"))
                    self._delete_selection()
                    self.text   = self.text[:self.cursor] + clean + self.text[self.cursor:]
                    self.cursor += len(clean)
                except Exception: pass
                return
            # Ctrl+← / Ctrl+→ : jump word
            if event.key == pygame.K_LEFT:
                if not shift: self.sel_start = None
                elif self.sel_start is None: self.sel_start = self.cursor
                self.cursor = self._word_left()
                return
            if event.key == pygame.K_RIGHT:
                if not shift: self.sel_start = None
                elif self.sel_start is None: self.sel_start = self.cursor
                self.cursor = self._word_right()
                return

        # ── Arrow keys ────────────────────────────────────────────────────────
        if event.key == pygame.K_LEFT:
            if self.sel_start is not None and not shift:
                self.cursor    = min(self.cursor, self.sel_start)
                self.sel_start = None
            else:
                if shift and self.sel_start is None: self.sel_start = self.cursor
                if self.cursor > 0: self.cursor -= 1
                if not shift: self.sel_start = None
            return
        if event.key == pygame.K_RIGHT:
            if self.sel_start is not None and not shift:
                self.cursor    = max(self.cursor, self.sel_start)
                self.sel_start = None
            else:
                if shift and self.sel_start is None: self.sel_start = self.cursor
                if self.cursor < len(self.text): self.cursor += 1
                if not shift: self.sel_start = None
            return
        if event.key == pygame.K_HOME:
            if shift and self.sel_start is None: self.sel_start = self.cursor
            self.cursor = 0
            if not shift: self.sel_start = None
            return
        if event.key == pygame.K_END:
            if shift and self.sel_start is None: self.sel_start = self.cursor
            self.cursor = len(self.text)
            if not shift: self.sel_start = None
            return

        # ── Delete / Backspace ────────────────────────────────────────────────
        if event.key == pygame.K_BACKSPACE:
            if self.sel_start is not None:
                self._delete_selection()
            elif self.cursor > 0:
                self.text   = self.text[:self.cursor - 1] + self.text[self.cursor:]
                self.cursor -= 1
            return
        if event.key == pygame.K_DELETE:
            if self.sel_start is not None:
                self._delete_selection()
            elif self.cursor < len(self.text):
                self.text = self.text[:self.cursor] + self.text[self.cursor + 1:]
            return

        # ── Printable chars ───────────────────────────────────────────────────
        if event.unicode and (event.unicode.isprintable() or
                              (self.allow_newline and event.unicode == "\n")):
            self._delete_selection()
            self.text   = self.text[:self.cursor] + event.unicode + self.text[self.cursor:]
            self.cursor += 1

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self, surface, rect, fnt, focused, cursor_on,
             border_focus=BLUE, border_idle=LGRAY, bg=WHITE, tc=BLACK):
        PAD = 10
        inner_w = rect.width - PAD * 2

        pygame.draw.rect(surface, bg, rect, border_radius=8)
        pygame.draw.rect(surface, border_focus if focused else border_idle, rect, 2, border_radius=8)

        disp = ("*" * len(self.text)) if self.password else self.text

        # keep cursor visible: adjust scroll
        cur_px = fnt.size(disp[:self.cursor])[0]
        if cur_px - self._scroll_px > inner_w:
            self._scroll_px = cur_px - inner_w
        if cur_px - self._scroll_px < 0:
            self._scroll_px = cur_px
        self._scroll_px = max(0, self._scroll_px)

        tx = rect.x + PAD - self._scroll_px
        ty = rect.y + (rect.height - fnt.get_height()) // 2

        clip = rect.inflate(-2, -2)
        surface.set_clip(clip)

        # selection highlight
        if focused and self.sel_start is not None:
            s0 = min(self.sel_start, self.cursor)
            s1 = max(self.sel_start, self.cursor)
            sx0 = tx + fnt.size(disp[:s0])[0]
            sx1 = tx + fnt.size(disp[:s1])[0]
            sel_rect = pygame.Rect(sx0, rect.y + 4, sx1 - sx0, rect.height - 8)
            pygame.draw.rect(surface, SEL_BG, sel_rect)

        if disp:
            surface.blit(fnt.render(disp, True, tc), (tx, ty))
        elif self.placeholder:
            surface.blit(fnt.render(self.placeholder, True, GRAY), (rect.x + PAD, ty))

        # cursor blink
        if focused and cursor_on:
            cx = tx + cur_px
            pygame.draw.line(surface, border_focus, (cx, rect.y + 6), (cx, rect.bottom - 6), 2)

        surface.set_clip(None)

    # ── internal helpers ──────────────────────────────────────────────────────
    def _selected_text(self):
        if self.sel_start is None: return ""
        s0, s1 = sorted((self.sel_start, self.cursor))
        return self.text[s0:s1]

    def _delete_selection(self):
        if self.sel_start is None: return
        s0, s1      = sorted((self.sel_start, self.cursor))
        self.text   = self.text[:s0] + self.text[s1:]
        self.cursor = s0
        self.sel_start = None

    def _word_left(self):
        p = self.cursor
        while p > 0 and self.text[p - 1] == " ": p -= 1
        while p > 0 and self.text[p - 1] != " ": p -= 1
        return p

    def _word_right(self):
        p = self.cursor
        while p < len(self.text) and self.text[p] != " ": p += 1
        while p < len(self.text) and self.text[p] == " ": p += 1
        return p

    def clear(self):
        self.text = ""; self.cursor = 0; self.sel_start = None; self._scroll_px = 0

    @property
    def value(self):
        return self.text


# ── App state ──────────────────────────────────────────────────────────────────
model_idx    = 0   # index vào FREE_MODELS
api_field    = TextInput(placeholder="AIza... hoặc sk-...  (Enter / Lưu để xác nhận)", password=True)
q_field      = TextInput(placeholder="Nhập câu hỏi rồi nhấn Enter hoặc Gửi…")
api_key      = ""
api_visible  = False
focus_api    = False     # True = ô API key đang active

messages     = []
loading      = False
prev_loading = False
dot_frame    = 0

scroll_y     = 0
cursor_on    = True
cursor_t     = 0.0
toast        = ""
toast_t      = 0.0

# ── Icon helpers ───────────────────────────────────────────────────────────────
def draw_arrow(surface, rect, direction, color):
    """Vẽ tam giác trỏ 'left' hoặc 'right' căn giữa rect."""
    cx, cy = rect.centerx, rect.centery
    s = 5   # kích thước nửa tam giác
    if direction == "left":
        pts = [(cx + s, cy - s), (cx + s, cy + s), (cx - s, cy)]
    else:
        pts = [(cx - s, cy - s), (cx - s, cy + s), (cx + s, cy)]
    pygame.draw.polygon(surface, color, pts)

def draw_send_icon(surface, rect, color):
    """Vẽ mũi tên giấy nhỏ (paper plane) bên phải nút Gửi."""
    cx, cy = rect.centerx + 16, rect.centery
    s = 5
    pts = [(cx - s, cy - s), (cx + s, cy), (cx - s, cy + s), (cx - 1, cy)]
    pygame.draw.polygon(surface, color, pts)

# ── Helpers ────────────────────────────────────────────────────────────────────
def get_cr():
    return pygame.Rect(0, TOP_H + APIKEY_H, W, H - TOP_H - APIKEY_H - INPUT_H)

def show_toast(msg, dur=2.5):
    global toast, toast_t
    toast, toast_t = msg, dur

def wrap_text(text, max_w, fnt):
    char_w = max(1, fnt.size("M")[0])
    cols   = max(1, max_w // char_w)
    lines  = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
        else:
            lines.extend(textwrap.wrap(para, width=cols) or [""])
    return lines

def total_chat_h():
    cr      = get_cr()
    bub_max = int(cr.width * 0.76)
    h       = 14
    for m in messages:
        lns = wrap_text(m["content"], bub_max - 28, font)
        h  += len(lns) * (font.get_linesize() + 2) + 24 + 10
    if loading:
        h += 48
    return h

def call_api(history, model_name):
    global loading
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        gemini_history = []
        for m in history[:-1]:
            role = "model" if m["role"] == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [m["content"]]})
        chat    = model.start_chat(history=gemini_history)
        resp    = chat.send_message(history[-1]["content"])
        messages.append({"role": "assistant", "content": resp.text or ""})
    except Exception as e:
        messages.append({"role": "assistant", "content": f"[Lỗi] {e}"})
    loading = False

def send_message():
    global loading
    if loading or not q_field.value.strip():
        return
    if not api_key:
        show_toast("Vui lòng nhập và lưu API key trước!")
        return
    text = q_field.value.strip()
    messages.append({"role": "user", "content": text})
    q_field.clear()
    loading = True
    history    = [{"role": m["role"], "content": m["content"]} for m in messages]
    model_name = FREE_MODELS[model_idx]
    threading.Thread(target=call_api, args=(history, model_name), daemon=True).start()

def save_api():
    global api_key, focus_api
    api_key   = api_field.value.strip()
    focus_api = False
    show_toast("API key đã được lưu!" if api_key else "API key không được để trống!")

# ── Main loop ──────────────────────────────────────────────────────────────────
while True:
    dt       = clock.tick(60) / 1000.0
    cursor_t += dt
    if cursor_t >= 0.5:
        cursor_t, cursor_on = 0.0, not cursor_on
    if loading:
        dot_frame = (dot_frame + 1) % 90
    if toast_t > 0:
        toast_t = max(0.0, toast_t - dt)

    cr      = get_cr()
    bub_max = int(cr.width * 0.76)

    if prev_loading and not loading:
        scroll_y = max(0, total_chat_h() - cr.height)
    prev_loading = loading

    # ── Events ────────────────────────────────────────────────────────────────
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if event.type == pygame.MOUSEWHEEL and cr.collidepoint(pygame.mouse.get_pos()):
            max_s    = max(0, total_chat_h() - cr.height)
            scroll_y = max(0, min(max_s, scroll_y - event.y * 30))

        if event.type == pygame.KEYDOWN:
            if focus_api:
                if event.key == pygame.K_RETURN:
                    save_api()
                elif event.key == pygame.K_ESCAPE:
                    focus_api = False
                else:
                    api_field.handle_key(event)
            else:
                if event.key == pygame.K_RETURN and not loading:
                    send_message()
                elif event.key == pygame.K_ESCAPE:
                    pass
                else:
                    q_field.handle_key(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            ai_box  = pygame.Rect(SIDE_PAD + 74, TOP_H + 11, W - SIDE_PAD*2 - 74 - 102, 34)
            tog_btn = pygame.Rect(W - SIDE_PAD - 94, TOP_H + 11, 44, 34)
            sav_btn = pygame.Rect(W - SIDE_PAD - 44, TOP_H + 11, 44, 34)
            s_btn   = pygame.Rect(W - SIDE_PAD - 86, H - INPUT_H + 12, 86, INPUT_H - 24)
            clr_btn = pygame.Rect(W - SIDE_PAD - 70, 9, 70, TOP_H - 18)
            q_rect  = pygame.Rect(SIDE_PAD, H - INPUT_H + 12, W - SIDE_PAD*2 - 92, INPUT_H - 24)

            if event.button == 1:
                mdl_prev = pygame.Rect(W // 2 - 110, 9, 26, TOP_H - 18)
                mdl_next = pygame.Rect(W // 2 + 84,  9, 26, TOP_H - 18)
                if ai_box.collidepoint(mx, my):
                    focus_api = True
                elif sav_btn.collidepoint(mx, my):
                    save_api()
                elif tog_btn.collidepoint(mx, my):
                    api_visible = not api_visible
                    api_field.password = not api_visible
                elif s_btn.collidepoint(mx, my):
                    send_message()
                elif clr_btn.collidepoint(mx, my) and messages:
                    messages.clear(); scroll_y = 0
                    show_toast("Đã xóa hội thoại")
                elif mdl_prev.collidepoint(mx, my) and not loading:
                    model_idx = (model_idx - 1) % len(FREE_MODELS)
                    show_toast(f"Model: {FREE_MODELS[model_idx]}")
                elif mdl_next.collidepoint(mx, my) and not loading:
                    model_idx = (model_idx + 1) % len(FREE_MODELS)
                    show_toast(f"Model: {FREE_MODELS[model_idx]}")
                elif q_rect.collidepoint(mx, my):
                    focus_api = False
                else:
                    if focus_api and not ai_box.collidepoint(mx, my):
                        focus_api = False

            # Right-click → copy bubble
            if event.button == 3 and cr.collidepoint(mx, my):
                y_pos = cr.y + 14 - scroll_y
                for msg in messages:
                    lns    = wrap_text(msg["content"], bub_max - 28, font)
                    ls     = font.get_linesize() + 2
                    bh     = len(lns) * ls + 24
                    max_lw = max((font.size(ln)[0] for ln in lns if ln), default=50)
                    bw     = min(bub_max, max_lw + 28)
                    bx     = (cr.right - bw - SIDE_PAD) if msg["role"] == "user" else (cr.x + SIDE_PAD)
                    if pygame.Rect(bx, y_pos, bw, bh).collidepoint(mx, my):
                        try:
                            pyperclip.copy(msg["content"]); show_toast("Đã copy!")
                        except Exception:
                            show_toast("Lỗi copy")
                        break
                    y_pos += bh + 10

    # ── Draw ──────────────────────────────────────────────────────────────────
    screen.fill(BG)

    # --- Title bar ---
    pygame.draw.rect(screen, WHITE, (0, 0, W, TOP_H))
    pygame.draw.line(screen, LGRAY, (0, TOP_H), (W, TOP_H), 1)

    pygame.draw.circle(screen, GREEN if api_key else LGRAY, (SIDE_PAD + 6, TOP_H // 2), 6)
    title = font_bold.render("  AI Chat", True, BLACK)
    screen.blit(title, (SIDE_PAD + 16, (TOP_H - title.get_height()) // 2))

    # model switcher  ◀  gemini-2.5-flash  ▶
    mdl_name   = FREE_MODELS[model_idx]
    mdl_surf   = font_small.render(mdl_name, True, BLUE if not loading else GRAY)
    mdl_w      = mdl_surf.get_width()
    mdl_prev   = pygame.Rect(W // 2 - 110, 9, 26, TOP_H - 18)
    mdl_next   = pygame.Rect(W // 2 + 84,  9, 26, TOP_H - 18)
    mdl_cx     = W // 2 - 42   # left edge of label area

    pygame.draw.rect(screen, (230, 232, 242), mdl_prev, border_radius=5)
    pygame.draw.rect(screen, (230, 232, 242), mdl_next, border_radius=5)
    arr_color = GRAY if loading else BLACK
    draw_arrow(screen, mdl_prev, "left",  arr_color)
    draw_arrow(screen, mdl_next, "right", arr_color)
    screen.blit(mdl_surf, (mdl_cx + (126 - mdl_w) // 2, (TOP_H - mdl_surf.get_height()) // 2))

    clr_btn    = pygame.Rect(W - SIDE_PAD - 70, 9, 70, TOP_H - 18)
    clr_active = bool(messages)
    pygame.draw.rect(screen, (250, 234, 234) if clr_active else (230, 232, 240), clr_btn, border_radius=7)
    pygame.draw.rect(screen, (200, 100, 100) if clr_active else LGRAY, clr_btn, 1, border_radius=7)
    clr_lbl = font_small.render("Xóa lịch sử", True, RED_SOFT if clr_active else GRAY)
    screen.blit(clr_lbl, clr_lbl.get_rect(center=clr_btn.center))

    # --- API key bar ---
    AY = TOP_H
    pygame.draw.rect(screen, (236, 237, 244), (0, AY, W, APIKEY_H))
    pygame.draw.line(screen, LGRAY, (0, AY + APIKEY_H), (W, AY + APIKEY_H), 1)

    lbl = font_small.render("API Key:", True, BLACK)
    screen.blit(lbl, (SIDE_PAD, AY + (APIKEY_H - lbl.get_height()) // 2))

    ai_box = pygame.Rect(SIDE_PAD + 74, AY + 11, W - SIDE_PAD*2 - 74 - 102, 34)
    api_field.draw(screen, ai_box, font, focus_api, cursor_on,
                   border_focus=BLUE, border_idle=GREEN if api_key else LGRAY, bg=WHITE)

    tog_btn = pygame.Rect(W - SIDE_PAD - 94, AY + 11, 44, 34)
    pygame.draw.rect(screen, LGRAY, tog_btn, border_radius=7)
    tl = font_small.render("hide" if api_visible else "show", True, BLACK)
    screen.blit(tl, tl.get_rect(center=tog_btn.center))

    sav_btn = pygame.Rect(W - SIDE_PAD - 44, AY + 11, 44, 34)
    pygame.draw.rect(screen, GREEN if api_key else BLUE, sav_btn, border_radius=7)
    sl = font_small.render("Lưu", True, WHITE)
    screen.blit(sl, sl.get_rect(center=sav_btn.center))

    # --- Chat area ---
    pygame.draw.rect(screen, BG, cr)
    screen.set_clip(cr)

    y_pos = cr.y + 14 - scroll_y
    for msg in messages:
        is_user = (msg["role"] == "user")
        lns     = wrap_text(msg["content"], bub_max - 28, font)
        ls      = font.get_linesize() + 2
        bh      = len(lns) * ls + 24
        max_lw  = max((font.size(ln)[0] for ln in lns if ln), default=50)
        bw      = min(bub_max, max_lw + 28)
        bx      = (cr.right - bw - SIDE_PAD) if is_user else (cr.x + SIDE_PAD)
        br      = pygame.Rect(bx, y_pos, bw, bh)

        if is_user:
            pygame.draw.rect(screen, BLUE, br, border_radius=14)
            tc = WHITE
        else:
            pygame.draw.rect(screen, WHITE, br, border_radius=14)
            pygame.draw.rect(screen, LGRAY, br, 1, border_radius=14)
            tc = BLACK

        for i, ln in enumerate(lns):
            screen.blit(font.render(ln, True, tc), (bx + 14, y_pos + 12 + i * ls))

        y_pos += bh + 10

    if loading:
        dots = "." * (dot_frame // 30 + 1)
        ld_s = font.render(f"Đang xử lý{dots}", True, BLUE)
        ld_r = pygame.Rect(cr.x + SIDE_PAD, y_pos, ld_s.get_width() + 28, 38)
        pygame.draw.rect(screen, WHITE, ld_r, border_radius=10)
        pygame.draw.rect(screen, LGRAY, ld_r, 1, border_radius=10)
        screen.blit(ld_s, (ld_r.x + 14, ld_r.y + (ld_r.height - ld_s.get_height()) // 2))

    if not messages and not loading:
        hint = font.render("Chưa có tin nhắn nào. Hãy bắt đầu hội thoại!", True, LGRAY)
        screen.blit(hint, hint.get_rect(center=cr.center))

    screen.set_clip(None)
    pygame.draw.line(screen, LGRAY, (0, cr.bottom), (W, cr.bottom), 1)

    # --- Input area ---
    pygame.draw.rect(screen, WHITE, (0, H - INPUT_H, W, INPUT_H))

    q_rect = pygame.Rect(SIDE_PAD, H - INPUT_H + 12, W - SIDE_PAD*2 - 92, INPUT_H - 24)
    q_field.draw(screen, q_rect, font, not focus_api, cursor_on,
                 border_focus=BLUE, border_idle=LGRAY, bg=BG)

    s_btn    = pygame.Rect(W - SIDE_PAD - 86, H - INPUT_H + 12, 86, INPUT_H - 24)
    can_send = not loading and bool(q_field.value.strip()) and bool(api_key)
    pygame.draw.rect(screen, BLUE if can_send else LGRAY, s_btn, border_radius=8)
    sl2 = font.render("Gửi", True, WHITE)
    sl2_rect = sl2.get_rect(center=(s_btn.centerx - 8, s_btn.centery))
    screen.blit(sl2, sl2_rect)
    draw_send_icon(screen, s_btn, WHITE)

    hint2 = font_small.render("Chuot phai > copy  |  Enter de gui", True, LGRAY)
    screen.blit(hint2, (W - SIDE_PAD - hint2.get_width(),
                        H - INPUT_H + (INPUT_H + hint2.get_height()) // 2 + 4))

    # --- Toast ---
    if toast and toast_t > 0:
        ts = font.render(toast, True, WHITE)
        tw, th = ts.get_width() + 24, ts.get_height() + 14
        pygame.draw.rect(screen, TOAST_BG,
                         ((W - tw) // 2, H - INPUT_H - th - 10, tw, th), border_radius=8)
        screen.blit(ts, ((W - tw) // 2 + 12, H - INPUT_H - th - 10 + 7))

    pygame.display.flip()
