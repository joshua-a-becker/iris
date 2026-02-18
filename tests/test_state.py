#!/usr/bin/env python3
"""
test_state.py - Unit tests for state_manager.py

Tests state management functionality including:
- Load/save operations
- Atomic writes and crash resilience
- Schema validation
- Merge operations
- Corrupted file recovery

Usage:
    python3 test_state.py
    python3 test_state.py -v  # Verbose output
"""

import sys
import os
import json
import tempfile
import unittest
from pathlib import Path

# Add state module to path
sys.path.insert(0, '/home/claude/iris/scripts/state')

from state_manager import (
    load_state,
    save_state,
    initialize_state,
    merge_state,
    get_state_schema
)


class TestStateManager(unittest.TestCase):
    """Test suite for state_manager.py"""

    def setUp(self):
        """Create temporary directory for test files"""
        self.test_dir = tempfile.mkdtemp(prefix='test_state_')
        self.test_file = os.path.join(self.test_dir, 'test_state.json')

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    # =========================================================================
    # Basic Operations
    # =========================================================================

    def test_initialize_state(self):
        """Test that initialize_state creates valid state structure"""
        state = initialize_state()

        # Check all required top-level keys
        required_keys = ['schema_version', 'last_updated', 'session',
                        'active_tasks', 'personality', 'recent_context', 'system']
        for key in required_keys:
            self.assertIn(key, state, f"Missing key: {key}")

        # Check nested structures
        self.assertIn('session_count', state['session'])
        self.assertIn('current_task', state['active_tasks'])
        self.assertIn('name', state['personality'])
        self.assertIn('last_email', state['recent_context'])
        self.assertIn('total_cycles', state['system'])

    def test_save_and_load_state(self):
        """Test basic save and load cycle"""
        state = initialize_state()
        state['session']['session_count'] = 42
        state['personality']['name'] = 'Iris'

        # Save
        result = save_state(state, self.test_file)
        self.assertTrue(result, "Save operation failed")
        self.assertTrue(os.path.exists(self.test_file), "State file not created")

        # Load
        loaded = load_state(self.test_file)
        self.assertEqual(loaded['session']['session_count'], 42)
        self.assertEqual(loaded['personality']['name'], 'Iris')

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file returns empty dict"""
        nonexistent = os.path.join(self.test_dir, 'does_not_exist.json')
        result = load_state(nonexistent)
        self.assertEqual(result, {}, "Should return empty dict for missing file")

    # =========================================================================
    # Atomic Write Tests
    # =========================================================================

    def test_atomic_write_no_temp_files(self):
        """Test that atomic writes don't leave temp files behind"""
        state = initialize_state()
        save_state(state, self.test_file)

        # Check for temp files
        temp_files = [f for f in os.listdir(self.test_dir)
                     if f.startswith('.state-') and f.endswith('.tmp')]
        self.assertEqual(len(temp_files), 0,
                        f"Temp files not cleaned up: {temp_files}")

    def test_atomic_write_overwrites_correctly(self):
        """Test that atomic writes correctly overwrite existing files"""
        # First write
        state1 = initialize_state()
        state1['session']['session_count'] = 1
        save_state(state1, self.test_file)

        # Second write (overwrite)
        state2 = initialize_state()
        state2['session']['session_count'] = 2
        save_state(state2, self.test_file)

        # Load and verify
        loaded = load_state(self.test_file)
        self.assertEqual(loaded['session']['session_count'], 2,
                        "Overwrite failed to update value")

    def test_save_creates_directory(self):
        """Test that save_state creates parent directory if missing"""
        nested_path = os.path.join(self.test_dir, 'nested', 'deep', 'state.json')
        state = initialize_state()

        result = save_state(state, nested_path)
        self.assertTrue(result, "Save to nested path failed")
        self.assertTrue(os.path.exists(nested_path),
                       "Nested directory not created")

    # =========================================================================
    # Crash Resilience Tests
    # =========================================================================

    def test_corrupted_json_recovery(self):
        """Test that corrupted JSON returns empty dict"""
        # Write invalid JSON
        with open(self.test_file, 'w') as f:
            f.write('{ this is not valid json !!!')

        # Load should return empty dict, not crash
        result = load_state(self.test_file)
        self.assertEqual(result, {}, "Should return empty dict for corrupted JSON")

    def test_partial_write_recovery(self):
        """Test that partial/truncated JSON is handled gracefully"""
        # Simulate truncated file (valid JSON start but incomplete)
        with open(self.test_file, 'w') as f:
            f.write('{"session": {"session_count": ')  # Incomplete

        result = load_state(self.test_file)
        self.assertEqual(result, {}, "Should handle truncated JSON gracefully")

    def test_empty_file_recovery(self):
        """Test that empty file is handled gracefully"""
        # Create empty file
        Path(self.test_file).touch()

        result = load_state(self.test_file)
        self.assertEqual(result, {}, "Should handle empty file gracefully")

    # =========================================================================
    # Schema Validation Tests
    # =========================================================================

    def test_schema_structure(self):
        """Test that schema has all expected sections"""
        schema = get_state_schema()

        required_sections = ['schema_version', 'last_updated', 'session',
                            'active_tasks', 'personality', 'recent_context',
                            'system']

        for section in required_sections:
            self.assertIn(section, schema, f"Schema missing section: {section}")

    def test_schema_session_fields(self):
        """Test that session section has required fields"""
        schema = get_state_schema()
        session = schema['session']

        required_fields = ['last_run', 'session_count', 'exit_reason',
                          'current_cycle_start', 'uptime_seconds']

        for field in required_fields:
            self.assertIn(field, session,
                         f"Session schema missing field: {field}")

    def test_schema_system_counters(self):
        """Test that system section has all counters"""
        schema = get_state_schema()
        system = schema['system']

        counters = ['total_cycles', 'tasks_completed', 'emails_sent',
                   'workers_spawned', 'voluntary_exits', 'context_refreshes']

        for counter in counters:
            self.assertIn(counter, system,
                         f"System schema missing counter: {counter}")

    # =========================================================================
    # Merge Operations Tests
    # =========================================================================

    def test_merge_state_simple(self):
        """Test simple merge operation"""
        existing = {
            'session': {'session_count': 1, 'exit_reason': None},
            'system': {'tasks_completed': 5}
        }

        updates = {
            'session': {'session_count': 2},
            'system': {'tasks_completed': 10}
        }

        merged = merge_state(existing, updates)

        self.assertEqual(merged['session']['session_count'], 2)
        self.assertEqual(merged['session']['exit_reason'], None)  # Preserved
        self.assertEqual(merged['system']['tasks_completed'], 10)

    def test_merge_state_deep(self):
        """Test that merge handles nested dicts correctly"""
        existing = {
            'personality': {
                'name': 'Iris',
                'self_notes': ['Note 1'],
                'preferences': {'style': 'brief'}
            }
        }

        updates = {
            'personality': {
                'interaction_count': 42
            }
        }

        merged = merge_state(existing, updates)

        # Check merge preserved existing fields
        self.assertEqual(merged['personality']['name'], 'Iris')
        self.assertEqual(merged['personality']['self_notes'], ['Note 1'])

        # Check new field added
        self.assertEqual(merged['personality']['interaction_count'], 42)

    def test_merge_state_new_keys(self):
        """Test that merge can add new top-level keys"""
        existing = {'session': {'session_count': 1}}
        updates = {'new_section': {'data': 'value'}}

        merged = merge_state(existing, updates)

        self.assertIn('session', merged)
        self.assertIn('new_section', merged)
        self.assertEqual(merged['new_section']['data'], 'value')

    # =========================================================================
    # Real-World Scenario Tests
    # =========================================================================

    def test_session_lifecycle(self):
        """Test typical session lifecycle: init -> work -> save -> restart -> load"""
        # Session 1: Initialize
        state = initialize_state()
        state['session']['session_count'] = 1
        state['system']['tasks_completed'] = 0
        save_state(state, self.test_file)

        # Do some work
        state['system']['tasks_completed'] = 5
        state['system']['emails_sent'] = 3
        state['session']['exit_reason'] = 'voluntary'
        save_state(state, self.test_file)

        # Session 2: Load and resume
        state2 = load_state(self.test_file)
        self.assertEqual(state2['system']['tasks_completed'], 5)
        self.assertEqual(state2['system']['emails_sent'], 3)

        # Update session
        state2['session']['session_count'] = 2
        state2['session']['exit_reason'] = None
        state2['system']['tasks_completed'] = 12
        save_state(state2, self.test_file)

        # Session 3: Load again
        state3 = load_state(self.test_file)
        self.assertEqual(state3['session']['session_count'], 2)
        self.assertEqual(state3['system']['tasks_completed'], 12)

    def test_personality_notes_accumulation(self):
        """Test that personality notes accumulate correctly"""
        state = initialize_state()
        state['personality']['self_notes'] = []

        # Add notes over multiple saves
        state['personality']['self_notes'].append('First note')
        save_state(state, self.test_file)

        state = load_state(self.test_file)
        state['personality']['self_notes'].append('Second note')
        save_state(state, self.test_file)

        state = load_state(self.test_file)
        state['personality']['self_notes'].append('Third note')
        save_state(state, self.test_file)

        # Load final state
        final = load_state(self.test_file)
        self.assertEqual(len(final['personality']['self_notes']), 3)
        self.assertIn('First note', final['personality']['self_notes'])
        self.assertIn('Third note', final['personality']['self_notes'])

    def test_checkpoint_recovery(self):
        """Test that checkpoints allow task resumption"""
        state = initialize_state()

        # Start a task with checkpoints
        state['active_tasks']['current_task'] = 'Research project'
        state['active_tasks']['task_id'] = 42
        state['active_tasks']['progress'] = 'Step 2 of 5'
        state['active_tasks']['checkpoints'] = [
            {'step': 1, 'status': 'Completed literature search'},
            {'step': 2, 'status': 'Started analysis'}
        ]
        save_state(state, self.test_file)

        # Simulate crash and restart
        recovered = load_state(self.test_file)

        self.assertEqual(recovered['active_tasks']['current_task'], 'Research project')
        self.assertEqual(recovered['active_tasks']['task_id'], 42)
        self.assertEqual(len(recovered['active_tasks']['checkpoints']), 2)

        # Can resume from checkpoint
        self.assertEqual(recovered['active_tasks']['checkpoints'][-1]['step'], 2)

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_unicode_in_state(self):
        """Test that unicode characters are handled correctly"""
        state = initialize_state()
        state['personality']['self_notes'] = [
            'Note with emoji 🐉',
            'Note with unicode: αβγδ',
            'Note with symbols: ←→↑↓'
        ]

        save_state(state, self.test_file)
        loaded = load_state(self.test_file)

        self.assertEqual(loaded['personality']['self_notes'][0], 'Note with emoji 🐉')
        self.assertEqual(loaded['personality']['self_notes'][1], 'Note with unicode: αβγδ')

    def test_large_state(self):
        """Test that large state files are handled correctly"""
        state = initialize_state()

        # Add lots of data
        state['recent_context']['recent_activity'] = [
            f'Activity entry {i}' for i in range(1000)
        ]
        state['personality']['self_notes'] = [
            f'Self note number {i}' * 50 for i in range(100)
        ]

        result = save_state(state, self.test_file)
        self.assertTrue(result, "Failed to save large state")

        loaded = load_state(self.test_file)
        self.assertEqual(len(loaded['recent_context']['recent_activity']), 1000)
        self.assertEqual(len(loaded['personality']['self_notes']), 100)

    def test_timestamp_updates(self):
        """Test that last_updated timestamp is set correctly"""
        state = initialize_state()
        timestamp1 = state.get('last_updated')

        import time
        time.sleep(0.1)  # Small delay

        save_state(state, self.test_file)
        loaded = load_state(self.test_file)
        timestamp2 = loaded.get('last_updated')

        # Timestamps should be different
        self.assertIsNotNone(timestamp2)
        self.assertNotEqual(timestamp1, timestamp2)


# =============================================================================
# Test Runner
# =============================================================================

def run_tests():
    """Run all tests with summary output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestStateManager)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("STATE MANAGER TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run:    {result.testsRun}")
    print(f"Passed:       {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed:       {len(result.failures)}")
    print(f"Errors:       {len(result.errors)}")
    print("=" * 70)

    if result.wasSuccessful():
        print("✓ ALL STATE MANAGER TESTS PASSED")
        print("\nState management functionality validated:")
        print("  ✓ Load/save operations")
        print("  ✓ Atomic writes (crash resilience)")
        print("  ✓ Schema validation")
        print("  ✓ Merge operations")
        print("  ✓ Corrupted file recovery")
        print("  ✓ Real-world scenarios")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
