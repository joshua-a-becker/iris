# Iris Documentation - Detailed Guides

This directory contains specialized documentation extracted from the main iris.md controller instructions to improve maintainability and readability.

## Quick Reference

| Document | Purpose | When to Read |
|----------|---------|--------------|
| `email-etiquette.md` | Email handling protocols | When handling email from unknown senders or questions about email style |
| `anti-patterns.md` | Common delegation failures | When feeling tempted to handle tasks directly, or debugging delegation issues |
| `error-recovery.md` | Error handling procedures | When encountering system failures or worker errors |
| `state-management-guide.md` | State schema and patterns | When working with state.json or implementing new state features |

## File Details

### email-etiquette.md (135 lines)
Comprehensive email handling guide covering:
- Authority rules (who to follow vs. who to forward)
- Email flow for authoritative senders (${OWNER_NAME})
- Email flow for unknown senders (dragon-themed responses)
- Email promise tracking (CRITICAL!)
- Update frequency guidelines
- Communication style guide

**Key sections:**
- Dragon ASCII art template for unknown senders
- Example acknowledgment templates
- Email promise tracking examples

### anti-patterns.md (234 lines)
Detailed guide to common mistakes that violate delegation discipline:
- Anti-Pattern #1: "Getting Absorbed in Debugging"
- Anti-Pattern #2: "One More Quick Thing" Syndrome
- Anti-Pattern #3: "I Can Do This Faster Than Spawning An Agent"
- Anti-Pattern #4: "Just Checking One More File"
- Anti-Pattern #5: "I'm Already Working On It, Might As Well Finish"
- Real-time recognition guide with warning signs

**Each anti-pattern includes:**
- The scenario (how it happens)
- Why it's wrong
- The correct approach (with code examples)

### error-recovery.md (116 lines)
Error handling strategies for common failure modes:
- State corruption or missing state.json
- Database unavailability
- Email system failures
- Worker failure handling
- General error handling strategy
- Recovery from context pollution

**Key procedures:**
- How to recover when core systems fail
- How to operate in degraded mode
- When and how to notify ${OWNER_NAME}

### state-management-guide.md (150 lines)
Complete guide to state.json management:
- State file locations (dev vs. prod)
- Complete state schema with all sections
- Continuous state update patterns
- State utilities usage (load_state, save_state, etc.)
- Self-notes system for personality continuity
- Checkpoint system for long-running tasks
- Best practices

**Key sections:**
- Full JSON schema example
- Code examples for common operations
- When to update what

## Integration with iris.md

The main `iris.md` file contains:
- Core operations (CRITICAL, never modified)
- Essential functioning overview
- Delegation decision making (30-second rule)
- Main loop structure
- Brief versions of all procedures

When you need **details** about any topic, iris.md points you to these specialized docs.

## Maintenance Guidelines

When updating these docs:
1. **Keep iris.md brief**: Core functions and pointers only
2. **Details go here**: Extensive examples and procedures
3. **Cross-reference**: Link between docs when topics overlap
4. **Test changes**: Verify Iris can follow the updated docs
5. **Update this README**: If adding new docs

## Refactoring History

- **2026-02-16**: Initial extraction from iris.md (Task #17)
  - Reduced iris.md from 1468 to 430 lines (70.7% reduction)
  - Created 4 specialized docs totaling 635 lines
  - Core operations (lines 1-13) preserved exactly
  - See REFACTORING-SUMMARY.md for complete details
