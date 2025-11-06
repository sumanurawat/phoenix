# Drafts & Posts Tab UI Testing Instructions

## Test Environment
- **URL**: http://localhost:8080 (or your deployed URL)
- **Browser**: Chrome/Safari (latest version)
- **Required**: Valid user account with tokens

---

## 🎯 What You're Testing

We've implemented an **Instagram-style tab interface** on user profile pages with two tabs:
1. **POSTS** - Published creations visible to everyone
2. **DRAFTS** - Unpublished creations only visible to profile owner

You need to test the complete flow from generation → drafts → publishing → viewing.

---

## 📋 Test Scenarios

### **Scenario 1: Profile Tab Navigation**

**Steps:**
1. Login to your account
2. Navigate to your profile: `/soho/[your-username]`
3. Observe the tabs below your profile stats

**Expected Results:**
- ✅ You should see **two tabs**: `POSTS` and `DRAFTS`
- ✅ POSTS tab has a grid icon (☷)
- ✅ DRAFTS tab has a folder icon (📁)
- ✅ POSTS tab is **active by default** (dark text, top border)
- ✅ Tab text is uppercase and minimal (Instagram style)

**Screenshot Required:** Full page showing both tabs

---

### **Scenario 2: View Another User's Profile**

**Steps:**
1. Navigate to someone else's profile (e.g., `/soho/testuser`)
2. Observe the tabs

**Expected Results:**
- ✅ You should **only see POSTS tab**
- ✅ DRAFTS tab should be **completely hidden**
- ✅ You can only see their published content

**Screenshot Required:** Another user's profile showing only one tab

---

### **Scenario 3: Generate Image (Draft Creation)**

**Steps:**
1. Navigate to Create page (`/create`)
2. Select "Image" as generation type
3. Enter prompt: "A serene beach at sunset"
4. Click "Generate"
5. Wait for generation to complete (~10-15 seconds)

**Expected Results:**
- ✅ You should see a **draft info banner** appear with message like "Your image is ready! Click 'Publish' to share it."
- ✅ A **"Publish to Feed"** button should be visible
- ✅ Your **token balance should decrease by 1** (check top-right corner)
- ✅ Image should appear on the page

**Screenshot Required:** 
- Generation complete screen with draft banner
- Token balance showing deduction

---

### **Scenario 4: Check Drafts Tab After Generation**

**Steps:**
1. Navigate to your profile: `/soho/[your-username]`
2. Click the **DRAFTS** tab

**Expected Results:**
- ✅ You should see the image you just generated
- ✅ It should have a **"Ready"** badge (green)
- ✅ You should see a **"Publish"** button
- ✅ You should see a **"Delete"** button
- ✅ The prompt should be visible

**Screenshot Required:** Drafts tab showing the draft creation with badges

---

### **Scenario 5: Drafts Navigation Link**

**Steps:**
1. From any page, click **"Drafts"** link in the top navigation bar
2. Observe where you land

**Expected Results:**
- ✅ Should navigate to `/soho/[your-username]?tab=drafts`
- ✅ DRAFTS tab should be **automatically active** (not POSTS)
- ✅ You should see your drafts immediately
- ✅ URL should show `?tab=drafts` parameter

**Screenshot Required:** URL bar and page showing drafts tab active

---

### **Scenario 6: Empty Drafts State**

**Steps:**
1. If you have drafts, delete them all first
2. Navigate to your profile → DRAFTS tab

**Expected Results:**
- ✅ You should see an **empty state message**:
  - Folder icon
  - "No drafts yet" heading
  - "Generated images and videos will appear here before publishing" subtext
- ✅ Should look clean and centered, not broken

**Screenshot Required:** Empty drafts state

---

### **Scenario 7: Publish a Draft**

**Steps:**
1. Go to DRAFTS tab
2. Click **"Publish"** button on a draft
3. When prompted, enter caption: "My beautiful sunset creation"
4. Click OK/Submit

