# BỘ CÂU HỎI VÀ ĐÁP ÁN — ASTER RAG DATASET 2

Bộ này dùng để **người test đọc và đối chiếu kết quả** của Dataset 2.

Upload **toàn bộ 12 tài liệu trong thư mục `documents/` vào cùng một notebook** trước khi chạy test.

> **Quan trọng:** Không upload file câu hỏi/đáp án này vào notebook RAG. File này chỉ dành cho người đánh giá.

## Cách dùng

- Upload 12 source documents và đợi ingestion hoàn tất.
- Có thể chạy tự động bằng `rag_eval_runner.py`, không cần nhập tay từng câu.
- Khi kiểm tra thủ công, hỏi nguyên văn câu hỏi bên dưới.
- Không đưa phần đáp án chuẩn, required facts hoặc forbidden facts cho RAG.
- Đối chiếu answer, citation và retrieval trace với đáp án chuẩn.
- Với câu `Unanswerable`, hệ thống phải thừa nhận corpus không đủ thông tin thay vì tự suy đoán.
- Với câu cần nhiều tài liệu, câu trả lời chỉ được coi là đầy đủ nếu lấy đủ các fact bắt buộc.
- Với các câu version/conflict, phải phân biệt đúng policy chuẩn, policy cũ và ngoại lệ riêng.

---

## Q01 — Version confusion

**Câu hỏi:** Theo chính sách chuẩn năm 2026, Aster Enterprise có thời gian gia hạn bao lâu?

**Đáp án chuẩn:** 30 ngày sau khi gói hết hạn.

**Required facts:** Enterprise 2026 grace period = 30 ngày.

**Forbidden facts:** 21 ngày; 45 ngày.

**Evidence:** `aster_enterprise_2026.md` — Renewal.

**Mục tiêu:** Không nhầm với policy 2025 hoặc hợp đồng riêng của ACME Corp.

---

## Q02 — Version comparison

**Câu hỏi:** Chính sách Enterprise 2026 thay đổi giới hạn thành viên và workspace như thế nào so với 2025?

**Đáp án chuẩn:** Giới hạn tăng từ 300 lên 400 active members và từ 25 lên 30 workspaces.

**Required facts:** 2025 = 300 members, 25 workspaces; 2026 = 400 members, 30 workspaces.

**Forbidden facts:** 600 members; 50 workspaces.

**Evidence:** `aster_enterprise_2025.md` + `aster_enterprise_2026.md`.

---

## Q03 — Near-duplicate / Multi-document

**Câu hỏi:** Gói nào cho phép tối đa 500 MB mỗi file và điều đó có làm thời gian gia hạn dài hơn không?

**Đáp án chuẩn:** Enterprise Plus cho phép tối đa 500 MB/file. Không, Plus không làm thay đổi grace period cơ bản của Enterprise; grace period vẫn là 30 ngày.

**Required facts:** Plus = 500 MB/file; Plus không đổi renewal; Enterprise = 30 ngày.

**Forbidden fact:** Plus có grace period 45 ngày.

**Evidence:** `aster_enterprise_plus_2026.md` + `aster_enterprise_2026.md`.

---

## Q04 — Multi-document / Constraint reasoning

**Câu hỏi:** Tôi cần SAML SSO, ít nhất 350 thành viên và backup không quá 6 giờ một lần. Gói tối thiểu nào đáp ứng?

**Đáp án chuẩn:** Aster Enterprise chuẩn đáp ứng. Enterprise có SAML SSO, hỗ trợ tối đa 400 thành viên và backup mỗi 6 giờ. Không cần Enterprise Plus.

**Required facts:** Enterprise có SAML SSO; 400 members; backup mỗi 6 giờ.

**Forbidden facts:** Lite đáp ứng; bắt buộc phải dùng Enterprise Plus.

**Evidence:** `security_identity_2026.md` + `aster_enterprise_2026.md` + `backup_and_recovery_2026.md`.

---

## Q05 — Multi-document

**Câu hỏi:** Nếu cần 450 thành viên và backup mỗi 3 giờ thì cấu hình nào phù hợp?

**Đáp án chuẩn:** Aster Enterprise với Enterprise Plus.

**Required facts:** Plus hỗ trợ 600 members; Plus backup mỗi 3 giờ.

**Forbidden fact:** Enterprise chuẩn một mình đáp ứng.

**Evidence:** `aster_enterprise_plus_2026.md` + `backup_and_recovery_2026.md`.

---

## Q06 — Incident distractor

