import pytest

from calculator.memory import MemoryRegister


def test_starts_empty():
    register = MemoryRegister()
    assert register.is_set is False
    assert register.recall() == 0.0


def test_initial_value_marks_register_as_set():
    register = MemoryRegister(4)
    assert register.is_set is True
    assert register.value == 4.0


def test_store_replaces_value():
    register = MemoryRegister()
    register.store(3)
    assert register.store(7.5) == 7.5
    assert register.recall() == 7.5


def test_add_and_subtract_accumulate():
    register = MemoryRegister()
    register.add(10)
    register.subtract(2.5)
    assert register.recall() == pytest.approx(7.5)
    assert register.is_set is True


def test_subtract_on_empty_register_starts_from_zero():
    register = MemoryRegister()
    assert register.subtract(4) == -4.0


def test_clear_resets_value_and_flag():
    register = MemoryRegister(9)
    register.clear()
    assert register.value == 0.0
    assert register.is_set is False