**Expected Results:**
- ✅ Browser should show success message (alert or notification)
- ✅ Page should **reload automatically**
- ✅ Draft should **disappear from DRAFTS tab**
- ✅ Switch to **POSTS tab** → draft should now appear there
- ✅ Caption should be visible on the post

**Screenshot Required:** 
- Before publishing (in drafts)
- After publishing (in posts with caption)

---

### **Scenario 8: Tab Switching UX**

**Steps:**
1. On your profile, click between POSTS and DRAFTS tabs rapidly
2. Observe the transition

**Expected Results:**
- ✅ Tab switches should be **instant** (no page reload)
- ✅ Active tab should update (dark text + top border)
- ✅ Content should swap smoothly
- ✅ URL should update with `?tab=posts` or `?tab=drafts`
- ✅ Browser back/forward buttons should work with tabs

**Screenshot Required:** Video/GIF of tab switching (if possible)

---

### **Scenario 9: Delete a Draft**

**Steps:**
1. Go to DRAFTS tab
2. Click **"Delete"** button on a draft
3. Confirm deletion

**Expected Results:**
- ✅ Draft should **disappear immediately** or after confirmation
- ✅ Should not appear in POSTS tab
- ✅ Should not appear in Explore feed
- ✅ Token should **NOT be refunded** (tokens already spent on generation)

**Screenshot Required:** Drafts tab before and after deletion

---

### **Scenario 10: Generate Video (Draft with Processing Status)**

**Steps:**
1. Navigate to Create page (`/create`)
2. Select "Video" as generation type
3. Enter prompt: "A bustling city street at night"
4. Click "Generate"
5. Immediately go to your profile → DRAFTS tab

**Expected Results:**
- ✅ You should see the video with **"Processing"** badge (blue)
- ✅ It should show the prompt
- ✅ After ~30-60 seconds, refresh → badge should change to **"Ready"** (green)
- ✅ Token balance should decrease by **10 tokens**

**Screenshot Required:** 
- Draft with "Processing" badge
- Draft with "Ready" badge after completion

---

### **Scenario 11: Explore Feed Shows Only Published**

**Steps:**
1. Publish a creation from drafts
2. Navigate to Explore page (`/soho/explore`)
3. Scroll through feed

**Expected Results:**
- ✅ Your published creation should appear in the feed
- ✅ **No drafts from any user** should appear in feed
- ✅ All visible content should be published posts

**Screenshot Required:** Explore feed showing your published post

---

### **Scenario 12: Mobile Responsiveness (Optional)**

**Steps:**
1. Resize browser to mobile width (iPhone size ~375px)
2. Navigate to your profile
3. Test tab switching

**Expected Results:**
- ✅ Tabs should stack or shrink appropriately
- ✅ Icons and text should remain visible
- ✅ Tab switching should still work
- ✅ Content should be mobile-friendly

**Screenshot Required:** Mobile view of tabs (if tested)

---

## 🐛 Known Issues to Report

While testing, specifically look for these potential issues:

### UI/Visual Issues
- [ ] Tabs not aligned properly
- [ ] Active tab not visually distinct
- [ ] Icons missing or broken
- [ ] Overlapping text on tabs
- [ ] Empty state message not centered

### Functional Issues
- [ ] Clicking DRAFTS tab doesn't work
- [ ] Draft doesn't disappear after publishing
- [ ] Published post doesn't appear in POSTS tab
- [ ] Drafts link in nav doesn't work
- [ ] Tab switching reloads the page (should be instant)
- [ ] URL doesn't update when switching tabs
- [ ] Can see other users' drafts

### Data Issues
- [ ] Draft shows as published in POSTS before clicking publish
- [ ] Tokens not deducted after generation
- [ ] Caption not appearing on published post
- [ ] Prompt appearing as caption when no caption provided
- [ ] Like count showing on drafts (should only show on published)

