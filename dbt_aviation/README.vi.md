# Dự án dbt: `aviation` (bản tiếng Việt)

**dbt làm gì ở đây?** `db_load.py` đã đổ dữ liệu **thô** từ AirLabs vào PostgreSQL. dbt lấy dữ liệu thô đó, **làm sạch**, **bỏ dòng trùng**, **lọc rác**, rồi tạo ra các **bảng báo cáo gọn gàng**. Sau đó dbt **tự kiểm tra (test)** xem dữ liệu có đúng không.

## Luồng dữ liệu

```
AirLabs API ──► db_load.py ──► Bảng THÔ: public.airports (23.383 dòng), public.airlines (6.600 dòng)
                                     │
                                     ▼  bước làm sạch (staging)
                         staging.stg_airports (23.291 dòng: đã bỏ 92 dòng trùng)
                         staging.stg_airlines (6.600 dòng)
                                     │
                                     ▼  bước tạo bảng báo cáo (marts)
                   marts.airports_by_country (243 quốc gia)
                   marts.vn_airports         (28 sân bay thương mại Việt Nam)
```

Hình dung như **nhà bếp**: bảng thô là **rau mới mua về** → staging là **rửa, nhặt, bỏ lá hỏng** → marts là **món ăn đã nấu xong**, dọn ra bàn (báo cáo).

---

## Từng file làm gì

### 1. Nhóm cấu hình: cho dbt biết chạy thế nào

**[dbt_project.yml](dbt_project.yml)**: "bảng điều khiển" của dự án.
- Khai báo các model (file SQL) nằm trong thư mục `models/`.
- Thư mục `staging` → tạo **view** (bảng ảo, không tốn dung lượng, luôn lấy dữ liệu mới nhất từ bảng thô).
- Thư mục `marts` → tạo **table** (bảng thật, tính sẵn, xem báo cáo nhanh).

**[profiles.yml](profiles.yml)**: thông tin **kết nối database**.
- Kết nối tới PostgreSQL ở `localhost:5432`, database `aviation`, tài khoản `postgres`.
- Mật khẩu **không ghi trong file**: dbt đọc từ biến `PGPASSWORD` trong file `.env`, nên đưa code lên GitHub vẫn an toàn.

**[macros/generate_schema_name.sql](macros/generate_schema_name.sql)**: một **macro** (hàm tái sử dụng).
- Mặc định dbt đặt tên schema rất dài (`public_staging`). Macro này sửa thành tên gọn: `staging` và `marts`.

**[dbt.cmd](dbt.cmd)**: **lệnh tắt** để chạy dbt.
- Tự đọc mật khẩu từ `.env`, dùng dbt trong `.venv`. Bạn chỉ cần gõ `.\dbt.cmd build`.

### 2. Nhóm staging: làm sạch dữ liệu thô

**[models/staging/_sources.yml](models/staging/_sources.yml)**: khai báo **nguồn dữ liệu** và **bài kiểm tra**.
- Nói cho dbt biết bảng thô ở đâu: `public.airports`, `public.airlines` (do `db_load.py` tạo).
- Đặt test: `airport_id` phải **duy nhất** (`unique`) và **không rỗng** (`not_null`); tên sân bay không được rỗng.
- Test "mã IATA không trùng" để ở mức **cảnh báo** (`warn`): có lỗi thì báo, nhưng không dừng chương trình.

**[models/staging/stg_airports.sql](models/staging/stg_airports.sql)**: **làm sạch bảng sân bay**.
- `trim()` **xóa khoảng trắng thừa** ở đầu/cuối (vd: `" Noi Bai "` → `"Noi Bai"`).
- `upper()` **viết hoa mã** (vd: `sgn` → `SGN`) để so sánh không bị lệch.
- `nullif(..., '')` **ô trống → NULL**, để đếm và kiểm tra cho đúng.
- Đổi tên cột `name` → `airport_name` cho dễ hiểu.
- `DISTINCT ON (...)` **bỏ dòng trùng**: **xóa 92 dòng bị lặp** (vd: sân bay Thọ Xuân `THD` bị ghi 2 lần). Từ 23.383 → **23.291 dòng**.

**[models/staging/stg_airlines.sql](models/staging/stg_airlines.sql)**: **làm sạch bảng hãng bay**.
- Cũng `trim`, viết hoa mã, ô trống → NULL, đổi `name` → `airline_name`.
- Không có dòng nào bị loại (6.600 → 6.600).

### 3. Nhóm marts: bảng báo cáo cuối cùng

**[models/marts/airports_by_country.sql](models/marts/airports_by_country.sql)**: **thống kê sân bay theo quốc gia**.
- Mỗi quốc gia một dòng: tổng số sân bay, bao nhiêu sân bay có mã IATA / ICAO, tỷ lệ % có IATA.
- Kết quả: **243 quốc gia**.

**[models/marts/vn_airports.sql](models/marts/vn_airports.sql)**: **danh sách sân bay thương mại Việt Nam**.
- Điều kiện: thuộc Việt Nam (`VN`) + có mã IATA + có mã ICAO.
- Từ 48 dòng của Việt Nam → còn **28 sân bay** (SGN, HAN, DAD, CXR, PQC…).
- Loại bỏ:
  - **4 dòng rác/spam**: `RKM "KM88 onl"`, `XAG` và `XHG` là quảng cáo casino, tọa độ nằm giữa biển.
  - **8 dòng** không có mã IATA (bãi đáp nhỏ).
  - **8 sân bay nhỏ, đã đóng hoặc đang xây** không có mã ICAO (Quảng Trị, Kon Tum, Sóc Trăng…).

**[models/marts/_marts.yml](models/marts/_marts.yml)**: **mô tả và test cho bảng báo cáo**.
- `country_code` phải duy nhất và không rỗng.
- `iata_code` của sân bay Việt Nam phải **duy nhất**. Chính test này **phát hiện ra dòng trùng THD và dòng spam XHG** ở lần chạy đầu tiên, nhờ đó mới biết phải sửa.

### 4. Thư mục tự sinh (không đưa lên GitHub)

- `target/`: SQL dbt đã dịch ra, kết quả chạy, và file của trang tài liệu.
- `logs/`: nhật ký mỗi lần chạy.

---

## Lệnh hay dùng

Mở terminal trong VS Code:

```powershell
cd dbt_aviation
.\dbt.cmd build                          # chạy toàn bộ: tạo bảng + chạy test
.\dbt.cmd show --select vn_airports      # xem nhanh dữ liệu một bảng
.\dbt.cmd docs generate                  # tạo trang tài liệu
.\dbt.cmd docs serve --port 8580         # mở trang tài liệu + sơ đồ tại http://127.0.0.1:8580
```

## Kết quả lần chạy gần nhất

`PASS=15, WARN=1, ERROR=0`: 15 test đạt, 1 cảnh báo, 0 lỗi.

Cảnh báo duy nhất là **222 mã IATA bị trùng trên toàn thế giới**. Đây là đặc điểm của dữ liệu thật (một số mã được dùng lại), không phải lỗi, nên để ở mức cảnh báo thay vì báo lỗi.
