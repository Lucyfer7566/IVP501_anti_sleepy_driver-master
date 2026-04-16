# Kịch bản Thuyết trình: Hệ thống Phát hiện Buồn ngủ cho Tài xế

> **Hướng dẫn chung:** 
> - Vì toàn bộ slide được xây dựng theo hướng tương tác (interactive), người thuyết trình cần **vừa nói vừa thao tác chuột** (click, hover, kéo slider) trên slide để làm cho bài thuyết trình sinh động.
> - Đi kèm kịch bản là các **[Chú thích]** màu xám về cách phát âm và ý nghĩa để các bạn tự tin hơn khi hội đồng đặt câu hỏi.
> - Kịch bản được chia làm 3 phần đều nhau dành cho 3 thành viên:
>   - **Thành viên 1 (Slide 1 → 4):** Giới thiệu, Đặt vấn đề và Tổng quan giải pháp.
>   - **Thành viên 2 (Slide 5 → 8):** Kiến trúc hệ thống, Thuật toán lõi, và Cơ chế tự hiệu chỉnh.
>   - **Thành viên 3 (Slide 9 → 12):** Mô phỏng Risk Timeline, Pipeline, Kết quả và Demo trực tiếp.

---

## 👨‍💻 THÀNH VIÊN 1: Mở đầu & Tổng quan (Slide 1 - 4)

### Slide 1: Cover (Trang bìa)
**Lời dẫn:** 
"Dạ em xin chào Cô Nguyễn Thị Bích Thủy cùng toàn thể các bạn có mặt trong buổi bảo vệ hôm nay. Đại diện cho nhóm, em xin phép được trình bày về đề tài: **'Hệ thống Phát hiện Buồn ngủ cho Tài xế'** – một ứng dụng Xử lý ảnh thời gian thực kết hợp giữa MediaPipe *[Phát âm: Mê-đi-a-pai]* và OpenCV. Nhóm chúng em gồm 3 thành viên là *(đọc tên các thành viên đang hiện trên slide)*."

### Slide 2: Vấn đề (Tại sao cần hệ thống này?)
**Lời dẫn:**
"Trước khi đi sâu vào hệ thống, chúng ta hãy nhìn vào thực trạng đáng báo động hiện nay. *(Nhấn mạnh vào 3 thẻ số liệu)* Theo tổ chức Y tế thế giới WHO, mỗi năm có tới 1.35 triệu ca tử vong vì tai nạn giao thông, trong đó 25% các vụ tai nạn thảm khốc đều liên quan đến việc tài xế ngủ gật. Tại Việt Nam, con số này cũng lên tới hàng ngàn vụ mỗi năm.

Hiện nay các dòng xe cũng đã có tính năng cảnh báo chệch làn dựa trên cảm biến vô lăng, hoặc tài xế xài vòng tay đo nhịp tim. Tuy nhiên các giải pháp này thường có **độ trễ cao** – tức là khi vô lăng lệch thì xe đã sắp gây tai nạn rồi. Chính vì vậy, nhóm chúng em chọn giải pháp **Camera kết hợp AI**, giúp phát hiện SỚM thông qua biểu cảm khuôn mặt từ trước khi tài xế mất hoàn toàn ý thức."

### Slide 3: Giải pháp của chúng tôi
**Lời dẫn:**
"Để giải quyết triệt để vấn đề này, sản phẩm của nhóm em được xây dựng với 4 cơ chế cốt lõi. *(Vừa nói vừa click mở các thẻ dropdown trên slide)*:
1. **Máy trạng thái tích lũy rủi ro — Risk Engine:** Đây là bộ não chính của hệ thống. Thay vì báo động kiểu 'nhắm mắt = buồn ngủ' như các hệ thống cũ, bọn em thu thập 5 tín hiệu cùng lúc: tỷ lệ mắt EAR, tỷ lệ miệng MAR, tỷ lệ nhắm mắt tích lũy PERCLOS *[Phát âm: Pơ-clốt]*, góc gật đầu Pitch, và góc quay đầu Yaw. Tất cả các tín hiệu này được quy đổi thành một **Điểm rủi ro từ 0 đến 100**. Hệ thống còn có cơ chế tự phục hồi — nghĩa là khi tài xế tỉnh lại, điểm rủi ro sẽ tự giảm về 0 mà không bị nghẽn lại.
   - Ngoài ra hệ thống có **Veto Rules** *[Phát âm: Vi-tâu]*, nghĩa là nếu tài xế đang ngước đầu lên hoặc quay đầu sang bên — ví dụ phanh gấp hay nhìn gương — hệ thống sẽ tự động tắt EAR penalty để không báo sai.