**Câu hỏi:** Backup chuẩn của Enterprise năm 2026 là mỗi bao lâu? Có phải sự cố tháng 6 đã đổi chuẩn thành hơn 6 giờ không?

**Đáp án chuẩn:** Chuẩn vẫn là backup mỗi 6 giờ. Sự cố tháng 6 là một ngoại lệ vận hành và không thay đổi policy chuẩn.

**Required facts:** Standard = 6 giờ; incident là ngoại lệ; incident không đổi standard.

**Forbidden fact:** Standard backup đã đổi thành hơn 6 giờ.

**Evidence:** `backup_and_recovery_2026.md` + `incident_notice_2026_06.md`.

---

## Q07 — Customer-specific conflict

**Câu hỏi:** Một khách hàng Enterprise thông thường có được gia hạn 45 ngày như ACME Corp không?

**Đáp án chuẩn:** Không. 45 ngày chỉ áp dụng cho hợp đồng riêng của ACME Corp. Policy chuẩn Enterprise 2026 là 30 ngày.

**Required facts:** ACME = 45 ngày; đây là customer-specific term; standard = 30 ngày.

**Forbidden fact:** Tất cả khách hàng Enterprise đều có 45 ngày.

**Evidence:** `legacy_contract_excerpt.md` + `aster_enterprise_2026.md`.

---

## Q08 — Contract override

**Câu hỏi:** Nếu ACME Corp hết hạn hợp đồng Enterprise, thời gian gia hạn áp dụng là 30 hay 45 ngày?

**Đáp án chuẩn:** 45 ngày đối với ACME Corp, vì hợp đồng riêng quy định rằng điều khoản hợp đồng được ưu tiên đối với các nội dung xung đột được bao phủ.

**Required facts:** ACME = 45 ngày; customer-specific contract governs the covered conflict.

**Forbidden fact:** ACME chỉ có 30 ngày.

**Evidence:** `legacy_contract_excerpt.md` + `aster_enterprise_2026.md`.

---

## Q09 — Cross-document comparison

**Câu hỏi:** Aster Enterprise 2026 giữ audit log trong bao lâu, và Lite thì bao lâu?

**Đáp án chuẩn:** Enterprise giữ 180 ngày; Lite giữ 45 ngày.

**Required facts:** Enterprise = 180 ngày; Lite = 45 ngày.

**Forbidden facts:** Enterprise = 120 ngày; Lite = 30 ngày.

**Evidence:** `aster_enterprise_2026.md` + `aster_lite_2026.md`.

---

## Q10 — Policy overlay

**Câu hỏi:** Một khách hàng APAC dùng Enterprise Plus có thể chọn Singapore làm vùng lưu trữ và vẫn dùng backup 3 giờ không?

**Đáp án chuẩn:** Có. Enterprise Plus ở APAC có thể yêu cầu primary storage tại Singapore; APAC compliance note không thay đổi backup schedule, nên Plus vẫn backup mỗi 3 giờ.

**Required facts:** Singapore residency có thể yêu cầu; APAC note không đổi backup; Plus = 3 giờ.

**Forbidden fact:** APAC bắt Plus quay về backup 6 giờ.

**Evidence:** `regional_compliance_apac.md` + `aster_enterprise_plus_2026.md`.

---

## Q11 — Hard unanswerable

**Câu hỏi:** Phí hàng tháng của Aster Enterprise Plus là bao nhiêu?

**Đáp án chuẩn:** Không có thông tin về giá/phí trong corpus.

**Expected behavior:** Không tự tạo mức giá.

**Evidence:** `faq_marketing.md` xác nhận FAQ không định nghĩa pricing.

---

## Q12 — Hard unanswerable / Near-topic

**Câu hỏi:** Aster cam kết xóa vĩnh viễn dữ liệu trong tối đa bao nhiêu giờ sau khi cửa sổ export kết thúc?

**Đáp án chuẩn:** Tài liệu không đưa ra thời gian hoàn tất xóa được đảm bảo.

**Expected behavior:** Không suy ra một deletion SLA cụ thể.

**Evidence:** `data_export_and_termination_2026.md` + `faq_marketing.md`.

---

## Q13 — Multi-document / Temporal

**Câu hỏi:** Sau khi Enterprise hết grace period mà chưa gia hạn, khách hàng còn bao lâu để yêu cầu full export?

**Đáp án chuẩn:** Account chuyển sang read-only trong 20 ngày và khách hàng có thể yêu cầu full export trong cửa sổ 20 ngày đó.

**Required facts:** Post-grace read-only = 20 ngày; full export window = 20 ngày sau khi chuyển read-only.

**Forbidden facts:** 15 ngày; 14 ngày.

