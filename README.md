# NodeTrail: học tiếng Anh (IELTS) cho người Việt

**Ứng dụng học tiếng Anh biết bạn đang ở đâu và dẫn bạn đi tiếp.** Linh vật: **Sena**, chú khỉ đồng hành học tập.

NodeTrail kiểm tra trình độ của bạn, dựng lộ trình ngữ pháp theo cấp độ CEFR (A1–C1), rồi chạy vòng lặp
**đánh giá → học → luyện tập → điều chỉnh → ôn tập** cho cả bốn kỹ năng IELTS. Người học đầu tiên là chủ dự án
(thi IELTS mùa hè 2027, mục tiêu 6.5), sau đó là bạn bè và gia đình, miễn phí.

## Học được gì

| Kỹ năng | Trong ứng dụng | Trạng thái |
|---|---|---|
| Kiểm tra trình độ và lộ trình | Bài kiểm tra trình độ, bản đồ cột mốc ngữ pháp (`/kiem-tra`, `/lo-trinh`), mỗi cột mốc có các phần nhỏ ẩn; làm sai thì truy ngược về phần nền tảng yếu | Đã chạy; câu hỏi là bản nháp chờ duyệt |
| Từ vựng | 3.663 từ (NGSL/NAWL và 130 từ tự soạn), thẻ ôn tập theo FSRS, bốn kiểu câu hỏi chấm bằng đáp án (`/tu-vung`) | Đã chạy; danh sách là bản nháp chờ kiểm tra mẫu |
| Ngữ pháp | Bài học kiểu lớp học: giọng đọc tiếng Anh, phụ đề Anh–Việt, bảng trắng, câu hỏi kiểm tra giữa bài (`/hoc/...`); luyện tập theo cột mốc (`/on-tap/...`) | Đã có trình phát và một bài mẫu; bài từ giáo trình mở đang làm |
| Viết | Task 2 và Task 1: lỗi ngữ pháp (LanguageTool, ERRANT), nhận xét theo bốn tiêu chí có trích dẫn, khoảng band, viết lại đoạn, cụm từ hay thành thẻ ôn (`/viet`) | Đã chạy; cổng đo chờ bài viết có điểm giám khảo |
| Phát âm | Đọc to câu mẫu, kiểm tra chất lượng bản ghi, chấm từng âm người Việt hay nhầm (phụ âm cuối, th, s/sh, r/l, nguyên âm dài…) (`/phat-am`) | Đã chạy, chỉ cho chủ dự án; chưa đánh dấu đúng/sai cho đến khi đo tỉ lệ báo nhầm |
| Đọc và Nghe | Bài đọc từ nguồn mở (Simple English Wikipedia, OpenStax), câu hỏi kiểu IELTS được tạo sẵn, kiểm chứng mù và duyệt tay; nghe bằng giọng máy | Đang làm (giai đoạn 4) |
| Nói | Part 1–3, bản ghi chép lời nói, nhận xét ngữ pháp, từ vựng, phát âm, độ trôi chảy | Đã có đặc tả; chưa làm |

## Nguyên tắc: AI giải thích, bộ máy quyết định

- **Bộ máy học tập** quyết định học gì tiếp. Nó gồm các hàm thuần, có kiểm thử:
  - BKT đo mức nắm vững từng phần;
  - luật trên đồ thị cột mốc xếp trình độ và truy ngược gốc lỗ hổng;
  - FSRS lên lịch ôn.

  Mỗi quyết định có dấu vết bằng tiếng Việt (bảng «Vì sao?»).
- **Công cụ và mô hình nhỏ chấm đúng sai:** đáp án, LanguageTool, mô hình chấm band, mô hình nhận dạng âm. Mô hình
  ngôn ngữ lớn chỉ giải thích và tạo nội dung, luôn kèm trích dẫn.
- **Cổng kiểm chứng:** mỗi câu hỏi được tạo ra phải được một mô hình **khác họ** trả lời mù, chỉ từ đoạn văn gốc.
  Câu chưa qua không bao giờ đến tay người học. Cổng giảm lỗi chứ không loại hết, nên chủ dự án vẫn duyệt tay, và tỉ
  lệ bắt lỗi được đo bằng lỗi cài sẵn.
- **Không khen tốc độ hay chuỗi ngày học.** Sena chỉ khen khi bạn thật sự nắm vững.

## Lộ trình

Chi tiết và cổng đo của từng giai đoạn: [`docs/v2/plan-english-pack.md`](docs/v2/plan-english-pack.md). Việc chủ dự
án cần làm: [`dolater.md`](dolater.md).

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| 0 | Nền móng: một lệnh chạy cả hệ thống, hộp cát chạy mã, CI chạy toàn bộ | Xong |
| 1 | Lộ trình, kiểm tra trình độ, từ vựng, ngữ pháp | Đã làm; chờ duyệt câu hỏi và đo độ chính xác xếp trình độ |
| 2 | Viết (Task 2, rồi Task 1) | Đã làm (2.1–2.5); cổng đo chờ bài viết có điểm giám khảo |
| 3 | Phát âm | Đã làm (3.1–3.5a); cổng đo chờ 50–100 bản ghi có nhãn của chủ dự án |
| 4 | Đọc và Nghe | Đang làm: kế hoạch 6 điểm kiểm tra đã duyệt; công cụ lấy bài đọc và bộ tạo câu hỏi kèm kiểm chứng mù đã có |
| 5 | Nói, và mở cho người dùng thử | Đã có đặc tả |

