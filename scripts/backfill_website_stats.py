#!/usr/bin/env python3
"""
Backfill Website Stats Script

This script counts existing conversations and messages in Firebase
and updates the website stats to reflect the current state.
"""
import os
import sys
import logging
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize Firebase Admin SDK
try:
    # Try to get existing app
    firebase_admin.get_app()
except ValueError:
    # Initialize if not already initialized
    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        # Try default credentials
        firebase_admin.initialize_app()

from services.website_stats_service import WebsiteStatsService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def count_existing_data():
    """Count existing conversations and messages in Firebase."""
    try:
        db = firestore.client()
        
        # Count conversations
        logger.info("🔍 Counting existing conversations...")
        conversations_ref = db.collection('conversations')
        conversations = list(conversations_ref.stream())
        total_conversations = len(conversations)
        
        logger.info(f"📊 Found {total_conversations} conversations")
        
        # Count messages
        logger.info("🔍 Counting existing messages...")
        messages_ref = db.collection('messages')
        messages = list(messages_ref.stream())
        total_messages = len(messages)
        
        logger.info(f"📊 Found {total_messages} messages")
        
        # Also count by conversation breakdown
        conversation_message_counts = {}
        for message in messages:
            msg_data = message.to_dict()
            conv_id = msg_data.get('conversation_id')
            if conv_id:
                conversation_message_counts[conv_id] = conversation_message_counts.get(conv_id, 0) + 1
        
        logger.info(f"📊 Messages span across {len(conversation_message_counts)} conversations")
        
        return {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'conversations_with_messages': len(conversation_message_counts),
            'conversation_message_breakdown': conversation_message_counts
        }
        
    except Exception as e:
        logger.error(f"❌ Error counting existing data: {e}")
        raise

def update_website_stats(counts):
    """Update website stats with the current counts."""
    try:
        stats_service = WebsiteStatsService()
        
        logger.info("📊 Getting current website stats...")
        current_stats = stats_service.get_website_stats()
        
        current_conversations = current_stats.get('total_conversations_started', 0)
        current_messages = current_stats.get('total_messages_exchanged', 0)
        
        logger.info(f"📊 Current stats: {current_conversations} conversations, {current_messages} messages")
        logger.info(f"📊 Actual counts: {counts['total_conversations']} conversations, {counts['total_messages']} messages")
        
        # Calculate differences
        conversation_diff = counts['total_conversations'] - current_conversations
        message_diff = counts['total_messages'] - current_messages
        
        if conversation_diff > 0:
            logger.info(f"🔄 Need to add {conversation_diff} conversations to stats")
            stats_service.increment_conversations_started(conversation_diff)
            logger.info(f"✅ Updated conversations count by {conversation_diff}")
        else:
            logger.info(f"✅ Conversations count is up to date (difference: {conversation_diff})")
            
        if message_diff > 0:
            logger.info(f"🔄 Need to add {message_diff} messages to stats")
            stats_service.increment_messages_exchanged(message_diff)
            logger.info(f"✅ Updated messages count by {message_diff}")
        else:
            logger.info(f"✅ Messages count is up to date (difference: {message_diff})")
        
        # Get final stats
        final_stats = stats_service.get_website_stats()
        logger.info(f"🎉 Final stats: {final_stats.get('total_conversations_started', 0)} conversations, {final_stats.get('total_messages_exchanged', 0)} messages")
        
    except Exception as e:
        logger.error(f"❌ Error updating website stats: {e}")
        raise

def main():
    """Main function to run the backfill process."""
    try:
        logger.info("🚀 Starting website stats backfill process...")
        
        # Count existing data
        counts = count_existing_data()
        
        # Display summary
        logger.info("=" * 60)
        logger.info("📊 EXISTING DATA SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Conversations: {counts['total_conversations']}")
        logger.info(f"Total Messages: {counts['total_messages']}")
        logger.info(f"Conversations with Messages: {counts['conversations_with_messages']}")
        logger.info("=" * 60)
        
        # Ask for confirmation
        confirm = input("\n🤔 Do you want to update the website stats with these counts? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            logger.info("❌ Backfill cancelled by user")
            return
        
        # Update stats
        update_website_stats(counts)
        
        logger.info("✅ Website stats backfill completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("\n❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Backfill process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()