**Evidence:** `aster_enterprise_2026.md` + `data_export_and_termination_2026.md`.

---

## Q14 — False inference

**Câu hỏi:** Aster Lite có được yêu cầu khôi phục một backup cụ thể trong 7 ngày retention không?

**Đáp án chuẩn:** Không. Lite giữ backup trong 7 ngày nhưng khách hàng Lite không thể yêu cầu restore một backup cụ thể.

**Required facts:** Lite retention = 7 ngày; Lite không được request specific backup restore.

**Forbidden inference:** Có retention 7 ngày đồng nghĩa khách hàng có quyền restore.

**Evidence:** `backup_and_recovery_2026.md`.

---

## Q15 — Migration + Add-on

**Câu hỏi:** Tôi đang dùng Lite, nâng cấp lên Enterprise rồi bật Plus. Sau khi hoàn tất, giới hạn thành viên và file upload là bao nhiêu?

**Đáp án chuẩn:** Sau khi upgrade và kích hoạt Plus, giới hạn là 600 active members và 500 MB mỗi file.

**Required facts:** Plus limits áp dụng sau activation; 600 members; 500 MB/file.

**Forbidden facts:** Vẫn dùng giới hạn Lite; chỉ dùng giới hạn Enterprise chuẩn 400/300 MB.

**Evidence:** `migration_guide.md` + `aster_enterprise_plus_2026.md`.

---

## Q16 — Paraphrase / Version distractor

**Câu hỏi:** Gói tiêu chuẩn dành cho doanh nghiệp lớn có thời gian phản hồi ban đầu cho sự cố nghiêm trọng là bao lâu trong năm 2026?

**Đáp án chuẩn:** 60 phút.

**Required fact:** Critical incident initial response target = 60 phút.

**Forbidden fact:** 90 phút.

**Evidence:** `aster_enterprise_2026.md`.

---

## Q17 — Apparent contradiction

**Câu hỏi:** Tài liệu sự cố nói có tenant được restore từ backup cũ hơn 6 giờ, còn standard nói backup mỗi 6 giờ. Hai thông tin này có mâu thuẫn policy không?

**Đáp án chuẩn:** Không. Incident mô tả một ngoại lệ vận hành; chính incident notice nói sự kiện này không thay đổi standard backup policy 6 giờ.

**Required facts:** Restore từ backup cũ hơn 6 giờ đã xảy ra; đó là ngoại lệ; standard vẫn là 6 giờ.

**Forbidden fact:** Policy đã thay đổi.

**Evidence:** `incident_notice_2026_06.md` + `backup_and_recovery_2026.md`.

---

## Q18 — Identification

**Câu hỏi:** Which plan has a 14-day grace period and blocks new uploads during that period?

**Đáp án chuẩn:** Aster Lite.

**Required facts:** Lite grace = 14 ngày; không thể upload file mới trong grace period.

**Forbidden fact:** Enterprise.

**Evidence:** `aster_lite_2026.md`.

---

## Q19 — Hard unanswerable / Security

**Câu hỏi:** Enterprise Plus có hỗ trợ customer-managed encryption keys không?

**Đáp án chuẩn:** Corpus không xác nhận có hỗ trợ customer-managed encryption keys.

**Expected behavior:** Không được tự khẳng định tính năng này có tồn tại.

**Evidence:** `security_identity_2026.md` nói tài liệu không specify customer-managed encryption keys.

---

## Q20 — Multi-document / Different units

**Câu hỏi:** So sánh thời gian session timeout của Lite với thời gian lưu audit log của Lite.

**Đáp án chuẩn:** Lite session hết hạn sau 4 giờ không hoạt động; audit log được giữ 45 ngày.

**Required facts:** Session inactivity = 4 giờ; audit retention = 45 ngày.

**Forbidden fact:** Audit retention = 30 ngày.

**Evidence:** `security_identity_2026.md` + `aster_lite_2026.md`.

---

## Q21 — Marketing distractor

**Câu hỏi:** Cụm "rapid recovery" trong FAQ có nghĩa là Aster cam kết restore trong dưới 1 giờ không?

**Đáp án chuẩn:** Không. FAQ nói đây chỉ là marketing language và không thay thế numerical service targets. Standard restoration request của Enterprise được xử lý trong 8 business hours.

**Required facts:** "Rapid recovery" chỉ là marketing; standard restoration = 8 business hours.

**Forbidden fact:** Restore SLA dưới 1 giờ.

**Evidence:** `faq_marketing.md` + `backup_and_recovery_2026.md`.

---