### Edge Cases
- [ ] What happens if you navigate to `?tab=drafts` on someone else's profile?
- [ ] What happens if you have 0 drafts and 0 posts?
- [ ] Can you publish the same draft twice?
- [ ] What happens if generation fails? (Does it show in drafts?)

---

## 📊 Test Report Format

Please provide your findings in this format:

```markdown
# Drafts UI Test Report

**Tester:** [Your Name]
**Date:** [Date]
**Browser:** [Chrome/Safari/Firefox Version]
**Device:** [Desktop/Mobile]
**URL Tested:** [http://localhost:8080 or production URL]

---

## ✅ Passed Scenarios
- [Scenario #] [Brief description]
- [Scenario #] [Brief description]

---

## ❌ Failed Scenarios
### Scenario [#]: [Name]
**What Happened:**
[Detailed description of the issue]

**Expected:**
[What should have happened]

**Actual:**
[What actually happened]

**Screenshot:**
[Attach screenshot]

**Reproducible:**
[Yes/No - Steps to reproduce if yes]

---

## 🎨 UI/UX Feedback
[Your subjective feedback on the design, usability, and overall experience]

### What Works Well
- [Positive feedback]

### What Needs Improvement
- [Constructive criticism]

### Suggested Changes
- [Your recommendations]

---

## 🐛 Bugs Found
1. **[Bug Title]**
   - **Severity:** Critical/High/Medium/Low
   - **Description:** [Details]
   - **Steps to Reproduce:** [1, 2, 3...]
   - **Screenshot:** [If applicable]

---

## 📈 Overall Assessment
- **Functionality:** [1-10]
- **Design/UI:** [1-10]
- **User Experience:** [1-10]
- **Performance:** [1-10]

**Comments:**
[Your overall thoughts]
```

---

## 🤖 Browser Agent Instructions

If you are **Comet** (browser automation agent), follow these instructions:

### Navigation Commands
1. Start at homepage: `navigate to http://localhost:8080`
2. Login if needed: `click login button` → `enter credentials`
3. Go to profile: `navigate to /soho/[username from session]`
4. Click tabs: `click element with text "DRAFTS"`
5. Generate content: `navigate to /create` → `select Image` → `enter prompt` → `click Generate`

### Assertion Commands
- Check tab visibility: `assert element with text "DRAFTS" is visible`
- Check URL: `assert current URL contains "?tab=drafts"`
- Check draft badge: `assert element with text "Ready" exists`
- Check token deduction: `assert token balance decreased by 1`

### Screenshot Commands
- `take screenshot named "scenario-1-tabs.png"`
- `take screenshot of element ".profile-tabs"`
- `take full page screenshot`

### Wait Commands
- After generation: `wait 15 seconds` (for image generation)
- After publishing: `wait for reload`
- After tab click: `wait 500ms` (for animation)

---

## 🚨 Critical Success Criteria

The implementation is considered **successful** if:

1. ✅ Tabs are visible and functional on own profile
2. ✅ DRAFTS tab is hidden on other users' profiles
3. ✅ Generated images/videos appear in DRAFTS tab
4. ✅ Publishing moves creation from DRAFTS to POSTS
5. ✅ Tokens are deducted correctly (1 for image, 10 for video)
6. ✅ Caption system works (no prompt fallback)
7. ✅ Drafts navigation link works from any page
8. ✅ Tab switching is smooth and instant
9. ✅ Empty states are handled gracefully
10. ✅ Only published posts appear in Explore feed

---

## 💡 Tips for Testing

- **Clear browser cache** before starting
- **Test with fresh account** (0 tokens → buy tokens → generate)
- **Test with multiple drafts** (3-5 items) to see layout
- **Test edge cases** (very long prompts, special characters in captions)
- **Check console logs** for JavaScript errors (F12 → Console tab)
- **Monitor network tab** to see API calls (F12 → Network tab)

---

## 📞 Contact

If you encounter blocking issues or need clarification:
- **Developer:** [Your contact info]
- **Expected Response Time:** [Timeframe]

---

**Good luck testing! 🧪**