2. **Face ID – Nhận diện chủ xe:** Kết hợp Landmark Signature (15 chiều) và Spatial Histogram (512 chiều), tự động thích ứng theo góc xoay đầu. *(⚠️ Module phụ trợ — hiện chưa kích hoạt trong luồng chính)*
3. **Cảnh báo âm thanh tự động:** Hệ thống có 13 file WAV, phát bất đồng bộ — tức là phát âm mà camera không dừng lại, kèm cooldown 3–5 giây chống phát liên tục.
4. **Face Mesh trực quan:** Vẽ 5 lớp contour lên camera: viền mặt, mắt, mống mắt, mũi, môi. Xanh lá là bình thường, đỏ là đang cảnh báo."

### Slide 4: Technology Stack
**Lời dẫn:**
"Về mặt công nghệ, kiến trúc được viết hoàn toàn bằng Python và xây dựng giao diện bằng thư viện Tkinter. Khối tính toán dùng OpenCV và NumPy. 

Lý do lớn nhất ở đây là việc chúng em chọn **MediaPipe** làm AI Engine thay thế cho các mạng cũ như Dlib *[Phát âm: Đi-líp]* hay MTCNN *[Phát âm: Em-ti-xi-en-en]*. Nhìn vào bảng so sánh bên dưới, có thể thấy MediaPipe cho khả năng bắt tới 478 điểm mốc khuôn mặt cực kì chi tiết kèm cả Iris tracking — theo dõi mống mắt, độ mượt lên đến 30 FPS ngay cả trên CPU thông thường của laptop, mà dung lượng AI Model lại nhẹ hơn Dlib gấp 20 lần."

*(Chuyển mic cho Thành viên 2)*

---

## 👨‍💻 THÀNH VIÊN 2: Kiến trúc & Thuật toán lõi (Slide 5 - 8)

### Slide 5: Kiến trúc hệ thống
**Lời dẫn:**
"Xin chào cô và các bạn, mình xin tiếp tục phần về Kiến trúc bên trong của dự án.
Để dự án dễ dàng bảo trì, nhóm áp dụng kiến trúc **Clean Architecture** *[Phát âm: Cờ-lin A-ki-tếch-chơ, nghĩa: Kiến trúc phần mềm sạch]*. Nó tách biệt chương trình làm 3 tầng: Tầng **UI** để vẽ giao diện, tầng **Core** chứa mô hình AI và xử lý thuật toán, tầng **Config** chứa hằng số cài đặt.

Một điểm rất quan trọng: hệ thống hoạt động theo cơ chế **Plug & Play** — tức là **không cần đăng ký khuôn mặt**. Cắm camera vào, bật ứng dụng là chạy ngay, hệ thống tự hiệu chỉnh ngưỡng phù hợp với mỗi khuôn mặt khác nhau. *(Hover chuột vào các module để hiện tooltip giải thích — đặc biệt hover vào detector.py)*

Module cốt lõi nhất là `detector.py` ở tầng Core — nó chứa toàn bộ Risk Engine, Veto Rules, và cơ chế tự hiệu chỉnh. Lưu ý module `face_id.py` đang ở trạng thái mờ — nghĩa là nó là module phụ trợ, hiện chưa được kích hoạt trong luồng chính mà giữ lại cho phát triển tương lai."

### Slide 6: EAR & MAR — Phát hiện mắt và miệng
**Lời dẫn:**
"Khối quan trọng nhất của Core là cách phát hiện mệt mỏi. Đây là trực quan hóa của thuật toán đánh giá Mắt (viết tắt là EAR) và Miệng (MAR). 
> **[Chú thích hội đồng hỏi:]** Ý tưởng EAR lấy từ đâu? — Dạ nhóm tham khảo từ công trình khoa học năm 2016 của tác giả Soukupová *[Xâu-ku-pô-va]* và Čech *[Chéch]*.

*(Vừa nói vừa dùng chuột kéo qua lại thanh slider mô phỏng của EAR và MAR)*
- Với **EAR**, khoảng cách dọc của mí mắt chia khoảng cách ngang. Mắt mở bình thường có trị số tầm 0.28. Điểm đặc biệt của hệ thống bọn em là **ngưỡng EAR tự hiệu chỉnh**: thay vì cố định một con số cứng, hệ thống sẽ tự tính ngưỡng bằng **60% giá trị EAR mở lớn nhất** trong 60 frame gần đây. Nhờ vậy, dù tài xế mắt to hay mắt híp, hệ thống đều hoạt động chính xác.
- Với **MAR**, khi tài xế há miệng ngáp, giá trị MAR sẽ vọt lên. Ngưỡng ngáp là **0.60** — và phải liên tục trong ít nhất **1 giây** (30 frame) mới tính là ngáp thật. Điều này rất quan trọng vì nó giúp **loại bỏ trường hợp hát theo nhạc hoặc cười lớn** — vì khi cười hay hát, miệng mở rồi đóng liên tục chứ không giữ cố định, nên hệ thống tự bỏ qua.
> **[Chú thích hội đồng hỏi:]** Tại sao ngưỡng MAR là 0.60 mà không phải 0.45? — Dạ nhóm đã test thực tế: ngưỡng 0.45 quá nhạy, hát hay cười to đều chạm, nên nâng lên 0.60 để chỉ bắt ngáp thật sự."

