# Substack CAPTCHA Auth Diagnostics

This reference documents the diagnostic techniques for detecting and confirming CAPTCHA blocks during Substack password login, as discovered in the May 29, 2026 session.

## Symptoms

After clicking "Continue" on the password sign-in form, the button either:
- Shows "Loading" briefly then reverts to "Continue" with no visible error
- Shows the regular form state with no error message displayed in the UI

## Detection Method

### DOM check (browser context)

```javascript
// Primary — the CAPTCHA error element
document.querySelector('.error.other-error')?.textContent
// Returns: "Please complete the captcha to continue" if blocked

// Broader scan
Array.from(document.querySelectorAll('[class*=error]')).map(e => e.textContent.trim())

// Check all error-classed elements explicitly
document.querySelectorAll('.error').length
document.querySelector('#error-container')?.outerHTML
```

The error element sits in: `<div id="error-container"><div class="error other-error">Please complete the captcha to continue</div></div>`

### Console verification

```javascript
// Check for error via console
document.querySelector('.error.other-error') ? 'CAPTCHA BLOCKED' : 'no captcha error'

// Check for any hidden captcha widgets
document.querySelector('[class*="g-recaptcha"]')  // reCAPTCHA
document.querySelector('[class*="turnstile"]')    // Cloudflare Turnstile
document.querySelector('[data-sitekey]')          // Any sitekey
```

Note: No reCAPTCHA/Turnstile iframes or data attributes appear in the DOM before the challenge triggers. The CAPTCHA appears to be at the Cloudflare infrastructure level, not embedded in the page.

### API diagnostic (curl — confirms blocker type)

```bash
curl -s -X POST "https://substack.com/api/v1/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"$SUBSTACK_EMAIL","password":"$SUBSTACK_PASSWORD","captcha_response":null,"redirect":"/dashboard"}'
```

| Response | Diagnosis |
|---|---|
| `{"error":"Please complete the captcha to continue","type":"single"}` | Password correct, CAPTCHA blocking |
| `401 Unauthorized` with different error | Wrong password or account issue |

### Session state cookie

```javascript
document.cookie.includes('substack.lli=1')  // logged in
document.cookie.includes('substack.lli=0')  // logged out
```

## Password Form Structure

The password sign-in form has 5 inputs:

| Type | Name | Notes |
|---|---|---|
| hidden | `redirect` | Post-login destination URL, often `/dashboard` |
| hidden | `for_pub` | Publication slug when signing in publication-specific; empty on main `substack.com/sign-in` |
| hidden | `isOAuth` | Always `false` for password auth |
| email | `email` | User email |
| password | `password` | User password |

## When CAPTCHA Blocks Both Strategies

When CAPTCHA blocks password auth AND magic link email silently fails at AgentMail, the session cannot proceed. Possible mitigations for future sessions:

1. **Pre-warm the session**: Start the browser with a valid session cookie obtained externally
2. **Residential proxy**: Upgrade Browserbase plan for residential proxies may reduce Cloudflare challenge frequency
3. **Different auth email**: Switch to a commercial email provider (not AgentMail) for reliable magic link delivery
4. **Recover session from prior login**: Navigate to `substack.com` and check if an existing session cookie is still valid before attempting auth

## Changelog

- 2026-05-29: Initial documentation from HYPER-post-2026-05-27 publish attempt
