# Dataset 2 — Raw Run Summary

- Runs: 36
- Retrieval median: 0.415s
- E2E median: 10.394s

> Retrieval quality metrics require resolving uploaded document IDs/chunk IDs to the manifest evidence after ingestion.

## D2-Q01

- Type: version_confusion
- Status: completed
- Citations: 1
- Retrieval: 0.775 s
- TTFT: 9.06 s
- E2E: 10.336 s

**Answer**

180 ngày — bản ghi kiểm toán được lưu giữ trong 180 ngày [5].

## D2-Q02

- Type: version_confusion
- Status: completed
- Citations: 2
- Retrieval: 0.413 s
- TTFT: 10.412 s
- E2E: 11.698 s

**Answer**

So với 2025, chính sách Enterprise 2026 tăng giới hạn như sau:

- Thành viên hoạt động: từ 300 (2025) lên 400 (2026) — tăng 100 thành viên. [2][1]  
- Workspaces: từ 25 (2025) lên 30 (2026) — tăng 5 workspaces. [2][1]

## D2-Q03

- Type: near_duplicate
- Status: completed
- Citations: 2
- Retrieval: 0.717 s
- TTFT: 12.101 s
- E2E: 14.612 s

**Answer**

- Gói Enterprise Plus cho phép tối đa 500 MB mỗi file [3].  
- Về thời gian gia hạn: không có thông tin nào trong mục Enterprise Plus cho thấy gói này làm thời gian gia hạn dài hơn; tài liệu Enterprise Plus không đề cập thay đổi thời hạn gia hạn [3].  
- Lưu ý: chỉ có hợp đồng riêng của ACME Corp nêu thời gian gia hạn 45 ngày, nhưng đó là điều khoản khách hàng cụ thể và không áp dụng làm chuẩn chung trừ khi có xung đột cho ACME Corp [5].

## D2-Q04

- Type: multi_document
- Status: completed
- Citations: 3
- Retrieval: 0.43 s
- TTFT: 8.113 s
- E2E: 10.452 s

**Answer**

Gói tối thiểu đáp ứng yêu cầu của bạn: Aster Enterprise.

Chi tiết và nguồn:
- SAML SSO có trong Aster Enterprise (và Enterprise Plus) nên đáp ứng yêu cầu SSO của bạn [1].  
- Aster Enterprise sao lưu mỗi 6 giờ, tức là “không quá 6 giờ một lần” được thỏa mãn (sao lưu Enterprise: every 6 hours) [5].  
- Tài liệu không nêu rõ giới hạn số thành viên cụ thể, chỉ cho biết Enterprise dành cho tổ chức lớn và Enterprise Plus có sức chứa cao hơn; do đó bạn nên xác nhận trực tiếp với đội bán hàng/hỗ trợ nếu cần đảm bảo tối thiểu 350 thành viên hoặc xem xét Enterprise Plus nếu cần sức chứa lớn hơn [4].

Nếu muốn, tôi có thể soạn một câu hỏi mẫu để bạn gửi cho đội bán hàng/hỗ trợ nhằm xác nhận giới hạn thành viên và các điều khoản phục hồi.

## D2-Q05

- Type: multi_document
- Status: completed
- Citations: 3
- Retrieval: 0.388 s
- TTFT: 11.24 s
- E2E: 13.555 s

**Answer**

Cấu hình phù hợp: Enterprise Plus — vì cung cấp backup mỗi 3 giờ [1].

Lưu ý:
- Aster Enterprise tiêu chuẩn chỉ hỗ trợ tới 400 thành viên (không đủ cho 450) [4].
- Tài liệu ghi Enterprise Plus “thêm dung lượng” nhưng không nêu rõ giới hạn thành viên cụ thể, nên cần xác nhận giới hạn thành viên của gói Enterprise Plus trước khi quyết định [5].

Khuyến nghị: Liên hệ bộ phận bán hàng/hỗ trợ để xác nhận Enterprise Plus có thể chứa ít nhất 450 thành viên; nếu không, cần xem xét cấu hình tùy chỉnh.

## D2-Q06

- Type: distractor
- Status: completed
- Citations: 2
- Retrieval: 0.416 s
- TTFT: 12.487 s
- E2E: 14.16 s

**Answer**

- Backup chuẩn của Aster Enterprise 2026 là mỗi 6 giờ. [2]  
- Sự cố ngày 18/6 là một trường hợp khôi phục ngoại lệ — một số tenant đã được khôi phục từ bản sao lưu cũ hơn 6 giờ vì snapshot gần nhất ở một vùng không khả dụng — nhưng sự kiện này không thay đổi lịch sao lưu hay chính sách giữ bản sao chuẩn. [1][2]

