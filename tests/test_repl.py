import builtins
from decimal import Decimal
from unittest.mock import MagicMock, patch
import pytest

from app.calculator_repl import calculator_repl
from app.exceptions import OperationError, ValidationError


@patch('builtins.input', side_effect=['help', 'exit'])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_help_command(mock_calculator, mock_print, mock_input):
    """
    Test the 'help' command displays available commands and then exits.
    """
    calculator_repl()

    mock_print.assert_any_call("\nAvailable commands:")
    mock_print.assert_any_call("Goodbye!")


@patch('builtins.input', side_effect=['exit'])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_exit_save_success(mock_calculator, mock_print, mock_input):
    """
    Test exiting the REPL when saving history succeeds.
    """
    mock_calc_instance = mock_calculator.return_value

    calculator_repl()

    mock_calc_instance.save_history.assert_called_once()
    mock_print.assert_any_call("History saved successfully.")
    mock_print.assert_any_call("Goodbye!")


@patch('builtins.input', side_effect=['exit'])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_exit_save_error(mock_calculator, mock_print, mock_input):
    """
    Test exiting the REPL when saving history raises an exception.
    """
    mock_calc_instance = mock_calculator.return_value
    mock_calc_instance.save_history.side_effect = Exception("Disk full")

    calculator_repl()

    mock_print.assert_any_call("Warning: Could not save history: Disk full")
    mock_print.assert_any_call("Goodbye!")


@patch('builtins.input', side_effect=['history', 'exit'])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_history_empty(mock_calculator, mock_print, mock_input):
    """
    Test 'history' command when calculation history is empty.
    """
    mock_calc_instance = mock_calculator.return_value
    mock_calc_instance.show_history.return_value = []

    calculator_repl()

    mock_print.assert_any_call("No calculations in history")


@patch('builtins.input', side_effect=['history', 'exit'])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_history_populated(mock_calculator, mock_print, mock_input):
    """
    Test 'history' command when calculation history contains entries.
    """
    mock_calc_instance = mock_calculator.return_value
    mock_calc_instance.show_history.return_value = ["add(10, 5) = 15"]

    calculator_repl()

    mock_print.assert_any_call("\nCalculation History:")
    mock_print.assert_any_call("1. add(10, 5) = 15")


@patch('builtins.input', side_effect=['clear', 'exit'])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_clear_command(mock_calculator, mock_print, mock_input):
    """
    Test the 'clear' command resets calculator history.
    """
    mock_calc_instance = mock_calculator.return_value

    calculator_repl()

    mock_calc_instance.clear_history.assert_called_once()
    mock_print.assert_any_call("History cleared")


@patch('builtins.input', side_effect=['undo', 'undo', 'exit'])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_undo_command(mock_calculator, mock_print, mock_input):
    """
    Test 'undo' command handling both successful undo and empty stack scenarios.
    """
    mock_calc_instance = mock_calculator.return_value
    mock_calc_instance.undo.side_effect = [True, False]

    calculator_repl()

    mock_print.assert_any_call("Operation undone")
    mock_print.assert_any_call("Nothing to undo")


@patch('builtins.input', side_effect=['redo', 'redo', 'exit'])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_redo_command(mock_calculator, mock_print, mock_input):
    """
    Test 'redo' command handling both successful redo and empty stack scenarios.
    """
    mock_calc_instance = mock_calculator.return_value
    mock_calc_instance.redo.side_effect = [True, False]

    calculator_repl()

    mock_print.assert_any_call("Operation redone")
    mock_print.assert_any_call("Nothing to redo")


@patch('builtins.input', side_effect=['save', 'save', 'load', 'load', 'exit'])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_save_and_load_commands(mock_calculator, mock_print, mock_input):
    """
    Test 'save' and 'load' commands for success and exception error paths.
    """
    mock_calc_instance = mock_calculator.return_value

    mock_calc_instance.save_history.side_effect = [None, Exception("Save failed")]
    mock_calc_instance.load_history.side_effect = [None, Exception("Load failed")]

    calculator_repl()

    mock_print.assert_any_call("History saved successfully")
    mock_print.assert_any_call("Error saving history: Save failed")
    mock_print.assert_any_call("History loaded successfully")
    mock_print.assert_any_call("Error loading history: Load failed")


