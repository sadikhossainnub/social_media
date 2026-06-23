# Facebook Automation System 🚀

একটি সম্পূর্ণ AI-পাওয়ারড অটোমেশন সিস্টেম Facebook পেজ ম্যানেজমেন্টের জন্য।

## ✨ প্রধান বৈশিষ্ট্য

### 1. 🤖 স্বয়ংক্রিয় বার্তা উত্তর (Automatic Message Reply)
**বৈশিষ্ট্য:**
- ✅ রিয়েল-টাইম মেসেজ সনাক্তকরণ
- ✅ কাস্টমাইজযোগ্য স্বয়ংক্রিয় উত্তর টেমপ্লেট
- ✅ দ্রুত প্রতিক্রিয়া পরামর্শ
- ✅ শর্তসাপেক্ষ ট্রিগার (সব বার্তা, কীওয়ার্ড মিল, সেন্টিমেন্ট)
- ✅ AI-চালিত প্রতিক্রিয়া জেনারেশন
- ✅ প্রশাসক অনুমোদন প্রয়োজন (ঐচ্ছিক)

**DocType:** `Facebook Auto Reply`
**ব্যবহার:**
```python
from social_media.facebook.doctype.facebook_auto_reply.facebook_auto_reply import process_incoming_message

message_data = {
    "page_id": "page_123",
    "message_id": "msg_456",
    "sender_id": "user_789",
    "sender_name": "গ্রাহক নাম",
    "message_text": "আপনার পণ্যের দাম কত?"
}
process_incoming_message(message_data)
```

---

### 2. 💬 AI মন্তব্য উত্তর (AI Comment Reply)
**বৈশিষ্ট্য:**
- ✅ স্বয়ংক্রিয় সেন্টিমেন্ট বিশ্লেষণ
- ✅ প্রসঙ্গ-সচেতন AI প্রতিক্রিয়া
- ✅ প্রশাসক অনুমোদন ওয়ার্কফ্লো
- ✅ টোন কাস্টমাইজেশন (পেশাদার, বন্ধুত্বপূর্ণ, হাস্যরস)
- ✅ একাধিক প্রতিক্রিয়া বিকল্প
- ✅ স্বয়ংক্রিয় প্রকাশনা

**DocType:** `Facebook AI Comment Reply`
**বৈশিষ্ট্য:**
- সেন্টিমেন্ট স্কোর: -1 (অত্যন্ত নেতিবাচক) থেকে +1 (অত্যন্ত ইতিবাচক)
- সনাক্ত করা মনোভাব: ইতিবাচক/নিরপেক্ষ/নেতিবাচক
- জেনারেট প্রতিক্রিয়া + বিকল্প

---

### 3. 🎯 স্মার্ট রেসপন্স জেনারেটর (Smart Response Generator)
**বৈশিষ্ট্য:**
- ✅ প্রসঙ্গ-সচেতন প্রস্তাব
- ✅ একাধিক প্রতিক্রিয়া বিকল্প
- ✅ টোন কাস্টমাইজেশন
- ✅ প্রতিটি প্রতিক্রিয়া স্কোর করা
- ✅ সহজ নির্বাচন এবং প্রকাশনা

**DocType:** `Facebook Smart Response`
**API উদাহরণ:**
```python
from social_media.facebook.doctype.facebook_smart_response.facebook_smart_response import generate_smart_response

response = generate_smart_response(
    page_id="page_123",
    query="আপনাদের কাছে বড় সাইজ আছে?",
    context="গ্রাহক আগে একটি ড্রেস সম্পর্কে প্রশ্ন করেছিল",
    response_type="Product Inquiry"
)

# ফলাফল:
# {
#     "success": True,
#     "options": [
#         {"text": "হ্যাঁ, আমাদের কাছে সব সাইজ আছে...", "score": 0.9},
#         {"text": "আমাদের সাইজ চার্ট এখানে দেখুন...", "score": 0.8},
#         {"text": "কোন নির্দিষ্ট সাইজ খুঁজছেন?", "score": 0.7}
#     ]
# }
```

---

### 4. 📅 স্বয়ংক্রিয় পোস্ট প্রকাশক (Auto Post Publisher)
**বৈশিষ্ট্য:**
- ✅ তাৎক্ষণিক/সময়সূচী প্রকাশনা
- ✅ সেরা সময় AI গণনা
- ✅ পুনরাবৃত্তি নির্ধারণ
- ✅ এনগেজমেন্ট ট্র্যাকিং
- ✅ বাল্ক পোস্ট প্রকাশনা
- ✅ প্রশাসক বিজ্ঞপ্তি

**DocType:** `Facebook Auto Post Publisher`
**সময়সূচী প্রকার:**
- `Immediate`: এখনই প্রকাশ করুন
- `Scheduled`: নির্দিষ্ট সময়ে
- `Best Time`: AI দ্বারা গণনা করা সেরা সময়
- `Recurring`: পুনরাবৃত্তি প্রকাশনা