## Hiện trạng trung thực

- **Kiểm thử** (đo cục bộ ngày 18/11/2026): 2.092 kiểm thử API đạt, 22 bị bỏ qua; ruff và mypy sạch; 178 kiểm thử web
  đạt; kiểm thử trình duyệt (Playwright) chạy trong CI trên toàn bộ hệ thống.
- **Nội dung còn là bản nháp:** câu hỏi ngữ pháp, danh sách từ, bài học mẫu và âm chuẩn của câu đọc đều chờ chủ dự án
  duyệt. Những gì chưa duyệt chỉ chủ dự án thấy, và được ghi rõ «Bản nháp».
- **Đã đo:**
  - Bộ kiểm tra câu hỏi (Ernie, miễn phí) bắt 20/20 lỗi cài sẵn, báo nhầm 0/20.
  - Mô hình nhận dạng âm trên speechocean762: tương quan với điểm chuyên gia 0,59; AUC tìm âm sai 0,86. Một ngưỡng
    chung vẫn báo nhầm 79–89%, nên chưa đánh dấu âm nào là sai.
- **Chưa đo:** độ chính xác xếp trình độ trên người thật, độ khớp band với giám khảo, tỉ lệ báo nhầm phát âm trên giọng
  người Việt, hiệu quả học. Tham số BKT là giá trị khởi đầu, chưa hiệu chỉnh trên dữ liệu thật.

## Chạy thử

Cần Docker và Git. Hướng dẫn đầy đủ: [`docker/LOCAL.md`](docker/LOCAL.md).

1. Sao chép `.env.example` thành `.env`, điền `API_KEY` và `RUNNER_TOKEN` (hai chuỗi ngẫu nhiên dài). Không commit
   tệp này.
2. Chạy cả hệ thống:

   ```bash
   docker compose up -d --build --wait
   ```

3. Mở <http://localhost:3000>.

Các dịch vụ nặng là tùy chọn, mỗi lần bật một cái nếu máy ít bộ nhớ:
- `writing`: LanguageTool;
- `scoring`: chấm band;
- `speech`: giọng đọc Piper;
- `pronunciation`: nhận dạng âm.

Kiểm thử API (chỉ cần cơ sở dữ liệu):

```bash
docker compose up -d --wait db
```

```bash
cd apps/api && uv sync --locked && uv run pytest -q
```

## Các môn khác (sau này)

NodeTrail bắt đầu là gia sư cho mọi môn: Deep Research trên giáo trình mở, khóa Python và thống kê, tải tài liệu
lên. Bộ máy đó vẫn còn trong mã nguồn (`apps/api/app/research/`, `app/sources/`, `data/courses/`) và là nền cho các
môn khác về sau. Hiện tại, mọi việc tập trung vào tiếng Anh. Kế hoạch cũ: [`docs/v2/plan-m0-m1.md`](docs/v2/plan-m0-m1.md)
(đã thay thế).

## Nguồn gốc và ghi công

Dự án tiếp nối bản dựng NodeTrail của đội **Sena Empire** trong cuộc thi hackathon 2026 (5 thành viên, repo nhóm
`thienandinh29/SenaEmpire36`, đã đóng băng). Mã kế thừa từ bản đó là công sức của cả đội. Tài liệu cuộc thi nằm trong
[`docs/archive/contest-2026/`](docs/archive/contest-2026/).

Nguồn nội dung mở, mỗi nguồn ghi giấy phép trong `data/sources/english-candidates.yaml`:
- Từ vựng NGSL và NAWL (CC BY-SA 4.0, Browne, Culligan & Phillips).
- Giáo trình ngữ pháp mở:
  - Bissonnette (CC BY-NC 4.0);
  - Al Haider (CC BY 4.0);
  - *Explorations* (CC BY-NC-SA 4.0);
  - Hall & Wallace (CC BY-NC-SA);
  - *A Digital Workbook for Beginning ESOL* (CC BY 4.0).
- Bài đọc:
  - Simple English Wikipedia (CC BY-SA 4.0);
  - OpenStax (CC BY-NC-SA 4.0).
- Giọng đọc Piper `en_GB-cori-high`.

Các nguồn NC chỉ dùng cho học tập, không thương mại.

## Giấy phép

- **Mã nguồn** (mọi thứ ngoài `data/` và `data-sa/`): [Apache-2.0](LICENSE). Xem thêm [NOTICE](NOTICE).
- **Dữ liệu** (`data/`): [CC BY-NC-SA 4.0](data/LICENSE.md), vì một phần dữ liệu phát sinh từ giáo trình có cùng giấy
  phép.
- **Từ vựng nhập từ NGSL/NAWL** (`data-sa/`): [CC BY-SA 4.0](data-sa/LICENSE.md), ghi công Browne, Culligan & Phillips.

Cả đội Sena Empire đã đồng ý lựa chọn giấy phép này (theo lời chủ repo, 2026-11-10; chưa có văn bản xác nhận trong
repo).
