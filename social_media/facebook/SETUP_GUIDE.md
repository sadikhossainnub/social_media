# Facebook Integration Setup Guide

আপনার ERPNext সিস্টেমে Facebook integration সেটআপ করার জন্য এই step-by-step গাইড অনুসরণ করুন।

## 📋 পূর্বশর্তসমূহ

- একটি Facebook পেজ
- Facebook Developer অ্যাকাউন্ট
- ERPNext সিস্টেম অ্যাক্সেস (System Manager রোল)

---

## ✅ Step 1: Facebook Developer App তৈরি করুন

### ধাপ ১.১: Developer Account এ লগইন করুন
1. https://developers.facebook.com এ যান
2. আপনার Facebook অ্যাকাউন্ট দিয়ে লগইন করুন
3. **"Get Started"** বাটনে ক্লিক করুন

### ধাপ ১.২: নতুন App তৈরি করুন
1. **"My Apps"** মেনুতে যান
2. **"Create App"** বাটনে ক্লিক করুন
3. App প্রকার হিসেবে **"Business"** নির্বাচন করুন
4. নিচের তথ্য পূরণ করুন:
   - **App Name**: আপনার ব্যবসার নাম (যেমন: MyBusiness Messenger)
   - **App Email**: আপনার ইমেইল
   - **App Purpose**: Business Management

### ধাপ ১.৩: Messenger Product যোগ করুন
1. App ড্যাশবোর্ডে যান
2. **"Add Products"** এ ক্লিক করুন
3. **Messenger** খুঁজুন এবং **"Set Up"** ক্লিক করুন
4. স্বাগত স্ক্রিন পরবর্তী করুন

---

## 🔑 Step 2: App Credentials পান

### ধাপ ২.১: App ID এবং Secret পান
1. **Settings > Basic** এ যান
2. নিচের তথ্য কপি করুন:
   - **App ID** (দীর্ঘ সংখ্যা)
   - **App Secret** (দীর্ঘ স্ট্রিং - গোপনীয় রাখুন!)

### ধাপ ২.२: ERPNext এ ক্রেডেনশিয়াল যোগ করুন
1. ERPNext-এ **Facebook Settings** খুলুন (`/app/facebook-settings`)
2. নিচের ফিল্ডগুলি পূরণ করুন:
   - **App ID**: আপনার Facebook App ID
   - **App Secret**: আপনার Facebook App Secret
3. **Save** ক্লিক করুন

---

## 🛡️ Step 3: Verification Token তৈরি করুন

### ধাপ ३.१: Token জেনারেট করুন
1. Facebook Settings পৃষ্ঠায় থাকুন
2. **"Generate Token"** বাটনে ক্লিক করুন
3. Token স্বয়ংক্রিয়ভাবে তৈরি হবে এবং পূরণ হবে

**বিকল্প**: আপনি নিজে একটি শক্তিশালী টোকেন তৈরি করতে পারেন
- কমপক্ষে ২০ অক্ষর দীর্ঘ হওয়া উচিত
- বড় হাতের এবং ছোট হাতের অক্ষর মিশ্রিত করুন
- সংখ্যা এবং বিশেষ চিহ্ন অন্তর্ভুক্ত করুন

উদাহরণ: `MyApp2024@SecureToken#789`

---

## 🔗 Step 4: Webhook Configure করুন

### ধাপ ४.१: Callback URL কপি করুন
1. ERPNext-এ Facebook Settings খোলা থাকুন
2. **"Callback URL"** ফিল্ড খুঁজুন
3. **"Copy Callback URL"** বাটনে ক্লিক করুন

এটি কিছু এমন দেখাবে:
```
https://yoursite.erpnext.com/api/method/social_media.facebook.api.webhook
```

### ধাপ ४.२: Facebook এ Webhook যোগ করুন
1. Facebook Developer Dashboard-এ যান
2. **Messenger > Settings** এ নেভিগেট করুন
3. **Webhooks** সেকশনে **"Add Callback URL"** ক্লিক করুন
4. নিচের তথ্য পূরণ করুন:
   - **Callback URL**: ERPNext থেকে কপি করা URL
   - **Verify Token**: আপনার তৈরি করা Verification Token
5. **"Subscribe to Webhook Events"** এ নিচের ইভেন্ট চেক করুন:
   - ✅ messages
   - ✅ messaging_postbacks
   - ✅ message_deliveries
   - ✅ message_reads
   - ✅ messaging_optins
   - ✅ messaging_optouts
6. **"Verify and Save"** ক্লিক করুন

### ধাপ ४.३: ERPNext এ Webhook চিহ্নিত করুন
1. ERPNext-এ Facebook Settings এ ফিরুন
2. **"Webhook Configured"** চেকবক্স চেক করুন
3. **Save** ক্লিক করুন

