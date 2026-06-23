# Social Media Integration for Frappe

A powerful Frappe application designed to integrate multiple social media platforms. Currently featuring a comprehensive **WhatsApp Integration** powered by **Evolution API v2.3**.

## 🚀 Features

### 🟢 WhatsApp Integration (Evolution API v2.3)
- **Instance Management**: Create, delete, and manage multiple WhatsApp instances directly from Frappe.
- **Modern Connection Flow**: Easy QR code pairing with real-time status updates.
- **Universal Search & Sync**: Synchronize existing WhatsApp instances from your Evolution API server.

### 💬 Manual Chat System
- **Real-time Chat UI**: A WhatsApp-like interface to view conversation history.
- **Quick Reply**: Send messages instantly via the chat input (supports Enter key).
- **Rich Media Support**: Send Text, Images, Videos, Documents, Audio, and Locations.
- **Contact Check**: Verify if a phone number exists on WhatsApp before sending.

### 🔔 Smart Notifications
- **Core Integration**: WhatsApp is integrated as a first-class channel in Frappe's standard **Notification** DocType.
- **Advanced Triggers**: Use standard Frappe notification triggers:
  - `New`, `Save`, `Submit`, `Cancel`
  - `Days Before` / `Days After` (Perfect for expiry reminders)
  - `Value Change` (Trigger alerts when a field value updates)
- **Automated Attachments**: Automatically sends Print Formats (PDFs) or attached files via WhatsApp.

### 🇧🇩 Specialized for Bangladesh
- **Auto-Formatting**: Automatically prepends `88` to Bangladesh mobile numbers if missing (supports `01XXXXXXXXX` and `1XXXXXXXXX` formats).
- **Cleanup**: Automatically strips spaces, dashes, and special characters from phone numbers.

---

## 🛠 Installation

```bash
cd ~/frappe-bench
bench get-app https://github.com/sadikhossainnub/social_media.git
bench --site <site_name> install-app social_media
bench --site <site_name> migrate
```

---

## ⚙️ Configuration

1. **Evolution API**: Ensure you have an instance of [Evolution API](https://evolution-api.com/) (v2.3 or higher) running.
2. **Frappe Settings**:
    - Go to **Whatsapp Settings**.
    - Enter your **Evolution API Endpoint** (e.g., `https://api.yourdomain.com`).
    - Enter your **Global API Key** (Admin Key).
3. **Webhook Setup**:
    - Our app automatically configures webhooks on the Evolution API to sync connection status and incoming messages back to Frappe.

---

## 📖 Usage

### Sending Manual Messages
1. Navigate to **Whatsapp Chat** DocType.
2. Create a new entry, select an **Instance** and enter the **Recipient Number**.
3. Use the Chat Interface at the bottom to talk or use the fields to send media.

### Setting up Automated Alerts
1. Navigate to the core **Notification** List.
2. Create a new Notification.
3. Select the **Document Type** and **Event**.
4. Set **Channel** to `WhatsApp`.
5. Select your **WhatsApp Instance**.
6. Write your message using Jinja templates.
7. (Optional) Check **Attach Print** to send a PDF of the document.

---

## 🛡 License
MIT License.

---
Developed with ❤️ by **Prime Technology of Bangladesh**.
