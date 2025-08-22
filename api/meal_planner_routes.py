"""
Meal Planner Routes
"""
from flask import Blueprint, render_template
from api.auth_routes import login_required

meal_planner_bp = Blueprint(
    'meal_planner',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/meal-planner'
)

@meal_planner_bp.route('/')
@login_required
def index():
    """Render the main meal planner dashboard."""
    return render_template('meal_planner_dashboard.html', title='Meal Planner')


@meal_planner_bp.route('/chat')
@login_required
def new_chat():
    """Render the chat interface for a new conversation."""
    # This will eventually create a new conversation and redirect
    return render_template('meal_planner_chat.html', title='New Meal Plan')


@meal_planner_bp.route('/chat/<conversation_id>')
@login_required
def show_chat(conversation_id):
    """Render the chat interface for an existing conversation."""
    # This will eventually load the conversation from the database
    return render_template(
        'meal_planner_chat.html',
        title='Continue Meal Plan',
        conversation_id=conversation_id
    )
