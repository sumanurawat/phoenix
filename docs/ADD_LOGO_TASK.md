# Add Logo to Fried Momo Website

## Objective
Add the Fried Momo logo to appear to the left of the website name ("MOMO") across all pages.

## Files to Modify

| File | Location |
|------|----------|
| `frontend/soho/src/components/layout/Header.tsx` | Navigation bar |
| `frontend/soho/src/pages/LoginPage.tsx` | Login form header |
| `frontend/soho/src/pages/SignupPage.tsx` | Signup form header |
| `frontend/soho/src/pages/LandingPage.tsx` | Hero section |

## Implementation

### 1. Add Logo Asset
Place logo file in `frontend/soho/public/logo.svg`

### 2. Update Components
Replace brand name text with logo + text:

```tsx
<div className="flex items-center gap-2">
  <img src="/logo.svg" alt="Fried Momo" className="w-8 h-8" />
  <span className="text-xl font-bold">MOMO</span>
</div>
```

## Checklist
- [ ] Add logo file to public folder
- [ ] Update Header.tsx
- [ ] Update LoginPage.tsx
- [ ] Update SignupPage.tsx
- [ ] Update LandingPage.tsx
- [ ] Test on mobile and desktop
