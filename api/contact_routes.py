import logging
from flask import Blueprint, request, jsonify
from firebase_admin import firestore
import datetime

logger = logging.getLogger(__name__)

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('/api/contact', methods=['POST'])
def submit_contact_form():
    """
    Handle direct contact form submissions.
    Stores the submission in Firestore and logs the intention to send emails.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Request body is required'}), 400

        first_name = data.get('firstName')
        last_name = data.get('lastName')
        email = data.get('email')
        message = data.get('message')

        if not all([first_name, last_name, email, message]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400

        # Store in Firestore
        db = firestore.client()
        submission_ref = db.collection('contact_submissions').document()
        submission_data = {
            'firstName': first_name,
            'lastName': last_name,
            'email': email,
            'message': message,
            'timestamp': datetime.datetime.now(datetime.timezone.utc),
            'recipients': ['sumanurawat12@gmail.com', 'vrushcodes@gmail.com']
        }
        submission_ref.set(submission_data)

        # Log for administrators
        logger.info(f"NEW CONTACT FORM SUBMISSION: From {first_name} {last_name} ({email})")
        logger.info(f"MESSAGE: {message}")
        logger.info(f"INTENDED RECIPIENTS: {submission_data['recipients']}")
        
        # NOTE: In a real production environment, we would trigger an email sending service here
        # (e.g., SendGrid, Mailgun, or AWS SES) using the recipients list above.

        return jsonify({
            'success': True,
            'message': 'Your message has been sent successfully. We will get back to you soon!'
        }), 200

    except Exception as e:
        logger.error(f"Error handling contact form submission: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to process your request. Please try again later.'
        }), 500