**বাল্ক প্রকাশনা:**
```python
from social_media.facebook.doctype.facebook_auto_post_publisher.facebook_auto_post_publisher import schedule_multiple_posts

posts_data = [
    {
        "page_id": "page_123",
        "content": "নতুন গ্রীষ্মকালীন সংগ্রহ এসে গেছে! 🌞",
        "image": "image_url",
        "schedule_type": "Scheduled",
        "schedule_datetime": "2026-05-30 18:00:00",
        "analyze": True,
        "notify": True
    },
    {
        "page_id": "page_123",
        "content": "বিশেষ ছাড় অফার - ৩০% পর্যন্ত! 🎉",
        "schedule_type": "Best Time",
        "analyze": True
    }
]

result = schedule_multiple_posts(posts_data)
```

---

### 5. 🖼️ ইমেজ ইন্টারঅ্যাকশন হ্যান্ডলিং (Image Interaction)
**বৈশিষ্ট্য:**
- ✅ ইমেজ স্বীকৃতি
- ✅ ভিজ্যুয়াল কন্টেন্ট পরামর্শ
- ✅ মিডিয়া সংযোজন সমর্থন
- ✅ স্বয়ংক্রিয় ইমেজ ট্যাগিং

---

### 6. 📊 ব্যবহারকারী ইন্টারঅ্যাকশন ডেটা সংরক্ষণ (User Interaction Data)
**বৈশিষ্ট্য:**
- ✅ বার্তা ইতিহাস ট্র্যাকিং
- ✅ মন্তব্য বিশ্লেষণ
- ✅ গ্রাহক অন্তর্দৃষ্টি
- ✅ এনগেজমেন্ট মেট্রিক্স

**ডেটা মডেল:**
```
Facebook Message Log:
- message_id: Facebook message ID
- sender_id, sender_name: প্রেরকের তথ্য
- message_text: বার্তা কন্টেন্ট
- is_auto_reply: স্বয়ংক্রিয় উত্তর ছিল?
- status: Received, Sent, Pending
- interaction_timestamp: সময়

Facebook Comment Analytics:
- comment_id: Facebook comment ID
- sentiment: Positive/Neutral/Negative
- sentiment_score: -1 থেকে +1
- engagement_count: প্রতিক্রিয়া সংখ্যা
```

---

### 7. 🔔 প্রশাসক বিজ্ঞপ্তি (Admin Notifications)
**বৈশিষ্ট্য:**
- ✅ নতুন বার্তা সতর্কতা
- ✅ মন্তব্য বিজ্ঞপ্তি
- ✅ সমালোচনামূলক ইভেন্ট সতর্কতা
- ✅ অনুমোদনের জন্য পেন্ডিং জিজ্ঞাসা
- ✅ প্রকাশনা সাফল্য বিজ্ঞপ্তি

**সতর্কতা ট্রিগার:**
- নতুন গ্রাহক থেকে বার্তা
- নেতিবাচক সেন্টিমেন্ট সনাক্ত করা
- এনগেজমেন্ট মাইলফলক
- পোস্ট প্রকাশনা সাফল্য/ব্যর্থতা
- প্রশাসক অনুমোদনের জন্য অপেক্ষমান আইটেম

---

## 🔧 অটোমেশন সিস্টেম API

### মূল ক্লাস: `FacebookAutomationSystem`

```python
from social_media.facebook.automation import FacebookAutomationSystem

# সিস্টেম শুরু করুন
automation = FacebookAutomationSystem(page_id="page_123")

# বার্তা হ্যান্ডেল করুন
automation.handle_incoming_message({
    "message_id": "msg_456",
    "sender_id": "user_789",
    "sender_name": "রহিম",
    "message_text": "আপনাদের কাছে কুর্তি আছে?",
    "has_image": False,
    "has_media": False
})

# মন্তব্য হ্যান্ডেল করুন
automation.handle_incoming_comment({
    "comment_id": "cmt_123",
    "post_id": "post_456",
    "comment_text": "দারুণ পোশাক!",
    "author_id": "user_789",
    "author_name": "রহিম"
})
```

### স্ট্যাটাস এবং অ্যানালিটিক্স

```python
from social_media.facebook.automation import get_automation_status, get_interaction_analytics

# অটোমেশন স্ট্যাটাস
status = get_automation_status("page_123")
# {
#     "auto_replies_enabled": 5,
#     "ai_comment_replies": 12,
#     "scheduled_posts": 8,
#     "automation_active": True
# }

# ইন্টারঅ্যাকশন অ্যানালিটিক্স (গত ৩০ দিন)
analytics = get_interaction_analytics("page_123", days=30)
# {
#     "total_messages": 145,
#     "unique_users": 87,
#     "period_days": 30
# }
```

---

## 🚀 দ্রুত শুরু

### ধাপ ১: অটো রিপ্লাই সেটআপ করুন

