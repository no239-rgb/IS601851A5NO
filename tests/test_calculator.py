import datetime
from pathlib import Path
import pandas as pd
import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from decimal import Decimal
from tempfile import TemporaryDirectory
from app.calculator import Calculator
from app.calculator_repl import calculator_repl
from app.calculator_config import CalculatorConfig
from app.exceptions import OperationError, ValidationError
from app.history import LoggingObserver, AutoSaveObserver
from app.operations import OperationFactory

# Fixture to initialize Calculator with a temporary directory for file paths
@pytest.fixture
def calculator():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config = CalculatorConfig(base_dir=temp_path)

        # Patch properties to use the temporary directory paths
        with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
             patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file, \
             patch.object(CalculatorConfig, 'history_dir', new_callable=PropertyMock) as mock_history_dir, \
             patch.object(CalculatorConfig, 'history_file', new_callable=PropertyMock) as mock_history_file:
            
            # Set return values to use paths within the temporary directory
            mock_log_dir.return_value = temp_path / "logs"
            mock_log_file.return_value = temp_path / "logs/calculator.log"
            mock_history_dir.return_value = temp_path / "history"
            mock_history_file.return_value = temp_path / "history/calculator_history.csv"
            
            # Return an instance of Calculator with the mocked config
            yield Calculator(config=config)

# Test Calculator Initialization

def test_calculator_initialization(calculator):
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []
    assert calculator.operation_strategy is None

# Test Logging Setup

@patch('app.calculator.logging.info')
def test_logging_setup(logging_info_mock):
    with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
         patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file:
        mock_log_dir.return_value = Path('/tmp/logs')
        mock_log_file.return_value = Path('/tmp/logs/calculator.log')
        
        # Instantiate calculator to trigger logging
        calculator = Calculator(CalculatorConfig())
        logging_info_mock.assert_any_call("Calculator initialized with configuration")

# Test Adding and Removing Observers

def test_add_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    assert observer in calculator.observers

def test_remove_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    calculator.remove_observer(observer)
    assert observer not in calculator.observers

# Test Setting Operations