## D2-Q07

- Type: contract_conflict
- Status: completed
- Citations: 1
- Retrieval: 0.429 s
- TTFT: 6.897 s
- E2E: 8.05 s

**Answer**

Không. Khoảng gia hạn 45 ngày là điều khoản riêng trong hợp đồng ký với ACME Corp và được ghi rõ là chỉ áp dụng cho ACME Corp, không định nghĩa chính sách tiêu chuẩn của Aster Enterprise cho các khách hàng khác [1].

## D2-Q08

- Type: contract_conflict
- Status: completed
- Citations: 1
- Retrieval: 0.454 s
- TTFT: 4.18 s
- E2E: 5.478 s

**Answer**

45 ngày.

Hợp đồng của ACME Corp quy định thời gian gia hạn là 45 ngày và đối với những điều khoản được bao phủ, ACME Corp sẽ tuân theo hợp đồng này nếu có mâu thuẫn với chính sách chuẩn [1].

## D2-Q09

- Type: cross_language
- Status: completed
- Citations: 1
- Retrieval: 0.427 s
- TTFT: 4.745 s
- E2E: 6.078 s

**Answer**

- Aster Enterprise 2026: audit log được lưu 180 ngày [1].  
- Aster Lite: không có thông tin về thời hạn lưu audit log trong các đoạn văn bản được cung cấp.  

Nếu bạn muốn, hãy cung cấp đoạn tài liệu về Data retention của Lite để tôi kiểm tra tiếp.

## D2-Q10

- Type: multi_document
- Status: completed
- Citations: 2
- Retrieval: 0.422 s
- TTFT: 5.527 s
- E2E: 6.62 s

**Answer**

Có.  

- Khách hàng Enterprise Plus ở APAC có thể yêu cầu lưu trữ chính ở vùng Singapore [1].  
- Enterprise Plus thiết lập sao lưu mỗi 3 giờ (và lưu trữ bản sao 45 ngày) nên họ vẫn được sao lưu 3 giờ một lần [2].

## D2-Q11

- Type: hard_no_answer
- Status: completed
- Citations: 2
- Retrieval: 0.377 s
- TTFT: 4.725 s
- E2E: 5.916 s

**Answer**

Tài liệu cung cấp không nêu mức phí hàng tháng cho Aster Enterprise Plus.

- Aster Enterprise Plus là một add-on tùy chọn cho khách hàng Aster Enterprise [2].  
- FAQ của Aster ghi rõ tài liệu FAQ không định nghĩa về giá cả (pricing) hoặc các điều khoản hoàn tiền [3].

## D2-Q12

- Type: hard_no_answer
- Status: completed
- Citations: 1
- Retrieval: 0.361 s
- TTFT: 8.97 s
- E2E: 10.291 s

**Answer**

Không có thông tin trong các đoạn ngữ cảnh được cung cấp về số giờ Aster cam kết xóa vĩnh viễn dữ liệu sau khi cửa sổ export kết thúc. Tài liệu chỉ nêu rằng khách hàng có thể yêu cầu full export trong 20 ngày [4].

## D2-Q13

- Type: multi_document
- Status: completed
- Citations: 1
- Retrieval: 0.425 s
- TTFT: 16.512 s
- E2E: 18.174 s

**Answer**

Tài liệu không nêu khoảng thời gian cụ thể để khách hàng Enterprise "yêu cầu full export" sau khi hết grace period. [4]

Thêm chi tiết hữu ích từ tài liệu:
- Grace period của gói Enterprise (2026) là 30 ngày; nếu không gia hạn sau 30 ngày, tài khoản chuyển sang chế độ read-only thêm 20 ngày. [4]

## D2-Q14

- Type: near_duplicate
- Status: completed
- Citations: 1
- Retrieval: 0.462 s
- TTFT: 4.872 s
- E2E: 6.44 s

**Answer**

Không. Khách hàng Aster Lite không thể yêu cầu khôi phục một backup cụ thể; mặc dù dữ liệu được sao lưu mỗi 24 giờ và được lưu giữ trong 7 ngày, yêu cầu khôi phục cụ thể không được hỗ trợ (đội vận hành chỉ có thể thực hiện khôi phục ở mức hệ thống sau sự cố nền tảng) [1].

## D2-Q15

