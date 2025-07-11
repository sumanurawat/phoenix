#!/usr/bin/env python3
"""
Migration script to transition from session-based chat to persistent chat storage.
This script helps set up the enhanced chat service and validates the configuration.
"""
import sys
import os
import logging
from datetime import datetime

# Add the parent directory to sys.path to import from services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import credentials, firestore
from services.enhanced_chat_service import EnhancedChatService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_firebase():
    """Initialize Firebase Admin SDK."""
    try:
        if not firebase_admin._apps:
            # Try service account file first
            try:
                cred = credentials.Certificate('../firebase-credentials.json')
                firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized with service account")
            except FileNotFoundError:
                # Fallback to Application Default Credentials
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized with Application Default Credentials")
        return firestore.client()
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return None

def validate_firestore_setup(db):
    """Validate that Firestore is properly configured."""
    try:
        # Test write to conversations collection
        test_doc = {
            'test': True,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        doc_ref = db.collection('conversations').document('test_migration')
        doc_ref.set(test_doc)
        
        # Test read
        doc = doc_ref.get()
        if doc.exists:
            logger.info("✓ Firestore write/read test successful")
            
            # Clean up test document
            doc_ref.delete()
            return True
        else:
            logger.error("✗ Firestore read test failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ Firestore validation failed: {e}")
        return False

def test_enhanced_chat_service():
    """Test the enhanced chat service functionality."""
    try:
        chat_service = EnhancedChatService()
        
        # Test user data
        test_user_id = "test_migration_user"
        test_user_email = "test@example.com"
        
        logger.info("Testing enhanced chat service...")
        
        # 1. Test conversation creation
        conversation = chat_service.create_conversation(
            user_id=test_user_id,
            user_email=test_user_email,
            origin="derplexity",
            title="Migration Test Conversation"
        )
        
        if conversation:
            logger.info(f"✓ Conversation creation successful: {conversation['conversation_id']}")
            
            # 2. Test message creation
            message_result = chat_service.create_message(
                conversation_id=conversation['conversation_id'],
                user_id=test_user_id,
                role="user",
                content="Test message for migration"
            )
            
            if message_result:
                logger.info(f"✓ Message creation successful: {message_result['message_id']}")
                
                # 3. Test conversation retrieval
                retrieved_conv = chat_service.get_conversation(
                    conversation['conversation_id'], 
                    test_user_id
                )
                
                if retrieved_conv:
                    logger.info("✓ Conversation retrieval successful")
                    
                    # 4. Test message retrieval
                    messages = chat_service.get_conversation_messages(
                        conversation['conversation_id'],
                        test_user_id
                    )
                    
                    if messages and len(messages) > 0:
                        logger.info(f"✓ Message retrieval successful: {len(messages)} messages")
                        
                        # 5. Test conversation deletion (cleanup)
                        delete_success = chat_service.delete_conversation(
                            conversation['conversation_id'],
                            test_user_id,
                            soft_delete=False  # Hard delete for test cleanup
                        )
                        
                        if delete_success:
                            logger.info("✓ Conversation deletion successful")
                            logger.info("🎉 Enhanced chat service validation completed successfully!")
                            return True
                        else:
                            logger.error("✗ Conversation deletion failed")
                    else:
                        logger.error("✗ Message retrieval failed")
                else:
                    logger.error("✗ Conversation retrieval failed")
            else:
                logger.error("✗ Message creation failed")
        else:
            logger.error("✗ Conversation creation failed")
            
        return False
        
    except Exception as e:
        logger.error(f"✗ Enhanced chat service test failed: {e}")
        return False

def check_firestore_indexes():
    """Check if required Firestore indexes are configured."""
    logger.info("📋 Required Firestore indexes for enhanced chat:")
    logger.info("1. conversations: user_id (ASC), origin (ASC), updated_at (DESC)")
    logger.info("2. conversations: user_id (ASC), is_deleted (ASC), updated_at (DESC)")
    logger.info("3. messages: conversation_id (ASC), sequence_number (ASC)")
    logger.info("4. messages: conversation_id (ASC), is_deleted (ASC), sequence_number (ASC)")
    logger.info("5. messages: user_id (ASC), created_at (DESC)")
    logger.info("")
    logger.info("Please ensure these indexes are created in your Firestore console")
    logger.info("or use the firestore.indexes.json file to deploy them.")

def check_security_rules():
    """Check Firestore security rules."""
    logger.info("🔒 Security Rules:")
    logger.info("Please ensure Firestore security rules are updated to include")
    logger.info("the new chat collections (conversations, messages, conversation_documents)")
    logger.info("Use the firestore.rules file for reference.")

def main():
    """Main migration validation script."""
    logger.info("🚀 Starting Enhanced Chat Service Migration Validation")
    logger.info("=" * 60)
    
    # Initialize Firebase
    logger.info("1. Initializing Firebase...")
    db = initialize_firebase()
    if not db:
        logger.error("❌ Firebase initialization failed. Migration cannot proceed.")
        return False
    
    # Validate Firestore setup
    logger.info("\n2. Validating Firestore setup...")
    if not validate_firestore_setup(db):
        logger.error("❌ Firestore validation failed. Check your Firebase configuration.")
        return False
    
    # Test enhanced chat service
    logger.info("\n3. Testing Enhanced Chat Service...")
    if not test_enhanced_chat_service():
        logger.error("❌ Enhanced Chat Service test failed.")
        return False
    
    # Check indexes and security rules
    logger.info("\n4. Checking configuration requirements...")
    check_firestore_indexes()
    logger.info("")
    check_security_rules()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Migration validation completed successfully!")
    logger.info("\nNext steps:")
    logger.info("1. Deploy Firestore indexes using: firebase deploy --only firestore:indexes")
    logger.info("2. Deploy security rules using: firebase deploy --only firestore:rules")
    logger.info("3. Update your application to use the enhanced chat service")
    logger.info("4. Test the new persistent chat functionality")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)