def test_set_operation(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    assert calculator.operation_strategy == operation

# Test Performing Operations

def test_perform_operation_addition(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    result = calculator.perform_operation(2, 3)
    assert result == Decimal('5')

def test_perform_operation_validation_error(calculator):
    calculator.set_operation(OperationFactory.create_operation('add'))
    with pytest.raises(ValidationError):
        calculator.perform_operation('invalid', 3)

def test_perform_operation_operation_error(calculator):
    with pytest.raises(OperationError, match="No operation set"):
        calculator.perform_operation(2, 3)

# Test Undo/Redo Functionality

def test_undo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    assert calculator.history == []

def test_redo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    calculator.redo()
    assert len(calculator.history) == 1

# Test History Management

@patch('app.calculator.pd.DataFrame.to_csv')
def test_save_history(mock_to_csv, calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.save_history()
    mock_to_csv.assert_called_once()

@patch('app.calculator.pd.read_csv')
@patch('app.calculator.Path.exists', return_value=True)
def test_load_history(mock_exists, mock_read_csv, calculator):
    # Mock CSV data to match the expected format in from_dict
    mock_read_csv.return_value = pd.DataFrame({
        'operation': ['Addition'],
        'operand1': ['2'],
        'operand2': ['3'],
        'result': ['5'],
        'timestamp': [datetime.datetime.now().isoformat()]
    })
    
    # Test the load_history functionality
    try:
        calculator.load_history()
        # Verify history length after loading
        assert len(calculator.history) == 1
        # Verify the loaded values
        assert calculator.history[0].operation == "Addition"
        assert calculator.history[0].operand1 == Decimal("2")
        assert calculator.history[0].operand2 == Decimal("3")
        assert calculator.history[0].result == Decimal("5")
    except OperationError:
        pytest.fail("Loading history failed due to OperationError")
        
            
# Test Clearing History

def test_clear_history(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.clear_history()
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []

# Test REPL Commands (using patches for input/output handling)

@patch('builtins.input', side_effect=['exit'])
@patch('builtins.print')
def test_calculator_repl_exit(mock_print, mock_input):
    with patch('app.calculator.Calculator.save_history') as mock_save_history:
        calculator_repl()
        mock_save_history.assert_called_once()
        mock_print.assert_any_call("History saved successfully.")
        mock_print.assert_any_call("Goodbye!")

@patch('builtins.input', side_effect=['help', 'exit'])
@patch('builtins.print')
def test_calculator_repl_help(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("\nAvailable commands:")

@patch('builtins.input', side_effect=['add', '2', '3', 'exit'])
@patch('builtins.print')
def test_calculator_repl_addition(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("\nResult: 5")

# Test History Loading Error Handling

@patch('app.calculator.logging.warning')
@patch('app.calculator.Calculator.load_history')
def test_load_history_exception_logging(mock_load_history, mock_logging_warning):
    """
    Test that when load_history raises an exception during initialization,
    it is caught and logged as a warning.
    """
    # Simulate load_history raising an exception
    mock_load_history.side_effect = Exception("Corrupted history file")

    with TemporaryDirectory() as temp_dir:
        config = CalculatorConfig(base_dir=Path(temp_dir))
        Calculator(config=config)

    # Verify that logging.warning was called with the exact expected error string
    mock_logging_warning.assert_called_once_with("Could not load existing history: Corrupted history file")

# Test Logging Setup Failure

@patch('app.calculator.logging.basicConfig')
def test_setup_logging_failure(mock_basic_config, capsys):
    """
    Test that if logging setup raises an exception, the error message is printed
    and the exception is re-raised.
    """
    # Force logging setup to throw an Exception
    mock_basic_config.side_effect = Exception("Permission denied")

    # Verify that the exception is re-raised
    with pytest.raises(Exception, match="Permission denied"):
        with TemporaryDirectory() as temp_dir:
            config = CalculatorConfig(base_dir=Path(temp_dir))
            Calculator(config=config)

    # Capture stdout to verify the printed error message
    captured = capsys.readouterr()
    assert "Error setting up logging: Permission denied" in captured.out

def test_max_history_size_trimming(calculator):
    """
    Test that when calculation history exceeds max_history_size,
    the oldest calculation (first element) is removed.
    """
    calculator.config.max_history_size = 2
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)

    calculator.perform_operation(1, 1)
    calculator.perform_operation(2, 2)
    calculator.perform_operation(3, 3)

    assert len(calculator.history) == 2
    assert calculator.history[0].result == Decimal('4')
    assert calculator.history[1].result == Decimal('6')

@patch('app.calculator.logging.error')
def test_perform_operation_generic_exception(mock_logging_error, calculator):
    """
    Test that any non-validation exception during execution is caught,
    logged as an error, and re-raised as an OperationError.
    """
    # 1. Setup a valid operation
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)

    # 2. Mock the inner execute method to force a generic Exception to occur
    with patch.object(operation, 'execute', side_effect=Exception("Database disconnected")):
        
        # 3. Verify it gets wrapped and re-raised as an OperationError
        with pytest.raises(OperationError, match="Operation failed: Database disconnected"):
            calculator.perform_operation(10, 5)

    # 4. Verify the exact string was sent to logging.error
    mock_logging_error.assert_called_once_with("Operation failed: Database disconnected")

# Test Saving Empty History

@patch('app.calculator.logging.info')
@patch('app.calculator.pd.DataFrame.to_csv')
def test_save_history_empty(mock_to_csv, mock_logging_info, calculator):
    """
    Test saving history when calculator history is empty.
    Verifies that an empty CSV structure is saved and logged.
    """
    calculator.history = []

    calculator.save_history()

    # Verify to_csv was called for the empty DataFrame
    mock_to_csv.assert_called_once_with(calculator.config.history_file, index=False)
    # Verify the empty history log message was sent
    mock_logging_info.assert_called_with("Empty history saved")

# Test Save History Exception Handling

@patch('app.calculator.logging.error')
@patch('app.calculator.pd.DataFrame.to_csv', side_effect=Exception("Disk full"))
def test_save_history_exception(mock_to_csv, mock_logging_error, calculator):
    """
    Test that exceptions during save_history are caught, logged,
    and re-raised as OperationError.
    """
    with pytest.raises(OperationError, match="Failed to save history: Disk full"):
        calculator.save_history()

    # Verify that logging.error was called with the exact message format
    mock_logging_error.assert_called_once_with("Failed to save history: Disk full")

@patch('app.calculator.logging.info')
@patch('app.calculator.pd.read_csv')
@patch.object(Path, 'exists', return_value=True)
def test_load_history_empty_file(mock_exists, mock_read_csv, mock_logging_info, calculator):
    """
    Test loading history when the file exists but contains no records (empty DataFrame).
    Verifies that 'Loaded empty history file' is logged.
    """
    # 1. Mock pd.read_csv to return an empty DataFrame (headers only)
    mock_read_csv.return_value = pd.DataFrame(
        columns=['operation', 'operand1', 'operand2', 'result', 'timestamp']
    )

    # 2. Execute load_history
    calculator.load_history()

    # 3. Verify logging.info received the expected message
    mock_logging_info.assert_called_with("Loaded empty history file")

@patch('app.calculator.logging.error')
@patch('app.calculator.pd.read_csv', side_effect=Exception("Corrupted CSV file"))
@patch.object(Path, 'exists', return_value=True)
def test_load_history_exception(mock_exists, mock_read_csv, mock_logging_error, calculator):
    """
    Test that exceptions during load_history are caught, logged as errors,
    and re-raised as an OperationError.
    """
    with pytest.raises(OperationError, match="Failed to load history: Corrupted CSV file"):
        calculator.load_history()

    # Verify that logging.error was called with the exact formatted message
    mock_logging_error.assert_called_once_with("Failed to load history: Corrupted CSV file")

def test_history_to_dataframe(calculator):
    """
    Test converting history entries into a pandas DataFrame with populated history.
    """
    # 1. Create mock Calculation instances
    calc1 = MagicMock()
    calc1.operation = "add"
    calc1.operand1 = 10
    calc1.operand2 = 5
    calc1.result = 15
    calc1.timestamp = "2026-10-07T10:00:00"

    calc2 = MagicMock()
    calc2.operation = "multiply"
    calc2.operand1 = 2
    calc2.operand2 = 4
    calc2.result = 8
    calc2.timestamp = "2026-10-07T10:05:00"

    calculator.history = [calc1, calc2]

    # 2. Call the method (adjust method name if different, e.g., calculator.get_history_dataframe())
    df = calculator.get_history_dataframe()

    # 3. Assertions
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ['operation', 'operand1', 'operand2', 'result', 'timestamp']
    
    # Check string conversions and row contents
    assert df.iloc[0]['operation'] == 'add'
    assert df.iloc[0]['operand1'] == '10'
    assert df.iloc[0]['operand2'] == '5'
    assert df.iloc[0]['result'] == '15'
    assert df.iloc[0]['timestamp'] == '2026-10-07T10:00:00'


def test_history_to_dataframe_empty(calculator):
    """
    Test converting history to a pandas DataFrame when history is empty.
    """
    calculator.history = []

    df = calculator.get_history_dataframe()

    assert isinstance(df, pd.DataFrame)
    assert df.empty

def test_show_history_populated(calculator):
    """
    Test that show_history returns correctly formatted string representations
    for calculations stored in history.
    """
    calc1 = MagicMock()
    calc1.operation = "add"
    calc1.operand1 = 10
    calc1.operand2 = 5
    calc1.result = 15

    calc2 = MagicMock()
    calc2.operation = "multiply"
    calc2.operand1 = 3
    calc2.operand2 = 4
    calc2.result = 12

    calculator.history = [calc1, calc2]

    result = calculator.show_history()

    assert result == [
        "add(10, 5) = 15",
        "multiply(3, 4) = 12"
    ]

def test_show_history_empty(calculator):
    """
    Test that show_history returns an empty list when history is empty.
    """
    calculator.history = []

    result = calculator.show_history()

    assert result == []

def test_undo_empty_stack(calculator):
    """
    Test that calling undo when the undo stack is empty returns False.
    """
    calculator.undo_stack = []

    result = calculator.undo()

    assert result is False

def test_redo_empty_stack(calculator):
    """
    Test that calling redo when the redo stack is empty returns False.
    """
    calculator.redo_stack = []

    result = calculator.redo()

    assert result is False