- Type: multi_document
- Status: completed
- Citations: 3
- Retrieval: 0.381 s
- TTFT: 8.234 s
- E2E: 10.617 s

**Answer**

Không có số cụ thể về giới hạn thành viên hay giới hạn file upload trong các đoạn văn bản bạn cung cấp. Thông tin chỉ nêu nguyên tắc áp dụng như sau:

- Sau khi nâng từ Lite lên Enterprise, các giới hạn của gói Enterprise sẽ có hiệu lực ngay khi nâng cấp hoàn tất [3].  
- Nếu bạn bật thêm Enterprise Plus sau khi đã nâng lên Enterprise, giới hạn theo dung lượng/capacity của Enterprise Plus sẽ áp dụng sau khi add-on được kích hoạt [3][2].  
- Nếu hóa đơn của bạn ở khu vực APAC, bạn có thể yêu cầu lưu trữ chính ở Singapore nhưng ghi chú APAC không thay đổi giới hạn thành viên hay giới hạn workspace (tức không ảnh hưởng tới giới hạn thành viên) [5].

Để biết các con số cụ thể (số thành viên tối đa, kích thước/giới hạn upload file), bạn phải xem tài liệu chính sách của từng gói (plan policy documents) hoặc tài liệu sản phẩm tương ứng; các đoạn ngữ cảnh hiện tại không liệt kê các giới hạn số liệu này [3][2].

## D2-Q16

- Type: paraphrase
- Status: completed
- Citations: 5
- Retrieval: 0.385 s
- TTFT: 7.578 s
- E2E: 9.246 s

**Answer**

Không có thông tin về "thời gian phản hồi ban đầu cho sự cố nghiêm trọng" trong các đoạn bạn cung cấp [1][2][3][4][5].

Các đoạn đã kiểm tra: [1][4][5] (chính sách và giới hạn thành viên/workspace), [3] (hợp đồng riêng cho ACME), [2] (xác thực hai yếu tố). Nếu bạn có đoạn chính sách SLA khác hoặc muốn tôi tìm trong tài liệu bổ sung, hãy gửi nội dung đó hoặc cho biết nơi tôi có thể tra cứu.

## D2-Q17

- Type: conflicting_evidence
- Status: completed
- Citations: 2
- Retrieval: 0.477 s
- TTFT: 8.988 s
- E2E: 11.343 s

**Answer**

Không mâu thuẫn.

- Thông báo sự cố nêu đây là một sự kiện phục hồi ngoại lệ: nhóm vận hành đã khôi phục một số tenant Enterprise từ bản sao lưu cũ hơn 6 giờ vì các snapshot gần nhất ở một vùng không khả dụng, và sự kiện này không thay đổi lịch sao lưu hay chính sách giữ bản sao lưu chuẩn [1].  
- Tiêu chuẩn Backup của Aster vẫn quy định dữ liệu Enterprise được sao lưu mỗi 6 giờ (backup frequency = 6 giờ) và giữ 30 ngày, tức là chính sách chuẩn vẫn là như vậy [2].  

Kết luận: hành động trong sự cố là ngoại lệ do tình huống cụ thể và không thay đổi policy chuẩn [1][2].

## D2-Q18

- Type: cross_language
- Status: completed
- Citations: 1
- Retrieval: 0.378 s
- TTFT: 4.407 s
- E2E: 5.372 s

**Answer**

Aster Lite (Lite). It has a 14-day renewal grace period during which customers can view/download existing files but cannot upload new files [1].

## D2-Q19

- Type: hard_no_answer
- Status: completed
- Citations: 1
- Retrieval: 0.356 s
- TTFT: 5.356 s
- E2E: 6.197 s

**Answer**

Không — tài liệu không chỉ định việc hỗ trợ khóa mã hóa do khách hàng quản lý (customer-managed encryption keys) [1].

## D2-Q20

- Type: multi_document
- Status: completed
- Citations: 2
- Retrieval: 0.415 s
- TTFT: 8.042 s
- E2E: 9.402 s

**Answer**

Session timeout của Lite là 4 giờ, còn thời gian lưu audit log của Lite là 45 ngày — tức là audit log được giữ lâu hơn rất nhiều so với thời hạn session [1][3].

- Lite session: hết hạn sau 4 giờ không hoạt động [1].  
- Audit logs (Lite): được lưu trong 45 ngày [3].

## D2-Q21

- Type: distractor
- Status: completed
- Citations: 2
- Retrieval: 0.388 s
- TTFT: 7.695 s
- E2E: 9.172 s

**Answer**

