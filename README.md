# NodeTrail: học tiếng Anh (IELTS) cho người Việt

**Ứng dụng học tiếng Anh biết bạn đang ở đâu và dẫn bạn đi tiếp.** Linh vật: **Sena**, chú khỉ đồng hành học tập.

NodeTrail kiểm tra trình độ của bạn, dựng lộ trình ngữ pháp theo cấp độ CEFR (A1–C1), rồi chạy vòng lặp
**đánh giá → học → luyện tập → điều chỉnh → ôn tập** cho cả bốn kỹ năng IELTS. Người học đầu tiên là chủ dự án
(thi IELTS mùa hè 2027, mục tiêu 7.0), sau đó là bạn bè và gia đình, miễn phí.

## Học được gì

| Kỹ năng | Trong ứng dụng | Trạng thái |
|---|---|---|
| Hôm nay và bản đồ kỹ năng | Mỗi ngày 3–5 việc nên làm, mỗi việc có «Vì sao?», giữ nguyên trong ngày và đánh dấu việc đã luyện, kèm thời gian ước tính; lịch các ngày có học trong tuần (không đếm chuỗi ngày) (trang chủ); bản đồ 17 kỹ năng thi IELTS và các nền tảng chúng cần, kèm mức chắc chắn của từng ước lượng (`/ban-do`) | Đã chạy; Viết được đo từ bài viết, các kỹ năng khác chờ bài luyện |
| Kiểm tra trình độ và lộ trình | Bài kiểm tra trình độ, bản đồ cột mốc ngữ pháp (`/kiem-tra`, `/lo-trinh`), mỗi cột mốc có các phần nhỏ ẩn; làm sai thì truy ngược về phần nền tảng yếu | Đã chạy; câu hỏi là bản nháp chờ duyệt |
| Từ vựng | 3.663 từ (NGSL/NAWL và 130 từ tự soạn), thẻ ôn tập theo FSRS, bốn kiểu câu hỏi chấm bằng đáp án (`/tu-vung`); tra từ trong danh sách bằng tiếng Anh hoặc tiếng Việt (`/tu-dien`) | Đã chạy; danh sách là bản nháp chờ kiểm tra mẫu |
| Ngữ pháp | Bài học kiểu lớp học: giọng đọc tiếng Anh, phụ đề Anh–Việt, bảng trắng, câu hỏi kiểm tra giữa bài (`/hoc/...`); luyện tập theo cột mốc (`/on-tap/...`) | Đã có trình phát và một bài mẫu; bài từ giáo trình mở đang làm |
| Viết | Task 2 và Task 1: lỗi ngữ pháp (LanguageTool, ERRANT), nhận xét theo bốn tiêu chí có trích dẫn, khoảng band, viết lại đoạn, cụm từ hay thành thẻ ôn; mỗi bài viết cập nhật năm kỹ năng Viết trên bản đồ (`/viet`) | Đã chạy; cổng đo chờ bài viết có điểm giám khảo |
| Phát âm | Đọc to câu mẫu, kiểm tra chất lượng bản ghi, chấm từng âm người Việt hay nhầm (phụ âm cuối, th, s/sh, r/l, nguyên âm dài…) (`/phat-am`) | Đã chạy, chỉ cho chủ dự án; chưa đánh dấu đúng/sai cho đến khi đo tỉ lệ báo nhầm |
| Đọc và Nghe | Bài đọc từ nguồn mở (Simple English Wikipedia, OpenStax), câu hỏi kiểu IELTS được tạo sẵn, kiểm chứng mù rồi giáo viên duyệt; nghe bằng giọng máy | Đã chạy (giai đoạn 4): 30 bài đọc OpenStax, luyện Đọc và bài thi 20 phút (`/doc`), nghe chép chính tả, nghe cả bài và nói đuổi (`/nghe`, `/noi-duoi`); chỉ đưa câu hỏi đạt mức Silver, nên mới có rất ít câu để luyện cho đến khi duyệt xong |
| Nói | Part 1–3, bản ghi chép lời nói, nhận xét ngữ pháp, từ vựng, phát âm, độ trôi chảy | Đã chạy phần đầu (bước 5.4a): bài thi nói thử đủ ba phần với giám khảo đọc câu hỏi, đúng thời gian, ghi âm từng câu và nghe lại (`/noi/thi`, chỉ chủ dự án); máy chép lại lời nói bằng Whisper small.en chạy trên máy của dự án (bước 5.1) và đếm tốc độ nói, số lần ngắt giữa và trong mệnh đề, từ đệm (bước 5.2, chỉ đếm, không chấm điểm); đã có luyện nói có hướng dẫn (`/noi/luyen`, bước 5.4b: gợi ý cách xây dựng ý trước khi nói, nói lại cùng một câu tối đa 3 lần với thời gian ngắn dần, số đo từng lần cạnh nhau), gợi ý ngữ pháp (có thể sai), kiểm tra cụm học thuộc và số đo vốn từ do công cụ chạy trên máy dự án (bước 5.3a); nhận xét do mô hình viết (5.3b) chờ chủ dự án chốt lời đồng ý |

## Nguyên tắc: AI giải thích, bộ máy quyết định

- **Bộ máy học tập** quyết định học gì tiếp. Nó gồm các hàm thuần, có kiểm thử:
  - BKT đo mức nắm vững từng phần;
  - luật trên đồ thị cột mốc xếp trình độ và truy ngược gốc lỗ hổng;
  - FSRS lên lịch ôn.

  Mỗi quyết định có dấu vết bằng tiếng Việt (bảng «Vì sao?»).
