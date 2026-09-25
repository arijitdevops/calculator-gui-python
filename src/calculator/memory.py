"""The calculator's single memory register (MC, MR, M+, M-, MS)."""

from __future__ import annotations

from typing import Optional

__all__ = ["MemoryRegister"]


class MemoryRegister:
    """A one-slot numeric memory, matching the behaviour of a desk calculator.

    The register starts empty.  ``MR`` on an empty register returns ``0.0`` but
    :attr:`is_set` stays ``False`` so the UI can dim its indicator.
    """

    def __init__(self, initial: Optional[float] = None) -> None:
        self._value: float = float(initial) if initial is not None else 0.0
        self._is_set: bool = initial is not None

    @property
    def value(self) -> float:
        """The stored value; ``0.0`` while the register is empty."""
        return self._value

    @property
    def is_set(self) -> bool:
        """Whether anything has been stored since the last :meth:`clear`."""
        return self._is_set

    def clear(self) -> None:
        """MC - forget the stored value."""
        self._value = 0.0
        self._is_set = False

    def recall(self) -> float:
        """MR - return the stored value."""
        return self._value

    def store(self, value: float) -> float:
        """MS - replace the stored value."""
        self._value = float(value)
        self._is_set = True
        return self._value

    def add(self, value: float) -> float:
        """M+ - add to the stored value."""
        self._value += float(value)
        self._is_set = True
        return self._value

    def subtract(self, value: float) -> float:
        """M- - subtract from the stored value."""
        self._value -= float(value)
        self._is_set = True
        return self._value

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        state = f"{self._value!r}" if self._is_set else "empty"
        return f"MemoryRegister({state})"