## Q22 — High-recall multi-document

**Câu hỏi:** Enterprise Plus thay đổi những gì so với Enterprise chuẩn: thành viên, workspace, file upload, backup; và những gì không đổi?

**Đáp án chuẩn:** Plus tăng giới hạn lên 600 members, 50 workspaces và 500 MB/file; backup thành mỗi 3 giờ và giữ 45 ngày. Plus không thay đổi base renewal grace period, lịch hỗ trợ 24/7 hoặc audit-log retention 180 ngày.

**Required facts:** 600 members; 50 workspaces; 500 MB/file; backup 3 giờ; retention 45 ngày; renewal unchanged; 24/7 support unchanged; audit retention vẫn 180 ngày.

**Evidence:** `aster_enterprise_plus_2026.md` + `backup_and_recovery_2026.md` + `aster_enterprise_2026.md`.

**Mục tiêu:** Đây là câu cần coverage cao. Trả lời đúng một phần chưa được tính là hoàn toàn đúng.

---

## Q23 — Hard unanswerable

**Câu hỏi:** Số điện thoại hotline cho incident severity critical là gì?

**Đáp án chuẩn:** Không có số điện thoại trong corpus.

**Expected behavior:** Có thể nói tài liệu có response target nhưng không cung cấp hotline number; không được tự tạo số điện thoại.

**Evidence:** `faq_marketing.md` + `aster_enterprise_2026.md`.

---

## Q24 — Multi-constraint boundary

**Câu hỏi:** Nếu tổ chức cần 350 thành viên, 28 workspace, file 280 MB và SSO thì Enterprise chuẩn 2026 có đủ không?

**Đáp án chuẩn:** Có. Enterprise 2026 hỗ trợ tối đa 400 members, 30 workspaces, 300 MB/file và có SAML SSO.

**Required facts:** 400 members; 30 workspaces; 300 MB/file; SAML SSO.

**Forbidden fact:** Bắt buộc phải dùng Plus.

**Evidence:** `aster_enterprise_2026.md` + `security_identity_2026.md`.

---

## Q25 — Boundary reasoning

**Câu hỏi:** Enterprise đã hết hạn 8 ngày nhưng chưa gia hạn. Admin còn tạo workspace mới được không?

**Đáp án chuẩn:** Không. Chỉ 7 ngày đầu của grace period được tạo workspace mới; ngày thứ 8 đã vượt giới hạn.

**Evidence:** `aster_enterprise_2026.md`.

---

## Q26 — Temporal reasoning

**Câu hỏi:** Enterprise hết hạn 35 ngày mà chưa gia hạn thì đang ở trạng thái nào?

**Đáp án chuẩn:** Read-only. Grace period kéo dài 30 ngày, sau đó account chuyển read-only thêm 20 ngày; ngày thứ 35 nằm trong read-only period.

**Required facts:** Grace = 30 ngày; read-only sau grace = 20 ngày.

**Evidence:** `aster_enterprise_2026.md`.

---

## Q27 — Document scope

**Câu hỏi:** APAC compliance note có tăng giới hạn thành viên của Enterprise không?

**Đáp án chuẩn:** Không. APAC note nói rõ nó không thay đổi member limits.

**Forbidden fact:** APAC làm tăng capacity.

**Evidence:** `regional_compliance_apac.md`.

---

## Q28 — Version confusion

**Câu hỏi:** Response target 90 phút còn áp dụng cho Enterprise chuẩn năm 2026 không?

**Đáp án chuẩn:** Không. 90 phút là policy 2025; policy 2026 đặt target là 60 phút.

**Required facts:** 2025 = 90 phút; 2026 = 60 phút.

**Forbidden fact:** 2026 = 90 phút.

**Evidence:** `aster_enterprise_2025.md` + `aster_enterprise_2026.md`.

---

## Q29 — Three-document negative synthesis

**Câu hỏi:** Lite có thể chọn Singapore residency, dùng SSO và yêu cầu restore backup cụ thể không?

**Đáp án chuẩn:** Không cho cả ba. Lite không có selectable Singapore data residency theo APAC note, không có SAML SSO và không thể yêu cầu restore một backup cụ thể.

**Required facts:** Lite không selectable residency; không SAML SSO; không specific backup restore.

**Evidence:** `regional_compliance_apac.md` + `security_identity_2026.md` + `backup_and_recovery_2026.md`.

---

## Q30 — High-load multi-constraint synthesis

**Câu hỏi:** Một Enterprise Plus customer ở APAC cần 550 thành viên, 40 workspace, file 450 MB, Singapore residency và backup 3 giờ. Có đáp ứng toàn bộ không?

