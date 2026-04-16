# Anti-Sleepy Driver — Hệ thống Phát hiện Buồn ngủ cho Tài xế

> Hệ thống giám sát tài xế thời gian thực sử dụng camera, kết hợp phân tích **tỷ lệ mắt (EAR)**, **tỷ lệ miệng (MAR)**, **góc nghiêng đầu (Pitch/Yaw)** và **máy trạng thái tích lũy rủi ro (Risk-Based State Machine)** để phát hiện các dấu hiệu buồn ngủ và cảnh báo bằng âm thanh.

**Môn học**: IVP501 — Xử lý ảnh và Thị giác máy tính

---

## Mục lục

- [Tính năng chính](#tính-năng-chính)
- [Demo giao diện](#demo-giao-diện)
- [Tổng quan kiến trúc](#tổng-quan-kiến-trúc)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Luồng hoạt động](#luồng-hoạt-động)
- [Máy trạng thái tích lũy rủi ro](#máy-trạng-thái-tích-lũy-rủi-ro)
- [Chi tiết các module](#chi-tiết-các-module)
- [Cài đặt và khởi chạy](#cài-đặt-và-khởi-chạy)
- [File âm thanh](#file-âm-thanh)
- [Cấu hình](#cấu-hình)
- [Cơ chế chống báo sai](#cơ-chế-chống-báo-sai)
- [Xử lý sự cố](#xử-lý-sự-cố)
- [Hạn chế đã biết](#hạn-chế-đã-biết)
- [Tài liệu tham khảo](#tài-liệu-tham-khảo)

---

## Tính năng chính

| Tính năng | Mô tả |
|---|---|
| **Tự hiệu chỉnh (Plug & Play)** | Không cần đăng ký khuôn mặt — hệ thống tự động hiệu chỉnh ngưỡng EAR và tư thế đầu ngay khi bắt đầu sử dụng |
| **Máy trạng thái tích lũy rủi ro** | Điểm risk tích lũy từ nhiều tín hiệu (EAR, MAR, PERCLOS, Head Pose) — phân biệt cảnh báo sớm (cam) và xác nhận ngủ gật (đỏ) |
| **Phát hiện microsleep** | Nhắm mắt > 0.5 giây → cảnh báo; nhắm mắt > 1.0 giây → báo động đỏ ngay lập tức |
| **Phát hiện ngáp** | Phân biệt ngáp thật (há miệng to > 1 giây liên tục) với cười/hát (ngắt quãng, biên độ nhỏ) |
| **PERCLOS (Percentage of Eye Closure)** | Theo dõi tỷ lệ nhắm mắt trong cửa sổ 3 giây — phát hiện buồn ngủ mãn tính không dùng ngưỡng cứng |
| **Phát hiện gật gù thông minh** | Chỉ cảnh báo khi gục đầu kèm theo mắt nhắm hoặc PERCLOS cao — không báo sai khi phanh gấp/cúi nhìn GPS |
| **Chống báo sai khi ngước đầu** | Veto Rule: khi ngước lên > 25° hoặc quay đầu > 30°, bỏ qua EAR thấp do biến dạng góc nhìn camera |
| **Tự nhận kính râm** | Phát hiện landmark bị "đóng băng" bằng phân tích phương sai EAR |
| **Đa khuôn mặt** | Hỗ trợ tới 4 khuôn mặt, tự động chọn vị trí tài xế (nửa trái khung hình) |
| **Face Mesh Overlay** | Vẽ viền mặt, mắt, mũi, môi, iris trực tiếp lên camera feed |
| **Cảnh báo âm thanh** | File WAV tự động phát theo từng tình huống (buồn ngủ, ngáp, ...) |
| **LED ảo** | Widget LED animated (9 trạng thái) phản ánh trạng thái hệ thống |
| **Log sự kiện** | Panel log có mã màu, chỉ hiển thị sự kiện quan trọng |
| **Risk tự phục hồi** | Decay luôn hoạt động (1.0 điểm/frame) — risk trở về 0 ngay khi tài xế tỉnh táo lại |

---

## Demo giao diện

**Layout giao diện:**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                    CAMERA FEED (960×720)                 │
│            [Face Mesh] [Eye Contours] [Iris]            │
│         ┌──────────┐               ┌──────────┐        │
│         │ TAI XE   │               │HANH KHACH│        │
│         └──────────┘               └──────────┘        │
│  EAR:0.28 MAR:0.02                                     │
│                                                         │
│  STATUS: TINH TAO (AWAKE) | RISK: 0/100                │
│  DEBUG: E:0 Y:0 Th:0.20 N:0                            │
├─────────────────────────────────────────────────────────┤
│ ● LED │ Mode: BINH THUONG │ EAR:0.28 MAR:0.02          │
├─────────────────────────────────────────────────────────┤
│ ┌─ Nhat ky su kien ──────────────────────────────────┐  │
│ │ [10:52:26] CANH BAO: DANG NGAP (YAWNING)          │  │
│ │ [10:52:27] Binh thuong tro lai                     │  │
│ │ [10:53:05] CANH BAO: NGU GAT! (CONFIRMED)         │  │
│ │ [10:53:13] Binh thuong tro lai                     │  │
│ └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Tổng quan kiến trúc

Dự án được tổ chức theo kiến trúc **Clean Architecture** với 3 tầng tách biệt:

```
┌─────────────────────────────────────────────────┐
│                    main.py                      │  ← Entry point
│              (Khởi tạo Camera, Detector, UI)    │
├────────────────────┬────────────────────────────┤
│       UI Layer     │       Core Layer           │
│  ┌──────────────┐  │  ┌──────────────────────┐  │
│  │   app.py     │  │  │   detector.py        │  │
│  │  (Tkinter)   │──┼──│  (MediaPipe + CV)    │  │
│  ├──────────────┤  │  ├──────────────────────┤  │
│  │ led_widget   │  │  │   face_id.py         │  │
│  │  (LED ảo)    │  │  │  (Nhận dạng mặt)     │  │
│  └──────────────┘  │  ├──────────────────────┤  │
│                    │  │   audio.py           │  │
│                    │  │  (Phát âm thanh)      │  │
│                    │  └──────────────────────┘  │
├────────────────────┴────────────────────────────┤
│                  config.py                      │  ← Cấu hình tập trung
│     (DetectorConfig + DriverState + AlertLevel) │
└─────────────────────────────────────────────────┘
```

**Nguyên tắc thiết kế:**
- **Core Layer** không phụ thuộc vào UI — có thể test độc lập hoặc thay Tkinter bằng framework khác.
- **UI Layer** chỉ gọi Core qua interface đơn giản (`process_frame()`).
- **Config** tập trung tại 1 file duy nhất, dễ điều chỉnh.
- **Plug & Play** — không cần đăng ký, hệ thống tự hiệu chỉnh ngưỡng theo hình dạng khuôn mặt.

---

## Công nghệ sử dụng

| Công nghệ | Phiên bản | Vai trò | Lý do chọn |
|---|---|---|---|
| **Python** | 3.10+ | Ngôn ngữ chính | Hệ sinh thái ML/CV phong phú, cú pháp đơn giản |
| **OpenCV** | ≥ 4.8 | Xử lý ảnh, camera | Thư viện CV chuẩn công nghiệp, hỗ trợ real-time video |
| **MediaPipe** | ≥ 0.10 | Phát hiện khuôn mặt & 468 landmark | Nhẹ, chạy trên CPU, không cần GPU, độ chính xác cao |
| **NumPy** | ≥ 1.24 | Tính toán vector/ma trận | Nền tảng tính toán khoa học cho Python |
| **SciPy** | ≥ 1.11 | (Dự phòng) Tính toán khoảng cách | Bổ sung cho NumPy khi cần các hàm toán học nâng cao |
| **Pillow** | ≥ 10.0 | Chuyển đổi ảnh OpenCV → Tkinter | Cầu nối giữa mảng NumPy (BGR) và PhotoImage (RGB) |
| **Tkinter** | Built-in | Giao diện đồ họa (GUI) | Có sẵn trong Python, không cần cài thêm, đủ cho desktop app |
| **winsound** | Built-in | Phát âm thanh WAV | API native Windows, phát async không block UI thread |

### Tại sao dùng MediaPipe thay vì Dlib/MTCNN?

| Tiêu chí | MediaPipe FaceMesh | Dlib (shape_predictor) | MTCNN |
|---|---|---|---|
| Số landmark | **478** (gồm iris) | 68 | 5 (chỉ detect) |
| Tốc độ CPU | ~30 FPS | ~15 FPS | ~10 FPS |
| Model file | Tải tự động (~5MB) | Cần tải thủ công (~100MB) | ~2MB |
| Đa khuôn mặt | ✅ Tối đa 4 | ❌ Xử lý từng mặt | ✅ |
| Iris tracking | ✅ | ❌ | ❌ |

### Các công thức toán học cốt lõi

**Eye Aspect Ratio (EAR):**

```
         ‖p2 - p6‖ + ‖p3 - p5‖
  EAR = ─────────────────────────
              2 × ‖p1 - p4‖

  Trong đó p1..p6 là 6 landmark quanh mắt.
  Mắt mở: EAR ≈ 0.25–0.35
  Mắt nhắm: EAR < 0.20 (tự hiệu chỉnh = 60% của EAR mở tối đa)
```

**Mouth Aspect Ratio (MAR):**

```
         ‖top - bottom‖
  MAR = ─────────────────
         ‖left - right‖

  Miệng khép: MAR ≈ 0.0–0.3
  Đang ngáp: MAR > 0.60 (liên tục ≥ 1.0 giây)
  Cười/Hát: MAR có thể > 0.60 nhưng không liên tục → không tính là ngáp
```

**Head Pose Estimation:**

```
  Sử dụng cv2.solvePnP() với 6 điểm 3D tham chiếu:
    - Đỉnh mũi (0, 0, 0)
    - Cằm (0, -330, -65)
    - Khóe mắt trái/phải (-225/225, 170, -135)
    - Khóe miệng trái/phải (-150/150, -150, -125)
  → Tính rotation matrix → trích xuất Pitch, Yaw, Roll (độ)
  → Sử dụng moving average để chống nhiễu tư thế
```

**PERCLOS (Percentage of Eye Closure):**

```
                  Số frame nhắm mắt (trong 90 frame gần nhất)
  PERCLOS = ────────────────────────────────────────────────────
                                   90

  Ngưỡng: 30% (bình thường chớp mắt ≈ 15%)
  Penalty: +2.0 risk/frame khi vượt ngưỡng
```

---

## Cấu trúc thư mục

```
anti_sleepy_driver/
├── anti_sleepy/                    # Package chính
│   ├── main.py                     # Entry point — quét camera, khởi tạo hệ thống
│   ├── config.py                   # Cấu hình tập trung (ngưỡng, state machine, risk)
│   ├── requirements.txt            # Danh sách thư viện cần cài
│   │
│   ├── core/                       # Tầng logic nghiệp vụ
│   │   ├── __init__.py
│   │   ├── detector.py             # Phát hiện buồn ngủ (EAR, MAR, PERCLOS, Head Pose, Risk)
│   │   ├── face_id.py              # Nhận dạng khuôn mặt (Landmark + Histogram)
│   │   └── audio.py                # Phát âm thanh async (winsound)
│   │
│   ├── ui/                         # Tầng giao diện
│   │   ├── __init__.py
│   │   ├── app.py                  # Giao diện chính Tkinter
│   │   └── led_widget.py           # Widget LED ảo (animated)
│   │
│   └── assets/
│       └── sounds/                 # 13 file âm thanh WAV
│           ├── alert_drowsy.wav
│           ├── alert_yawning.wav
│           ├── alert_nodding.wav
│           └── ... (10 file khác)
│
├── .gitignore
└── README.md
```

---

## Luồng hoạt động

### 1. Khởi động hệ thống

```
main.py
  │
  ├── 1. Quét camera khả dụng (0 → camera_scan_limit)
  ├── 2. Mở camera với resolution 960×720
  ├── 3. Khởi tạo DrowsinessDetector (MediaPipe FaceMesh)
  └── 4. Khởi tạo Tkinter GUI → AntiSleepyApp
```

### 2. Vòng lặp xử lý chính (~33 FPS)

```
AntiSleepyApp._update()  [gọi lại mỗi 30ms]
  │
  ├── 1. Đọc frame từ camera → flip ngang (mirror)
  ├── 2. Gửi frame → detector.process_frame()
  │      │
  │      ├── Tiền xử lý: Grayscale → CLAHE → RGB
  │      ├── MediaPipe FaceMesh → 478 landmarks / khuôn mặt
  │      ├── Chọn khuôn mặt TÀI XẾ (nửa trái, diện tích lớn nhất)
  │      ├── Tính EAR, MAR, Head Pose (Pitch/Yaw/Roll)
  │      ├── Tự hiệu chỉnh ngưỡng EAR (60% max EAR trong 60 frame)
  │      ├── Đánh giá trạng thái: _evaluate_state()
  │      │      ├── Thu thập bằng chứng (Evidence Tracking)
  │      │      ├── Áp dụng Veto Rules (Head Pose distortion)
  │      │      ├── Tích lũy risk score (penalties + decay)
  │      │      └── State machine transition
  │      ├── Vẽ Face Mesh (viền mặt, mắt, mũi, môi, iris)
  │      └── Trả frame đã vẽ + dict metrics
  │
  ├── 3. Phát cảnh báo âm thanh (cooldown chống spam)
  ├── 4. Cập nhật LED, labels, log panel
  └── 5. Chuyển đổi BGR→RGB → PIL Image → Tkinter PhotoImage → hiển thị
```

---

## Máy trạng thái tích lũy rủi ro

Thay vì sử dụng ngưỡng cứng kiểu ON/OFF, hệ thống áp dụng kiến trúc **Risk-Based State Machine** — tích lũy điểm rủi ro từ nhiều tín hiệu, cho phép phân biệt giữa hành vi bình thường, cảnh báo sớm và xác nhận buồn ngủ.

### Trạng thái hệ thống (DriverState)

```
  NORMAL                 ← Risk = 0, mọi thứ bình thường
    │
    ├── DISTRACTED       ← Yaw > 30° (nhìn sang bên)
    ├── HEAD_DOWN        ← Pitch drop > 30° + mắt nhắm
    ├── YAWN_CANDIDATE   ← MAR > 0.60 liên tục > 0.8 giây
    │
    ├── SUSPECTED (Cam)  ← Risk ≥ 50 → Cảnh báo sớm
    └── CONFIRMED (Đỏ)   ← Risk ≥ 85 → Báo động buồn ngủ!
```

### Bảng tín hiệu và điểm phạt

| Tín hiệu | Điều kiện | Điểm risk cộng thêm | Ghi chú |
|---|---|---|---|
| **Nhắm mắt bất thường** | EAR < threshold liên tục 15 frame (~0.5s) | +25.0 (1 lần) | Bị chặn nếu đang ngáp hoặc đầu ngước lên |
| **Microsleep (Hard Rule)** | EAR < threshold liên tục 30 frame (~1.0s) | → Risk = 100 ngay | Không cần tích lũy, báo động tức thì |
| **Ngáp** | MAR > 0.60 liên tục 30 frame (~1.0s) | +25.0 (1 lần) | Không tính nếu há miệng ngắt quãng (hát/cười) |
| **Gật gù** | Pitch drop > 30° + mắt nhắm/PERCLOS cao | +30.0 (1 lần sau 0.5s) | Mắt phải nhắm — mở mắt cúi đầu = phanh gấp, bỏ qua |
| **PERCLOS > 30%** | > 30% thời gian nhắm mắt trong 3 giây | +2.0/frame | Phát hiện buồn ngủ mãn tính dạng lờ đờ |
| **Decay (phục hồi)** | Luôn luôn hoạt động | −1.0/frame | Risk tự trôi về 0 khi tài xế tỉnh táo |

### Dòng thời gian minh họa

```
  Risk
  100 ┤                        ████████  ← CONFIRMED (≥85)
      │                      ██
   85 ┤- - - - - - - - - - ██ - - - - -  ← Ngưỡng xác nhận
      │                  ██
   50 ┤- - - - - - - - ██  - - - - - - -  ← Ngưỡng cảnh báo sớm
      │             ████
   25 ┤     ████████                       ← Ngáp 1 cái (+25)
      │   ██      ↗ decay trừ dần
    0 ┤███                 ███████████     ← Tỉnh táo, risk = 0
      └──────────────────────────────────→ Thời gian (frames)
       Bình      Ngáp   Lờ đờ  Microsleep
       thường                    (Hard Rule)
```

---

## Chi tiết các module

### `main.py` — Entry Point

| Hàm | Mô tả |
|---|---|
| `select_camera(scan_limit)` | Quét các camera ID từ 0 đến `scan_limit`, tự động chọn nếu chỉ có 1 camera |
| `main()` | Khởi tạo config → quét camera → tạo detector → tạo GUI |

---

### `config.py` — Cấu hình tập trung

Chứa 3 class: `DriverState` (enum trạng thái), `AlertLevel` (enum mức cảnh báo), và `DetectorConfig` (dataclass tham số).

#### Bảng tham số DetectorConfig đầy đủ

| Nhóm | Tham số | Mặc định | Ý nghĩa |
|---|---|---|---|
| **Mắt** | `ear_thresh` | 0.20 | Ngưỡng EAR ban đầu (sẽ được tự hiệu chỉnh) |
| | `ear_consec_frames` | 30 | Hard rule: 1.0s nhắm mắt = Risk tối đa ngay lập tức |
| | `ear_recovery_frames` | 15 | Số frame EAR bình thường để reset bộ đếm (~0.5s) |
| | `abnormal_blink_frames` | 15 | Ngưỡng chớp mắt dài bất thường (~0.5s) |
| **Miệng** | `mar_thresh` | 0.60 | Ngưỡng MAR — trên giá trị này coi là đang ngáp |
| | `mar_consec_frames` | 30 | Phải há miệng liên tục 1.0 giây mới tính ngáp |
| | `mar_recovery_frames` | 3 | Khép miệng 0.1 giây = reset bộ đếm (chống nhầm hát/cười) |
| **Đầu** | `pitch_drop_thresh` | 30.0 | Độ gục đầu (°) so với baseline để coi là gật gù |
| | `yaw_distraction_thresh` | 30.0 | Góc quay ngang (°) để coi là xao lãng |
| **PERCLOS** | `perclos_window_frames` | 90 | Cửa sổ theo dõi PERCLOS (~3 giây ở 30 FPS) |
| | `perclos_thresh` | 0.30 | Tỷ lệ nhắm mắt > 30% = buồn ngủ mãn tính |
| **Risk** | `risk_max` | 100.0 | Điểm risk tối đa |
| | `risk_decay_rate` | 1.0 | Tốc độ phục hồi (trừ mỗi frame, luôn hoạt động) |
| | `risk_suspected_thresh` | 50.0 | Ngưỡng cảnh báo sớm (cam) |
| | `risk_confirmed_thresh` | 85.0 | Ngưỡng xác nhận buồn ngủ (đỏ) |
| | `risk_penalty_blink_long` | 25.0 | Điểm phạt khi nhắm mắt bất thường > 0.5s |
| | `risk_penalty_nodding` | 30.0 | Điểm phạt khi gật gù kèm mắt nhắm |
| | `risk_penalty_yawn` | 25.0 | Điểm phạt khi ngáp dài > 1.0s |
| | `risk_penalty_perclos` | 2.0 | Điểm phạt mỗi frame khi PERCLOS cao |
| **Camera** | `frame_width` | 960 | Chiều rộng khung hình (pixel) |
| | `frame_height` | 720 | Chiều cao khung hình (pixel) |
| | `max_num_faces` | 4 | Số khuôn mặt tối đa MediaPipe theo dõi |
| | `driver_zone_ratio` | 0.5 | Tỷ lệ chiều rộng màn hình coi là vùng tài xế |
| **Tiền xử lý** | `clahe_clip_limit` | 2.0 | Giới hạn contrast CLAHE |
| | `clahe_tile_grid_size` | (8, 8) | Kích thước lưới CLAHE |
| | `bbox_padding` | 10 | Khoảng đệm bounding box |

---

### `core/detector.py` — Phát hiện buồn ngủ

Module cốt lõi xử lý từng frame camera. Đây là trái tim của hệ thống.

| Hàm | Mô tả |
|---|---|
| `__init__(config)` | Khởi tạo MediaPipe FaceMesh, CLAHE, bộ đếm risk, PERCLOS buffer |
| `preprocess_image(frame)` | Grayscale → CLAHE histogram equalization → RGB |
| `get_ear(landmarks, indices)` | Tính Eye Aspect Ratio từ 6 landmark quanh mắt |
| `get_mar(landmarks)` | Tính Mouth Aspect Ratio từ 4 landmark quanh miệng |
| `get_head_pose(landmarks, w, h)` | Ước lượng Pitch/Yaw/Roll bằng `cv2.solvePnP` + mô hình 6 điểm 3D |
| `_extract_faces(results, w, h)` | Trích xuất danh sách khuôn mặt (landmarks, bbox, area, center_x) |
| `_choose_driver_index(faces, w)` | Chọn tài xế: khuôn mặt có diện tích lớn nhất ở nửa trái |
| `_draw_face_mesh(frame, landmarks, is_alert)` | Vẽ đường viền: oval, mắt, mũi, môi, iris |
| `_evaluate_state(ear, mar, pitch, yaw)` | **Hàm chính**: tích lũy risk, áp dụng veto rules, chuyển trạng thái |
| `process_frame(frame)` | Pipeline chính: tiền xử lý → detect → metrics → risk → vẽ → trả kết quả |
| `close()` | Giải phóng MediaPipe FaceMesh |

#### Cơ chế tự hiệu chỉnh EAR

```
  Hệ thống theo dõi EAR tối đa trong cửa sổ 60 frame gần nhất:
  → dynamic_ear_open = max(EAR trong 60 frame)
  → ear_thresh = max(0.12, dynamic_ear_open × 0.60)

  Ví dụ: Người mắt to (EAR mở = 0.35) → thresh = 0.21
         Người mắt híp (EAR mở = 0.22) → thresh = 0.13
         Đeo kính râm (EAR mở = 0.15) → thresh = 0.12 (sàn an toàn)
```

---

### `core/face_id.py` — Nhận dạng khuôn mặt

Sử dụng **2 phương pháp kết hợp** để nhận dạng:

#### Phương pháp 1: Landmark Signature (15D)
| Hàm | Mô tả |
|---|---|
| `extract_face_signature(landmarks)` | Tính 15 khoảng cách chuẩn hóa giữa các cặp landmark ổn định |
| `compare_signatures(sig1, sig2)` | So sánh L2 distance → similarity [0, 1] |

#### Phương pháp 2: Spatial Histogram (512D)
| Hàm | Mô tả |
|---|---|
| `extract_face_crop(frame, bbox)` | Cắt vùng mặt → resize 128×128 → grayscale |
| `compute_face_histogram(crop)` | Chia 4×4 grid × 32 bins = 512D vector |
| `compare_face_histograms(h1, h2)` | So sánh bằng `cv2.compareHist` (HISTCMP_CORREL) |

---

### `core/audio.py` — Phát âm thanh

| Hàm | Mô tả |
|---|---|
| `AudioPlayer.get_instance()` | Singleton pattern — toàn bộ ứng dụng dùng 1 instance |
| `play(filename, cooldown, force)` | Phát WAV async qua `winsound.SND_ASYNC`, có cooldown chống spam |
| `stop()` | Dừng âm thanh đang phát bằng `winsound.SND_PURGE` |

---

### `ui/app.py` — Giao diện chính

| Hàm | Mô tả |
|---|---|
| `__init__(root, cap, detector)` | Khởi tạo UI, bắt đầu vòng lặp frame |
| `build_ui()` | Xây dựng layout: Camera + Controls + Log |
| `_log(message, tag)` | Ghi log có mã màu (alert/success/info/warn) |
| `_update()` | Vòng lặp 30ms: đọc frame → process → cảnh báo → hiển thị |
| `on_closing()` | Giải phóng camera và detector khi đóng cửa sổ |

---

### `ui/led_widget.py` — LED ảo

Widget Tkinter Canvas mô phỏng đèn LED vật lý:

| Trạng thái | Màu | Hiệu ứng | Ý nghĩa |
|---|---|---|---|
| `OFF` | Xám | Tĩnh | Chờ / không hoạt động |
| `RUNNING_OK` | Xanh lá | Nhịp thở 1Hz | Đang giám sát, tài xế tỉnh táo |
| `RUNNING_UNKNOWN` | Vàng | Nhịp thở 1Hz | Đang giám sát, chưa xác định |
| `ALERT` | Đỏ | Nhấp nháy 5Hz | Cảnh báo buồn ngủ! |

---

## Cài đặt và khởi chạy

### Yêu cầu hệ thống

- **OS**: Windows 10/11 (do sử dụng `winsound` API)
- **Python**: 3.10 trở lên
- **Camera**: Webcam USB hoặc built-in
- **RAM**: ≥ 4GB
- **CPU**: Intel i5 thế hệ 8+ hoặc tương đương (không cần GPU)

### Bước 1: Clone repository

```bash
git clone https://github.com/Lucyfer7566/anti-sleepy-driver.git
cd anti-sleepy-driver
```

### Bước 2: Tạo môi trường ảo (khuyến nghị)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
```

### Bước 3: Cài đặt thư viện

```bash
pip install -r anti_sleepy/requirements.txt
```

### Bước 4: Khởi chạy

```bash
python anti_sleepy/main.py
```

Hệ thống sẽ:
1. Tự động quét và chọn camera
2. Tự hiệu chỉnh ngưỡng EAR theo hình dạng khuôn mặt trong vài giây đầu tiên
3. Bắt đầu giám sát ngay lập tức — **không cần đăng ký khuôn mặt**

---

## File âm thanh

Đặt trong `anti_sleepy/assets/sounds/`. Định dạng **WAV** (PCM, 16-bit).

| File | Thời điểm phát | Nhóm |
|---|---|---|
| `alert_drowsy.wav` | Cảnh báo ngủ gật (risk ≥ 85) | Cảnh báo |
| `alert_yawning.wav` | Cảnh báo ngáp (MAR > 0.60 >1.0s) | Cảnh báo |
| `alert_nodding.wav` | Cảnh báo gật gù | Cảnh báo |
| `sys_welcome_owner.wav` | Nhận diện đúng chủ xe | Hệ thống |
| `sys_unknown_driver.wav` | Phát hiện người lạ ngồi ghế lái | Hệ thống |
| `sys_no_profile.wav` | Chưa có profile | Hệ thống |
| `reg_*.wav` (6 file) | Âm thanh hướng dẫn đăng ký | Đăng ký |

---

## Cấu hình

Mọi tham số đều nằm trong `anti_sleepy/config.py`. Chỉnh sửa trực tiếp để tinh chỉnh:

```python
@dataclass
class DetectorConfig:
    # === Ngưỡng mắt ===
    ear_thresh: float = 0.20          # Tự hiệu chỉnh → 60% max EAR
    ear_consec_frames: int = 30       # 1.0s nhắm mắt = Microsleep (Hard Rule)
    abnormal_blink_frames: int = 15   # 0.5s nhắm mắt = Bất thường (+25 risk)

    # === Ngưỡng miệng ===
    mar_thresh: float = 0.60          # Ngưỡng ngáp (cao hơn cười/hát)
    mar_consec_frames: int = 30       # 1.0s liên tục mới tính ngáp
    mar_recovery_frames: int = 3      # 0.1s khép miệng = reset (chống nhầm hát)

    # === Ngưỡng đầu ===
    pitch_drop_thresh: float = 30.0   # Gật gù (độ)
    yaw_distraction_thresh: float = 30.0  # Xao lãng (độ)

    # === PERCLOS ===
    perclos_window_frames: int = 90   # Cửa sổ 3 giây
    perclos_thresh: float = 0.30      # 30% nhắm mắt = buồn ngủ mãn tính

    # === Risk Engine ===
    risk_max: float = 100.0
    risk_decay_rate: float = 1.0      # Luôn hoạt động, tự phục hồi
    risk_suspected_thresh: float = 50.0   # Cảnh báo sớm (cam)
    risk_confirmed_thresh: float = 85.0   # Xác nhận buồn ngủ (đỏ)
    risk_penalty_blink_long: float = 25.0
    risk_penalty_nodding: float = 30.0
    risk_penalty_yawn: float = 25.0
    risk_penalty_perclos: float = 2.0     # Mỗi frame khi PERCLOS cao
```

> **Quan trọng**: Ngưỡng `ear_thresh` sẽ được hệ thống tự hiệu chỉnh theo cấu trúc khuôn mặt thực tế khi chạy. Giá trị trong config chỉ là giá trị khởi tạo ban đầu.

---

## Cơ chế chống báo sai

Hệ thống được trang bị nhiều lớp lọc để giảm thiểu cảnh báo nhầm trong các tình huống lái xe thực tế:

### 1. Veto Rule — Chống nhầm góc đầu

| Tình huống | Vấn đề | Giải pháp |
|---|---|---|
| Ngước nhìn biển báo/trần xe | EAR bị ép thấp do góc camera | Pitch < −25° → `eyes_closed = False` |
| Quay đầu nhìn gương/bên cạnh | EAR bị méo do nghiêng mặt | Yaw > 30° → `eyes_closed = False` |

### 2. Nodding Validation — Chống nhầm phanh gấp

| Hành vi | Pitch drop | Mắt | Kết quả |
|---|---|---|---|
| Phanh gấp | ✅ > 30° | Mở to | ❌ Không phạt |
| Cúi nhìn GPS | ✅ > 30° | Mở to | ❌ Không phạt |
| Ngủ gật gục đầu | ✅ > 30° | Nhắm | ✅ +30 risk |

### 3. Yawn Hysteresis — Chống nhầm hát/cười

| Hành vi | MAR | Thời gian | Recovery | Kết quả |
|---|---|---|---|---|
| Cười ha ha | > 0.60 | < 1.0s | — | ❌ Không phạt |
| Hát ngân nga | > 0.60 | Ngắt quãng | Reset mỗi 0.1s khi khép miệng | ❌ Không phạt |
| Ngáp mệt mỏi | > 0.60 | ≥ 1.0s liên tục | Không khép lại | ✅ +25 risk |

### 4. Yawn Eye Suppression — Chống nhầm EAR khi ngáp

Khi người dùng ngáp, mắt tự nhiên nheo lại. Hệ thống tự động tạm ngưng penalty nhắm mắt (`blink_duration`) và loại bỏ khỏi PERCLOS buffer khi MAR > ngưỡng ngáp.

### 5. Risk Decay luôn hoạt động

Risk trừ 1.0 điểm/frame **vô điều kiện** — kể cả khi chớp mắt bình thường. Điều này đảm bảo:
- Sau khi ngáp 1 cái (+25 risk), risk sẽ tự về 0 trong ~0.8 giây nếu không có tín hiệu buồn ngủ khác
- Chớp mắt tự nhiên không "khoá" decay lại gây tích lũy oan

---

## Xử lý sự cố

| Vấn đề | Nguyên nhân | Giải pháp |
|---|---|---|
| `Khong tim thay camera hoat dong!` | Không có webcam hoặc bị app khác chiếm | Đóng các app dùng camera (Zoom, Teams), kiểm tra Device Manager |
| Cảnh báo liên tục dù tỉnh táo | PERCLOS hoặc EAR threshold chưa phù hợp | Đợi vài giây để hệ thống tự hiệu chỉnh; nếu vẫn sai, tăng `perclos_thresh` |
| Báo nhầm khi cười/hát | `mar_thresh` quá thấp | Tăng `mar_thresh` hoặc `mar_consec_frames` trong config |
| Báo nhầm khi phanh gấp/ngước đầu | Veto rule chưa đủ mạnh | Giảm ngưỡng veto (hiện tại: -25° pitch, 30° yaw) |
| App bị lag / giật hình | CPU yếu hoặc resolution quá cao | Giảm `frame_width`/`frame_height` (ví dụ: 640×480) |
| `Warning: Audio file not found` | Thiếu file WAV trong thư mục sounds | Đảm bảo đủ 13 file trong `anti_sleepy/assets/sounds/` |
| MediaPipe không detect được mặt | Ánh sáng quá tối hoặc camera bị che | Tăng `clahe_clip_limit` hoặc cải thiện ánh sáng |
| Risk tăng dần dù không làm gì | Phiên bản cũ có bug decay bị khoá | Cập nhật lên phiên bản mới nhất (decay luôn hoạt động) |

---

## Hạn chế đã biết

- **Chỉ hỗ trợ Windows** — do phụ thuộc vào `winsound` API cho phát âm thanh. Trên macOS/Linux cần thay bằng `pygame.mixer` hoặc `sounddevice`.
- **Phụ thuộc vào MediaPipe** — nếu tay che mặt hoặc đội mũ bảo hiểm che hết mặt, hệ thống không thể phát hiện.
- **EAR bị ảnh hưởng bởi góc lớn** — khi đầu nghiêng > 45°, EAR không còn chính xác dù có Veto Rule.
- **Âm thanh đơn kênh** — `winsound.SND_ASYNC` chỉ phát 1 âm thanh cùng lúc.
- **Chưa có module phát hiện xao lãng** — hệ thống chỉ ghi nhận DISTRACTED nhưng chưa phạt risk khi nhìn sang bên quá lâu.
- **Chưa có logging dữ liệu** — chưa ghi file log lịch sử risk để phân tích sau chuyến đi.

---

## Tài liệu tham khảo

1. **Soukupová, T. & Čech, J.** (2016). *Real-Time Eye Blink Detection using Facial Landmarks*. 21st Computer Vision Winter Workshop. — Công thức EAR gốc.
2. **Lugaresi, C. et al.** (2019). *MediaPipe: A Framework for Building Perception Pipelines*. arXiv:1906.08172. — Framework MediaPipe.
3. **Google AI.** *MediaPipe Face Mesh*. https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker — Tài liệu FaceMesh 478 landmarks.
4. **OpenCV Documentation.** *solvePnP — Perspective-n-Point pose estimation*. https://docs.opencv.org/4.x/ — Ước lượng head pose.
5. **Bradski, G.** (2000). *The OpenCV Library*. Dr. Dobb's Journal of Software Tools. — Thư viện OpenCV.
6. **Dinges, D.F. & Grace, R.** (1998). *PERCLOS: A valid psychophysiological measure of alertness as assessed by psychomotor vigilance*. — Cơ sở lý thuyết PERCLOS.

---