Không. Cụm "rapid recovery" là cụm mô tả tiếp thị và không thay thế các giới hạn số liệu hoặc cam kết thời gian trong chính sách. [1]

Thời gian khôi phục cụ thể được quy định trong tiêu chuẩn Backup and Recovery — ví dụ, yêu cầu khôi phục tiêu chuẩn cho gói Enterprise được xử lý trong vòng 8 giờ làm việc. [2]

## D2-Q22

- Type: multi_document
- Status: completed
- Citations: 3
- Retrieval: 0.759 s
- TTFT: 8.296 s
- E2E: 11.616 s

**Answer**

Thay đổi:
- Giới hạn thành viên tổ chức: trở thành 600 active members. [1]
- Số workspaces: trở thành 50 workspaces. [1]
- Kích thước tải lên tối đa: 500 MB mỗi file. [1]
- Backup: khoảng cách sao lưu 3 giờ một lần và giữ sao lưu trong 45 ngày. [2]

Không đổi (theo ngữ cảnh được cung cấp):
- Thời hạn xuất dữ liệu (export window) vẫn là 20 ngày, giống như Enterprise. [3]

## D2-Q23

- Type: hard_no_answer
- Status: completed
- Citations: 2
- Retrieval: 0.892 s
- TTFT: 9.36 s
- E2E: 11.522 s

**Answer**

Không có; trong các đoạn văn bản được cung cấp không nêu số điện thoại hotline cho incident severity critical.

- Tài liệu Enterprise (2026) chỉ ghi mục tiêu phản hồi ban đầu cho critical là 60 phút và hỗ trợ 24/7 [1].  
- Tài liệu Lite (2026) chỉ ghi giờ hỗ trợ 08:00–18:00 Thứ Hai–Thứ Sáu và không nêu số điện thoại hay mục tiêu theo mức độ nghiêm trọng [3].

## D2-Q24

- Type: multi_document
- Status: completed
- Citations: 2
- Retrieval: 0.413 s
- TTFT: 10.276 s
- E2E: 13.117 s

**Answer**

Tóm tắt nhanh:

- Thành viên và workspace: Aster Enterprise 2026 hỗ trợ tới 400 thành viên và 30 workspace, nên 350 thành viên và 28 workspace được hỗ trợ [2].  
- File 280 MB: Các đoạn cung cấp không nêu giới hạn upload của bản Enterprise 2026. Nếu bật Enterprise Plus thì giới hạn upload tối đa là 500 MB/tập tin (vì vậy 280 MB được chấp nhận) [1].  
- SSO: Trong các đoạn cung cấp không có thông tin về việc hỗ trợ SSO, nên không thể xác nhận.  

Kết luận: Enterprise 2026 đáp ứng yêu cầu về số thành viên và workspace; để chắc chắn về tải file 280 MB và SSO bạn cần kiểm tra thêm hoặc cân nhắc nâng lên Enterprise Plus (upload 500 MB) [2][1].

## D2-Q25

- Type: boundary_reasoning
- Status: completed
- Citations: 5
- Retrieval: 0.397 s
- TTFT: 12.479 s
- E2E: 15.237 s

**Answer**

Không rõ — trong các đoạn văn bản bạn cung cấp không có quy định về việc tính năng tạo workspace khi gói Enterprise đã hết hạn.  

Chi tiết:
- Các đoạn chỉ nêu giới hạn số thành viên và workspace cho các gói: Enterprise 2025 [1], Enterprise 2026 [2], Enterprise Plus (thay đổi dung lượng) [3], và Lite [5].  
- FAQ cho biết các tài liệu marketing/FAQ không thay thế các giới hạn/chính sách và không định nghĩa các điều khoản như giá cả, hoàn tiền hoặc SLA cho xóa dữ liệu — nó không đưa ra quy định về hành vi khi hết hạn dịch vụ [4].

Đề xuất (không có trong các đoạn trên): kiểm tra văn bản chính sách/gia hạn đầy đủ của gói hoặc liên hệ bộ phận hỗ trợ/nhóm quản trị để biết quy tắc áp dụng khi thuê bao đã hết hạn.

## D2-Q26

- Type: boundary_reasoning
- Status: completed
- Citations: 1
- Retrieval: 0.433 s
- TTFT: 6.744 s
- E2E: 8.191 s

**Answer**

Không có thông tin trong các đoạn cung cấp về trạng thái của gói Enterprise sau 35 ngày hết hạn. Tài liệu chỉ nêu rằng khách hàng Enterprise Plus theo cùng cửa sổ xuất dữ liệu 20 ngày như Enterprise [4]. Vì vậy, từ các đoạn này không thể xác định trạng thái cụ thể sau 35 ngày.

