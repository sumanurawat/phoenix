"""
Subscription Cron Service

This service provides automated subscription management tasks that should be run
on a schedule (daily, hourly, etc.) to ensure subscription status is always
up-to-date and follows industry standards.

Industry Standard Features:
- Daily expiration checks
- Webhook failure recovery
- Subscription sync with Stripe
- Scheduled downgrade processing
- Usage cleanup and aggregation
"""

import os
import logging
import schedule
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any
from services.subscription_expiration_service import SubscriptionExpirationService
from services.subscription_management_service import SubscriptionManagementService

logger = logging.getLogger(__name__)

class SubscriptionCronService:
    """Service for running scheduled subscription management tasks."""
    
    def __init__(self):
        """Initialize the cron service."""
        self.expiration_service = SubscriptionExpirationService()
        self.management_service = SubscriptionManagementService()
        self.is_running = False
        self.scheduler_thread = None
        
        # Configure schedule times from environment
        self.daily_check_time = os.getenv('SUBSCRIPTION_DAILY_CHECK_TIME', '02:00')  # 2 AM
        self.hourly_sync_enabled = os.getenv('SUBSCRIPTION_HOURLY_SYNC', 'true').lower() == 'true'
        
        logger.info(f"Subscription cron service initialized - Daily checks at {self.daily_check_time}, Hourly sync: {self.hourly_sync_enabled}")
    
    def setup_schedules(self):
        """Set up all scheduled tasks."""
        # Daily subscription expiration check
        schedule.every().day.at(self.daily_check_time).do(self._run_daily_expiration_check)
        
        # Daily scheduled downgrade processing
        schedule.every().day.at(self.daily_check_time).do(self._run_scheduled_downgrades)
        
        # Hourly subscription sync (if enabled)
        if self.hourly_sync_enabled:
            schedule.every().hour.do(self._run_hourly_sync)
        
        # Weekly usage cleanup (every Sunday at 3 AM)
        schedule.every().sunday.at("03:00").do(self._run_weekly_cleanup)
        
        logger.info("All subscription cron schedules configured")
    
    def start_scheduler(self):
        """Start the background scheduler thread."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.setup_schedules()
        self.is_running = True
        
        def run_scheduler():
            logger.info("🕐 Subscription scheduler thread started")
            while self.is_running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"Error in scheduler thread: {e}")
                    time.sleep(60)  # Continue after error
            logger.info("🕐 Subscription scheduler thread stopped")
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("✅ Subscription scheduler started successfully")
    
    def stop_scheduler(self):
        """Stop the background scheduler thread."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        schedule.clear()
        logger.info("🛑 Subscription scheduler stopped")
    
    def _run_daily_expiration_check(self):
        """Run daily subscription expiration check."""
        logger.info("🔍 Starting daily subscription expiration check...")
        
        try:
            start_time = datetime.now(timezone.utc)
            results = self.expiration_service.check_all_expired_subscriptions()
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            # Log summary
            logger.info(f"✅ Daily expiration check completed in {duration:.2f}s")
            logger.info(f"📊 Results: {results['total_checked']} checked, {results['downgraded']} downgraded, {results['errors']} errors")
            
            # Store execution log
            self._log_cron_execution('daily_expiration_check', results, duration)
            
        except Exception as e:
            logger.error(f"❌ Daily expiration check failed: {e}")
            self._log_cron_execution('daily_expiration_check', {'error': str(e)}, 0)
    
    def _run_scheduled_downgrades(self):
        """Process all scheduled downgrades."""
        logger.info("📅 Processing scheduled downgrades...")
        
        try:
            start_time = datetime.now(timezone.utc)
            results = self.management_service.process_scheduled_downgrades()
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            # Log summary
            logger.info(f"✅ Scheduled downgrades processed in {duration:.2f}s")
            logger.info(f"📊 Results: {results['total_processed']} processed, {results['successful']} successful, {results['failed']} failed")
            
            # Store execution log
            self._log_cron_execution('scheduled_downgrades', results, duration)
            
        except Exception as e:
            logger.error(f"❌ Scheduled downgrades processing failed: {e}")
            self._log_cron_execution('scheduled_downgrades', {'error': str(e)}, 0)
    
    def _run_hourly_sync(self):
        """Run hourly subscription sync check."""
        logger.info("🔄 Starting hourly subscription sync...")
        
        try:
            start_time = datetime.now(timezone.utc)
            
            # Run a lighter version of expiration check (sync only)
            results = self.expiration_service.check_all_expired_subscriptions()
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            # Only log if there were changes or errors
            if results.get('sync_needed', 0) > 0 or results.get('errors', 0) > 0:
                logger.info(f"✅ Hourly sync completed in {duration:.2f}s")
                logger.info(f"📊 Sync results: {results.get('sync_needed', 0)} synced, {results.get('errors', 0)} errors")
                self._log_cron_execution('hourly_sync', results, duration)
            
        except Exception as e:
            logger.error(f"❌ Hourly sync failed: {e}")
            self._log_cron_execution('hourly_sync', {'error': str(e)}, 0)
    
    def _run_weekly_cleanup(self):
        """Run weekly cleanup tasks."""
        logger.info("🧹 Starting weekly cleanup tasks...")
        
        try:
            start_time = datetime.now(timezone.utc)
            cleanup_results = self._cleanup_old_data()
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ Weekly cleanup completed in {duration:.2f}s")
            logger.info(f"📊 Cleanup results: {cleanup_results}")
            
            self._log_cron_execution('weekly_cleanup', cleanup_results, duration)
            
        except Exception as e:
            logger.error(f"❌ Weekly cleanup failed: {e}")
            self._log_cron_execution('weekly_cleanup', {'error': str(e)}, 0)
    
    def _cleanup_old_data(self) -> Dict[str, Any]:
        """Clean up old usage data and completed downgrades."""
        from firebase_admin import firestore
        from datetime import timedelta
        
        results = {
            'old_usage_cleaned': 0,
            'completed_downgrades_cleaned': 0,
            'old_logs_cleaned': 0
        }
        
        if not self.expiration_service.db:
            return results
        
        try:
            current_time = datetime.now(timezone.utc)
            cutoff_date = current_time - timedelta(days=90)  # Keep 90 days of data
            
            # Clean up old usage records (keep last 90 days)
            old_usage_docs = self.expiration_service.db.collection('user_usage')\
                .where('created_at', '<', cutoff_date)\
                .limit(100).get()  # Process in batches
            
            batch = self.expiration_service.db.batch()
            for doc in old_usage_docs:
                batch.delete(doc.reference)
            
            if old_usage_docs:
                batch.commit()
                results['old_usage_cleaned'] = len(old_usage_docs)
            
            # Clean up completed scheduled downgrades older than 30 days
            downgrade_cutoff = current_time - timedelta(days=30)
            old_downgrades = self.expiration_service.db.collection('scheduled_downgrades')\
                .where('status', '==', 'completed')\
                .where('completed_at', '<', downgrade_cutoff)\
                .limit(50).get()
            
            batch = self.expiration_service.db.batch()
            for doc in old_downgrades:
                batch.delete(doc.reference)
            
            if old_downgrades:
                batch.commit()
                results['completed_downgrades_cleaned'] = len(old_downgrades)
            
            # Clean up old cron execution logs (keep last 30 days)
            log_cutoff = current_time - timedelta(days=30)
            old_logs = self.expiration_service.db.collection('cron_execution_logs')\
                .where('executed_at', '<', log_cutoff)\
                .limit(100).get()
            
            batch = self.expiration_service.db.batch()
            for doc in old_logs:
                batch.delete(doc.reference)
            
            if old_logs:
                batch.commit()
                results['old_logs_cleaned'] = len(old_logs)
            
            return results
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            results['error'] = str(e)
            return results
    
    def _log_cron_execution(self, task_name: str, results: Dict[str, Any], duration: float):
        """Log cron execution results for monitoring."""
        if not self.expiration_service.db:
            return
        
        try:
            log_ref = self.expiration_service.db.collection('cron_execution_logs')
            log_ref.add({
                'task_name': task_name,
                'executed_at': datetime.now(timezone.utc),
                'duration_seconds': duration,
                'results': results,
                'success': 'error' not in results
            })
        except Exception as e:
            logger.error(f"Failed to log cron execution: {e}")
    
    def run_task_manually(self, task_name: str) -> Dict[str, Any]:
        """
        Manually run a specific cron task.
        
        Args:
            task_name: Name of the task to run
            
        Returns:
            Dict with execution results
        """
        logger.info(f"🔧 Manually running task: {task_name}")
        
        try:
            start_time = datetime.now(timezone.utc)
            
            if task_name == 'expiration_check':
                results = self.expiration_service.check_all_expired_subscriptions()
            elif task_name == 'scheduled_downgrades':
                results = self.management_service.process_scheduled_downgrades()
            elif task_name == 'sync_check':
                results = self.expiration_service.check_all_expired_subscriptions()
            elif task_name == 'cleanup':
                results = self._cleanup_old_data()
            else:
                return {
                    'success': False,
                    'error': f'Unknown task: {task_name}',
                    'available_tasks': ['expiration_check', 'scheduled_downgrades', 'sync_check', 'cleanup']
                }
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            # Log the manual execution
            self._log_cron_execution(f'manual_{task_name}', results, duration)
            
            return {
                'success': True,
                'task_name': task_name,
                'duration_seconds': duration,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Failed to run manual task {task_name}: {e}")
            return {
                'success': False,
                'task_name': task_name,
                'error': str(e)
            }
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status and next run times."""
        status = {
            'is_running': self.is_running,
            'daily_check_time': self.daily_check_time,
            'hourly_sync_enabled': self.hourly_sync_enabled,
            'next_runs': {}
        }
        
        try:
            # Get next run times for each job
            for job in schedule.jobs:
                task_name = job.job_func.__name__ if hasattr(job.job_func, '__name__') else str(job.job_func)
                status['next_runs'][task_name] = str(job.next_run) if job.next_run else 'Not scheduled'
            
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            status['error'] = str(e)
        
        return status
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent cron execution history.
        
        Args:
            limit: Number of recent executions to return
            
        Returns:
            List of execution logs
        """
        if not self.expiration_service.db:
            return []
        
        try:
            logs = self.expiration_service.db.collection('cron_execution_logs')\
                .order_by('executed_at', direction=firestore.Query.DESCENDING)\
                .limit(limit).get()
            
            history = []
            for log_doc in logs:
                log_data = log_doc.to_dict()
                history.append({
                    'id': log_doc.id,
                    'task_name': log_data.get('task_name'),
                    'executed_at': log_data.get('executed_at'),
                    'duration_seconds': log_data.get('duration_seconds'),
                    'success': log_data.get('success'),
                    'results_summary': self._summarize_results(log_data.get('results', {}))
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting execution history: {e}")
            return []
    
    def _summarize_results(self, results: Dict[str, Any]) -> str:
        """Create a summary string from results."""
        if 'error' in results:
            return f"Error: {results['error']}"
        
        summary_parts = []
        if 'total_checked' in results:
            summary_parts.append(f"{results['total_checked']} checked")
        if 'downgraded' in results:
            summary_parts.append(f"{results['downgraded']} downgraded")
        if 'total_processed' in results:
            summary_parts.append(f"{results['total_processed']} processed")
        if 'successful' in results:
            summary_parts.append(f"{results['successful']} successful")
        if 'errors' in results and results['errors'] > 0:
            summary_parts.append(f"{results['errors']} errors")
        
        return ', '.join(summary_parts) if summary_parts else 'No changes'