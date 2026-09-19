# tests/test_state_machine.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.state_machine import can_transition, validate_and_transition, VALID_TRANSITIONS
from backend.incident_logger import log_transition, get_logs, get_all_logs

def test_valid_forward_transitions():
    assert can_transition("DETECTED", "CLASSIFIED")
    assert can_transition("CLASSIFIED", "ASSESSED")
    assert can_transition("ASSESSED", "ALERTED")
    assert can_transition("ALERTED", "ACKNOWLEDGED")
    assert can_transition("ACKNOWLEDGED", "RESOLVED")

def test_invalid_transitions():
    assert not can_transition("DETECTED", "RESOLVED")
    assert not can_transition("DETECTED", "ALERTED")
    assert not can_transition("RESOLVED", "DETECTED")
    assert not can_transition("ACKNOWLEDGED", "CLASSIFIED")

def test_responder_sub_states():
    assert can_transition("ACKNOWLEDGED", "EN_ROUTE")
    assert can_transition("EN_ROUTE", "ARRIVED")
    assert can_transition("ARRIVED", "CONTAINED")
    assert can_transition("CONTAINED", "RESOLVED")

def test_responder_invalid():
    assert not can_transition("DETECTED", "EN_ROUTE")
    assert not can_transition("EN_ROUTE", "RESOLVED")

def test_validate_and_transition_success():
    result = validate_and_transition("INC-001", "DETECTED", "CLASSIFIED", "system", "Auto-classified")
    assert result["old_status"] == "DETECTED"
    assert result["new_status"] == "CLASSIFIED"
    assert result["changed_by"] == "system"
    assert result["incident_id"] == "INC-001"

def test_validate_and_transition_failure():
    try:
        validate_and_transition("INC-001", "DETECTED", "RESOLVED", "system")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "DETECTED" in str(e) and "RESOLVED" in str(e)

def test_terminal_state():
    assert not can_transition("RESOLVED", "DETECTED")
    assert not can_transition("RESOLVED", "ACKNOWLEDGED")

def test_log_writes_and_reads():
    record = validate_and_transition("INC-TEST-001", "DETECTED", "CLASSIFIED", "system", "auto")
    log_transition(record)
    logs = get_logs("INC-TEST-001")
    assert len(logs) >= 1
    assert logs[-1]["new_status"] == "CLASSIFIED"
    assert logs[-1]["incident_id"] == "INC-TEST-001"

def test_log_all():
    all_logs = get_all_logs()
    assert isinstance(all_logs, list)

if __name__ == "__main__":
    test_valid_forward_transitions()
    test_invalid_transitions()
    test_responder_sub_states()
    test_responder_invalid()
    test_validate_and_transition_success()
    test_validate_and_transition_failure()
    test_terminal_state()
    test_log_writes_and_reads()
    test_log_all()
    print("All state_machine tests passed")