## D2-Q27

- Type: document_scope
- Status: completed
- Citations: 1
- Retrieval: 0.391 s
- TTFT: 4.631 s
- E2E: 5.761 s

**Answer**

Không — APAC compliance note không làm tăng giới hạn thành viên; nó nêu rõ “does not alter ... member limits” [1].

## D2-Q28

- Type: version_confusion
- Status: completed
- Citations: 2
- Retrieval: 0.389 s
- TTFT: 7.122 s
- E2E: 9.463 s

**Answer**

Ngắn gọn: Không thể xác nhận — trong các đoạn văn cung cấp không có chỗ nào nêu rõ “response target 90 phút” cho Aster Enterprise 2026.  

Chi tiết:
- Ghi chú APAC chỉ nói rằng nó không thay đổi các “support response targets” nhưng không nêu giá trị cụ thể của các target ([1]).  
- Tài liệu về Aster Enterprise 2026 chỉ nêu điều kiện eligibility (hỗ trợ đến 400 thành viên và 30 workspace) mà không đề cập thời gian phản hồi ([2]).  

Gợi ý: Để chắc chắn, bạn nên kiểm tra tài liệu chính thức về support response targets hoặc liên hệ đội hỗ trợ của Aster.

## D2-Q29

- Type: multi_document
- Status: completed
- Citations: 3
- Retrieval: 0.475 s
- TTFT: 6.742 s
- E2E: 8.997 s

**Answer**

Tóm tắt ngắn: Không / Không / Không.

- Chọn Singapore residency: Không — Aster Lite không cung cấp tùy chọn chọn vùng lưu trữ (selectable data residency) theo ghi chú APAC (chỉ Enterprise và Enterprise Plus được yêu cầu giữ lưu trữ chính ở Singapore) [1].
- Dùng SSO: Không — SAML Single Sign‑On chỉ được bao gồm cho Aster Enterprise và Enterprise Plus; Aster Lite không có SAML SSO [5].
- Yêu cầu restore backup cụ thể: Không — Khách hàng Lite không thể yêu cầu khôi phục một bản backup cụ thể; backups được tạo mỗi 24 giờ và giữ 7 ngày, và chỉ có thể thực hiện khôi phục cấp hệ thống bởi operations sau sự cố nền tảng [2].

## D2-Q30

- Type: multi_document
- Status: completed
- Citations: 3
- Retrieval: 0.44 s
- TTFT: 9.571 s
- E2E: 11.365 s

**Answer**

Có — tất cả các yêu cầu của khách hàng đều được đáp ứng.

- 550 thành viên: trong Enterprise Plus giới hạn là 600 active members → đáp ứng [1].  
- 40 workspace: giới hạn 50 workspaces → đáp ứng [1].  
- File 450 MB: kích thước tải lên tối đa 500 MB/file → đáp ứng [1].  
- Singapore residency: khách hàng Enterprise Plus ở APAC có thể yêu cầu lưu trữ chính ở Singapore → đáp ứng [2].  
- Backup 3 giờ: Enterprise Plus có khoảng cách backup 3 giờ (và giữ backup 45 ngày) — ghi chú APAC không thay đổi lịch backup → đáp ứng [4][2].

## D2-F01-T1

- Type: followup
- Status: completed
- Citations: 2
- Retrieval: 0.368 s
- TTFT: 11.486 s
- E2E: 13.572 s

**Answer**

Tài liệu 2026 được cung cấp không nêu con số cụ thể cho “base renewal grace period”, nên không thể xác định từ ngữ cảnh này.

- Hợp đồng riêng của ACME ghi 45 ngày nhưng đó là điều khoản dành riêng cho khách hàng và không định nghĩa chính sách chuẩn Aster Enterprise [1].  
- Phần Enterprise Plus chỉ nói rằng nó không thay đổi “base renewal grace period” nhưng cũng không cho biết giá trị cụ thể [3].

## D2-F01-T2

- Type: followup
- Status: completed
- Citations: 4
- Retrieval: 0.452 s
- TTFT: 11.614 s
- E2E: 19.213 s

**Answer**

Phụ thuộc vào gói/case cụ thể — tóm tắt theo từng trường hợp:

