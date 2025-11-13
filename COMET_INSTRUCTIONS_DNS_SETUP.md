# Instructions for Comet: Configure friedmomo.com DNS

## 🎯 Goal
Connect the custom domain **friedmomo.com** (purchased on Squarespace) to the Firebase-hosted SOHO frontend at **friedmomo.web.app**.

---

## 📋 Part 1: Add Custom Domain in Firebase Console

### Step 1: Navigate to Firebase Hosting
1. Go to: https://console.firebase.google.com/project/phoenix-project-386/hosting/sites
2. You should see a site called **"friedmomo"** with the default URL `https://friedmomo.web.app`
3. Click on the **"friedmomo"** site

### Step 2: Add Custom Domain
1. Look for a button that says **"Add custom domain"** or **"Connect domain"**
2. Click that button
3. Enter the domain: **`friedmomo.com`** (without www)
4. Click **"Continue"** or **"Next"**

### Step 3: DNS Setup Instructions
Firebase will now show you DNS records that need to be added. You should see:

**A Records (usually 2):**
- Type: `A`
- Host: `@`
- Value: IP address (something like `151.101.1.195` or similar)

**TXT Record (for verification):**
- Type: `TXT`
- Host: `@`
- Value: Verification string (starts with something like `firebase-hosting-site=`)

**Optional - For www subdomain:**
Firebase might also ask you to add:
- Type: `CNAME`
- Host: `www`
- Value: `friedmomo.web.app`

### Step 4: Copy DNS Records
**IMPORTANT:** Copy ALL the DNS records Firebase shows you. We'll need them for Squarespace.

---

## 📋 Part 2: Configure DNS in Squarespace

### Step 1: Log into Squarespace
1. Go to: https://account.squarespace.com
2. Log in with your credentials

### Step 2: Access Domain Settings
1. Click **"Settings"** in the left sidebar
2. Click **"Domains"**
3. Find and click on **"friedmomo.com"**

### Step 3: Go to DNS Settings
1. Click **"DNS Settings"** or **"Advanced DNS"**
2. You should see a list of DNS records

### Step 4: Add DNS Records from Firebase

For EACH record that Firebase provided, click **"Add Record"** and enter:

#### For A Records:
- **Record Type:** Select `A`
- **Host:** Enter `@`
- **Data/Value:** Enter the IP address from Firebase
- **TTL:** Leave as default (3600) or select "Auto"
- Click **"Save"** or **"Add"**

**Repeat for the second A record** if Firebase provided two IP addresses.

#### For TXT Record (Verification):
- **Record Type:** Select `TXT`
- **Host:** Enter `@`
- **Data/Value:** Paste the verification string from Firebase (e.g., `firebase-hosting-site=friedmomo-abc123`)
- **TTL:** Leave as default (3600) or select "Auto"
- Click **"Save"** or **"Add"**

#### For CNAME Record (www subdomain):
- **Record Type:** Select `CNAME`
- **Host:** Enter `www`
- **Data/Value:** Enter `friedmomo.web.app`
- **TTL:** Leave as default (3600) or select "Auto"
- Click **"Save"** or **"Add"**

### Step 5: Remove Conflicting Records (if any)
If Squarespace shows any existing A or AAAA records pointing to Squarespace servers:
1. Look for records with Host `@` that have different IP addresses
2. **Delete** those old records
3. Only keep the new Firebase A records

**Common conflicting IPs to remove:**
- `198.185.159.144`
- `198.185.159.145`
- `198.49.23.144`
- `198.49.23.145`

---

## 📋 Part 3: Verify in Firebase

### Step 1: Return to Firebase Console
1. Go back to the Firebase tab in your browser
2. On the custom domain setup page, click **"Verify"** or **"Connect Domain"**

### Step 2: Wait for Verification
- Firebase will check if the DNS records are set up correctly
- This can take **5 minutes to 1 hour** for verification
- You might see a message like "Waiting for DNS records to propagate"

### Step 3: SSL Certificate Provisioning
Once verified, Firebase will automatically:
- Provision a free SSL certificate (HTTPS)
- This usually takes **10-30 minutes**
- You'll see status change to "Connected" when done

---

## 🔍 How to Check Progress

### Check DNS Propagation:
Visit these sites to see if DNS has propagated globally:
- https://dnschecker.org/#A/friedmomo.com
- https://www.whatsmydns.net/#A/friedmomo.com

### Expected Results:
- **A Record:** Should show Firebase IP address(es)
- **TXT Record:** Should show Firebase verification string
- **CNAME (www):** Should point to `friedmomo.web.app`

---

## ⏱️ Timeline Expectations

| Step | Time Required |
|------|---------------|
| Add DNS records in Squarespace | 5-10 minutes |
| DNS propagation (partial) | 5 minutes - 1 hour |
| DNS propagation (global) | 1-48 hours |
| Firebase verification | 5 minutes - 1 hour |
| SSL certificate provisioning | 10-30 minutes |
| **Total (optimistic)** | **30 minutes - 2 hours** |
| **Total (typical)** | **1-4 hours** |
| **Total (worst case)** | **24-48 hours** |

---

## ✅ Success Checklist

Once everything is set up, you should be able to:

- [ ] Visit https://friedmomo.com (redirects from Squarespace to Firebase)
- [ ] See the SOHO landing page (not Squarespace "under construction")
- [ ] Have a green padlock (HTTPS/SSL working)
- [ ] Visit https://www.friedmomo.com (also works with www)
- [ ] Log in with Google (OAuth flow working)
- [ ] Navigate the site without errors

---

## ❗ Common Issues & Solutions

### Issue 1: "Can't add A record in Squarespace"
**Solution:** Delete any existing A records pointing to Squarespace servers first

### Issue 2: "Firebase says DNS not verified after 1 hour"
**Solution:**
1. Double-check all records are entered correctly (no typos)
2. Wait another hour for propagation
3. Try https://dnschecker.org to see if records are visible

### Issue 3: "Certificate provisioning failed"
**Solution:**
1. Check that A records point to correct Firebase IPs
2. Remove any other CNAME or AAAA records for `@` host
3. Wait 24 hours for DNS to fully propagate

### Issue 4: "Site still shows Squarespace page"
**Solution:**
1. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
2. Try incognito/private browsing window
3. Wait for DNS propagation (can take hours)
4. Check dnschecker.org to see if your ISP has updated DNS

---

## 📞 What to Report Back

After completing these steps, please report:

1. ✅ **Completed:** DNS records added in Squarespace
2. ✅ **Completed:** Firebase verification successful
3. ✅ **Completed:** SSL certificate provisioned
4. ✅ **Working:** friedmomo.com shows SOHO website
5. ✅ **Working:** OAuth login works on custom domain

Or if you encounter issues:
- Screenshot of error messages
- Which step you're stuck on
- Current status in Firebase Console

---

## 🎉 Expected Final Result

Once complete:
- **https://friedmomo.com** → SOHO React Frontend (your social media site)
- **https://www.friedmomo.com** → Redirects to friedmomo.com
- **https://friedmomo.web.app** → Still works (Firebase default URL)
- **Backend API:** https://phoenix-234619602247.us-central1.run.app (unchanged)

All with:
- ✅ HTTPS/SSL encryption
- ✅ Google OAuth login working
- ✅ Fast global CDN delivery
- ✅ Professional custom domain

---

**Instructions Created:** 2025-11-12
**Status:** Ready for Comet to execute
**Estimated Time:** 30 minutes - 2 hours (mostly waiting for DNS)