### Slide 7: Head Pose & Risk Engine
**Lời dẫn:**
"Tuy nhiên, nếu chỉ đo mắt thì người đeo kính đen sẽ làm hệ thống bị lòa? Nhóm giải quyết bằng cách đo thêm chuyển động gật gù của đầu — gobọn em sử dụng hàm tính toán phối cảnh 3D ngược rất nổi tiếng của OpenCV là `solvePnP` *[Phát âm: Xôn-vờ-pi-en-pi]* để ước lượng góc **Pitch** *[Phát âm: Pích]*. Khi tài xế gật đầu xuống quá 30 độ và mắt đang nhắm → hệ thống cộng 30 điểm rủi ro. Nhưng nếu tài xế chỉ phanh gấp (đầu chúi nhưng mắt mở to) thì Veto Rules sẽ tắt penalty — không báo sai.

Phần hay nhất là **Risk Engine — Máy trạng thái tích lũy rủi ro**:
> **[Chú thích]**: Risk Engine hoạt động thế nào? — Giống đồng hồ đo nhiệt. Nhiều tín hiệu bất thường cộng dồn → risk tăng. Tài xế tỉnh lại → risk tự giảm (−1.0/frame). 

*(Trỏ chuột vào bảng Risk Info trên slide)*
- Nhắm mắt bất thường hơn 0.5 giây: **+25 risk**
- Microsleep — nhắm tịt mắt hơn 1 giây: **Risk = 100** tức thì — cảnh báo tối đa
- Ngáp liên tục hơn 1 giây: **+25 risk**
- Gật gù kèm mắt nhắm: **+30 risk**
- PERCLOS — tỷ lệ nhắm mắt vượt 30% trong 3 giây: **+2.0 risk mỗi frame**
- Risk decays — phục hồi **−1.0 mỗi frame** và **luôn hoạt động**, nghĩa là risk tự giảm về 0 sau vài giây nếu tài xế tỉnh lại

*(Nhấn Play để biểu đồ sóng EAR chạy)*
Nhìn vào biểu đồ sóng EAR bên phải, vạch đỏ là ngưỡng 0.20. Các rãnh tụt nhanh là chớp mắt bình thường — quá ngắn nên không phạt. Nhưng khi EAR tụt xuống và ở dưới ngưỡng suốt nhiều giây liên tục (vùng đỏ), risk sẽ tích lũy và kích hoạt cảnh báo."

### Slide 8: Tự hiệu chỉnh & Giao diện
**Lời dẫn:**
"Đây là điểm nhấn sáng tạo nhất của hệ thống: **Plug & Play** — không cần đăng ký khuôn mặt, không cần bước cài đặt nào.

Khi bật ứng dụng, trong vài giây đầu tiên, hệ thống sẽ tự thu thập EAR qua một cửa sổ trượt 60 frame, ghi nhận giá trị mắt mở lớn nhất, rồi tự động tính ngưỡng bằng công thức `ear_thresh = max(0.12, dynamic_ear_open × 0.60)`. Con số 0.12 là sàn an toàn — dùng cho trường hợp đeo kính râm mà camera bắt EAR rất thấp, hệ thống sẽ chuyển sang chế độ Sunglasses Mode.

*(Trỏ vào bảng ví dụ)*
Nhìn bảng ví dụ: Người mắt to có EAR mở max là 0.35 → ngưỡng tự động 0.21. Người mắt híp chỉ 0.22 → ngưỡng giảm xuống 0.13. Nhờ vậy, cùng một hệ thống mà hoạt động chính xác với bất kỳ ai.

Bên dưới là mô phỏng giao diện Desktop: phía trên là Camera Feed, phần giữa hiển thị LED trạng thái, chỉ số EAR, MAR và Risk Score. Phía dưới là bảng log ghi nhận mọi sự kiện cảnh báo theo thời gian thực."

*(Chuyển mic cho Thành viên 3)*