- Gói Lite: thời gian gia hạn là 14 ngày; trong 14 ngày đó khách hàng chỉ có thể xem và tải các file hiện có, không được tải lên; sau 14 ngày chính sách không cho phép yêu cầu xuất toàn bộ dữ liệu (không có quyền tải/xem thêm theo mô tả) [5][3].  
- Khách hàng có hợp đồng riêng (ví dụ ACME Corp): hợp đồng này cho phép 45 ngày gia hạn và các điều khoản trong hợp đồng áp dụng cho ACME thay vì chính sách chuẩn nếu có xung đột [1].  
- Enterprise Plus: phụ lục Enterprise Plus không thay đổi thời hạn gia hạn cơ bản (không làm thay đổi giá trị gia hạn đã áp dụng cho gói cơ bản) [2].

Bạn đang hỏi cho gói/case nào để mình trả lời chi tiết hơn?

## D2-F01-T3

- Type: followup
- Status: completed
- Citations: 2
- Retrieval: 0.398 s
- TTFT: 8.629 s
- E2E: 15.715 s

**Answer**

Bạn chỉ có thể yêu cầu/tải xuất trong 14 ngày của giai đoạn gia hạn (renewal grace period); chính sách Lite cho phép tải các file hiện có chỉ trong 14 ngày và không nêu quyền yêu cầu full export sau khi giai đoạn này kết thúc [2].

Nếu bạn là ACME Corp thì hợp đồng riêng của họ cho phép giai đoạn gia hạn 45 ngày, nhưng đó là điều khoản riêng dành cho ACME và không thay đổi chính sách Lite chuẩn [1].

## D2-F02-T1

- Type: followup
- Status: completed
- Citations: 1
- Retrieval: 0.387 s
- TTFT: 5.155 s
- E2E: 6.032 s

**Answer**

ACME Corp có thời gian gia hạn (grace period) là 45 ngày [1].

Đây là điều khoản riêng trong hợp đồng ký năm 2024 áp dụng cho ACME Corp và được ưu tiên nếu có mâu thuẫn với chính sách tiêu chuẩn [1].

## D2-F02-T2

- Type: followup
- Status: completed
- Citations: 3
- Retrieval: 0.371 s
- TTFT: 7.086 s
- E2E: 12.503 s

**Answer**

Đối với khách hàng Enterprise thông thường:

- Thời gian gia hạn (renewal grace period) là 21 ngày sau khi hết hạn đăng ký. [4]  
- Trong 5 ngày đầu tiên của thời gian gia hạn, quản trị viên vẫn có thể tạo workspace mới. [4]  
- Sau ngày thứ 5, việc tạo workspace bị khóa. [4]

Lưu ý:
- Nếu có hợp đồng riêng của khách hàng (ví dụ ACME) thì hợp đồng đó có thể quy định thời gian gia hạn khác và sẽ áp dụng cho khách hàng đó. [3]  
- Ghi chú khu vực APAC không thay đổi thời gian gia hạn cho khách hàng Enterprise. [5]

## D2-F02-T3

- Type: followup
- Status: completed
- Citations: 5
- Retrieval: 0.516 s
- TTFT: 8.267 s
- E2E: 16.813 s

**Answer**

Tóm tắt ưu tiên dựa trên các đoạn được cung cấp:

- Hợp đồng riêng với khách hàng (ví dụ ACME Corp) được ưu tiên hơn chính sách tiêu chuẩn cho những điều khoản được hợp đồng bao phủ [1].  
- Ghi chú tuân thủ APAC chỉ áp dụng cho khách hàng vùng APAC và nó KHÔNG thay đổi một số mục như: thời hạn gia hạn, giới hạn thành viên, giới hạn workspace, mục tiêu phản hồi hỗ trợ, lịch sao lưu — tức là những mục này vẫn tuân theo nguồn chính sách tương ứng chứ không bị Ghi chú APAC ghi đè [5].  
- Các câu mô tả trong tài liệu marketing là mang tính mô tả và KHÔNG thay thế các giới hạn số hoặc mục tiêu dịch vụ trong tài liệu chính sách — nghĩa là tài liệu chính sách có giá trị hơn so với nội dung marketing khi có mâu thuẫn [2].  
- Trong trường hợp hai phiên bản chính sách tiêu chuẩn mâu thuẫn (ví dụ mục tiêu phản hồi sự cố: 90 phút trong 2025 so với 60 phút trong 2026), các đoạn trích cho thấy sự khác nhau nhưng không nêu quy tắc chung về thứ tự ưu tiên giữa các phiên bản—không thể xác định ưu tiên chỉ từ các đoạn này [3][4].

