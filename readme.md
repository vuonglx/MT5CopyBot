# Bot Copy Trade cho MetaTrader 5

Đây là một công cụ copy trade mạnh mẽ được viết bằng Python, giúp bạn tự động sao chép các giao dịch từ một tài khoản MT5 (Master) sang một tài khoản MT5 khác (Slave) với nhiều tính năng quản lý rủi ro nâng cao.



## Tính năng Chính ✨

### Giao diện & Theo dõi
* **Giao diện Trực quan:** Dễ dàng cài đặt và quản lý mọi thứ trên một cửa sổ duy nhất.
* **Dashboard Thời gian thực:** Theo dõi Vốn, Lời/Lỗ ($ và %), và Số lệnh đang mở của tài khoản Slave ngay trên giao diện.
* **Quản lý Profile:** Lưu và chuyển đổi giữa các cặp tài khoản Master-Slave khác nhau một cách nhanh chóng.
* **Thông báo Telegram:** Nhận thông báo tức thì về các hoạt động quan trọng.

### Sao chép Thông minh & Tối ưu
* **Cơ chế Tối ưu:** Bot chỉ giám sát Master và chỉ kết nối đến Slave khi có thay đổi, giúp giảm độ trễ và hoạt động hiệu quả.
* **Tính Lot theo Tỷ lệ Vốn:** Tự động điều chỉnh khối lượng giao dịch phù hợp với số vốn của bạn.
* **Đồng bộ SL/TP:** Tự động cập nhật Stop Loss và Take Profit theo tài khoản Master.
* **Ánh xạ Symbol:** Dễ dàng sao chép giữa các sàn có tên sản phẩm khác nhau (ví dụ: `XAUUSD` và `GOLD`).

### Quản lý Rủi ro Toàn diện 🛡️
1.  **Dừng theo P/L:** Tự động dừng bot và đóng mọi lệnh khi tài khoản đạt ngưỡng Lời/Lỗ mong muốn.
2.  **Giới hạn Volume Tối đa:** Kiểm soát rủi ro trên từng lệnh, không cho phép vào lệnh với khối lượng quá lớn so với vốn.
3.  **Giãn Lệnh:** Tránh sao chép dồn dập khi Master nhồi lệnh, chỉ vào lệnh khi có khoảng cách giá đủ an toàn.
4.  **Giới hạn Số lệnh:** Đảm bảo số lệnh trên tài khoản của bạn không bao giờ nhiều hơn tài khoản Master.
5.  **Đồng bộ Toàn diện:** Nếu Master đóng hết lệnh, bot sẽ tự động đóng tất cả các lệnh còn sót lại trên tài khoản của bạn.

## Yêu cầu
1.  **Python 3.9+** đã được cài đặt.
2.  **Phần mềm MetaTrader 5** (bản desktop) đã được cài đặt và đang chạy.
3.  Các thư viện Python cần thiết.

## Hướng dẫn Cài đặt & Sử dụng 🚀

### Bước 1: Cài đặt Thư viện
Mở Command Prompt (CMD) hoặc Terminal và chạy lệnh sau:
```bash
pip install MetaTrader5 requests
```

### Bước 2: Cấu hình Bắt buộc trong Code
Mở file bot (`.py`) bằng một trình soạn thảo code (như VS Code, Notepad++). Tìm và **thay đổi đường dẫn** trong dòng sau để trỏ đến file `terminal64.exe` của bạn:
```python
MT5_TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe" 
```

### Bước 3: Chạy Bot
Lưu file lại và chạy bot bằng lệnh:
```bash
python ten_file_bot_cua_ban.py
```

### Bước 4: Sử dụng Giao diện
1.  **Điền thông tin:** Nhập đầy đủ thông tin Login, Mật khẩu, Server cho cả hai tài khoản Master và Slave.
2.  **Tạo Profile:** Đặt một tên cho cấu hình của bạn (ví dụ: "Copy từ A sang B") và nhấn **Lưu**.
3.  **Tùy chỉnh Rủi ro:** Điều chỉnh các thông số trong khung "Quản lý Rủi ro" theo ý muốn.
4.  **Bắt đầu:** Nhấn nút **"Bắt đầu Bot"**. Nhật ký sẽ bắt đầu chạy và Dashboard sẽ cập nhật trạng thái.

## ⚠️ Lưu ý Quan trọng
* Phần mềm MetaTrader 5 **bắt buộc phải đang chạy** trên máy tính thì bot mới có thể kết nối.
* Luôn **thử nghiệm trên tài khoản Demo** trước khi sử dụng trên tài khoản thật.
* Sử dụng công cụ với rủi ro của riêng bạn. Tác giả không chịu trách nhiệm cho bất kỳ tổn thất tài chính nào.