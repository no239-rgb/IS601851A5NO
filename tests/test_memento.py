import datetime
from unittest.mock import MagicMock, patch
import pytest

from app.calculator_memento import CalculatorMemento


def test_memento_initialization():
    """
    Test basic instantiation and default timestamp factory generation.
    """
    history = []
    memento = CalculatorMemento(history=history)

    assert memento.history == history
    assert isinstance(memento.timestamp, datetime.datetime)


def test_memento_to_dict_empty():
    """
    Test serialization to dictionary when history is empty.
    """
    timestamp = datetime.datetime(2026, 10, 7, 10, 0, 0)
    memento = CalculatorMemento(history=[], timestamp=timestamp)

    result = memento.to_dict()

    assert result == {
        'history': [],
        'timestamp': "2026-10-07T10:00:00"
    }


def test_memento_to_dict_populated():
    """
    Test serialization to dictionary with populated history list.
    """
    calc1 = MagicMock()
    calc1.to_dict.return_value = {
        'operation': 'add',
        'operand1': '10',
        'operand2': '5',
        'result': '15',
        'timestamp': '2026-10-07T10:00:00'
    }

    timestamp = datetime.datetime(2026, 10, 7, 10, 5, 0)
    memento = CalculatorMemento(history=[calc1], timestamp=timestamp)

    result = memento.to_dict()

    assert result == {
        'history': [
            {
                'operation': 'add',
                'operand1': '10',
                'operand2': '5',
                'result': '15',
                'timestamp': '2026-10-07T10:00:00'
            }
        ],
        'timestamp': '2026-10-07T10:05:00'
    }
    calc1.to_dict.assert_called_once()


def test_memento_from_dict_empty():
    """
    Test deserialization from dictionary when history data is empty.
    """
    data = {
        'history': [],
        'timestamp': '2026-10-07T11:00:00'
    }

    memento = CalculatorMemento.from_dict(data)

    assert memento.history == []
    assert memento.timestamp == datetime.datetime(2026, 10, 7, 11, 0, 0)


@patch('app.calculator_memento.Calculation.from_dict')
def test_memento_from_dict_populated(mock_calc_from_dict):
    """
    Test deserialization from dictionary with serialized calculation items.
    """
    mock_calc_obj = MagicMock()
    mock_calc_from_dict.return_value = mock_calc_obj

    calc_dict = {
        'operation': 'multiply',
        'operand1': '3',
        'operand2': '4',
        'result': '12',
        'timestamp': '2026-10-07T10:00:00'
    }
    data = {
        'history': [calc_dict],
        'timestamp': '2026-10-07T11:30:00'
    }

    memento = CalculatorMemento.from_dict(data)

    assert memento.history == [mock_calc_obj]
    assert memento.timestamp == datetime.datetime(2026, 10, 7, 11, 30, 0)
    mock_calc_from_dict.assert_called_once_with(calc_dict)