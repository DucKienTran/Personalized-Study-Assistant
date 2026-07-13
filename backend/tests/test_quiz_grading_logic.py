from app.services.ai.quiz_service import QuizService


class DummyDB:
    def query(self, *_args, **_kwargs):
        raise AssertionError("_grade_logic là pure logic, không được đụng DB")


class DummyDocumentService:
    pass


class DummyAIClient:
    pass


def _service() -> QuizService:
    return QuizService(DummyDB(), DummyDocumentService(), DummyAIClient())


# ── multiple_choice ──────────────────────────────────────────────


def test_multiple_choice_correct():
    service = _service()
    assert service._grade_logic("multiple_choice", "A", "A") is True


def test_multiple_choice_case_insensitive():
    service = _service()
    assert service._grade_logic("multiple_choice", "A", "a") is True


def test_multiple_choice_wrong():
    service = _service()
    assert service._grade_logic("multiple_choice", "A", "B") is False


# ── multiple_response ────────────────────────────────────────────


def test_multiple_response_exact_match():
    service = _service()
    assert service._grade_logic("multiple_response", ["A", "C"], ["A", "C"]) is True


def test_multiple_response_order_does_not_matter():
    service = _service()
    assert service._grade_logic("multiple_response", ["A", "C"], ["C", "A"]) is True


def test_multiple_response_missing_one_answer_is_wrong():
    service = _service()
    assert service._grade_logic("multiple_response", ["A", "C"], ["A"]) is False


def test_multiple_response_extra_answer_is_wrong():
    service = _service()
    assert (
        service._grade_logic("multiple_response", ["A", "C"], ["A", "C", "D"]) is False
    )


def test_multiple_response_wrong_type_returns_false():
    # correct_answer là list nhưng user gửi string thay vì list -> phải False, không crash
    service = _service()
    assert service._grade_logic("multiple_response", ["A", "C"], "A") is False


# ── true_false ────────────────────────────────────────────────────


def test_true_false_boolean_match():
    service = _service()
    assert service._grade_logic("true_false", True, True) is True


def test_true_false_string_variants():
    service = _service()
    assert service._grade_logic("true_false", True, "true") is True
    assert service._grade_logic("true_false", True, "1") is True
    assert service._grade_logic("true_false", False, "false") is True
    assert service._grade_logic("true_false", False, "0") is True


def test_true_false_unparseable_user_value_returns_false():
    service = _service()
    assert service._grade_logic("true_false", True, "khong_ro") is False


# ── fill_blank ────────────────────────────────────────────────────


def test_fill_blank_matches_any_acceptable_answer():
    service = _service()
    acceptable = ["Hà Nội", "thủ đô Hà Nội"]
    assert service._grade_logic("fill_blank", acceptable, "Hà Nội") is True
    assert service._grade_logic("fill_blank", acceptable, "thủ đô Hà Nội") is True


def test_fill_blank_case_and_whitespace_insensitive():
    service = _service()
    assert service._grade_logic("fill_blank", ["Hà Nội"], "  hà nội  ") is True


def test_fill_blank_no_match():
    service = _service()
    assert service._grade_logic("fill_blank", ["Hà Nội"], "Hồ Chí Minh") is False


def test_fill_blank_does_not_split_comma_inside_single_answer():
    # correct_answer chỉ có 1 đáp án chứa dấu phẩy -> KHÔNG được tách thành 2 đáp án riêng
    service = _service()
    acceptable = ["TCP/IP, Internet Protocol Suite"]
    assert service._grade_logic("fill_blank", acceptable, "TCP/IP") is False
    assert (
        service._grade_logic(
            "fill_blank", acceptable, "TCP/IP, Internet Protocol Suite"
        )
        is True
    )


# ── short_answer ──────────────────────────────────────────────────


def test_short_answer_exact_match():
    service = _service()
    assert service._grade_logic("short_answer", "3.14", "3.14") is True


def test_short_answer_accepts_comma_as_decimal_separator():
    service = _service()
    assert service._grade_logic("short_answer", "3.14", "3,14") is True
    assert service._grade_logic("short_answer", "0.5", "0,5") is True


def test_short_answer_wrong_value():
    service = _service()
    assert service._grade_logic("short_answer", "3.14", "3.15") is False


# ── chung ─────────────────────────────────────────────────────────


def test_none_user_answer_always_false_regardless_of_type():
    service = _service()
    for q_type in [
        "multiple_choice",
        "multiple_response",
        "true_false",
        "fill_blank",
        "short_answer",
    ]:
        assert service._grade_logic(q_type, "A", None) is False


def test_unknown_question_type_returns_false():
    service = _service()
    assert service._grade_logic("essay", ["ý 1", "ý 2"], "bài làm tự luận") is False