1. নতুন `Facebook Auto Reply` ডকুমেন্ট তৈরি করুন
2. Facebook পেজ নির্বাচন করুন
3. ট্রিগার টাইপ সেট করুন (সব বার্তা/কীওয়ার্ড মিল)
4. টেমপ্লেট প্রতিক্রিয়া লিখুন বা AI সক্ষম করুন
5. সংরক্ষণ এবং সক্ষম করুন

### ধাপ ২: মন্তব্য উত্তর সক্ষম করুন

1. `Facebook Settings` এ যান
2. "Enable AI Comment Replies" চেক করুন
3. টোন এবং সেটিংস পছন্দ করুন

### ধাপ ৩: পোস্ট নির্ধারণ করুন

1. নতুন `Facebook Auto Post Publisher` তৈরি করুন
2. পোস্ট কন্টেন্ট এবং ইমেজ যোগ করুন
3. সময়সূচী প্রকার নির্বাচন করুন
4. জমা দিন এবং প্রকাশ করা হবে

---

## 🔌 ওয়েবহুক ইন্টিগ্রেশন

```python
# Facebook webhook থেকে ডেটা প্রক্রিয়া করুন
from social_media.facebook.automation import process_facebook_webhook

@frappe.whitelist(allow_guest=True)
def facebook_webhook():
    data = frappe.request.get_json()
    process_facebook_webhook(data)
    return {"status": "ok"}
```

---

## ⚙️ কনফিগারেশন

### AI মডেল নির্বাচন

সমর্থিত মডেল:
- Claude 3.5 Sonnet (সুপারিশকৃত - সর্বোত্তম ভারসাম্য)
- Claude 3 Opus (দীর্ঘ প্রসঙ্গ)
- GPT-4 (উন্নত ক্ষমতা)
- Gemini Pro (দ্রুত প্রতিক্রিয়া)

### তাপমাত্রা সেটিংস

- `0.0`: নির্ধারক, সামঞ্জস্যপূর্ণ প্রতিক্রিয়া
- `0.5-0.7`: ভারসাম্য (সুপারিশকৃত)
- `1.0`: সৃজনশীল, বৈচিত্র্যময় প্রতিক্রিয়া

---

## 📈 পর্যবেক্ষণ এবং বিশ্লেষণ

### রিপোর্ট এবং মেট্রিক্স

উপলব্ধ প্রতিবেদন:
- বার্তা এবং মন্তব্য পরিসংখ্যান
- সেন্টিমেন্ট বিশ্লেষণ ট্রেন্ড
- এনগেজমেন্ট মেট্রিক্স
- স্বয়ংক্রিয় প্রতিক্রিয়া কার্যকারিতা
- পোস্ট পারফরম্যান্স বিশ্লেষণ

### ডেটা রপ্তানি

সমস্ত ডেটা স্ট্যান্ডার্ড Frappe রপ্তানি বিন্যাসে উপলব্ধ:
- CSV
- Excel
- JSON

---

## 🛡️ নিরাপত্তা এবং গোপনীয়তা

- সমস্ত API কল এনক্রিপ্ট করা হয়
- ব্যবহারকারীর ডেটা নিরাপদভাবে সংরক্ষণ করা হয়
- নিয়মিত ব্যাকআপ সক্ষম
- অডিট লগ সমস্ত পরিবর্তনের জন্য

---

## 🐛 সমস্যা সমাধান

### সাধারণ সমস্যা

**প্রশ্ন: অটো রিপ্লাই কাজ করছে না**
- ✓ Facebook পেজ সংযোগ যাচাই করুন
- ✓ অটো রিপ্লাই সক্ষম আছে তা যাচাই করুন
- ✓ Facebook logs এ ত্রুটি দেখুন

**প্রশ্ন: AI প্রতিক্রিয়া খুব দীর্ঘ**
- ✓ `max_tokens` কমিয়ে দিন
- ✓ প্রম্পট টেমপ্লেট ছোট করুন
- ✓ ভিন্ন AI মডেল চেষ্টা করুন

**প্রশ্ন: পোস্ট প্রকাশিত হয়নি**
- ✓ সময়সূচী সময় ভবিষ্যতে আছে কিনা চেক করুন
- ✓ Facebook টোকেন এখনও বৈধ কিনা যাচাই করুন
- ✓ ত্রুটি লগ দেখুন

---

## 📞 সমর্থন

সমস্যার জন্য, দয়া করে লগ ফাইল দেখুন:
- `দেশ/সেটিংস/Error Log` - সমস্ত ত্রুটি
- প্রতিটি ডকুমেন্টে মন্তব্য/নোট ট্যাব
- Facebook অ্যাপ এবিলিটি লগ

---

**ডেভেলপড দ্বারা:** Prime Technology of Bangladesh  
**লাইসেন্স:** MIT  
**সংস্করণ:** 1.0.0  
**আপডেট:** May 28, 2026