- **Công cụ và mô hình nhỏ chấm đúng sai:** đáp án, LanguageTool, mô hình chấm band, mô hình nhận dạng âm. Mô hình
  ngôn ngữ lớn chỉ giải thích và tạo nội dung, luôn kèm trích dẫn.
- **Cổng kiểm chứng:** mỗi câu hỏi được tạo ra phải được một mô hình **khác họ** trả lời mù, chỉ từ đoạn văn gốc.
  Câu chưa qua không bao giờ đến tay người học. Cổng giảm lỗi chứ không loại hết, nên tỉ lệ bắt lỗi được đo bằng lỗi
  cài sẵn và bằng nhãn của giáo viên.
- **Người làm ứng dụng không phải là người quyết định đúng sai.** Chủ dự án là người học, người làm và người thử, không
  phải người chấm tiếng Anh. Mỗi nhãn ghi rõ nguồn: **Vàng** (giáo viên, giám khảo, dữ liệu do chuyên gia gán nhãn),
  **Bạc** (hai kiểm tra độc lập khớp nhau), **Đồng** (một nguồn). Cổng đo chỉ chấp nhận nhãn Vàng; giáo viên gán nhãn
  qua một đường link riêng (`/kiem-duyet`). Tiến bộ được đo bằng bài thi độc lập mỗi 4 tuần, không bằng ước lượng của
  chính NodeTrail.
- **Không khen tốc độ hay chuỗi ngày học.** Sena chỉ khen khi bạn thật sự nắm vững.

## Lộ trình

Chi tiết và cổng đo của từng giai đoạn: [`PLAN.md`](PLAN.md). Ứng dụng làm gì và giữ những quy tắc nào: [`SPEC.md`](SPEC.md).
Cách làm việc với dự án (cho người và AI agent): [`AGENTS.md`](AGENTS.md). Việc chủ dự án cần làm: [`dolater.md`](dolater.md).

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| 0 | Nền móng: một lệnh chạy cả hệ thống, hộp cát chạy mã, CI chạy toàn bộ | Xong |
| 1 | Lộ trình, kiểm tra trình độ, từ vựng, ngữ pháp | Đã làm; chờ duyệt câu hỏi và đo độ chính xác xếp trình độ |
| 2 | Viết (Task 2, rồi Task 1) | Đã làm (2.1–2.8); cổng đo chờ bài viết có điểm giám khảo |
| 3 | Phát âm | Đã làm (3.1–3.7c, cả phát âm từng từ vựng); cổng đo chờ nhãn của người có chuyên môn ngữ âm trên 50–100 bản ghi |
| 4 | Đọc và Nghe | Đang làm: Đọc và Nghe đã chạy; 30 bài đọc OpenStax, 291 câu hỏi trên bản bài đọc hiện tại (52 câu đã kiểm chứng mù, chờ duyệt); còn bài kiểm tra lỗi cài sẵn và báo cáo cổng đo |
| Song song | Hệ thống kiểm chứng (nhãn Vàng/Bạc/Đồng, cổng duyệt cho giáo viên, nghiên cứu tiến bộ cá nhân); hai bản đồ và «Hôm nay» | Đã làm |
| 5 | Nói, và mở cho người dùng thử | Đang làm: bài thi nói thử (5.4a) đã chạy |

## Hiện trạng trung thực

- **Kiểm thử** (đo cục bộ ngày 20/11/2026): 2.290 kiểm thử API đạt, 22 bị bỏ qua; ruff và mypy sạch; 240 kiểm thử web
  đạt; 39 kiểm thử trình duyệt (Playwright) đạt trên toàn bộ hệ thống, cũng chạy trong CI. Ba cổng mô phỏng chạy trong
  CI: xếp trình độ, lộ trình tiếng Anh, và bộ gợi ý việc học (đúng 100% ở cả hai kịch bản).
- **Nội dung còn là bản nháp:** câu hỏi ngữ pháp, danh sách từ, bài học mẫu, âm chuẩn của câu đọc, liên kết giữa kỹ năng
  thi và nền tảng, và luật chấm kỹ năng Viết đều chờ giáo viên kiểm tra. Những gì chưa duyệt chỉ chủ dự án thấy, và được ghi rõ «Bản nháp».
- **Đã đo:**
  - Bộ kiểm tra câu hỏi (Ernie, miễn phí) bắt 20/20 lỗi cài sẵn, báo nhầm 0/20.
  - Mô hình nhận dạng âm trên speechocean762: tương quan với điểm chuyên gia 0,59; AUC tìm âm sai 0,86. Một ngưỡng
    chung vẫn báo nhầm 79–89%, nên chưa đánh dấu âm nào là sai.
- **Chưa đo:** độ chính xác xếp trình độ trên người thật, độ khớp band với giám khảo, tỉ lệ báo nhầm phát âm trên giọng
  người Việt, hiệu quả học (chờ bài thi nền của chủ dự án). Nghiên cứu «quên gì sau một tuần» (FORGET-001) đang thu dữ
  liệu (`research/`). Tham số BKT là giá trị khởi đầu, chưa hiệu chỉnh trên dữ liệu thật.

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
môn khác về sau. Phần đó hiện **đóng băng**: không phát triển thêm trước kỳ thi của chủ dự án, mọi việc tập trung vào
tiếng Anh. Kế hoạch cũ: [`docs/v2/plan-m0-m1.md`](docs/v2/plan-m0-m1.md)
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
