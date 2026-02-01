# Task: Token Audit Logging

## Context

friedmomo.com uses a token-based economy where users:
- **Buy tokens** via Stripe (real money → tokens)
- **Spend tokens** on AI generations (images, videos)
- **Transfer tokens** to other users

Currently, token operations are logged via Python's `logging` module, but there's no persistent audit trail. If a user disputes a transaction or we suspect fraud, we have no reliable way to investigate.

## Vision

A complete, queryable audit trail of every token movement in the system. Think of it like a bank statement - every credit and debit recorded with timestamp, reason, and context.

## Why This Matters for Production

1. **User disputes**: "I had 100 tokens, now I have 50, what happened?"
2. **Fraud detection**: Spot unusual patterns (rapid transfers, suspicious purchases)
3. **Debugging**: Track down bugs in token logic
4. **Analytics**: Understand how users spend tokens
5. **Compliance**: Financial audit trail if needed

## Current State

- `services/token_service.py` - Handles all token operations
- `transactions` collection exists but only tracks purchases, not all movements
- No unified audit log

## End Result

A new `token_audit_log` Firestore collection that captures:

```
{
  id: "auto-generated",
  user_id: "firebase-uid",
  type: "credit" | "debit" | "transfer_in" | "transfer_out",
  amount: 50,
  balance_before: 100,
  balance_after: 150,
  reason: "stripe_purchase" | "image_generation" | "video_generation" | "transfer" | "refund" | "admin_adjustment",
  reference_id: "creation_id or transaction_id or transfer_id",
  metadata: { ... },  // Additional context
  created_at: timestamp,
  ip_address: "optional - for fraud detection"
}
```

## Implementation Approach

### Option A: Modify token_service.py directly
Add audit logging to each method (`add_tokens`, `deduct_tokens`, `transfer_tokens`)

**Pros**: Simple, all in one place
**Cons**: Couples audit logic with business logic

### Option B: Create a separate audit service
New `services/token_audit_service.py` that token_service calls

**Pros**: Clean separation, reusable
**Cons**: More files, need to ensure it's always called

### Recommended: Option B

## Files to Modify/Create

1. **CREATE** `services/token_audit_service.py`
   - `log_credit(user_id, amount, reason, reference_id, metadata)`
   - `log_debit(user_id, amount, reason, reference_id, metadata)`
   - `get_user_audit_log(user_id, limit, offset)`
   - `get_audit_log_by_reference(reference_id)`

2. **MODIFY** `services/token_service.py`
   - Import and use `TokenAuditService`
   - Call audit methods after each successful token operation
   - Pass balance_before and balance_after

3. **MODIFY** `firestore.rules`
   - Add rules for `token_audit_log` collection (admin read-only, system write)

4. **CREATE** `tests/test_token_audit.py`
   - Test audit entries are created for all operations
   - Test query methods work correctly

## Local Testing Instructions

```bash
# 1. Start local server
source venv/bin/activate
./start_local.sh

# 2. Run token operation tests
pytest tests/test_token_audit.py -v

# 3. Manual testing:
#    - Buy tokens (check audit log)
#    - Generate an image (check audit log)
#    - Transfer tokens (check both users' audit logs)

# 4. Verify in Firebase Console:
#    - Go to Firestore > token_audit_log
#    - Confirm entries exist with correct structure
```

## Success Criteria

- [ ] Every `add_tokens` call creates an audit entry
- [ ] Every `deduct_tokens` call creates an audit entry
- [ ] Every `transfer_tokens` call creates TWO entries (sender debit, receiver credit)
- [ ] Audit entries include balance_before and balance_after
- [ ] Can query audit log by user_id
- [ ] Can query audit log by reference_id (e.g., find all entries for a creation)
- [ ] Firestore rules prevent users from reading/modifying audit logs

## Security Considerations

- Audit log should be **append-only** (no updates or deletes)
- Users should NOT be able to read their own audit log directly (admin/API only)
- Consider rate limiting audit queries to prevent abuse
- Don't log sensitive data (full credit card numbers, etc.)

## Future Enhancements (Out of Scope)

- Admin dashboard to view audit logs
- Automated anomaly detection
- Export to analytics platform
- User-facing "transaction history" page

---

## Approval

- [ ] Reviewed approach
- [ ] Ready to implement

**Approved by**: _________________ **Date**: _________________