---

## 🔐 Step 5: Page Access Token পান

### ধাপ ५.१: Token জেনারেট করুন
1. Facebook Developer Dashboard-এ যান
2. **Messenger > Settings** এ স্ক্রোল করুন
3. **"Access Tokens"** সেকশনে **"Add or Remove Page"** ক্লিক করুন
4. আপনার Facebook Page নির্বাচন করুন
5. কনফার্মেশনের পরে, নতুন **Page Access Token** দেখা যাবে
6. এটি কপি করুন

### ধাপ ५.२: ERPNext এ Page Access Token যোগ করুন
1. ERPNext-এ Facebook Settings খুলুন
2. **"Page Access Token"** ফিল্ডে পেস্ট করুন
3. **Save** ক্লিক করুন

---

## ✔️ Step 6: Integration পরীক্ষা করুন

### ধাপ ६.१: সেটআপ ভেরিফাই করুন
1. ERPNext-এ Facebook Settings খোলা থাকুন
2. সব ফিল্ড পূরণ হয়েছে কিনা চেক করুন
3. **Save** ক্লিক করুন

### ধাপ ६.२: একটি Test Message পাঠান
1. আপনার Facebook Page এ যান
2. আপনার নিজের Page-কে একটি বার্তা পাঠান
3. ERPNext-এ **Facebook Message Log** তে যান (`/app/facebook-message-log`)
4. বার্তা প্রদর্শিত হয়েছে কিনা চেক করুন

### ধাপ ६.३: Response পাঠানোর পরীক্ষা করুন
1. ERPNext-এ একটি নতুন Facebook Message তৈরি করুন
2. একটি প্রতিক্রিয়া বার্তা লিখুন
3. **Send** ক্লিক করুন
4. Facebook Page এ চেক করুন যে বার্তা পৌঁছেছে কিনা

---

## 🚀 Troubleshooting

### সমস্যা: "Webhook verification failed"
**সমাধান:**
- Verification Token সঠিক কিনা নিশ্চিত করুন
- Callback URL সঠিক কিনা চেক করুন
- আপনার সাইট internet এ accessible কিনা যাচাই করুন

### সমস্যা: "Invalid App ID or Secret"
**সমাধান:**
- Facebook Developer Dashboard থেকে সঠিক credentials কপি করুন
- কোন অতিরিক্ত স্পেস নেই কিনা চেক করুন

### সমস্যা: "Page access denied"
**সমাধান:**
- নিশ্চিত করুন যে আপনি আপনার নিজের Page-এর অ্যাডমিন
- নতুন Page Access Token জেনারেট করুন

### সমস্যা: বার্তা ERPNext-এ দেখা যাচ্ছে না
**সমাধান:**
- Webhook events সঠিকভাবে subscribe করা হয়েছে কিনা চেক করুন
- আপনার সাইটের logs দেখুন (`/app/error-log`)
- Facebook Settings এ "Webhook Verified" চেক করুন

---

## 📚 সহায়ক সম্পদ

- [Facebook Messenger Platform Documentation](https://developers.facebook.com/docs/messenger-platform)
- [Webhook Setup Guide](https://developers.facebook.com/docs/messenger-platform/webhooks)
- [Access Tokens বুঝুন](https://developers.facebook.com/docs/access-tokens)
- [Facebook Developer Community](https://developers.facebook.com/community)

---

## ✨ এখন কী করবেন?

Integration সেটআপ সম্পন্ন হয়েছে! এখন আপনি:

1. **বার্তা পাঠানো/গ্রহণ করা** - Facebook থেকে বার্তা পান এবং প্রতিক্রিয়া পাঠান
2. **Auto-Replies সেটআপ করা** - বিশেষ বার্তার জন্য স্বয়ংক্রিয় উত্তর সেট করুন
3. **Scheduled Posts তৈরি করা** - ভবিষ্যতের জন্য পোস্ট সাজান
4. **Lead Forms একীভূত করা** - Facebook Lead Ads থেকে লিড সংগ্রহ করুন

ERPNext-এ Facebook Workspace-এ যান এই সব বৈশিষ্ট্য অ্যাক্সেস করতে।

---

## 📞 সাপোর্ট প্রয়োজন?

যদি আপনি কোনো সমস্যার সম্মুখীন হন:
1. উপরের Troubleshooting সেকশন চেক করুন
2. আপনার সিস্টেম অ্যাডমিনিস্ট্রেটরের সাথে যোগাযোগ করুন
3. সোশ্যাল মিডিয়া মডিউলের ডকুমেন্টেশন দেখুন

সুখী ইন্টিগ্রেশন! 🎉
