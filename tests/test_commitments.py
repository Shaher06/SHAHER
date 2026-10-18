from datetime import datetime, timedelta

import pytest

from app.database.db import connect
from app.services.commitment_service import CommitmentService
from app.utils.validation import ValidationError

D = datetime


def test_create_and_read(commitments):
    c = commitments.create("  دفع الإيجار ", "تفاصيل", D(2026, 10, 15, 9, 30), "high", "فواتير")
    assert c.id and c.title == "دفع الإيجار"
    assert (c.priority, c.category, c.status) == ("high", "فواتير", "open")
    assert c.due_at == D(2026, 10, 15, 9, 30)


@pytest.mark.parametrize("kwargs,fragment", [
    (dict(title="   "), "عنوان"),
    (dict(due_at=None), "تاريخ"),
    (dict(priority="urgent"), "أولوية"),
    (dict(title="ع" * 500), "طويل"),
])
def test_validation_errors_are_arabic_and_nothing_saved(commitments, conn, kwargs, fragment):
    args = dict(title="مهمة", description="", due_at=D(2026, 10, 15, 9, 0), priority="medium", category="")
    args.update(kwargs)
    with pytest.raises(ValidationError) as e:
        commitments.create(**args)
    assert fragment in str(e.value)
    assert conn.execute("SELECT COUNT(*) FROM commitments").fetchone()[0] == 0


def test_duplicate_submission_prevented(commitments):
    commitments.create("مهمة", "", D(2026, 10, 15, 9, 0))
    with pytest.raises(ValidationError):
        commitments.create("مهمة", "", D(2026, 10, 15, 9, 0))
    assert len(commitments.list("all")) == 1


def test_edit(commitments, clock):
    c = commitments.create("قديم", "", D(2026, 10, 15, 9, 0), "low", "أ")
    clock.set(D(2026, 10, 13, 12, 5))
    e = commitments.update(c.id, "جديد", "وصف", D(2026, 10, 16, 18, 0), "high", "ب")
    assert (e.title, e.description, e.priority, e.category) == ("جديد", "وصف", "high", "ب")
    assert e.due_at == D(2026, 10, 16, 18, 0)
    assert e.updated_at > e.created_at


def test_complete_and_reopen_preserve_record(commitments, clock):
    c = commitments.create("مهمة", "", D(2026, 10, 15, 9, 0))
    clock.set(D(2026, 10, 14, 8, 0))
    done = commitments.complete(c.id)
    assert done.status == "completed" and done.completed_at == D(2026, 10, 14, 8, 0)
    assert commitments.list("completed")[0].id == c.id
    assert commitments.list("all") == []
    reopened = commitments.reopen(c.id)
    assert reopened.status == "open" and reopened.completed_at is None
    assert reopened.title == "مهمة"


def test_cannot_complete_twice_or_reopen_open(commitments):
    c = commitments.create("مهمة", "", D(2026, 10, 15, 9, 0))
    with pytest.raises(ValidationError):
        commitments.reopen(c.id)
    commitments.complete(c.id)
    with pytest.raises(ValidationError):
        commitments.complete(c.id)


def test_overdue_calculation(commitments, clock):
    commitments.create("فات", "", D(2026, 10, 13, 11, 59))
    commitments.create("الآن بالضبط", "", D(2026, 10, 13, 12, 0))
    commitments.create("بعد قليل", "", D(2026, 10, 13, 12, 1))
    assert [c.title for c in commitments.list("overdue")] == ["فات"]
    clock.set(D(2026, 10, 13, 12, 30))
    assert {c.title for c in commitments.list("overdue")} == {"فات", "الآن بالضبط", "بعد قليل"}


def test_completed_and_archived_are_never_overdue(commitments):
    a = commitments.create("أ", "", D(2026, 10, 1, 9, 0))
    b = commitments.create("ب", "", D(2026, 10, 2, 9, 0))
    commitments.complete(a.id)
    commitments.archive(b.id)
    assert commitments.list("overdue") == []
    assert commitments.counts()["overdue"] == 0


def test_today_upcoming_partition(commitments):
    commitments.create("اليوم مساءً", "", D(2026, 10, 13, 20, 0))
    commitments.create("آخر اليوم", "", D(2026, 10, 13, 23, 59))
    commitments.create("غدًا فجرًا", "", D(2026, 10, 14, 0, 0))
    commitments.create("الأسبوع القادم", "", D(2026, 10, 20, 9, 0))
    commitments.create("أمس", "", D(2026, 10, 12, 9, 0))
    assert [c.title for c in commitments.list("today")] == ["اليوم مساءً", "آخر اليوم"]
    assert [c.title for c in commitments.list("upcoming")] == ["غدًا فجرًا", "الأسبوع القادم"]
    assert [c.title for c in commitments.list("overdue")] == ["أمس"]
    assert commitments.counts() == {"today": 2, "overdue": 1, "upcoming": 2, "completed": 0}


def test_search_and_filters(commitments):
    commitments.create("اجتماع الفريق", "جدول الأعمال", D(2026, 10, 15, 9, 0), "high", "عمل")
    commitments.create("شراء خبز", "", D(2026, 10, 15, 10, 0), "low", "بيت")
    commitments.create("تقرير شهري", "للاجتماع", D(2026, 10, 16, 10, 0), "high", "عمل")
    assert {c.title for c in commitments.list("all", query="اجتماع")} == {"اجتماع الفريق", "تقرير شهري"}
    assert [c.title for c in commitments.list("all", priority="low")] == ["شراء خبز"]
    assert len(commitments.list("all", category="عمل")) == 2
    assert [c.title for c in commitments.list("all", query="اجتماع", priority="high", category="عمل")] \
        == ["اجتماع الفريق", "تقرير شهري"]
    assert commitments.categories() == ["بيت", "عمل"]


def test_archive_restore_and_delete(commitments):
    c = commitments.create("مهمة", "", D(2026, 10, 15, 9, 0))
    commitments.complete(c.id)
    a = commitments.archive(c.id)
    assert a.status == "archived" and a.completed_at is not None and a.archived_at is not None
    assert commitments.list("archived")[0].id == c.id
    assert commitments.restore(c.id).status == "completed"
    commitments.delete(c.id)
    assert commitments.get(c.id) is None


def test_data_persists_after_reconnecting(db_path, clock):
    first = connect(db_path)
    svc = CommitmentService(first, None, clock.now)
    c = svc.create("باقٍ", "", D(2026, 10, 15, 9, 0), "high", "عمل")
    svc.complete(c.id)
    first.close()
    second = connect(db_path)
    again = CommitmentService(second, None, clock.now).get(c.id)
    assert again.title == "باقٍ" and again.status == "completed" and again.priority == "high"


def test_focus_list_orders_overdue_first(commitments):
    commitments.create("قادم", "", D(2026, 10, 20, 9, 0))
    commitments.create("متأخر", "", D(2026, 10, 12, 9, 0))
    commitments.create("اليوم", "", D(2026, 10, 13, 18, 0))
    assert [c.title for c in commitments.focus_list()] == ["متأخر", "اليوم", "قادم"]


def test_unknown_view_rejected(commitments):
    with pytest.raises(ValueError):
        commitments.list("nonsense")
