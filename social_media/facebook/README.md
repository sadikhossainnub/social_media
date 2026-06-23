# Facebook Integration Module for ERPNext

ERPNext এর জন্য সম্পূর্ণ Facebook integration সলিউশন। বার্তা পাঠান, গ্রহণ করুন, auto-replies সেটআপ করুন এবং আরও অনেক কিছু।

## 🚀 Quick Links

### নতুন ব্যবহারকারীদের জন্য
- **[⚡ 5 মিনিটের Quick Start](QUICK_START.md)** - দ্রুত সেটআপ  
- **[📖 সম্পূর্ণ Setup Guide](SETUP_GUIDE.md)** - বিস্তারিত ধাপে ধাপে গাইড
- **[🎯 Interactive Setup Wizard](/app/facebook-settings)** - Step-by-step wizard ব্যবহার করুন

### Technical Users এর জন্য
- **[💻 API Documentation](API_GUIDE.md)** - API methods, configuration, scripting
- **[🔧 Advanced Configuration](API_GUIDE.md#configuration)** - Custom hooks, cron jobs

---

## ✨ মূল বৈশিষ্ট্য

- ✅ **বার্তা গ্রহণ/পাঠান** - Facebook থেকে আসা বার্তা দেখুন এবং উত্তর দিন
- ✅ **স্বয়ংক্রিয় উত্তর** - নির্দিষ্ট keywords এর জন্য auto-replies সেটআপ করুন
- ✅ **Scheduled Posts** - ভবিষ্যতের জন্য পোস্ট সাজান, Best time এ পোস্ট করুন
- ✅ **Engagement Tracking** - পোস্ট engagement মনিটর করুন
- ✅ **Lead Forms Integration** - Facebook Lead Ads থেকে leads সংগ্রহ করুন
- ✅ **Comment Management** - পেজের সব কমেন্ট একই জায়গায় ম্যানেজ করুন
- ✅ **Multi-Page Support** - একাধিক Facebook page এর সাথে সংযুক্ত থাকুন

---

## 📋 সেটআপের পূর্বশর্তসমূহ

- Facebook পেজ (আপনার ব্যবসার)
- Facebook Developer অ্যাকাউন্ট
- ERPNext সিস্টেম (আপনার সাইট publicly accessible হতে হবে)

---

## 🎯 সেটআপ শুরু করুন

### অপশন ১: Interactive Wizard (সুপারিশকৃত) ⭐
```
1. ERPNext এ যান: /app/facebook-settings
2. "Launch Setup Wizard" বাটন ক্লিক করুন
3. প্রতিটি ধাপ অনুসরণ করুন
```

### অপশন २: Quick Manual Setup (5 মিনিট)
[QUICK_START.md](QUICK_START.md) পড়ুন এবং অনুসরণ করুন

### অপশন ३: বিস্তারিত Setup (15 মিনিট)
[SETUP_GUIDE.md](SETUP_GUIDE.md) পড়ুন এবং অনুসরণ করুন

---

## 📁 মডিউল কম্পোনেন্টস

```
facebook/
├── QUICK_START.md                 # 5 মিনিটের দ্রুত গাইড
├── SETUP_GUIDE.md                 # বিস্তারিত সেটআপ গাইড
├── API_GUIDE.md                   # API methods এবং advanced configuration
├── AUTOMATION_FEATURES.md         # Automation এবং advanced features
├── README.md                      # এই ফাইল
└── doctype/
    ├── facebook_settings/                    # Main configuration
    │   ├── facebook_settings.json
    │   ├── facebook_settings.py
    │   └── facebook_settings.js             # Interactive wizard
    ├── facebook_page/                       # Page management
    ├── facebook_message_log/                # Message history
    ├── facebook_comment/                    # Comment management
    ├── facebook_auto_reply/                 # Auto-replies
    ├── facebook_auto_post_publisher/        # Scheduled posts
    └── facebook_integration_guide/          # Interactive guide
```

---

## 💻 মূল DocTypes

### 1. Facebook Settings
**Configuration এবং credentials পরিচালনা করুন**
```
/app/facebook-settings
```
- App ID, Secret, Tokens save করুন
- Webhook verify করুন
- Setup progress track করুন

### 2. Facebook Page
**আপনার Facebook pages ম্যানেজ করুন**
```
/app/facebook-page
```
- Page তথ্য save করুন
- বার্তা পাঠান
- Posts view করুন

### 3. Facebook Message Log
**সব বার্তার ইতিহাস**
```
/app/facebook-message-log
```
- আসা-যাওয়া বার্তা দেখুন
- Conversation history ট্র্যাক করুন
- বার্তা status মনিটর করুন

### 4. Facebook Comment
**পেজের comments ম্যানেজ করুন**
```
/app/facebook-comment
```
- পোস্টের সব comments দেখুন
- Comments এর জবাব দিন

### 5. Facebook Auto Reply
**স্বয়ংক্রিয় উত্তর সেটআপ করুন**
```
/app/facebook-auto-reply
```
- Keywords অনুযায়ী auto-replies সেট করুন
- উদাহরণ: "price" → "আমাদের দাম তালিকা..."

### 6. Facebook Auto Post Publisher
**Posts schedule করুন**
```
/app/facebook-auto-post-publisher
```
- ভবিষ্যতের জন্য posts সাজান
- Best engagement time এ স্বয়ংক্রিয় পোস্ট করুন

---

## 💬 বার্তা গ্রহণ/পাঠান

### বার্তা গ্রহণ করুন
Facebook থেকে আসা সব বার্তা এখানে:
```
/app/facebook-message-log
```

### বার্তা পাঠান
Facebook Page থেকে সরাসরি বার্তা পাঠান:
```
/app/facebook-page
[Page খুলুন] → [New Message] → [পাঠান]
```

### স্বয়ংক্রিয় উত্তর
নির্দিষ্ট keywords এর জন্য auto-reply:
```
/app/facebook-auto-reply
```

---

## 📊 বৈশিষ্ট্য বিস্তারিত

### যোগাযোগ সুবিধা
- Text বার্তা পাঠান
- Media (ছবি, ভিডিও) পাঠান
- Quick replies button সহ পাঠান
- Typing indicator দেখান

### স্বয়ংক্রিয়করণ
- নির্দিষ্ট শব্দের জবাব স্বয়ংক্রিয়ভাবে
- নির্দিষ্ট সময়ে posts পাঠান
- Engagement metrics track করুন

### বহুপৃষ্ঠ সমর্থন
- একাধিক Facebook pages সংযুক্ত করুন
- প্রতিটি page এর জন্য আলাদা configuration

### Lead Management
- Facebook Lead Forms একীভূত করুন
- Leads স্বয়ংক্রিয়ভাবে ERPNext এ আসুক
- Custom field mapping

---

## 🔧 Configuration

### Facebook Settings এ সাইন ইন করুন
```
/app/facebook-settings
```

**প্রয়োজনীয় ফিল্ড:**

| ফিল্ড | উৎস | নোট |
|------|------|------|
| App ID | Facebook Developer Dashboard | Settings > Basic |
| App Secret | Facebook Developer Dashboard | Settings > Basic |
| Verification Token | Generate বা আপনি তৈরি করুন | যেকোনো ৩২ চ্যার শক্তিশালী স্ট্রিং |
| Page Access Token | Facebook Dashboard | Messenger > Access Tokens |
| Callback URL | Auto-generated | কপি করুন এবং Facebook এ paste করুন |

---

## 🆘 সমস্যা নিষ্পত্তি

### সাধারণ সমস্যা

#### "Webhook verification failed"
**সমাধান:**
- Callback URL সঠিক কিনা চেক করুন
- Verification Token যাচাই করুন
- আপনার সাইট internet এ accessible কিনা নিশ্চিত করুন

#### "বার্তা আসছে না"
**সমাধান:**
1. Webhook events properly subscribe করা হয়েছে কিনা চেক করুন
2. Facebook Settings এ "Webhook Verified" চেক করুন
3. আপনার site logs দেখুন: `/app/error-log`

#### "Invalid App ID or Secret"
**সমাধান:**
- Facebook Developer Dashboard থেকে সঠিক credentials কপি করুন
- কোনো অতিরিক্ত space নেই কিনা চেক করুন

#### "Page access denied"
**সমাধান:**
- আপনি আপনার নিজের Page এর অ্যাডমিন কিনা নিশ্চিত করুন
- নতুন Page Access Token জেনারেট করুন

**আরও সমস্যা সমাধানের জন্য:** [SETUP_GUIDE.md - Troubleshooting](SETUP_GUIDE.md#troubleshooting)

---

## 📚 Documentation

| ডকুমেন্ট | জন্য | সময় |
|----------|------|------|
| [QUICK_START.md](QUICK_START.md) | দ্রুত সেটআপ | 5 মিনিট |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | বিস্তারিত সেটআপ | 15 মিনিট |
| [API_GUIDE.md](API_GUIDE.md) | Developers | 30 মিনিট |
| [AUTOMATION_FEATURES.md](AUTOMATION_FEATURES.md) | Advanced users | 20 মিনিট |

---

## 🔐 নিরাপত্তা নোট

⚠️ **গুরুত্বপূর্ণ:**
- **কখনো App Secret শেয়ার করবেন না**
- **Access Tokens গোপনীয় রাখুন**
- Regular token refresh করুন (প্রতি 60 দিনে)
- সব credentials encrypted database এ রাখা হয়

---

## 🔗 সহায়ক রিসোর্স

### Facebook Official Documentation
- [Messenger Platform](https://developers.facebook.com/docs/messenger-platform)
- [Webhooks Guide](https://developers.facebook.com/docs/messenger-platform/webhooks)
- [Access Tokens](https://developers.facebook.com/docs/access-tokens)

### ERPNext Resources
- [ERPNext Documentation](https://docs.erpnext.com)
- [Frappe Framework](https://frappeframework.com)

---

## 🎯 কী করতে পারেন

এই integration দিয়ে আপনি:

1. **বার্তা ম্যানেজমেন্ট**
   - Facebook বার্তা ট্র্যাক করুন
   - Customer inquiry এর উত্তর দিন
   - Conversation history রাখুন

2. **বিক্রয় এবং মার্কেটিং**
   - Leads সংগ্রহ করুন (Lead Forms)
   - Promotional posts সাজান
   - Best time এ পোস্ট করুন

3. **গ্রাহক সেবা**
   - Auto-replies সেটআপ করুন
   - FAQ এর উত্তর স্বয়ংক্রিয়ভাবে দিন
   - Response time উন্নত করুন

---

## 📞 সহায়তা

সমস্যা হলে:

1. ✅ Troubleshooting guides পড়ুন
2. ✅ আপনার System Administrator এর সাথে যোগাযোগ করুন
3. ✅ Error logs দেখুন: `/app/error-log`

---

## 🤝 অবদান

ফিডব্যাক এবং পরামর্শ স্বাগত!

---

## 📄 লাইসেন্স

এই মডিউল Frappe Framework license এর অধীন।

---

## 🚀 শুরু করুন

**এখনই শুরু করুন:**

1. 👉 [QUICK_START.md](QUICK_START.md) পড়ুন (5 মিনিট)
2. 👉 `/app/facebook-settings` খুলুন
3. 👉 "Launch Setup Wizard" ক্লিক করুন

**সুখী integrating! 🎉**

---

**আপডেট:** এই নতুন সংস্করণ comprehensive documentation, interactive wizard এবং improved user experience সহ আসে।
