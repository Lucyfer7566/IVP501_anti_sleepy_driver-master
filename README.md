# Anti-Sleepy Driver — Hệ thống Phát hiện Buồn ngủ cho Tài xế

> Hệ thống giám sát tài xế thời gian thực sử dụng camera, kết hợp phân tích **tỷ lệ mắt (EAR)**, **tỷ lệ miệng (MAR)**, **góc nghiêng đầu (Pitch)** và **nhận dạng khuôn mặt chủ xe** để phát hiện các dấu hiệu buồn ngủ và cảnh báo bằng âm thanh.

**Môn học**: IVP501 — Xử lý ảnh và Thị giác máy tính

---

## Mục lục

- [Tính năng chính](#tính-năng-chính)
- [Demo giao diện](#demo-giao-diện)
- [Tổng quan kiến trúc](#tổng-quan-kiến-trúc)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Luồng hoạt động](#luồng-hoạt-động)
- [Chi tiết các module](#chi-tiết-các-module)
- [Cài đặt và khởi chạy](#cài-đặt-và-khởi-chạy)
- [File âm thanh](#file-âm-thanh)
- [Cấu hình](#cấu-hình)
- [Xử lý sự cố](#xử-lý-sự-cố)
- [Hạn chế đã biết](#hạn-chế-đã-biết)
- [Tài liệu tham khảo](#tài-liệu-tham-khảo)

---

## Tính năng chính

| Tính năng | Mô tả |
|---|---|
| **Phát hiện buồn ngủ** | Theo dõi EAR (mắt), MAR (miệng), Pitch (đầu) theo thời gian thực |
| **Nhận dạng chủ xe** | Kết hợp Landmark Signature + Spatial Histogram để nhận diện tài xế đã đăng ký |
| **Cảnh báo âm thanh** | 13 file WAV tự động phát theo từng tình huống (buồn ngủ, ngáp, người lạ, ...) |
| **Đăng ký khuôn mặt** | Quy trình 5 bước có hướng dẫn bằng giọng nói |
|   **Face Mesh Overlay** | Vẽ viền mặt, mắt, mũi, môi, iris trực tiếp lên camera feed |
|   **Tự nhận kính râm** | Phát hiện landmark bị "đóng băng" bằng phân tích phương sai EAR |
|   **Đa khuôn mặt** | Hỗ trợ tới 4 khuôn mặt, tự động chọn vị trí tài xế (nửa trái) |
|   **Hysteresis** | Chống nhảy trạng thái — cần nhiều frame liên tục mới kích hoạt/tắt cảnh báo |
|   **LED ảo** | Widget LED animated (9 trạng thái) phản ánh trạng thái hệ thống |
|   **Log sự kiện** | Panel log có mã màu, chỉ hiển thị sự kiện quan trọng |

---

## Demo giao diện

>  Ảnh demo sẽ được cập nhật sau khi hoàn tất testing.

**Layout giao diện:**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                    CAMERA FEED (960×720)                 │
│            [Face Mesh] [Eye Contours] [Iris]            │
│         ┌──────────┐               ┌──────────┐        │
│         │ TAI XE   │               │HANH KHACH│        │
│         └──────────┘               └──────────┘        │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ ● LED │ Dang ky │ Owner: DA DANG KY │ Nhan dang: CHU XE│
│        │         │ Mode: BINH THUONG │ EAR:0.28 MAR:0.02│
├─────────────────────────────────────────────────────────┤
│ ┌─ Nhat ky su kien ──────────────────────────────────┐  │
│ │ [09:04:19] Nhan dang: CHU XE                       │  │
│ │ [09:04:27] CANH BAO: NGU GAT! (DROWSY)             │  │
│ │ [09:04:28] Binh thuong tro lai                     │  │
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
│  │register_flow │  │  │   face_id.py         │  │
│  │  (Đăng ký)   │  │  │  (Nhận dạng mặt)    │  │
│  ├──────────────┤  │  ├──────────────────────┤  │
│  │ led_widget   │  │  │   audio.py           │  │
│  │  (LED ảo)    │  │  │  (Phát âm thanh)     │  │
│  └──────────────┘  │  ├──────────────────────┤  │
│                    │  │   profile.py          │  │
│                    │  │  (Lưu/đọc JSON)      │  │
│                    │  └──────────────────────┘  │
├────────────────────┴────────────────────────────┤
│                  config.py                      │  ← Cấu hình tập trung
└─────────────────────────────────────────────────┘
```

**Nguyên tắc thiết kế:**
- **Core Layer** không phụ thuộc vào UI — có thể test độc lập hoặc thay Tkinter bằng framework khác.
- **UI Layer** chỉ gọi Core qua interface đơn giản (`process_frame()`, `feed_frame()`).
- **Config** tập trung tại 1 file duy nhất, dễ điều chỉnh.

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

### Tại sao dùng Tkinter thay vì PyQt/Web?

- **Không cần cài đặt thêm** — Tkinter đi kèm Python.
- **Nhẹ** — Phù hợp với hệ thống nhúng/laptop cấu hình thấp.
- **Đủ tính năng** — Hiển thị video real-time, nút bấm, log panel, LED ảo.

### Các công thức toán học cốt lõi

**Eye Aspect Ratio (EAR):**

```
         ‖p2 - p6‖ + ‖p3 - p5‖
  EAR = ─────────────────────────
              2 × ‖p1 - p4‖

  Trong đó p1..p6 là 6 landmark quanh mắt.
  Mắt mở: EAR ≈ 0.25–0.35
  Mắt nhắm: EAR < 0.20
```

**Mouth Aspect Ratio (MAR):**

```
         ‖top - bottom‖
  MAR = ─────────────────
         ‖left - right‖

  Miệng khép: MAR ≈ 0.0–0.1
  Đang ngáp: MAR > 0.45
```

**Head Pose Estimation:**

```
  Sử dụng cv2.solvePnP() với 6 điểm 3D tham chiếu:
    - Đỉnh mũi (0, 0, 0)
    - Cằm (0, -330, -65)
    - Khóe mắt trái/phải (-225/225, 170, -135)
    - Khóe miệng trái/phải (-150/150, -150, -125)
  → Tính rotation matrix → trích xuất Pitch, Yaw, Roll (độ)
```

---

## Cấu trúc thư mục

```
anti_sleepy_driver/
├── anti_sleepy/                    # Package chính
│   ├── main.py                     # Entry point — quét camera, khởi tạo hệ thống
│   ├── config.py                   # Cấu hình tập trung (ngưỡng, resolution, ...)
│   ├── requirements.txt            # Danh sách thư viện cần cài
│   │
│   ├── core/                       # Tầng logic nghiệp vụ
│   │   ├── __init__.py
│   │   ├── detector.py             # Phát hiện buồn ngủ (EAR, MAR, Pitch, FaceMesh)
│   │   ├── face_id.py              # Nhận dạng chủ xe (Landmark + Histogram)
│   │   ├── audio.py                # Phát âm thanh async (winsound)
│   │   └── profile.py              # Đọc/ghi/xóa profile chủ xe (JSON)
│   │
│   ├── ui/                         # Tầng giao diện
│   │   ├── __init__.py
│   │   ├── app.py                  # Giao diện chính Tkinter
│   │   ├── register_flow.py        # Luồng đăng ký khuôn mặt 5 bước
│   │   └── led_widget.py           # Widget LED ảo (animated)
│   │
│   └── assets/
│       └── sounds/                 # 13 file âm thanh WAV
│           ├── alert_drowsy.wav
│           ├── alert_yawning.wav
│           ├── alert_nodding.wav
│           ├── reg_start.wav
│           ├── reg_eyes_open.wav
│           ├── reg_eyes_closed.wav
│           ├── reg_pitch_cal.wav
│           ├── reg_success.wav
│           ├── reg_no_face.wav
│           ├── reg_remove_glasses.wav
│           ├── sys_welcome_owner.wav
│           ├── sys_unknown_driver.wav
│           └── sys_no_profile.wav
│
├── data/                           # Dữ liệu runtime (auto-generated)
│   └── owner_profile.json          # Profile chủ xe (tạo khi đăng ký)
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
  ├── 4. Load profile chủ xe từ data/owner_profile.json (nếu có)
  └── 5. Khởi tạo Tkinter GUI → AntiSleepyApp
```

### 2. Vòng lặp xử lý chính (~33 FPS)

```
AntiSleepyApp._update()  [gọi lại mỗi 30ms]
  │
  ├── 1. Đọc frame từ camera → flip ngang (mirror)
  ├── 2. Gửi frame → detector.process_frame()
  │      │
  │      ├── Tiền xử lý: Grayscale → CLAHE → RGB
  │      ├── MediaPipe FaceMesh → 468 landmarks / khuôn mặt
  │      ├── Chọn khuôn mặt TÀI XẾ (nửa trái, diện tích lớn nhất)
  │      ├── Tính EAR, MAR, Head Pose (Pitch/Yaw/Roll)
  │      ├── Đánh giá trạng thái: _evaluate_state()
  │      │      ├── EAR < threshold (45 frames liên tục) → NGỦ GẬT
  │      │      ├── MAR > threshold (15 frames liên tục) → ĐANG NGÁP
  │      │      └── Pitch drop > 20° so với baseline → GẬT GÙ
  │      ├── Vẽ Face Mesh (viền mặt, mắt, mũi, môi, iris)
  │      └── Trả frame đã vẽ + dict metrics
  │
  ├── 3. Nhận dạng chủ xe (nếu có profile)
  │      ├── Extract face signature (15 khoảng cách landmark chuẩn hóa)
  │      ├── Extract face histogram (ảnh mặt 128×128 → 4×4 grid × 32 bins = 512D)
  │      ├── Blend 2 phương pháp theo góc Yaw hiện tại:
  │      │      nhìn thẳng (<15°) → 60% signature + 40% histogram
  │      │      hơi nghiêng (15–30°) → 30% signature + 70% histogram
  │      │      quay mạnh (>30°) → 10% signature + 90% histogram
  │      └── Majority vote buffer (25 frames) → CHỦ XE / NGƯỜI LẠ
  │
  ├── 4. Phát cảnh báo âm thanh (cooldown 5 giây chống spam)
  ├── 5. Cập nhật LED, labels, log panel
  └── 6. Chuyển đổi BGR→RGB → PIL Image → Tkinter PhotoImage → hiển thị
```

### 3. Luồng đăng ký khuôn mặt

```
RegisterFlow.feed_frame()  [5 giai đoạn tuần tự]
  │
  ├── Phase 1: FACE_SIG (3 giây)
  │   └── Thu thập landmark signature (15D) + face histogram (512D)
  │       Trung bình tất cả mẫu → 1 signature & 1 histogram chuẩn
  │
  ├── Phase 2: EAR_OPEN (3 giây)
  │   └── Đo EAR khi mắt mở bình thường → ear_open_baseline
  │
  ├── Phase 3: EAR_CLOSED (3 giây)
  │   └── Đo EAR khi nhắm mắt → ear_closed_baseline
  │       → ear_thresh = (ear_open + ear_closed) / 2
  │
  ├── Phase 4: PITCH_CAL (2 giây)
  │   └── Đo góc Pitch chuẩn khi nhìn thẳng → pitch_base
  │
  └── Phase 5: SUCCESS
      └── Tổng hợp profile → lưu data/owner_profile.json
```

**Dữ liệu profile được lưu:**

```json
{
    "registered_at": "2026-04-09T09:04:17",
    "face_signature": [15 số thực],
    "face_histogram": [512 số thực],
    "ear_open_baseline": 0.276,
    "ear_closed_baseline": 0.151,
    "ear_thresh": 0.213,
    "mar_baseline": 0.005,
    "mar_thresh": 0.450,
    "pitch_base": -164.538,
    "sunglasses_ear_cutoff": 0.15
}
```

---

## Chi tiết các module

### `main.py` — Entry Point

| Hàm | Mô tả |
|---|---|
| `select_camera(scan_limit)` | Quét các camera ID từ 0 đến `scan_limit`, tự động chọn nếu chỉ có 1 camera |
| `main()` | Khởi tạo config → quét camera → tạo detector → load profile → tạo GUI |

---

### `config.py` — Cấu hình tập trung

Dataclass `DetectorConfig` chứa tất cả tham số có thể điều chỉnh:

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `ear_thresh` | 0.20 | Ngưỡng EAR — dưới giá trị này coi là nhắm mắt |
| `ear_consec_frames` | 45 | Số frame liên tục EAR thấp để kích hoạt cảnh báo (~1.5 giây ở 30 FPS) |
| `ear_recovery_frames` | 15 | Số frame EAR bình thường liên tục để tắt cảnh báo (~0.5 giây) |
| `mar_thresh` | 0.45 | Ngưỡng MAR — trên giá trị này coi là đang ngáp |
| `mar_consec_frames` | 15 | Số frame liên tục MAR cao để kích hoạt cảnh báo ngáp |
| `mar_recovery_frames` | 10 | Số frame MAR bình thường liên tục để tắt cảnh báo ngáp |
| `pitch_drop_thresh` | 20.0 | Độ nghiêng đầu (°) so với baseline để coi là gật gù |
| `max_num_faces` | 4 | Số khuôn mặt tối đa MediaPipe theo dõi đồng thời |
| `frame_width` | 960 | Chiều rộng khung hình camera (pixel) |
| `frame_height` | 720 | Chiều cao khung hình camera (pixel) |
| `clahe_clip_limit` | 2.0 | Giới hạn contrast của CLAHE (tiền xử lý ảnh) |
| `bbox_padding` | 10 | Khoảng đệm (pixel) xung quanh bounding box khuôn mặt |
| `driver_zone_ratio` | 0.5 | Tỷ lệ chiều rộng màn hình coi là vùng tài xế (nửa trái) |

---

### `core/detector.py` — Phát hiện buồn ngủ

Module cốt lõi xử lý từng frame camera.

| Hàm | Mô tả |
|---|---|
| `__init__(config)` | Khởi tạo MediaPipe FaceMesh, CLAHE, bộ đếm hysteresis |
| `load_owner_profile(profile)` | Ghi đè ngưỡng EAR/MAR/Pitch từ profile đã đăng ký |
| `preprocess_image(frame)` | Grayscale → CLAHE histogram equalization → RGB |
| `get_ear(landmarks, indices)` | Tính Eye Aspect Ratio từ 6 landmark quanh mắt |
| `get_mar(landmarks)` | Tính Mouth Aspect Ratio từ 4 landmark quanh miệng |
| `get_head_pose(landmarks, w, h)` | Ước lượng Pitch/Yaw/Roll bằng `cv2.solvePnP` + mô hình 6 điểm 3D |
| `_extract_faces(results, w, h)` | Trích xuất danh sách khuôn mặt (landmarks, bbox, area, center_x) |
| `_choose_driver_index(faces, w)` | Chọn tài xế: khuôn mặt có diện tích lớn nhất ở nửa trái khung hình |
| `_draw_face_mesh(frame, landmarks, is_alert)` | Vẽ đường viền: oval (36 pts), mắt (16 pts/mắt), mũi (6 pts), môi (20 pts), iris |
| `_evaluate_state(ear, mar, pitch)` | Đánh giá trạng thái buồn ngủ với **cơ chế hysteresis** |
| `process_frame(frame)` | Pipeline chính: tiền xử lý → detect → tính metrics → vẽ → trả kết quả |

**Cơ chế Hysteresis (chống nhảy trạng thái):**

```
  Trạng thái bình thường          Kích hoạt cảnh báo
         ──────────────────────────────────────>
         Cần 45 frame liên tục EAR < threshold

         Đang cảnh báo              Tắt cảnh báo
         ──────────────────────────────────────>
         Cần 15 frame liên tục EAR > threshold

  → Ngăn hiện tượng flickering khi EAR dao động quanh ngưỡng.
```

---

### `core/face_id.py` — Nhận dạng khuôn mặt

Sử dụng **2 phương pháp kết hợp** để nhận dạng chủ xe:

#### Phương pháp 1: Landmark Signature (15D)
| Hàm | Mô tả |
|---|---|
| `extract_face_signature(landmarks)` | Tính 15 khoảng cách chuẩn hóa giữa các cặp landmark ổn định (trán-cằm, gò má, sống mũi, ...) |
| `average_signatures(sigs)` | Trung bình nhiều signature → 1 vector chuẩn (dùng khi đăng ký) |
| `compare_signatures(sig1, sig2)` | So sánh L2 distance → similarity = 1/(1+distance), range [0, 1] |

- Cách hoạt động: MediaPipe FaceMesh trả về 468 điểm đặc trưng trên khuôn mặt. Hệ thống chọn 15 cặp điểm ổn định (trán, cằm, gò má, sống mũi, khóe miệng) rồi tính khoảng cách giữa từng cặp, chuẩn hóa theo chiều rộng khuôn mặt → tạo thành vector 15 số thực.
- Ưu điểm: Nhanh, nhẹ, không cần model AI riêng.
- Nhược điểm: Rất nhạy với góc xoay đầu — khi nghiêng đầu, tọa độ 2D của các điểm thay đổi mạnh → khoảng cách bị sai lệch.

#### Phương pháp 2: Spatial Histogram (512D)
| Hàm | Mô tả |
|---|---|
| `extract_face_crop(frame, bbox)` | Cắt vùng mặt → resize 128×128 → grayscale → histogram equalize |
| `compute_face_histogram(crop)` | Chia ảnh thành lưới 4×4, mỗi ô tính histogram 32 bin → vector 512D |
| `compare_face_histograms(h1, h2)` | So sánh bằng `cv2.compareHist` (HISTCMP_CORREL), range [-1, 1] |

- Cách hoạt động: Cắt vùng mặt từ khung hình ra, resize về 128×128 pixel, chuyển sang grayscale, cân bằng sáng. Sau đó chia ảnh mặt thành lưới 4×4 = 16 ô, mỗi ô tính histogram 32 bin → tạo vector 512 giá trị mô tả phân bố sáng/tối trên từng vùng khuôn mặt.
- Ưu điểm: Bền vững hơn nhiều khi xoay đầu vì nó ghi nhớ cấu trúc sáng tối tổng thể thay vì vị trí điểm cụ thể.
- Nhược điểm: Nhạy với thay đổi ánh sáng mạnh (ban ngày/đêm).

#### Hàm kết hợp
| Hàm | Mô tả |
|---|---|
| `is_owner(sig, saved_sig, hist, saved_hist, yaw)` | Blend 2 phương pháp theo góc Yaw, trả về `(is_match: bool, combined_score: float)` |

**Bảng trọng số blend theo góc Yaw:**

| Góc đầu (Yaw) | Signature weight | Histogram weight | Ngưỡng |
|---|---|---|---|
| < 15° (nhìn thẳng) | 60% | 40% | 0.55 |
| 15°–30° (hơi nghiêng) | 30% | 70% | 0.50 |
| > 30° (quay mạnh) | 10% | 90% | 0.45 |

Kết quả mỗi frame (khớp/không khớp) được đẩy vào bộ đệm 25 frames. Chỉ khi >55% frames nói "khớp" mới kết luận CHỦ XE, <30% mới kết luận NGƯỜI LẠ.
---

### `core/audio.py` — Phát âm thanh

| Hàm | Mô tả |
|---|---|
| `AudioPlayer.get_instance()` | Singleton pattern — đảm bảo toàn bộ ứng dụng chỉ dùng 1 instance |
| `play(filename, cooldown, force)` | Phát WAV async qua `winsound.SND_ASYNC`, có cooldown chống phát lặp liên tục |
| `stop()` | Dừng âm thanh đang phát bằng `winsound.SND_PURGE` |

---

### `core/profile.py` — Lưu trữ Profile

| Hàm | Mô tả |
|---|---|
| `profile_exists(path)` | Kiểm tra file `data/owner_profile.json` tồn tại |
| `save_profile(profile, path)` | Lưu dict → JSON (tự tạo thư mục `data/` nếu chưa có) |
| `load_profile(path)` | Đọc JSON → dict, trả về `None` nếu file lỗi/không tồn tại |
| `delete_profile(path)` | Xóa file profile (reset toàn bộ đăng ký) |

---

### `ui/app.py` — Giao diện chính

| Hàm | Mô tả |
|---|---|
| `__init__(root, cap, detector)` | Khởi tạo UI, load profile, bắt đầu vòng lặp frame |
| `build_ui()` | Xây dựng layout ngang: Camera → Controls → Log |
| `_log(message, tag)` | Ghi log có mã màu (alert/success/info/warn) vào panel + terminal |
| `start_registration()` | Khởi động luồng đăng ký khi bấm nút |
| `_update()` | Vòng lặp 30ms: đọc frame → process → nhận dạng → cảnh báo → hiển thị |
| `on_closing()` | Giải phóng camera và detector khi đóng cửa sổ |

---

### `ui/register_flow.py` — Luồng đăng ký

| Hàm | Mô tả |
|---|---|
| `start()` | Reset accumulator, chuyển Phase = FACE_SIG, phát audio hướng dẫn |
| `cancel()` | Hủy/kết thúc đăng ký, đưa LED về OFF |
| `feed_frame(landmarks, ear, mar, pitch, hist)` | Xử lý 1 frame: tích lũy dữ liệu theo phase, trả text hướng dẫn |
| `_compute_profile()` | Tính profile cuối: trung bình signature/histogram, tính ear_thresh, mar_thresh |
| `_reset_accumulators()` | Xóa toàn bộ buffer (sig_list, ear_open_list, ear_closed_list, pitch_list, histograms) |

---

### `ui/led_widget.py` — LED ảo

Widget Tkinter Canvas mô phỏng đèn LED vật lý với 9 trạng thái và hiệu ứng animation:

| Trạng thái | Màu | Hiệu ứng | Ý nghĩa |
|---|---|---|---|
| `OFF` | Xám | Tĩnh | Chờ / không hoạt động |
| `REGISTERING` | Vàng | Nhấp nháy 2Hz | Đang đăng ký |
| `EAR_OPEN` | Xanh dương | Nhấp nháy 2Hz | Thu thập EAR mắt mở |
| `EAR_CLOSED` | Cam | Nhấp nháy 2Hz | Thu thập EAR mắt nhắm |
| `PITCH_CAL` | Tím | Nhấp nháy 2Hz | Hiệu chỉnh góc đầu |
| `SUCCESS` | Xanh lá | Tĩnh | Đăng ký thành công |
| `RUNNING_OK` | Xanh lá | Nhịp thở 1Hz | Đang giám sát, nhận diện chủ xe |
| `RUNNING_UNKNOWN` | Vàng | Nhịp thở 1Hz | Đang giám sát, người lạ |
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

### Bước 5: Đăng ký khuôn mặt

1. Khi app mở lên, bấm nút **"Dang ky"**
2. Nhìn thẳng vào camera (3 giây) — thu thập đặc trưng khuôn mặt
3. Mở mắt bình thường (3 giây) — đo EAR baseline
4. Nhắm mắt lại (3 giây) — đo EAR khi nhắm mắt
5. Nhìn thẳng phía trước (2 giây) — hiệu chỉnh góc đầu
6. Hoàn tất! Profile được lưu tự động vào `data/owner_profile.json`

> **Lưu ý**: Để đăng ký lại, bấm nút "Dang ky" khi đã có profile → hệ thống sẽ hỏi xác nhận xóa profile cũ trước khi đăng ký mới.

---

## File âm thanh

Đặt trong `anti_sleepy/assets/sounds/`. Định dạng **WAV** (PCM, 16-bit).

| File | Thời điểm phát | Nhóm |
|---|---|---|
| `reg_start.wav` | Bắt đầu đăng ký | Đăng ký |
| `reg_eyes_open.wav` | Chuyển sang giai đoạn đo mắt mở | Đăng ký |
| `reg_eyes_closed.wav` | Chuyển sang giai đoạn đo mắt nhắm | Đăng ký |
| `reg_pitch_cal.wav` | Chuyển sang hiệu chỉnh góc đầu | Đăng ký |
| `reg_success.wav` | Đăng ký thành công | Đăng ký |
| `reg_no_face.wav` | Không tìm thấy khuôn mặt khi đăng ký | Đăng ký |
| `reg_remove_glasses.wav` | Phát hiện đeo kính râm | Đăng ký |
| `alert_drowsy.wav` | Cảnh báo ngủ gật | Cảnh báo |
| `alert_yawning.wav` | Cảnh báo ngáp | Cảnh báo |
| `alert_nodding.wav` | Cảnh báo gật gù | Cảnh báo |
| `sys_welcome_owner.wav` | Nhận diện đúng chủ xe | Hệ thống |
| `sys_unknown_driver.wav` | Phát hiện người lạ ngồi ghế lái | Hệ thống |
| `sys_no_profile.wav` | Chưa có profile, cần đăng ký | Hệ thống |

---

## Cấu hình

Mọi tham số đều nằm trong `anti_sleepy/config.py`. Chỉnh sửa trực tiếp để tinh chỉnh độ nhạy:

```python
@dataclass
class DetectorConfig:
    ear_thresh: float = 0.20          # Hạ xuống → nhạy hơn, dễ báo sai
    ear_consec_frames: int = 45       # Tăng lên → ít báo sai, phản hồi chậm hơn
    ear_recovery_frames: int = 15     # Tăng lên → cảnh báo kéo dài hơn
    mar_thresh: float = 0.45          # Ngưỡng ngáp
    mar_consec_frames: int = 15       # Số frame liên tục để kích hoạt cảnh báo ngáp
    pitch_drop_thresh: float = 20.0   # Ngưỡng gật gù (độ)
    frame_width: int = 960            # Resolution camera
    frame_height: int = 720
```

> **Mẹo**: Sau khi đăng ký, các ngưỡng `ear_thresh`, `mar_thresh`, `pitch_base` sẽ được profile cá nhân ghi đè, phù hợp hơn với cấu trúc khuôn mặt riêng của tài xế.

---

## Xử lý sự cố

| Vấn đề | Nguyên nhân | Giải pháp |
|---|---|---|
| `Khong tim thay camera hoat dong!` | Không có webcam hoặc bị app khác chiếm | Đóng các app đang dùng camera (Zoom, Teams, ...), kiểm tra Device Manager |
| Cảnh báo liên tục dù đang tỉnh | `ear_thresh` quá cao (>0.25) | Đăng ký lại: bấm "Dang ky", nhắm mắt chặt ở bước 4 |
| Nhận nhầm người lạ thành chủ xe | Đăng ký khi ánh sáng yếu hoặc góc lệch | Đăng ký lại trong điều kiện ánh sáng tốt, nhìn thẳng camera |
| App bị lag / giật hình | CPU yếu hoặc resolution quá cao | Giảm `frame_width`/`frame_height` trong `config.py` (ví dụ: 640×480) |
| `Warning: Audio file not found` | Thiếu file WAV trong thư mục sounds | Đảm bảo đủ 13 file trong `anti_sleepy/assets/sounds/` |
| MediaPipe không detect được mặt | Ánh sáng quá tối hoặc camera bị che | Tăng `clahe_clip_limit` hoặc cải thiện ánh sáng |

---

## Hạn chế đã biết

- **Chỉ hỗ trợ Windows** — do phụ thuộc vào `winsound` API cho phát âm thanh. Trên macOS/Linux cần thay bằng `playsound` hoặc `pygame.mixer`.
- **Nhận dạng khuôn mặt chưa hoàn hảo** — phương pháp Landmark + Histogram không bằng deep learning (face_recognition/ArcFace), có thể bị ảnh hưởng bởi thay đổi ánh sáng mạnh hoặc góc quay >45°.
- **Phụ thuộc vào MediaPipe** — nếu tay che mặt hoặc đội mũ bảo hiểm che hết mặt, hệ thống không thể phát hiện.
- **Đơn tài xế** — hệ thống chỉ lưu profile 1 chủ xe. Muốn thay đổi phải đăng ký lại.
- **Âm thanh đơn kênh** — `winsound.SND_ASYNC` chỉ phát 1 âm thanh cùng lúc, âm thanh mới sẽ cắt âm thanh cũ.

---

## Tài liệu tham khảo

1. **Soukupová, T. & Čech, J.** (2016). *Real-Time Eye Blink Detection using Facial Landmarks*. 21st Computer Vision Winter Workshop. — Công thức EAR gốc.
2. **Lugaresi, C. et al.** (2019). *MediaPipe: A Framework for Building Perception Pipelines*. arXiv:1906.08172. — Framework MediaPipe.
3. **Google AI.** *MediaPipe Face Mesh*. https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker — Tài liệu FaceMesh 468 landmarks.
4. **OpenCV Documentation.** *solvePnP — Perspective-n-Point pose estimation*. https://docs.opencv.org/4.x/ — Ước lượng head pose.
5. **Bradski, G.** (2000). *The OpenCV Library*. Dr. Dobb's Journal of Software Tools. — Thư viện OpenCV.

---
