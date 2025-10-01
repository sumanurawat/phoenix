import { ReelProject } from "./types";

export const mockProjects: ReelProject[] = [
  {
    id: "proj-001",
    title: "Spring Launch Hype",
    description: "15-second teaser for our seasonal collection featuring quick cuts and bold typography.",
    lastUpdated: "2024-06-02T15:21:00Z",
    status: "rendering",
    thumbnailUrl: "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?auto=format&fit=crop&w=600&q=80",
    brandVoice: "Energetic, optimistic, fashion-forward",
    objective: "Drive awareness for the upcoming Spring drop and encourage waitlist sign-ups.",
    callToAction: "Join the waitlist and get early access",
    targetAudience: "Style-conscious Gen Z shoppers who spend time on TikTok and Instagram Reels.",
    script: `Scene 1 (2s): Close-up of vibrant fabric floating in slow motion. Overlay text: "Spring is calling".
Scene 2 (3s): Quick cuts of models laughing and dancing in the street. Overlay text: "New drops weekly".
Scene 3 (4s): Macro shots of signature accessories. Voiceover: "Fresh fits. Zero wait.".
Scene 4 (4s): Call-to-action screen with app UI. Voiceover: "Tap to join the waitlist".
Scene 5 (2s): Logo lockup with animated confetti.`,
    scenes: [
      {
        id: "scene-1",
        title: "Floating Fabrics",
        description: "Slo-mo macro shots of bright fabrics swirling against a clean backdrop.",
        durationSeconds: 2,
        status: "done",
      },
      {
        id: "scene-2",
        title: "Street Energy",
        description: "High-energy street shots of models transitioning between outfits.",
        durationSeconds: 3,
        status: "rendering",
      },
      {
        id: "scene-3",
        title: "Accessory Focus",
        description: "Macro detail shots of accessories with dramatic lighting.",
        durationSeconds: 4,
        status: "pending",
      },
      {
        id: "scene-4",
        title: "App CTA",
        description: "Animated screen recording of the app sign-up flow with CTA overlay.",
        durationSeconds: 4,
        status: "pending",
      },
      {
        id: "scene-5",
        title: "Logo Outro",
        description: "Animated logo lockup with confetti burst and tagline.",
        durationSeconds: 2,
        status: "pending",
      },
    ],
    settings: {
      orientation: "Portrait",
      durationSeconds: 15,
      quality: "Optimized",
      audio: "Enabled",
      model: "Veo 3 Fast",
    },
  },
  {
    id: "proj-002",
    title: "Campus Ambassador Spotlight",
    description: "30-second narrative featuring micro-influencers talking about their day wearing our pieces.",
    lastUpdated: "2024-05-28T11:08:00Z",
    status: "draft",
    brandVoice: "Friendly, aspirational, rooted in real student life",
    objective: "Recruit 100 new campus ambassadors in priority universities",
    callToAction: "Apply to become an ambassador",
    targetAudience: "College sophomores and juniors interested in fashion and content creation.",
    script: `Opening montage of campus life.
Influencer voiceover describing their favorite outfit.
Overlay of social proof stats.
CTA inviting viewers to apply via link in bio.`,
    scenes: [
      {
        id: "scene-1",
        title: "Campus Morning",
        description: "Establishing shots of campus landmarks during golden hour.",
        durationSeconds: 6,
        status: "pending",
      },
      {
        id: "scene-2",
        title: "Outfit Breakdown",
        description: "Ambassador discussing outfit components with close-up shots.",
        durationSeconds: 8,
        status: "pending",
      },
      {
        id: "scene-3",
        title: "Social Proof",
        description: "Motion graphics highlighting community stats and testimonials.",
        durationSeconds: 6,
        status: "pending",
      },
      {
        id: "scene-4",
        title: "Call To Action",
        description: "Direct-to-camera message inviting viewers to apply.",
        durationSeconds: 4,
        status: "pending",
      },
    ],
    settings: {
      orientation: "Portrait",
      durationSeconds: 30,
      quality: "High",
      audio: "Enabled",
      model: "Veo 3 Studio",
    },
  },
  {
    id: "proj-003",
    title: "Creator Collab Pitch",
    description: "Pitch deck reel for potential creators highlighting revenue share and creative freedom.",
    lastUpdated: "2024-05-12T09:44:00Z",
    status: "completed",
    brandVoice: "Confident, collaborative, opportunity-driven",
    objective: "Sign three new creators for summer limited capsule releases",
    callToAction: "Book a discovery call",
    targetAudience: "Mid-tier fashion creators with 50k-250k followers on Instagram/TikTok",
    script: `High-level overview of partnership benefits.
Testimonials from current creators.
Revenue projections slide.
CTA inviting to schedule a discovery call.`,
    scenes: [
      {
        id: "scene-1",
        title: "Value Proposition",
        description: "Animated typography summarizing key partnership benefits.",
        durationSeconds: 5,
        status: "done",
      },
      {
        id: "scene-2",
        title: "Creator Testimonials",
        description: "Intercut testimonials from current creator partners.",
        durationSeconds: 7,
        status: "done",
      },
      {
        id: "scene-3",
        title: "Revenue Breakdown",
        description: "Infographic animation showing revenue share model.",
        durationSeconds: 6,
        status: "done",
      },
      {
        id: "scene-4",
        title: "CTA",
        description: "Direct invite to schedule a call with booking link overlay.",
        durationSeconds: 4,
        status: "done",
      },
    ],
    settings: {
      orientation: "Portrait",
      durationSeconds: 45,
      quality: "Ultra",
      audio: "Enabled",
      model: "Veo 3 Studio",
    },
  },
];