**Đáp án chuẩn:** Có. Enterprise Plus hỗ trợ 600 members, 50 workspaces, 500 MB/file và backup mỗi 3 giờ; Enterprise Plus customer ở APAC có thể yêu cầu primary storage tại Singapore.

**Required facts:** 600 members; 50 workspaces; 500 MB/file; backup 3 giờ; Singapore residency available.

**Evidence:** `aster_enterprise_plus_2026.md` + `regional_compliance_apac.md`.

---

# FOLLOW-UP TESTS

Các câu trong từng sequence phải được hỏi **liên tiếp trong cùng conversation**.

Không reset conversation giữa các turn.

## F01 — Three-turn coreference

### F01-T1

**Câu hỏi:** Theo policy chuẩn 2026, Enterprise có grace period bao lâu?

**Đáp án chuẩn:** 30 ngày.

### F01-T2

**Câu hỏi:** Sau thời gian đó thì tài khoản thế nào?

**Đáp án chuẩn:** Nếu chưa gia hạn, account chuyển sang trạng thái read-only trong 20 ngày.

### F01-T3

**Câu hỏi:** Trong giai đoạn đó tôi còn yêu cầu full export được bao lâu?

**Đáp án chuẩn:** Có thể yêu cầu full export trong 20 ngày kể từ khi account chuyển sang read-only.

**Evidence:** `aster_enterprise_2026.md` + `data_export_and_termination_2026.md`.

**Mục tiêu:** Kiểm tra history/query rewriting có giữ đúng chuỗi tham chiếu:

`grace period` → `sau thời gian đó` → `giai đoạn read-only đó`.

---

## F02 — Entity switching + Conflict resolution

### F02-T1

**Câu hỏi:** ACME Corp có grace period bao lâu?

**Đáp án chuẩn:** 45 ngày.

### F02-T2

**Câu hỏi:** Còn khách hàng Enterprise bình thường thì sao?

**Đáp án chuẩn:** 30 ngày theo standard policy 2026.

### F02-T3

**Câu hỏi:** Vậy trường hợp nào được ưu tiên nếu hai tài liệu khác nhau?

**Đáp án chuẩn:** Với ACME Corp, customer-specific contract được ưu tiên đối với điều khoản xung đột được contract bao phủ. Khách hàng Enterprise thông thường dùng standard policy 2026.

**Evidence:** `legacy_contract_excerpt.md` + `aster_enterprise_2026.md`.

**Mục tiêu:** Kiểm tra hệ thống có:
1. giữ đúng entity ACME;
2. chuyển sang standard customer ở turn 2;
3. hiểu conflict-resolution rule ở turn 3;
4. không biến ngoại lệ ACME thành policy chung.

---

# GỢI Ý CHẤM NHANH

## PASS hoàn toàn

Một câu được coi là PASS hoàn toàn khi:

- trả lời đúng kết luận;
- chứa đủ required facts;
- không chứa forbidden fact;
- citation hỗ trợ đúng claim;
- với multi-document question, không bỏ mất evidence quan trọng từ tài liệu còn lại.

## PARTIAL

Có thể đánh PARTIAL nếu:

- kết luận chính đúng nhưng thiếu một hoặc nhiều required facts;
- câu trả lời không sai nhưng chưa giải quyết đầy đủ tất cả constraint;
- citation đúng một phần nhưng coverage chưa đủ.

## FAIL

Đánh FAIL nếu:

- trả lời sai;
- nhầm Lite / Enterprise / Enterprise Plus;
- nhầm 2025 / 2026;
- biến ACME-specific contract thành standard policy;
- suy luận từ marketing wording thành SLA;
- tự tạo thông tin cho câu unanswerable;
- bỏ qua một điều kiện khiến recommendation cuối cùng sai.

# NHÓM CÂU KHÓ CẦN CHÚ Ý

Nếu chỉ muốn review nhanh những câu có khả năng phát hiện lỗi pipeline tốt nhất, ưu tiên:

- **Q03:** near-duplicate + renewal inference
- **Q04:** 3-document recommendation
- **Q06:** incident distractor
- **Q07–Q08:** standard policy vs customer-specific override
- **Q10:** policy overlay
- **Q12:** hard no-answer có numerical bait
- **Q17:** apparent contradiction
- **Q21:** marketing distractor
- **Q22:** high-recall synthesis
- **Q24:** multi-constraint boundary
- **Q29:** three-document negative synthesis
- **Q30:** high-load multi-constraint synthesis
- **F01/F02:** conversational retrieval/query rewriting