@patch('app.calculator_repl.OperationFactory.create_operation')
@patch('builtins.input', side_effect=[
    'add', 'cancel',         # Cancel on first operand
    'add', '10', 'cancel',  # Cancel on second operand
    'add', '10.00', '5.00', # Successful operation with Decimal normalization
    'exit'
])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_arithmetic_operations_and_cancel(mock_calculator, mock_print, mock_input, mock_create_operation):
    """
    Test arithmetic operations, input cancellation, and Decimal normalization on result.
    """
    mock_calc_instance = mock_calculator.return_value
    mock_calc_instance.perform_operation.return_value = Decimal('15.00')

    calculator_repl()

    mock_print.assert_any_call("Operation cancelled")
    mock_print.assert_any_call("\nResult: 15")


@patch('app.calculator_repl.OperationFactory.create_operation')
@patch('builtins.input', side_effect=[
    'add', '10', 'abc',  # Triggers ValidationError
    'add', '10', '0',    # Triggers OperationError
    'add', '5', '5',     # Triggers generic Exception
    'exit'
])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_arithmetic_operation_exceptions(mock_calculator, mock_print, mock_input, mock_create_operation):
    """
    Test arithmetic operations raising ValidationError, OperationError, and generic Exception.
    """
    mock_calc_instance = mock_calculator.return_value
    mock_calc_instance.perform_operation.side_effect = [
        ValidationError("Invalid number"),
        OperationError("Division by zero"),
        Exception("Unexpected arithmetic error")
    ]

    calculator_repl()

    mock_print.assert_any_call("Error: Invalid number")
    mock_print.assert_any_call("Error: Division by zero")
    mock_print.assert_any_call("Unexpected error: Unexpected arithmetic error")


@patch('builtins.input', side_effect=[
    'invalid_cmd',       # Unknown command branch
    KeyboardInterrupt,   # KeyboardInterrupt catch block
    EOFError             # EOFError break block
])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_unknown_command_and_interrupts(mock_calculator, mock_print, mock_input):
    """
    Test unknown command handling, KeyboardInterrupt (Ctrl+C), and EOFError (Ctrl+D).
    """
    calculator_repl()

    mock_print.assert_any_call("Unknown command: 'invalid_cmd'. Type 'help' for available commands.")
    mock_print.assert_any_call("\nOperation cancelled")
    mock_print.assert_any_call("\nInput terminated. Exiting...")

@patch('app.calculator_repl.logging.error')
@patch('app.calculator_repl.Calculator', side_effect=Exception("Initialization failed"))
@patch('builtins.print')
def test_repl_fatal_initialization_error(mock_print, mock_calculator, mock_logging_error):
    """
    Test fatal error during calculator initialization logs error and re-raises exception.
    """
    with pytest.raises(Exception, match="Initialization failed"):
        calculator_repl()

    mock_print.assert_called_once_with("Fatal error: Initialization failed")
    mock_logging_error.assert_called_once_with("Fatal error in calculator REPL: Initialization failed")

@patch('builtins.input', side_effect=['clear', 'exit'])
@patch('builtins.print')
@patch('app.calculator_repl.Calculator')
def test_repl_inner_unexpected_exception(mock_calculator, mock_print, mock_input):
    """
    Test the REPL inner loop generic exception handler when an unhandled 
    exception occurs during command processing.
    """
    mock_calc_instance = mock_calculator.return_value
    mock_calc_instance.clear_history.side_effect = Exception("Unexpected inner error")

    calculator_repl()

    mock_print.assert_any_call("Error: Unexpected inner error")
    mock_print.assert_any_call("Goodbye!")
