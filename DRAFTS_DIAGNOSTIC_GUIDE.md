# Drafts Tab Diagnostic Guide

## 🔍 Understanding the Issue

You mentioned: **"When I click on Drafts, it still opens the profile section (same thing that the Soho button redirects to)"**

This is actually **CORRECT BEHAVIOR** - but you should be seeing tabs! Here's why:

### How It's Supposed to Work (Instagram Style)

1. **"Soho" button** → Takes you to `/soho` (main social feed)
2. **"Drafts" button** → Takes you to `/soho/[your-username]?tab=drafts` (YOUR profile with drafts tab)

The key difference is:
- **Same profile page** but **different tab active**
- You should see **two tab buttons**: `POSTS` and `DRAFTS`
- Clicking "Drafts" should make the `DRAFTS` tab active

### What You Should See

```
[Your Profile Header with Avatar and Stats]
─────────────────────────────────────
[POSTS]     [DRAFTS] ← Two tab buttons
─────────────────────────────────────
[Content changes based on active tab]
```

---

## 🐛 Diagnostic Steps

### Step 1: Open Browser Console
1. Open your browser
2. Press `F12` (Windows/Linux) or `Cmd+Option+J` (Mac)
3. Click on the **Console** tab

### Step 2: Navigate to Your Profile
1. Click the **"Drafts"** link in the navigation
2. Watch the console output

### Step 3: Check Console Logs

You should see output like this:

```
🔍 Profile Debug Info:
  - Username: sumanurawat12
  - isOwnProfile: true  ← SHOULD BE TRUE
  - User Data: {username: "sumanurawat12", ...}
  - Drafts tab element: <button class="profile-tab" ...>
  ✅ This is YOUR profile - showing drafts tab
  - URL tab parameter: drafts
  📂 Switching to DRAFTS tab
🔄 Switching to tab: drafts
  - Target tab button: <button class="profile-tab" ...>
  - Target content: <div id="draftsContent" ...>
  - New URL: http://localhost:8080/soho/sumanurawat12?tab=drafts
```

### Step 4: Visual Inspection

Look at the page and check:

- [ ] **Do you see TWO tab buttons?** (POSTS and DRAFTS)
- [ ] **Is the DRAFTS tab highlighted/active?** (dark text, top border)
- [ ] **Does the URL say `?tab=drafts`?**
- [ ] **Is there content below the tabs?** (drafts or empty state)

---

## 🚨 Possible Issues and Solutions

### Issue 1: `isOwnProfile: false` in Console

**Problem:** API not returning correct ownership status

**Check Console for:**
```
  - isOwnProfile: false  ← BAD! Should be true
  ❌ Not your profile - hiding drafts tab
```

**Solution:** Backend fix wasn't applied or server not restarted

**Fix:**
```bash
# Make sure you've saved all files
# Restart the Flask server
# Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
```

---

### Issue 2: No Tab Buttons Visible

**Problem:** Tabs exist but are hidden by CSS

**Check Console for:**
```
  - Drafts tab element: null  ← BAD! Tab doesn't exist in DOM
```

**Solution:** Template not rendered correctly

**Check in Browser:**
1. Right-click on page → Inspect
2. Search for `profile-tabs` in HTML
3. Verify buttons exist:
```html
<div class="profile-tabs">
    <button class="profile-tab active" data-tab="posts">POSTS</button>
    <button class="profile-tab" data-tab="drafts" style="display: flex;">DRAFTS</button>
</div>
```

---

### Issue 3: Tabs Exist But Not Styled

**Problem:** Bootstrap Icons not loading or CSS not applied

**Check:**
1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Refresh page
4. Look for failed requests (red lines)
5. Check if `bootstrap-icons.css` loaded successfully

**Solution:**
```html
<!-- Verify this is in your <head> -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
```

---

### Issue 4: Tab Switching Not Working

**Problem:** JavaScript not firing

**Check Console for:**
```
🔄 Switching to tab: drafts  ← Should see this
  - Target tab button: null  ← BAD! Button not found
```

**Solution:** Tab selector incorrect

**Check in Console:**
```javascript
// Run this in browser console:
document.querySelector('[data-tab="drafts"]')
// Should return: <button class="profile-tab" ...>
// If it returns null, the button doesn't exist
```

---

### Issue 5: Content Not Changing

**Problem:** Both tabs show same content

**Check:**
1. Inspect the page HTML
2. Look for `<div id="postsContent">` and `<div id="draftsContent">`
3. Check which has the `active` class

**Should look like:**
```html
<!-- When on POSTS tab -->
<div id="postsContent" class="tab-content active">...</div>
<div id="draftsContent" class="tab-content">...</div>  ← hidden

<!-- When on DRAFTS tab -->
<div id="postsContent" class="tab-content">...</div>  ← hidden
<div id="draftsContent" class="tab-content active">...</div>
```

---

## 🎯 Quick Test

Run this in your browser console **while on your profile page**:

```javascript
// Test 1: Check if tab buttons exist
console.log('Posts tab:', document.getElementById('postsTab'));
console.log('Drafts tab:', document.getElementById('draftsTab'));

// Test 2: Check tab visibility
const draftsTab = document.getElementById('draftsTab');
console.log('Drafts tab display style:', draftsTab?.style.display);

// Test 3: Check content containers
console.log('Posts content:', document.getElementById('postsContent'));
console.log('Drafts content:', document.getElementById('draftsContent'));

// Test 4: Manually switch to drafts
switchTab('drafts');
```

---

## 📸 What to Screenshot

Please take screenshots showing:

1. **Full page view** - showing profile header and tabs area
2. **Browser console** - showing the debug logs
3. **Browser DevTools** - showing the HTML structure (Inspect Element on tab area)
4. **URL bar** - showing the current URL

---

## 🔧 Emergency Fix: Force Show Tabs

If tabs still don't appear, try this temporary fix in browser console:

```javascript
// Force show drafts tab
const draftsTab = document.getElementById('draftsTab');
if (draftsTab) {
    draftsTab.style.display = 'flex';
    console.log('✅ Forced drafts tab to show');
} else {
    console.error('❌ Drafts tab element not found in DOM');
}

// Switch to drafts tab
switchTab('drafts');
```

---

## 📋 Report Template

After running diagnostics, please report back with:

```
### Console Output
[Paste the 🔍 Profile Debug Info output here]

### Visual Check
- [ ] I see TWO tab buttons (POSTS and DRAFTS)
- [ ] I see ONLY ONE tab button (POSTS)
- [ ] I see NO tab buttons at all
- [ ] URL shows ?tab=drafts: [YES/NO]
- [ ] DRAFTS tab is highlighted/active: [YES/NO]

### Screenshots
[Attach screenshots]

### Additional Info
- Browser: [Chrome/Safari/Firefox]
- Server restarted after code changes: [YES/NO]
- Browser cache cleared: [YES/NO]
```

---

## 💡 Most Likely Issue

Based on your description, I suspect one of these:

1. **Server not restarted** - The `isOwnProfile` fix isn't active yet
2. **Browser cache** - Old JavaScript is running
3. **Styling issue** - Tabs exist but look like regular text/links
4. **No visual distinction** - Tabs are there but POSTS and DRAFTS look identical

**Quick Fix to Try:**
1. Stop your Flask server (Ctrl+C)
2. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
3. Restart server: `./start_local.sh`
4. Navigate to your profile again
5. Check console logs

---

Let me know what you find! 🔍
