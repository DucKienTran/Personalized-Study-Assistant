class SummaryPromptBuilder:
    @staticmethod
    def build(
        content: str,
        level: str,
        format_type: str,
        instruction: str,
    ) -> str:
        base_prompt = (
            "Bạn là một trợ lý học tập AI xuất sắc. "
            "Nhiệm vụ của bạn là tóm tắt tài liệu.\n"
            "- Tuyệt đối không bịa đặt thông tin ngoài tài liệu.\n"
            "- Giữ nguyên các thuật ngữ chuyên ngành.\n\n"
        )

        levels = {
            "short": "Mức độ: Hãy tóm tắt rất ngắn gọn, tối đa 300 từ.",
            "normal": "Mức độ: Hãy giữ đầy đủ các ý chính của tài liệu.",
            "detailed": "Mức độ: Hãy giải thích kỹ các khái niệm, đi sâu vào chi tiết.",
        }

        formats = {
            "paragraph": (
                "Định dạng: Trình bày dưới dạng các đoạn văn liên tục, dễ đọc."
            ),
            "bullet": (
                "Định dạng: Trình bày hoàn toàn dưới dạng gạch đầu dòng (bullet points)."
            ),
            "markdown": (
                "Định dạng: Sử dụng Markdown (Heading 1, 2, in đậm, list, table) để trình bày đẹp mắt."
            ),
        }

        instruction_prompt = (
            f"Yêu cầu bổ sung từ người dùng: {instruction}\n" if instruction else ""
        )

        return (
            f"{base_prompt}"
            "--- CẤU HÌNH ---\n"
            f"{levels.get(level.lower(), levels['normal'])}\n"
            f"{formats.get(format_type.lower(), formats['markdown'])}\n"
            f"{instruction_prompt}\n"
            "--- NỘI DUNG TÀI LIỆU ---\n"
            f"{content}"
        )
