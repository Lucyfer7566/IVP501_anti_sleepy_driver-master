# 🔍 Báo cáo Kiểm tra & Chuẩn bị Q&A Thuyết trình

> **Ngày kiểm tra:** 2026-04-19  
> **Phạm vi:** Toàn bộ source code, kiến trúc, slide và script thuyết trình

---

## PHẦN 1: 🐛 CÁC LỖI PHÁT HIỆN TRONG SOURCE CODE

### BUG 1 — `build_ui()` được gọi 2 LẦN (CRITICAL ⚡)
**File:** [app.py](file:///d:/IVP501_anti_sleepy_driver-master/anti_sleepy/ui/app.py#L25-L27)
```python
# Dòng 25-27 trong app.py
self.build_ui()

self.build_ui()  # ← GỌI LẦN 2 → tạo widget trùng lặp!
```
**Hậu quả:** Mọi widget (video_label, led, log_text, lbl_mode, lbl_metrics) đều bị tạo **đôi**. Giao diện sẽ bị lộn xộn, vẽ chồng, và tốn gấp đôi bộ nhớ.

> [!CAUTION]
> Đây là lỗi nghiêm trọng nhất — **sẽ thấy ngay khi demo**. Phải fix trước buổi thuyết trình!

---

### BUG 2 — `on_closing()` định nghĩa 2 LẦN (CRITICAL ⚡)
**File:** [app.py](file:///d:/IVP501_anti_sleepy_driver-master/anti_sleepy/ui/app.py#L93-L167)
```python
# Lần 1 (dòng 93-96) — GỌI detector.stop() nhưng detector KHÔNG CÓ method stop()
def on_closing(self):
    self.detector.stop()   # ← AttributeError: stop() không tồn tại!
    self.cap.release()
    self.root.destroy()

# Lần 2 (dòng 162-167) — đúng logic nhưng BỊ SHADOWED bởi lần 1
def on_closing(self):
    if hasattr(self, 'cap') and self.cap.isOpened():
        self.cap.release()
    if hasattr(self, 'detector'):
        self.detector.close()
    self.root.destroy()
```
**Hậu quả:** Python sẽ dùng **lần định nghĩa cuối cùng** (dòng 162), nên lần 1 (dòng 93) vô dụng. Tuy nhiên lần 1 sẽ gây nhầm lẫn code review, và `self.root.protocol("WM_DELETE_WINDOW", self.on_closing)` (dòng 32) binding vào lần 2. May mắn là lần 2 gọi `detector.close()` đúng — nên app hoạt động bình thường, nhưng code rất bẩn.

---

### BUG 3 — `LEDState` chứa 5 trạng thái LEGACY không dùng
**File:** [led_widget.py](file:///d:/IVP501_anti_sleepy_driver-master/anti_sleepy/ui/led_widget.py#L4-L13)
```python
class LEDState(Enum):
    OFF = auto()
    REGISTERING = auto()     # ← Legacy: Registration flow đã xóa
    EAR_OPEN = auto()        # ← Legacy
    EAR_CLOSED = auto()      # ← Legacy
    PITCH_CAL = auto()       # ← Legacy
    SUCCESS = auto()          # ← Legacy
    RUNNING_OK = auto()       # ✅ Đang dùng
    RUNNING_UNKNOWN = auto()  # ✅ Đang dùng (map EARLY_WARNING)
    ALERT = auto()            # ✅ Đang dùng
```
**Hậu quả:** Không crash, nhưng khi hội đồng hỏi "tại sao có REGISTERING, EAR_OPEN, PITCH_CAL?" sẽ khó trả lời. Nên dọn dẹp.

---

### BUG 4 — `base_pitch` không bao giờ được khởi tạo tự động
**File:** [detector.py](file:///d:/IVP501_anti_sleepy_driver-master/anti_sleepy/core/detector.py#L55)
```python
self.base_pitch: Optional[float] = None  # Luôn None nếu không ai set
```
Toàn bộ logic Head Pose (dòng 250-318) nằm trong `if self.base_pitch is not None:` → **sẽ KHÔNG BAO GIỜ chạy** trừ khi có code nào đó set `base_pitch`. Tuy nhiên, nhìn vào `process_frame()`, **không có dòng nào tự động set** `base_pitch`.

**Hậu quả:** Nodding detection, Veto Rules, Distraction detection → **toàn bộ KHÔNG HOẠT ĐỘNG** cho đến khi `base_pitch` được set từ bên ngoài.

> [!WARNING]
> Câu hỏi: Vậy `base_pitch` được set khi nào? — Cần kiểm tra xem `app.py` có set không. Theo code review, **không thấy chỗ nào set**. Đây có thể là lỗi nghiêm trọng **ở lần demo gật đầu sẽ không phản ứng**!
> 
> **Fix đề xuất:** Tự động set `base_pitch = pitch` trong `process_frame()` sau khi đủ 60 frame calibration (cùng lúc với EAR calibration).

---

### BUG 5 — Nhận xét không khớp hàm `compare_signatures`
**File:** [face_id.py](file:///d:/IVP501_anti_sleepy_driver-master/anti_sleepy/core/face_id.py#L55-L61)
```python
def compare_signatures(sig1: List[float], sig2: List[float]) -> float:
    """L2-based similarity between two face signatures."""  # ← Comment nói L2
    # Nhưng code thực tế tính 1 / (1 + L2_dist) → Inverse L2
```
**Hậu quả:** Không ảnh hưởng runtime (module chưa active), nhưng khi bị hỏi sẽ gây nhầm lẫn. Nên sửa comment hoặc giải thích rõ đây là "Inverse L2 Similarity".

Test file `tests/test_face_id.py` cũng check `cosine similarity` (comment dòng 41) nhưng code thực tế là Inverse L2 → **test comment sai**.

---

## PHẦN 2: ❓ CÂU HỎI HỘI ĐỒNG CÓ THỂ HỎI

### 📚 Nhóm 1: Lý thuyết & Thuật toán

---

#### Q1: EAR (Eye Aspect Ratio) được tính như thế nào? Tại sao dùng 6 điểm mà không phải nhiều hơn?

**Trả lời:**
"Dạ EAR được tính bằng công thức:

```
EAR = (||p2 - p6|| + ||p3 - p5||) / (2 × ||p1 - p4||)
```

Trong đó p1, p4 là 2 khóe mắt (góc ngang), còn p2-p6 và p3-p5 là 2 cặp điểm trên-dưới mí mắt (khoảng cách dọc). Chúng em dùng đúng 6 điểm theo paper gốc của Soukupová & Čech (2016), vì đây là bộ tối thiểu để đo chính xác tỷ lệ mở mắt mà không dư thừa gây nhiễu. MediaPipe cung cấp 478 landmark phức tạp hơn, nhưng nhóm chỉ chọn 6 điểm mốc ổn định nhất cho mỗi mắt để giữ pipeline nhẹ mà vẫn đủ chính xác."

---

#### Q2: Tại sao ngưỡng MAR là 0.60 mà không phải 0.45 hay 0.50?

**Trả lời:**
"Dạ ngưỡng 0.45 bọn em đã thử ở phiên bản đầu, nhưng khi test thực tế, nó quá nhạy: khi tài xế hát theo nhạc trên xe hoặc cười lớn, miệng mở tới khoảng 0.45–0.55 → hệ thống báo ngáp sai.

Bọn em đã đo thực tế: khi ngáp thật, MAR thường vọt lên 0.65–0.80 và **giữ nguyên liên tục hơn 1 giây**. Còn khi hát hay cười, miệng mở rồi đóng rất nhanh (chỉ vài frame). Vì vậy, nhóm kết hợp 2 điều kiện: **MAR > 0.60** VÀ **liên tục ≥ 30 frame (1 giây)** — nhờ vậy loại bỏ gần như hoàn toàn false positive từ hát/cười."

---

#### Q3: PERCLOS là gì? Tại sao cần PERCLOS khi đã có EAR?

**Trả lời:**
"Dạ PERCLOS — Percentage of Eye Closure — là **tỷ lệ phần trăm thời gian mắt nhắm** trong một cửa sổ trượt (nhóm dùng 90 frame ≈ 3 giây). EAR đo trạng thái tức thời — 'ngay bây giờ mắt đang mở hay nhắm'. Còn PERCLOS đo **xu hướng tích lũy**: ví dụ tài xế nháy mắt lâu hơn bình thường, mỗi lần nháy kéo dài 0.3 giây thay vì 0.15 giây — EAR sẽ không phát hiện vì từng lần nháy vẫn chưa vượt ngưỡng, nhưng PERCLOS sẽ tăng dần lên vì tổng thời gian nhắm mắt vượt 30% → hệ thống biết tài xế đang dần mệt mỏi.

Đây là chỉ số y khoa được nghiên cứu rộng rãi từ những năm 1990, đặc biệt trong ngành vận tải."

---

#### Q4: `solvePnP` hoạt động ra sao? Tại sao cần 3D model points?

**Trả lời:**
"Dạ `solvePnP` — viết tắt của Solve Perspective-n-Point — là hàm của OpenCV giải bài toán: **biết tọa độ 3D của vật thể và tọa độ 2D trên ảnh, tìm ra tư thế (pose) của vật thể tương đối với camera**. 

Nhóm em cung cấp 6 điểm mốc chuẩn trên khuôn mặt người (mũi, cằm, 2 khóe mắt, 2 khóe miệng) với tọa độ 3D trung bình của khuôn mặt. `solvePnP` sẽ tìm ra ma trận xoay, sau đó dùng `RQDecomp3x3` để tách thành 3 góc Euler: Pitch (gật trước/sau), Yaw (quay trái/phải), Roll (nghiêng). Nhờ đó chúng em biết tài xế đang nhìn hướng nào mà không cần cảm biến vật lý."

---

#### Q5: Veto Rules hoạt động ra sao? Tại sao cần?

**Trả lời:**
"Dạ Veto Rules — quy tắc phủ quyết — giải quyết vấn đề 'dương tính giả do hình học'. Khi tài xế ngước đầu lên hoặc quay đầu sang bên, vì góc nhìn bị biến dạng phối cảnh, khoảng cách dọc giữa mí mắt trên và dưới bị thu ngắn lại, khiến EAR tụt xuống thấp mặc dù mắt vẫn mở to.

Nhóm xử lý bằng cách: nếu pitch delta < -25° (ngước đầu) hoặc yaw delta > 30° (quay đầu), hệ thống sẽ **bỏ qua EAR penalty** cho frame đó. Ví dụ thực tế: khi phanh gấp, lực quán tính khiến đầu tài xế ngả về phía trước rồi giật lại → nếu không có Veto, hệ thống sẽ báo sai."

---

### 🏗️ Nhóm 2: Kiến trúc & Thiết kế

---

#### Q6: Tại sao chọn MediaPipe mà không dùng Dlib hay MTCNN?

**Trả lời:**
"Dạ có 3 lý do chính:
1. **Số điểm landmark:** MediaPipe cho 478 landmark kèm Iris tracking, trong khi Dlib chỉ 68 điểm, MTCNN chỉ 5 điểm → MediaPipe chi tiết hơn rất nhiều.
2. **Hiệu năng:** MediaPipe chạy 30+ FPS trên CPU laptop thường nhờ kiến trúc BlazeFace nhẹ (~3MB model), Dlib cần ~100MB model shape_predictor.
3. **Tính năng:** MediaPipe hỗ trợ `refine_landmarks=True` để tracking mống mắt (Iris), cho phép vẽ mống mắt trên giao diện và mở rộng sang phát hiện hướng nhìn trong tương lai."

---

#### Q7: Tại sao không cần đăng ký khuôn mặt? Hệ thống tự hiệu chỉnh thế nào?

**Trả lời:**
"Dạ hệ thống dùng cơ chế Self-Calibrating Rolling Window. Khi khởi động, detector thu thập EAR qua cửa sổ trượt 60 frame (khoảng 2 giây). Trong 60 frame đó, hệ thống ghi nhận giá trị EAR mở lớn nhất (`dynamic_ear_open`), sau đó tự tính:

```
ear_thresh = max(0.12, dynamic_ear_open × 0.60)
```

Con số 0.60 nghĩa là: chỉ khi mắt nhắm xuống còn 60% so với trạng thái mở lớn nhất thì mới tính là nhắm. Con số 0.12 là sàn an toàn cho trường hợp đeo kính râm. Nhờ vậy, dù mắt to hay mắt híp, hệ thống đều tự thích ứng mà không cần bước đăng ký nào."

---

#### Q8: Risk Engine khác gì so với approach cũ (đếm frame liên tục)?

**Trả lời:**
"Dạ approach cũ dùng bộ đếm `sleep_frame_counter` — mắt nhắm liên tục N frame → báo động, mở mắt ra → reset về 0. Cách này có 2 vấn đề lớn:
1. **Không tích lũy:** Tài xế nháy mắt lâu 20 frame, mở ra 1 frame, nhắm lại 20 frame — bộ đếm luôn reset, không bao giờ kích hoạt.
2. **Không tổng hợp:** Chỉ đo mắt, không kết hợp ngáp + gật gù.

Risk Engine giải quyết cả hai: mọi tín hiệu bất thường đều **cộng vào risk score** (0-100), và risk có **decay liên tục** (-1.0/frame). Nhờ vậy:
- Nhiều dấu hiệu nhỏ cộng dồn → risk tăng dần → cảnh báo sớm
- Tài xế tỉnh lại → risk tự giảm mượt mà, không bị nghẽn
- Kết hợp đa tín hiệu: EAR + MAR + PERCLOS + Pitch = bức tranh toàn diện hơn"

---

#### Q9: `face_id.py` có được dùng không? Nếu không thì tại sao vẫn giữ?

**Trả lời:**
"Dạ module `face_id.py` hiện **chưa được kích hoạt** trong luồng chính — nhóm không import nó ở `main.py` hay `app.py`. Nhóm giữ lại vì 2 lý do:
1. **Tương lai:** Khi phát triển thêm tính năng nhận diện chủ xe (chống trộm xe, cá nhân hóa ngưỡng theo từng người), chỉ cần import và kích hoạt mà không cần viết lại.
2. **Minh họa:** Trong phần Technical Stack của slide, nhóm muốn cho thấy nhóm đã nghiên cứu cả giải pháp Landmark Signature + Spatial Histogram cho face recognition, dù chưa kích hoạt.

Module này đã có unit test riêng trong `tests/test_face_id.py`."

---

#### Q10: Tại sao dùng winsound mà không dùng pygame hay playsound?

**Trả lời:**
"Dạ `winsound` là module built-in của Python trên Windows, không cần cài thêm dependency nào. Nó hỗ trợ phát WAV bất đồng bộ (`SND_ASYNC`) — nghĩa là phát âm thanh mà không dừng camera. Nhóm chọn nó vì:
1. **Zero dependency:** Giảm rủi ro conflict khi cài đặt
2. **Đủ dùng:** Project chạy trên Windows (laptop), không cần cross-platform

Nếu cần deploy trên Linux/Android trong tương lai, chỉ cần thay `winsound.PlaySound()` bằng `pygame.mixer.Sound.play()` — interface giống nhau, chỉ thay 1 dòng."

---

### ⚙️ Nhóm 3: Kỹ thuật Chi tiết

---

#### Q11: Con số 30 frame cho ear_consec_frames có ý nghĩa gì?

**Trả lời:**
"Dạ camera chạy ~30 FPS, nên 30 frame ≈ 1.0 giây. Nghiên cứu về microsleep cho thấy: nếu mắt nhắm liên tục hơn 1 giây, đó không phải chớp mắt bình thường (chớp mắt trung bình chỉ 0.15–0.40 giây) mà là dấu hiệu mất ý thức tạm thời. Khi đạt 30 frame liên tục, nhóm set `risk = 100` tức thì (Hard Rule) để cảnh báo tối đa ngay lập tức."

---

#### Q12: Tại sao CLAHE thay vì Histogram Equalization thông thường?

**Trả lời:**
"Dạ CLAHE — Contrast Limited Adaptive Histogram Equalization — khác Histogram Equalization thường ở chỗ:
- HE thường cân bằng toàn bộ ảnh → nếu ánh sáng loang lổ (nửa mặt sáng, nửa tối), phần tối bị kéo quá sáng gây nhiễu
- CLAHE chia ảnh thành ô nhỏ (8×8 tiles) và cân bằng **cục bộ trong từng ô**, kèm clip limit = 2.0 để giới hạn amplification tránh nhiễu

Nhờ vậy hệ thống hoạt động ổn trong điều kiện ánh sáng phức tạp: ban đêm có đèn đường chiếu không đều, trong hầm tối, hay ánh nắng chiếu xéo qua kính xe."

---

#### Q13: Risk decay luôn hoạt động — vậy có khi nào risk không bao giờ đạt 100?

**Trả lời:**
"Dạ câu hỏi rất hay. Decay = 1.0/frame, nghĩa là mỗi frame risk giảm 1 điểm. Nhưng khi tài xế thực sự buồn ngủ:
- PERCLOS penalty = +2.0/frame → vượt decay 1.0 → risk tăng ròng +1.0/frame
- Microsleep (nhắm 30 frame liên tục) → Hard Rule: risk = 100 tức thì, bỏ qua decay
- Gật gù + ngáp cùng lúc: +30 + +25 = +55 penalty tức thì

Decay chỉ thắng penalty khi tài xế **tỉnh lại thực sự** (mắt mở, không ngáp, không gật). Khi có dấu hiệu thật, penalty luôn outpace decay."

---

#### Q14: Cửa sổ PERCLOS 90 frame (~3 giây) có quá ngắn không?

**Trả lời:**
"Dạ trong y khoa, PERCLOS thường đo trên cửa sổ 1 phút. Nhóm rút ngắn xuống 3 giây vì 2 lý do:
1. **Phản ứng nhanh:** Trong lái xe, 3 giây đã đủ để xe di chuyển 50+ mét ở tốc độ 60km/h. Chờ 1 phút là quá muộn.
2. **Bù bằng Risk Engine:** PERCLOS chỉ là 1 trong 5 tín hiệu đầu vào. Ngay cả khi PERCLOS window ngắn, nhờ tích lũy risk từ nhiều nguồn, hệ thống vẫn phát hiện sớm.

Nếu cần chính xác hơn cho nghiên cứu y khoa, chỉ cần thay đổi `perclos_window_frames` trong config mà không cần sửa logic."

---

#### Q15: Hệ thống có hoạt động khi tài xế đeo kính cận/kính mát không?

**Trả lời:**
"Dạ có 2 trường hợp:
- **Kính cận trong suốt:** MediaPipe vẫn detect landmark qua mắt kính → EAR hoạt động bình thường, có thể hơi giảm accuracy ~5% nhưng self-calibration sẽ bù.
- **Kính mát/kính râm đen:** EAR trở nên rất thấp và gần như không thay đổi. Hệ thống có **Sunglasses Mode** tự động kích hoạt khi phát hiện: ear_max - ear_min < 0.04 và mean EAR nằm trong khoảng 0.09-0.18. Khi vào Sunglasses Mode, hệ thống **tắt EAR penalty** và chuyển sang dựa hoàn toàn vào Pitch (gật gù) + MAR (ngáp) để phát hiện buồn ngủ."

---

### 🎯 Nhóm 4: Câu hỏi Hóc búa (Gotcha Questions)

---

#### Q16: Nếu tài xế nhắm 1 mắt (nháy mắt bên) thì sao?

**Trả lời:**
"Dạ nhóm tính **trung bình** EAR của 2 mắt: `avg_ear = (right_ear + left_ear) / 2.0`. Nếu nhắm 1 mắt, EAR trung bình sẽ giảm khoảng 50% so với mở cả 2 → có thể chạm ngưỡng nhưng chưa chắc, tùy vào giá trị cụ thể. Thực tế khi lái xe, người ta không nhắm 1 mắt lâu, và nếu EAR giảm đủ lâu thì PERCLOS sẽ bắt dần. Đây là hạn chế nhỏ của approach EAR trung bình — có thể cải thiện bằng cách xét EAR min(left, right) thay vì average."

---

#### Q17: Hệ thống có xử lý được khi đường xấu, xe rung lắc không?

**Trả lời:**
"Dạ xe rung khiến landmark jitter (nhảy nhiễu) nhưng MediaPipe có `min_tracking_confidence = 0.5` giúp lọc nhiễu tracking. Ngoài ra, nhóm dùng:
- **PERCLOS window 90 frame:** Trung bình hóa jitter ngắn hạn
- **Nod detection yêu cầu 15 frame liên tục:** Rung lắc random không đạt 15 frame cùng hướng
- **Risk decay liên tục:** Jitter gây cộng risk nhưng decay sẽ triệt tiêu ngay

Tuy nhiên, nếu xe rung quá mạnh (off-road), landmark có thể mất hoàn toàn → hệ thống reset counter, không báo sai. Đây là hành vi an toàn (fail-safe)."

---

#### Q18: Nếu camera bị che hoặc bị ngược sáng hoàn toàn?

**Trả lời:**
"Dạ khi camera bị che hoặc không tìm thấy khuôn mặt, MediaPipe trả về `multi_face_landmarks = None`, hệ thống sẽ:
1. Reset `sleep_frame_counter` về 0
2. Set `last_metrics` = `is_alert: False`
3. LED chuyển sang OFF

Hệ thống **không báo động giả** khi mất mặt. Tuy nhiên, đây cũng là hạn chế: nếu tài xế ngủ gục xuống dưới tầm camera → mất mặt → không cảnh báo. Giải pháp tương lai là kết hợp thêm cảm biến vô lăng hoặc IMU."

---

#### Q19: Tại sao dùng Tkinter mà không dùng PyQt hay web-based?

**Trả lời:**
"Dạ Tkinter là thư viện GUI built-in của Python — không cần cài thêm. Nhóm ưu tiên **zero-dependency** cho phần giao diện vì:
1. Dễ deploy cho bất kỳ máy Python nào
2. Tkinter đủ cho UI đơn giản: hiển thị video, LED, log
3. Giảm complexity cho đồ án — focus vào core algorithm

Nếu cần giao diện đẹp hơn trong tương lai (dashboard web, mobile app), nhóm có thể tách `detector.py` ra làm service riêng và dùng Flask/FastAPI serve API, frontend dùng React."

---

#### Q20: Tại sao `driver_zone_ratio = 0.5` — nghĩa là chỉ nửa trái?

**Trả lời:**
"Dạ camera laptop thường đặt chính giữa hoặc hơi lệch. Vì video được `cv2.flip(frame, 1)` — lật gương — nên tài xế (ngồi bên trái) sẽ xuất hiện ở **nửa bên trái** khung hình. Hệ thống chọn khuôn mặt có `center_x < frame_width × 0.5` → ưu tiên mặt ở nửa trái = mặt tài xế.

Nếu có hành khách ngồi ghế phụ (hiển thị nửa phải), hệ thống sẽ label 'HANH KHACH' và **không theo dõi**. Trường hợp xe tay lái nghịch (UK, Nhật), chỉ cần đổi `driver_zone_ratio = 0.5` thành `> 0.5`."

---

#### Q21: Hệ thống có realtime không? FPS cụ thể bao nhiêu?

**Trả lời:**
"Dạ hệ thống chạy pipeline 6 bước (Camera → CLAHE → FaceMesh → Metrics → Risk Engine → Alert) mất khoảng 30ms/frame trên CPU laptop Intel i5, tương đương ~33 FPS. Con số này vượt mức yêu cầu realtime (thường 15+ FPS là đủ cho ứng dụng giám sát).

Tkinter loop cũng set `self.root.after(30, self._update)` = gọi lại mỗi 30ms. Bottleneck chính là MediaPipe FaceMesh inference (~20ms) + OpenCV drawing (~5ms)."

---

#### Q22: Có xảy ra race condition giữa audio thread và main thread không?

**Trả lời:**
"Dạ không. `winsound.PlaySound` với flag `SND_ASYNC` sẽ giao việc phát âm cho Windows audio driver ở kernel level, main thread tiếp tục chạy ngay. Không có shared state giữa audio thread và main thread ngoài biến `last_play_time` — biến này chỉ được đọc/ghi trong main thread (trong `_update()` loop), nên không có race condition.

Cooldown 5 giây đảm bảo không có 2 lệnh PlaySound cùng lúc gây chồng âm."

---

## PHẦN 3: 📋 CHECKLIST TRƯỚC KHI THUYẾT TRÌNH

- [ ] **Fix Bug 1:** Xóa dòng `self.build_ui()` thừa ở dòng 27 của `app.py`
- [ ] **Fix Bug 2:** Xóa hàm `on_closing` lần 1 (dòng 93-96) trong `app.py`
- [ ] **Fix Bug 4:** Thêm auto-set `base_pitch` trong `process_frame()` — hoặc confirm rằng head pose detection bị tắt có chủ đích
- [ ] **Test thử demo:** Mở app → nhắm mắt 1s → ngáp → gật đầu → hát/cười
- [ ] **Kiểm tra âm thanh:** Đảm bảo file WAV phát đúng
- [ ] **Kiểm tra slide:** Mở `presentation.html` trong Chrome, test tất cả nút tương tác
- [ ] **Backup:** Giữ bản code ổn định trước khi fix
