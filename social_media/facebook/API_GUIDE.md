# Facebook Integration API Guide

Technical users এবং developers এর জন্য API documentation এবং advanced configuration options।

## 📑 Table of Contents

- [Overview](#overview)
- [API Methods](#api-methods)
- [Configuration](#configuration)
- [Custom Scripting](#custom-scripting)
- [Troubleshooting](#troubleshooting)

---

## Overview

Facebook Integration তিনটি main components এ বিভক্ত:

1. **Webhook Handler** (`/api/method/social_media.facebook.api.webhook`)
   - Facebook থেকে events গ্রহণ করে
   - বার্তা, postbacks, leads ইত্যাদি প্রসেস করে

2. **Settings Manager** (`FacebookSettings`)
   - App credentials এবং configuration পরিচালনা করে
   - Setup progress track করে

3. **Document Types**
   - `Facebook Page` - Page configuration
   - `Facebook Message Log` - Message history
   - `Facebook Comment` - Comment management
   - `Facebook Auto Post Publisher` - Scheduled posts

---

## API Methods

### get_setup_steps()

Setup wizard এর জন্য step-by-step instructions পান।

**Method Path:**
```
social_media.facebook.doctype.facebook_settings.facebook_settings.get_setup_steps
```

**Parameters:** None

**Response:**
```json
{
  "steps": [
    {
      "step": 1,
      "title": "Get Your Facebook App Credentials",
      "description": "...",
      "instructions": [...],
      "external_link": "...",
      "fields_required": ["app_id", "app_secret"]
    }
    // ... more steps
  ],
  "helpful_links": [...]
}
```

**Example:**
```javascript
frappe.call({
  method: 'social_media.facebook.doctype.facebook_settings.facebook_settings.get_setup_steps',
  callback: function(r) {
    console.log(r.message);
  }
});
```

---

### generate_verification_token()

Random verification token generate করুন।

**Method Path:**
```
social_media.facebook.doctype.facebook_settings.facebook_settings.generate_verification_token
```

**Parameters:** None

**Response:**
```
32-character random token string
Example: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

**Example:**
```python
# Backend
import frappe
token = frappe.call(
  'social_media.facebook.doctype.facebook_settings.facebook_settings.generate_verification_token'
)

# Frontend
frappe.call({
  method: 'social_media.facebook.doctype.facebook_settings.facebook_settings.generate_verification_token',
  callback: function(r) {
    console.log('Generated token:', r.message);
  }
});
```

---

### test_webhook_connection()

Webhook configuration পরীক্ষা করুন।

**Method Path:**
```
social_media.facebook.doctype.facebook_settings.facebook_settings.test_webhook_connection
```

**Parameters:** None

**Response:**
```json
{
  "success": true/false,
  "message": "Detailed message",
  "callback_url": "https://..."
}
```

**Example:**
```javascript
frappe.call({
  method: 'social_media.facebook.doctype.facebook_settings.facebook_settings.test_webhook_connection',
  callback: function(r) {
    if (r.message.success) {
      frappe.msgprint('Webhook is properly configured!');
    }
  }
});
```

---

### schedule_multiple_posts()

একসাথে multiple posts schedule করুন।

**Method Path:**
```
social_media.facebook.doctype.facebook_auto_post_publisher.facebook_auto_post_publisher.schedule_multiple_posts
```

**Parameters:**
```json
{
  "posts_data": [
    {
      "page_id": "123456789",
      "content": "Post content here",
      "image": "image_url",
      "schedule_type": "Scheduled",
      "schedule_datetime": "2026-06-01 10:30:00",
      "analyze": true,
      "notify": true
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "scheduled_posts": [
    {
      "name": "Auto Post 001",
      "status": "Scheduled"
    }
  ]
}
```

**Example:**
```python
frappe.call(
  'social_media.facebook.doctype.facebook_auto_post_publisher.facebook_auto_post_publisher.schedule_multiple_posts',
  args={
    'posts_data': [
      {
        'page_id': '123456789',
        'content': 'Hello Facebook!',
        'schedule_type': 'Scheduled',
        'schedule_datetime': '2026-06-01 10:30:00'
      }
    ]
  }
)
```

---

### process_scheduled_posts()

Scheduled posts process করুন (cron দ্বারা প্রতি 5 মিনিটে run হয়)।

**Method Path:**
```
social_media.facebook.doctype.facebook_auto_post_publisher.facebook_auto_post_publisher.process_scheduled_posts
```

**Parameters:** None

**Response:** None (logs generated instead)

---

## Configuration

### Facebook Settings Fields

```python
# Programmatic access
settings = frappe.get_single("Facebook Settings")

# Read values
app_id = settings.app_id
app_secret = settings.app_secret
callback_url = settings.callback_url

# Set values programmatically
frappe.db.set_value(
  "Facebook Settings",
  "Facebook Settings",
  {
    "app_id": "new_app_id",
    "webhook_configured": 1
  }
)
```

### Webhook Events

Facebook থেকে পাঠানো events:

| Event | Handler | Purpose |
|-------|---------|---------|
| message | `handle_message()` | Incoming messages |
| postback | `handle_postback()` | Button clicks |
| delivery | `handle_delivery()` | Message delivery confirmations |
| read | `handle_read()` | Message read status |
| comment | `handle_comment()` | Page comments |
| lead_generation | `handle_lead_generation()` | Lead ads |

---

## Custom Scripting

### Send Message Programmatically

```python
import frappe

# Create and send message
message = frappe.get_doc({
  "doctype": "Facebook Message",
  "facebook_page": "Your Page Name",
  "recipient_psid": "1234567890",
  "message_text": "Hello from ERPNext!",
  "message_type": "text"
})
message.insert()

# এটি স্বয়ংক্রিয়ভাবে Facebook এ পাঠানো হয়
```

### Listen for Incoming Messages

```python
# Custom event handler
from social_media.facebook.api import handle_message

def custom_message_handler(event, sender_psid, recipient_psid):
  """কাস্টম বার্তা প্রসেসিং লজিক"""
  message = event.get("message", {})
  text = message.get("text", "")
  
  # আপনার কাস্টম লজিক
  if "order" in text.lower():
    # Order processing logic
    pass
```

### Schedule Posts with Cron

```python
# hooks.py এ যোগ করুন
{
  "cron": {
    "0 10 * * *": [  # প্রতিদিন সকাল ১০ টায়
      "my_app.facebook.methods.process_daily_posts"
    ]
  }
}

# my_app/facebook/methods.py
def process_daily_posts():
  """প্রতিদিনের scheduled posts process করুন"""
  posts = frappe.get_list(
    "Facebook Auto Post Publisher",
    filters={
      "publish_status": "Scheduled",
      "schedule_datetime": ["<=", frappe.utils.now()]
    }
  )
  
  for post in posts:
    doc = frappe.get_doc("Facebook Auto Post Publisher", post.name)
    doc.publish_now()
```

---

## Error Handling

### Common Errors and Solutions

```python
# Error: Invalid access token
try:
  response = publish_to_facebook(content)
except InvalidAccessTokenError:
  # Token refresh করুন
  settings = frappe.get_single("Facebook Settings")
  settings.regenerate_access_token()

# Error: Page not found
try:
  page = frappe.get_doc("Facebook Page", page_name)
except frappe.DoesNotExistError:
  frappe.log_error(f"Page {page_name} not found")
  raise frappe.ValidationError("Facebook Page not configured")

# Error: Rate limit exceeded
try:
  response = send_message(recipient, message)
except RateLimitError:
  # একটু পরে retry করুন
  frappe.enqueue(
    send_message,
    scheduled_time=frappe.utils.add_to_date(None, seconds=60)
  )
```

---

## Logging and Debugging

### Enable Debugging

```python
# facebook_settings.py তে debug logging যোগ করুন
import frappe

frappe.logger().info(
  f"Facebook message received: {message_text}",
  extra={"page_id": page_id, "sender_psid": sender_psid}
)

# Error logging
frappe.log_error(
  "Facebook API Error",
  f"Failed to send message: {str(e)}"
)
```

### View Logs

```
ERPNext UI → Tools → Error Log
Search: "Facebook"
```

---

## Troubleshooting

### Webhook Not Receiving Events

1. **Check webhook URL is public:**
   ```bash
   curl https://yoursite.com/api/method/social_media.facebook.api.webhook
   # Should return "Invalid request" - this means URL is accessible
   ```

2. **Verify subscription:**
   ```
   Facebook Developer Dashboard → Messenger → Settings → Webhooks
   Check: All required events are subscribed
   ```

3. **Check logs:**
   ```python
   # See webhook logs
   import frappe
   logs = frappe.get_list("Error Log", 
     filters={"title": ["like", "Facebook Webhook"]}
   )
   ```

### Access Token Expired

```python
# Automatically refresh token
settings = frappe.get_single("Facebook Settings")
# Implement token refresh logic
# See Facebook docs: https://developers.facebook.com/docs/facebook-login/access-tokens

# Manual refresh
# 1. Go to Facebook Developer Dashboard
# 2. Generate new Page Access Token
# 3. Update Facebook Settings
```

### Rate Limiting

Facebook API rate limits implement করুন:

```python
import time
from frappe.rate_limiter import RateLimiter

limiter = RateLimiter(key="facebook_api", limit=100, window=60)

if limiter.is_allowed("facebook_api"):
  send_message(recipient, message)
else:
  # Enqueue for later
  frappe.enqueue(send_message, recipient, message)
```

---

## Best Practices

1. **Always validate inputs:**
   ```python
   if not frappe.utils.validate_email_address(email):
     raise frappe.ValidationError("Invalid email")
   ```

2. **Use async for long operations:**
   ```python
   frappe.enqueue(process_large_batch, queue='long')
   ```

3. **Log everything:**
   ```python
   frappe.logger().info(f"Processing post {post_id}")
   ```

4. **Handle rate limits:**
   ```python
   # Add delays between API calls
   time.sleep(1)
   ```

5. **Secure credentials:**
   ```python
   # Never log sensitive data
   # Use frappe.utils.get_safe_password() for logging
   ```

---

## Performance Tips

- Batch messages: একবারে ১০+ বার্তা পাঠান
- Use async webhooks: Long-running operations background এ করুন
- Cache Facebook data: Frequently accessed data cache করুন
- Index message logs: Database performance এর জন্য

---

## API Rate Limits

Facebook API rate limits:

| Endpoint | Limit | Window |
|----------|-------|--------|
| Send Message | 1000 | 1 hour |
| Get Insights | 200 | 1 hour |
| Upload Media | 100 | 1 hour |

---

## Resources

- [Facebook Messenger Platform Docs](https://developers.facebook.com/docs/messenger-platform)
- [Access Tokens Guide](https://developers.facebook.com/docs/access-tokens)
- [Error Codes](https://developers.facebook.com/docs/graph-api/using-graph-api/error-handling)
- [Rate Limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting)

---

Happy coding! 🚀
