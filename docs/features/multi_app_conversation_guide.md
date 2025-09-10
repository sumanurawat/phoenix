# 🗣️ Multi-App Conversation Management Guide

## Overview
The Phoenix AI Platform supports independent conversation management for each application (Derplexity, Robin, Doogle, etc.). Each app maintains its own conversation history while sharing the same underlying database structure.

## How It Works

### 1. Origin-Based Isolation
Each conversation has an `origin` field that identifies which app created it:
- `derplexity` - Conversational AI chat
- `robin` - News aggregation and analysis  
- `doogle` - AI-powered search
- `video-generation` - Video creation workflows (future)

### 2. Per-App Conversation Loading
When a user opens an app, they only see conversations from that app:

```javascript
// Derplexity loads only derplexity conversations
const response = await fetch('/api/conversations?origin=derplexity');

// Robin would load only robin conversations  
const response = await fetch('/api/conversations?origin=robin');

// Doogle would load only doogle conversations
const response = await fetch('/api/conversations?origin=doogle');
```

### 3. Independent Message Types
Each app can use different message types and rendering:

**Derplexity**: Text-based conversational AI
- Message type: `text`
- Rendering: Standard chat bubbles with markdown support

**Robin** (future): News articles and summaries
- Message types: `text`, `article`, `summary`
- Rendering: News cards, article previews, summary blocks

**Video Generation** (future): Video creation workflow
- Message types: `text`, `image`, `video`, `workflow_step`
- Rendering: Media previews, progress indicators, workflow steps

## Implementation for New Apps

### 1. Frontend Template
Each app should implement conversation loading in their template:

```javascript
async function loadConversations() {
    const response = await fetch('/api/conversations?origin=YOUR_APP_NAME');
    const data = await response.json();
    conversations = data.conversations || [];
    renderConversations(); // Custom rendering for your app
}
```

### 2. Create Conversations
Use the standard API with your app's origin:

```javascript
const response = await fetch('/api/chat/start-conversation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        message: firstMessage,
        origin: 'YOUR_APP_NAME'  // Set your app's origin
    })
});
```

### 3. Custom Message Rendering
Each app can render messages differently based on content_type:

```javascript
function renderMessage(message) {
    switch(message.content_type) {
        case 'text':
            return renderTextMessage(message);
        case 'article':  // Robin-specific
            return renderArticleMessage(message);
        case 'video':    // Video generation-specific
            return renderVideoMessage(message);
        default:
            return renderTextMessage(message);
    }
}
```

## Current Implementation Status

### ✅ Derplexity
- **Status**: Fully implemented and working
- **Location**: `/derplexity` route → `derplexity_v2.html`
- **Features**: Sidebar conversation list, new conversation creation, message history
- **Message Types**: Text only (as requested)

### 🔄 Robin (ready for implementation)
- **Database**: Ready (conversations with origin='robin')
- **API**: Ready (same endpoints with origin filter)
- **Frontend**: Needs implementation in robin template
- **Message Types**: Text, article, summary (when implemented)

### 🔄 Doogle (ready for implementation)  
- **Database**: Ready (conversations with origin='doogle')
- **API**: Ready (same endpoints with origin filter)
- **Frontend**: Needs implementation in doogle template
- **Message Types**: Text, search results (when implemented)

## Benefits of This Architecture

1. **Isolation**: Each app's conversations are completely separate
2. **Flexibility**: Each app can implement custom message types and rendering
3. **Scalability**: Easy to add new apps without affecting existing ones
4. **Consistency**: All apps use the same database schema and API endpoints
5. **User Experience**: Users get familiar conversation management across all apps

## Next Steps for Other Apps

1. **Robin**: Add conversation sidebar to `robin.html` template
2. **Doogle**: Add conversation sidebar to `doogle.html` template  
3. **Video Generation**: Implement workflow-based conversation management
4. **Custom Message Types**: Implement rendering for app-specific message types

The foundation is complete - each new app just needs to implement the frontend conversation management using the existing API endpoints with their specific origin value.