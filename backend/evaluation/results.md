## Q01

**Question:** Thời hạn gia hạn của Orion Enterprise là bao lâu?

**Expected:** 30 ngày kể từ ngày gói dịch vụ hết hạn.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_4
- Citation hits gold: PASS
- Retrieval latency: 1.711 s
- TTFT: 6.702 s
- LLM total: 7.746 s
- E2E: 9.477 s

## Q06

**Question:** Enterprise và Lite khác nhau như thế nào về chu kỳ sao lưu và thời gian lưu bản sao lưu?

**Expected:** Enterprise sao lưu mỗi 6 giờ và giữ 30 ngày; Lite sao lưu mỗi 24 giờ và giữ 7 ngày.

- Retrieval Hit@5: PASS
- First relevant rank: 2
- RR: 0.5
- Citation: doc_21_chunk_10
- Citation hits gold: PASS
- Retrieval latency: 0.625 s
- TTFT: 3.691 s
- LLM total: 4.489 s
- E2E: 13.917 s

## Q09

**Question:** Orion Lite có thời gian gia hạn 30 ngày đúng không?

**Expected:** Không. Orion Lite có thời gian gia hạn 14 ngày; 30 ngày là thời gian gia hạn của Orion Enterprise.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_7,doc_21_chunk_4
- Citation hits gold: PASS
- Retrieval latency: 0.716 s
- TTFT: 7.773 s
- LLM total: 8.768 s
- E2E: 9.493 s

## Q14

**Question:** Một khách hàng Enterprise đã hết hạn gói 10 ngày nhưng chưa gia hạn. Họ có thể tạo workspace mới không?

**Expected:** Không. Enterprise chỉ cho phép tạo workspace mới trong 7 ngày đầu của thời gian gia hạn; ngày thứ 10 đã vượt giới hạn này.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_4
- Citation hits gold: PASS
- Retrieval latency: 0.574 s
- TTFT: 5.879 s
- LLM total: 6.883 s
- E2E: 7.464 s

## Q16

**Question:** Orion Enterprise có giá bao nhiêu mỗi tháng?

**Expected:** Không có thông tin trong tài liệu.

- Retrieval Hit@5: FAIL
- First relevant rank: N/A
- RR: 0.0
- Citation: None
- Citation hits gold: FAIL
- Retrieval latency: 0.42 s
- TTFT: 8.594 s
- LLM total: 9.091 s
- E2E: 9.52 s

## Q02

**Question:** Orion Lite cung cấp bao nhiêu GB dung lượng lưu trữ?

**Expected:** 50 GB cho mỗi tổ chức.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_8
- Citation hits gold: PASS
- Retrieval latency: 1.875 s
- TTFT: 5.349 s
- LLM total: 5.794 s
- E2E: 7.683 s

## Q03

**Question:** Mỗi file tải lên Orion Enterprise được phép có dung lượng tối đa bao nhiêu?

**Expected:** 200 MB.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_5
- Citation hits gold: PASS
- Retrieval latency: 0.467 s
- TTFT: 5.686 s
- LLM total: 6.118 s
- E2E: 6.595 s

## Q04

**Question:** Nếu gói Enterprise vừa hết hạn thì khách hàng còn bao nhiêu ngày để gia hạn?

**Expected:** 30 ngày.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_4
- Citation hits gold: PASS
- Retrieval latency: 0.584 s
- TTFT: 4.897 s
- LLM total: 5.972 s
- E2E: 6.563 s

## Q05

**Question:** Gói nào cho phép một tổ chức có tối đa 250 người dùng đang hoạt động?

**Expected:** Orion Enterprise.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_6
- Citation hits gold: PASS
- Retrieval latency: 0.441 s
- TTFT: 3.856 s
- LLM total: 4.257 s
- E2E: 4.709 s

## Q07

**Question:** Trong thời gian gia hạn Enterprise, khách hàng còn làm được gì và bị hạn chế gì?

**Expected:** Khách hàng vẫn có thể đăng nhập và xem tài liệu đã lưu. Sau 7 ngày đầu của thời gian gia hạn, họ không thể tạo workspace mới.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_4
- Citation hits gold: PASS
- Retrieval latency: 0.409 s
- TTFT: 9.956 s
- LLM total: 10.493 s
- E2E: 16.835 s

## Q08

**Question:** Nếu tôi cần SSO và lưu nhật ký hoạt động ít nhất 6 tháng thì nên dùng gói nào?

**Expected:** Orion Enterprise, vì SSO chỉ có ở Enterprise và Enterprise lưu nhật ký hoạt động 180 ngày.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_13
- Citation hits gold: PASS
- Retrieval latency: 0.456 s
- TTFT: 9.159 s
- LLM total: 10.159 s
- E2E: 10.624 s

## Q10

**Question:** Orion Enterprise chỉ hỗ trợ tối đa 25 thành viên phải không?

**Expected:** Không. Enterprise hỗ trợ tối đa 250 thành viên hoạt động; 25 là giới hạn của Orion Lite.