---

## 👨‍💻 THÀNH VIÊN 3: Mô phỏng, Kết quả & Demo (Slide 9 - 12)

### Slide 9: Risk Timeline — Mô phỏng tích lũy rủi ro
**Lời dẫn:**
"Cảm ơn bạn. Để mọi người hình dung rõ hơn cách Risk Engine hoạt động, nhóm em đã xây dựng một bộ mô phỏng tương tác ngay trên slide này.

*(Bắt đầu demo từng nút một trên slide)*
- Đầu tiên, nhấn nút **'Chớp mắt'** — đây là chớp mắt bình thường, chỉ cộng có 3 điểm risk rồi tự decay ngay về 0. Nhấn liên tục nhiều lần cũng không vượt ngưỡng cảnh báo — chứng tỏ hệ thống không báo sai khi chớp mắt.
- Tiếp theo, nhấn **'Ngáp 1 cái'** — cộng 25 điểm. Nhìn trên biểu đồ, risk nhảy lên rồi từ từ decay trở lại. Nếu chỉ ngáp 1 cái thì chưa tới mức cảnh báo.
- Nhấn **'Gật gù'** — cộng 30 điểm. Giờ nếu tài xế vừa ngáp vừa gật gù, risk sẽ tích lũy lên tới vùng SUSPECTED (vàng cam) ở mức 50.
- Cuối cùng, nhấn **'Microsleep'** — risk nhảy thẳng lên 100, vào vùng đỏ CONFIRMED, âm thanh cảnh báo kích hoạt tức thì.
- Nhấn **'Reset'** để quan sát: risk tự giảm mượt mà về 0 nhờ decay luôn hoạt động.

Đây chính là điểm khác biệt lớn nhất so với hệ thống cũ: risk không bị nghẽn lại, luôn tự phục hồi khi tài xế tỉnh táo trở lại."

### Slide 10: Pipeline xử lý 1 Frame
**Lời dẫn:**
"Khi app chạy, yêu cầu khắt khe nhất là độ trễ. App mà trễ thì gật gù xong 1 lúc mới báo thì xe đã đâm rồi. 

*(Click lần lượt từng bước trên pipeline)*
Bọn em đo lường Pipeline của mọi frame ảnh gồm 6 bước:
1. **Camera** — Đọc frame 960×720, flip ngang để hiển thị giống gương
2. **CLAHE** *[Phát âm: Cờ-la-hê]* — Cân bằng độ tương phản thích ứng, giúp hệ thống vẫn nhìn rõ mặt khi trời tối hoặc ánh sáng loang lổ
3. **FaceMesh** — MediaPipe trả về 478 landmark cho mỗi khuôn mặt, hệ thống tự chọn mặt lớn nhất ở nửa trái khung hình làm tài xế
4. **Metrics** — Tính EAR, MAR, PERCLOS, và Pitch/Yaw/Roll. EAR tự hiệu chỉnh ngưỡng
5. **Risk Engine** — Đánh giá toàn bộ tín hiệu, tích lũy risk, áp dụng Veto Rules và decay
6. **Alert** — Risk ≥ 50 thì cảnh báo sớm (LED cam), Risk ≥ 85 thì xác nhận buồn ngủ (LED đỏ + phát âm thanh)

Tất cả 6 bước này chỉ mất **~30 mili-giây** trên CPU laptop thường, tương đương **33 FPS** — vượt mức mượt mà cho ứng dụng realtime."

### Slide 11: Kết quả thử nghiệm & Hướng phát triển
**Lời dẫn:**
"Nhóm đã tiến hành tự nghiệm thu với **24 kịch bản test** mô phỏng các tình huống lái xe thực tế.

*(Trỏ vào danh sách kết quả bên trái)*
Tất cả đều PASS:
- Nhắm mắt 1 giây → Risk nhảy thẳng lên 100, cảnh báo tức thì
- Ngáp liên tục hơn 1 giây → +25 risk, đúng kịch bản
- Gật đầu hơn 30 độ kèm nhắm mắt → +30 risk
- **Chớp mắt bình thường → KHÔNG báo sai** — đây là điểm rất quan trọng
- **Hát theo nhạc, cười lớn → KHÔNG bị nhận nhầm là ngáp** — nhờ ngưỡng MAR 0.60 và yêu cầu liên tục 1 giây
- **Phanh gấp, ngước đầu → KHÔNG báo sai** — nhờ Veto Rules
- Risk tự phục hồi về 0 sau khi tài xế tỉnh lại
- Đeo kính râm → hệ thống tự chuyển Sunglasses Mode

