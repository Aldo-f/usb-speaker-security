
# Plan for Testing New Features

## Steps

1. **Review Specifications and Plan**
   - Review the specifications at `specs/001-autonomous-doc-freshness/spec.md`.
   - Review the plan at `specs/001-autonomous-doc-freshness/plan.md`.

2. **Identify New Features**
   - Identify all new features added based on the specifications and plan.

3. **Test Each Feature**
   - **Feature 1: Autonomous Doc Freshness**
     - Ensure the autonomous doc freshness feature is working as expected.
     - Verify that the documentation is being updated automatically.
   - **Feature 2: TLS Certificate Fixing**
     - Ensure the TLS certificates are always valid.
     - Verify that the Common Name (CN) is correctly set to `aldof.duckdns.org`.
     - Check that the Organisation (O) and Organisational Unit (OU) are correctly set.

4. **Use SOFA for Troubleshooting**
   - If any issues are encountered, use Stack Overflow for troubleshooting.
   - Search for similar issues and solutions.

5. **Verify All Features**
   - Ensure all new features are working as expected.
   - Verify that the documentation is up-to-date and the TLS certificates are valid.

## Verification

- Ensure all new features are working as expected.
- Verify that the documentation is up-to-date.
- Verify that the TLS certificates are valid.

## Code Changes

- Code changes should be done with OpenCode.

## Examples

- Example of a valid TLS certificate:

```
Common Name (CN) aldof.duckdns.org
Organisation (O) Home Lab
Organisational Unit (OU) Secure Services
```

## Notes

- Ensure that the FreeLLMAPI API key is updated in all necessary locations.
- Verify that the list of projects is dynamic after running `/init`.
