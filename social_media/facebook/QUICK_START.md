# Facebook Integration - Quick Start (5 মিনিট)

এই দ্রুত গাইড অনুসরণ করে মাত্র ৫ মিনিটে Facebook integration সেটআপ করুন!

## 📊 সংক্ষিপ্ত ওভারভিউ

```
5 সহজ ধাপ:
1️⃣ Facebook Developer App তৈরি করুন (২ মিনিট)
2️⃣ Credentials কপি করুন (১ মিনিট)  
3️⃣ ERPNext এ ভরুন (১ মিনিট)
4️⃣ Webhook Configure করুন (১ মিনিট)
```

---

## ⚡ Step-by-Step (দ্রুত সংস্করণ)

### ✅ Step 1: Facebook App তৈরি করুন (2 মিনিট)

```
1. https://developers.facebook.com যান
2. "Get Started" → নতুন অ্যাকাউন্ট তৈরি করুন
3. "Create App" → "Business" নির্বাচন করুন
4. "Messenger" product যোগ করুন
```

### ✅ Step 2: সাঁতার পান (1 মিনিট)

Settings > Basic এ যান এবং কপি করুন:
- **App ID** (বড় নম্বর)
- **App Secret** (দীর্ঘ অক্ষর)

### ✅ Step 3: ERPNext এ যান (1 মিনিট)

```
1. Facebook Settings খুলুন (/app/facebook-settings)
2. App ID এবং Secret পেস্ট করুন
3. "Generate Token" বাটন ক্লিক করুন
4. Save করুন ✅
```

### ✅ Step 4: Webhook Setup করুন (1 মিনিট)

Facebook Dashboard এ:
```
1. Messenger > Settings যান
2. Webhooks > "Add Callback URL" ক্লিক করুন
3. ERPNext থেকে URL কপি করুন (Facebook Settings এ)
4. Token পেস্ট করুন (যা আপনি generate করেছিলেন)
5. Subscribe করুন: messages, postbacks, deliveries, reads
6. Save করুন ✅
```

---

## 🎉 সমাপ্ত!

আপনার Facebook integration এখন লাইভ! এখন করতে পারেন:
- Facebook থেকে বার্তা পান
- ERPNext থেকে বার্তা পাঠান  
- Auto-replies সেটআপ করুন
- Posts তৈরি করুন

---

## 🆘 সমস্যা?

| সমস্যা | সমাধান |
|--------|--------|
| Webhook verification failed | Callback URL এবং Token ভেরিফাই করুন |
| Invalid App ID/Secret | Facebook থেকে সঠিক credentials কপি করুন |
| বার্তা আসছে না | Webhook events subscribe করা হয়েছে কিনা চেক করুন |
| Token হারিয়ে গেছে | "Generate Token" বাটন আবার ক্লিক করুন |

---

## 📚 আরও জানতে

বিস্তারিত গাইডের জন্য দেখুন: `/app/facebook-integration-guide`

সুখী ইন্টিগ্রেশন! 🚀