*(Click vào các mục hạn chế bên phải để mở accordion)*
Về hướng phát triển, nhóm nhận thấy 3 điểm cần cải thiện chính:
- Hiện tại chỉ chạy trên Windows do dùng winsound API — có thể thay bằng pygame.mixer để hỗ trợ đa nền tảng
- Chưa có module ghi log dữ liệu risk ra file — để phân tích sau chuyến đi
- Chưa có module phát hiện xao lãng (nhìn sang bên quá lâu)
- Tương lai có thể gửi cảnh báo về điện thoại qua MQTT hoặc Firebase cho quản lý đội xe
- Tích hợp camera hành trình qua RTSP stream"

### Slide 12: Demo trực tiếp & Hỏi đáp
**Lời dẫn:**
"Dạ phần báo cáo mô hình, logic và kết quả của dự án tới đây là hết. Mọi thứ trên slide cũng chỉ là mô phỏng giả lập. Giờ đây kính mời cô và ban hội đồng theo sát hướng nhìn lên cửa sổ app thật của nhóm.

*(Bật cửa sổ terminal gõ `python anti_sleepy/main.py`)*

Nhóm sẽ demo trực tiếp 4 tình huống:
1. **Khởi động → Tự hiệu chỉnh:** Ngay khi bật, hệ thống tự thu thập EAR và tính ngưỡng trong vài giây đầu, không cần đăng ký gì cả.
2. **Nhắm mắt liên tục → Risk tăng → Cảnh báo:** Em sẽ nhắm mắt khoảng 1 giây để mọi người nghe tiếng cảnh báo vang lên.
3. **Ngáp 1 cái → +25 risk → Decay về 0:** Em sẽ giả ngáp, risk tăng lên rồi tự trôi về 0 sau vài giây.
4. **Hát / Cười → Không báo sai:** Em sẽ há miệng liên tục như nói chuyện hoặc cười to — hệ thống sẽ không nhận nhầm là ngáp.

Xin cảm ơn cô và các bạn đã lắng nghe!"

---

## 📋 PHỤ LỤC: Bảng tham chiếu nhanh cho Q&A

| Câu hỏi thường gặp | Câu trả lời gợi ý |
|---|---|
| EAR là gì? Của ai? | Eye Aspect Ratio — Soukupová & Čech (2016), CVWW |
| Tại sao MAR = 0.60 mà không thấp hơn? | Test thực tế: 0.45 quá nhạy, hát/cười đều chạm, nên chọn 0.60 + yêu cầu liên tục 1 giây |
| Hysteresis là gì? | "Cơ chế trễ" — đã thay bằng Risk Engine tích lũy, mạnh hơn nhiều |
| Sao không dùng Deep Learning? | CPR laptop không đủ GPU, MediaPipe đủ mạnh; có thể upgrade ArcFace sau |
| Kính râm thì sao? | EAR rất thấp → ngưỡng chạm sàn 0.12 → chuyển Sunglasses Mode, phát hiện qua gật gù |
| Risk bị nghẽn thì sao? | Decay −1.0/frame LUÔN hoạt động, nghĩa là risk luôn tự giảm — đã test chống nghẽn |
| PERCLOS là gì? | Percentage of Eye Closure — tỷ lệ % mắt nhắm trong cửa sổ 90 frame (~3 giây). >30% → +2.0 risk/frame |
| Veto Rules là gì? | Nếu tài xế ngước >25° hoặc quay >30° → tắt EAR penalty chống báo sai (phanh gấp, nhìn gương) |
| Tại sao không cần đăng ký? | Hệ thống tự hiệu chỉnh EAR = 60% × max(EAR) trong rolling window 60 frame |
| FPS bao nhiêu? | ~33 FPS trên CPU laptop Intel i5, trễ ~30ms/frame |
| Có test bao nhiêu scenario? | 24 kịch bản test đều PASS — từ microsleep, hát, cười, phanh gấp, ngước đầu, kính râm |

> **Lưu ý phát âm quan trọng:**
> - **MediaPipe**: Mê-đi-a-pai
> - **PERCLOS**: Pơ-clốt
> - **Hysteresis**: Hít-tơ-ri-sít (cơ chế trễ — đã thay bằng Risk Engine)
> - **CLAHE**: Cờ-la-hê
> - **solvePnP**: Xôn-vờ-pi-en-pi
> - **Veto**: Vi-tâu (quyền phủ quyết)
> - **Pitch**: Pích (góc gật trước/sau)
> - **Yaw**: Yoo (góc quay trái/phải)
> - **Threshold**: Th-rét-hâu (ngưỡng giới hạn)
> - **Decay**: Đi-kây (suy giảm dần)