- Retrieval Hit@5: PASS
- First relevant rank: 3
- RR: 0.3333
- Citation: doc_21_chunk_6,doc_21_chunk_9
- Citation hits gold: PASS
- Retrieval latency: 0.402 s
- TTFT: 4.441 s
- LLM total: 5.052 s
- E2E: 5.461 s

## Q11

**Question:** So sánh khả năng khôi phục dữ liệu của Enterprise và Lite.

**Expected:** Enterprise cho phép yêu cầu khôi phục từ bản sao lưu còn hạn và xử lý yêu cầu tiêu chuẩn trong 8 giờ làm việc. Lite không hỗ trợ yêu cầu khôi phục một bản sao lưu cụ thể; đội vận hành chỉ có thể khôi phục ở cấp hệ thống khi xảy ra sự cố.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_11,doc_21_chunk_10
- Citation hits gold: PASS
- Retrieval latency: 0.553 s
- TTFT: 7.308 s
- LLM total: 9.487 s
- E2E: 14.06 s

## Q12

**Question:** Gói Enterprise có những lợi thế nào về hỗ trợ kỹ thuật so với Lite?

**Expected:** Enterprise hỗ trợ 24/7 và có mục tiêu phản hồi ban đầu 1 giờ cho sự cố nghiêm trọng. Lite chỉ hỗ trợ 08:00–18:00 từ thứ Hai đến thứ Sáu và tài liệu không quy định thời gian phản hồi cụ thể theo mức độ nghiêm trọng.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_12,doc_21_chunk_11,doc_21_chunk_13
- Citation hits gold: PASS
- Retrieval latency: 0.605 s
- TTFT: 9.661 s
- LLM total: 11.929 s
- E2E: 12.54 s

## Q13

**Question:** Tôi cần 100 thành viên, 10 workspace và file 120 MB. Gói Lite có đáp ứng được không?

**Expected:** Không. Lite chỉ hỗ trợ tối đa 25 thành viên, 5 workspace và file tối đa 50 MB. Enterprise đáp ứng cả ba yêu cầu với giới hạn 250 thành viên, 20 workspace và 200 MB mỗi file.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_9,doc_21_chunk_8,doc_21_chunk_6
- Citation hits gold: PASS
- Retrieval latency: 0.352 s
- TTFT: 9.736 s
- LLM total: 11.567 s
- E2E: 11.926 s

## Q14

**Question:** Một khách hàng Enterprise đã hết hạn gói 10 ngày nhưng chưa gia hạn. Họ có thể tạo workspace mới không?

**Expected:** Không. Enterprise chỉ cho phép tạo workspace mới trong 7 ngày đầu của thời gian gia hạn; ngày thứ 10 đã vượt giới hạn này.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_4
- Citation hits gold: PASS
- Retrieval latency: 0.356 s
- TTFT: 3.545 s
- LLM total: 4.406 s
- E2E: 4.768 s

## Q15

**Question:** Enterprise đã hết hạn 35 ngày và chưa gia hạn thì tài khoản đang ở trạng thái nào theo tài liệu?

**Expected:** Read-only. Sau 30 ngày gia hạn, tài khoản chuyển sang read-only trong 15 ngày tiếp theo; ngày thứ 35 nằm trong giai đoạn đó.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_4
- Citation hits gold: PASS
- Retrieval latency: 0.415 s
- TTFT: 7.752 s
- LLM total: 8.346 s
- E2E: 8.767 s

## Q17

**Question:** Chính sách hoàn tiền của Orion Lite là gì?

**Expected:** Không có thông tin trong tài liệu.

- Retrieval Hit@5: PASS
- First relevant rank: 3
- RR: 0.3333
- Citation: doc_21_chunk_15
- Citation hits gold: PASS
- Retrieval latency: 0.343 s
- TTFT: 7.761 s
- LLM total: 8.38 s
- E2E: 8.733 s

## Q18

**Question:** Số điện thoại hỗ trợ kỹ thuật 24/7 của Orion Enterprise là gì?

**Expected:** Không có thông tin trong tài liệu. Tài liệu chỉ nói Enterprise hỗ trợ 24/7, không cung cấp số điện thoại.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_12
- Citation hits gold: PASS
- Retrieval latency: 0.36 s
- TTFT: 8.466 s
- LLM total: 9.339 s
- E2E: 9.705 s

## Q19

**Question:** Orion có cung cấp bảo hiểm vận chuyển cho tài liệu bị thất lạc không?

**Expected:** Không có thông tin về bảo hiểm vận chuyển trong tài liệu.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_15
- Citation hits gold: PASS
- Retrieval latency: 0.419 s
- TTFT: 8.019 s
- LLM total: 9.335 s
- E2E: 9.762 s

## Q20

**Question:** Orion Lite có ứng dụng dành cho Apple Watch không?

**Expected:** Không có thông tin trong tài liệu.

- Retrieval Hit@5: PASS
- First relevant rank: 1
- RR: 1.0
- Citation: doc_21_chunk_15
- Citation hits gold: PASS
- Retrieval latency: 0.474 s
- TTFT: 3.802 s
- LLM total: 4.471 s
- E2E: 4.953 s

