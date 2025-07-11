# 💬 Chat Service Database Schema

## Overview
Generic chat service supporting multiple applications (Derplexity, Robin, Doogle) with Firebase Firestore backend.

## Collections Structure

### 1. `conversations` Collection

**Purpose:** Store conversation metadata and settings
**Document ID:** Auto-generated UUID (e.g., `conv_abc123def456`)

```javascript
{
  // Basic Information
  "conversation_id": "conv_abc123def456",          // Document ID
  "title": "Climate Change Discussion",            // Auto-generated or user-set
  "origin": "derplexity",                         // App that created this chat
  
  // User Information
  "user_id": "user123",                           // Creator user ID
  "user_email": "user@example.com",              // Creator email
  
  // Metadata
  "created_at": Timestamp,                        // Creation time
  "updated_at": Timestamp,                        // Last message time
  "message_count": 15,                            // Total messages
  
  // Settings
  "model_settings": {
    "current_model": "gemini-1.5-flash-8b",      // Current AI model
    "temperature": 0.7,                          // Model temperature
    "max_tokens": 8192                           // Token limit
  },
  
  // Status
  "is_archived": false,                          // Archived status
  "is_pinned": false,                            // Pinned to top
  "is_deleted": false,                           // Soft delete flag
  "deleted_at": null,                            // Deletion timestamp
  
  // Statistics
  "total_input_tokens": 1250,                   // Total input tokens
  "total_output_tokens": 3400,                  // Total output tokens
  "last_activity": Timestamp                     // Last user interaction
}
```

### 2. `messages` Collection

**Purpose:** Store individual messages within conversations
**Document ID:** Auto-generated UUID (e.g., `msg_xyz789abc123`)

```javascript
{
  // Basic Information
  "message_id": "msg_xyz789abc123",              // Document ID
  "conversation_id": "conv_abc123def456",        // Parent conversation
  
  // Message Content
  "role": "user",                                // "user" or "assistant" or "system"
  "content": "What is climate change?",          // Message text content
  "content_type": "text",                        // "text", "image", "document"
  
  // Metadata
  "created_at": Timestamp,                       // Message creation time
  "updated_at": Timestamp,                       // Last edit time
  "sequence_number": 1,                          // Message order in conversation
  
  // User Information (for user messages)
  "user_id": "user123",                          // Message sender
  "user_email": "user@example.com",             // Sender email
  
  // AI Response Information (for assistant messages)
  "model_used": "gemini-1.5-flash-8b",         // AI model that generated response
  "model_settings": {
    "temperature": 0.7,
    "max_tokens": 8192
  },
  
  // Token Usage
  "input_tokens": 45,                           // Tokens in input
  "output_tokens": 156,                         // Tokens in output
  "generation_time": 2.34,                      // Response generation time (seconds)
  
  // Status
  "is_edited": false,                           // Was message edited
  "is_deleted": false,                          // Soft delete flag
  "deleted_at": null,                           // Deletion timestamp
  
  // Additional Features
  "attachments": [],                            // File attachments (future)
  "citations": [],                              // Source citations (future)
  "feedback": {                                 // User feedback (future)
    "rating": null,                             // 1-5 stars
    "helpful": null                             // true/false
  }
}
```

### 3. `conversation_documents` Collection

**Purpose:** Store document attachments linked to conversations
**Document ID:** Auto-generated UUID

```javascript
{
  "document_id": "doc_abc123",
  "conversation_id": "conv_abc123def456",
  "user_id": "user123",
  "filename": "research_paper.pdf",
  "file_type": "pdf",
  "file_size": 2048576,
  "upload_path": "documents/user123/doc_abc123.pdf",
  "preview_text": "First 500 characters...",
  "created_at": Timestamp,
  "is_deleted": false
}
```

## Database Indexes

### Required Firestore Indexes

1. **Conversations by User and Origin:**
   - Collection: `conversations`
   - Fields: `user_id` (Ascending), `origin` (Ascending), `updated_at` (Descending)

2. **Active Conversations:**
   - Collection: `conversations`
   - Fields: `user_id` (Ascending), `is_deleted` (Ascending), `updated_at` (Descending)

3. **Messages by Conversation:**
   - Collection: `messages`
   - Fields: `conversation_id` (Ascending), `sequence_number` (Ascending)

4. **Messages by User:**
   - Collection: `messages`
   - Fields: `user_id` (Ascending), `created_at` (Descending)

## Query Patterns

### Common Operations

```python
# Get user's conversations for specific app
conversations = db.collection('conversations') \
    .where('user_id', '==', user_id) \
    .where('origin', '==', 'derplexity') \
    .where('is_deleted', '==', False) \
    .order_by('updated_at', direction=firestore.Query.DESCENDING) \
    .limit(50)

# Get messages for a conversation
messages = db.collection('messages') \
    .where('conversation_id', '==', conv_id) \
    .where('is_deleted', '==', False) \
    .order_by('sequence_number', direction=firestore.Query.ASCENDING)

# Get conversation with latest message
conversation = db.collection('conversations').document(conv_id).get()
latest_message = db.collection('messages') \
    .where('conversation_id', '==', conv_id) \
    .order_by('sequence_number', direction=firestore.Query.DESCENDING) \
    .limit(1)
```

## Security Rules (Firestore)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Conversations: Users can only access their own
    match /conversations/{conversationId} {
      allow read, write: if request.auth != null 
        && request.auth.uid == resource.data.user_id;
      allow create: if request.auth != null 
        && request.auth.uid == request.resource.data.user_id;
    }
    
    // Messages: Users can only access messages in their conversations
    match /messages/{messageId} {
      allow read, write: if request.auth != null
        && exists(/databases/$(database)/documents/conversations/$(resource.data.conversation_id))
        && get(/databases/$(database)/documents/conversations/$(resource.data.conversation_id)).data.user_id == request.auth.uid;
    }
    
    // Documents: Users can only access their own documents
    match /conversation_documents/{documentId} {
      allow read, write: if request.auth != null 
        && request.auth.uid == resource.data.user_id;
    }
  }
}
```

## API Endpoints Design

### Conversation Management
- `GET /api/conversations` - List user conversations
- `POST /api/conversations` - Create new conversation
- `GET /api/conversations/{id}` - Get conversation details
- `PUT /api/conversations/{id}` - Update conversation
- `DELETE /api/conversations/{id}` - Delete conversation

### Message Management
- `GET /api/conversations/{id}/messages` - Get conversation messages
- `POST /api/conversations/{id}/messages` - Send new message
- `PUT /api/messages/{id}` - Edit message
- `DELETE /api/messages/{id}` - Delete message

### Document Management
- `POST /api/conversations/{id}/documents` - Upload document
- `GET /api/conversations/{id}/documents` - List documents
- `DELETE /api/documents/{id}` - Delete document