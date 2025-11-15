"""
Centralized Token Package Configuration
Single source of truth for all token packages across the application.
"""

# Token package configurations - SINGLE SOURCE OF TRUTH
# Used by: API routes, Stripe service, security validation, frontend
TOKEN_PACKAGES = {
    'tasting': {
        'name': 'Tasting Pack',
        'tokens': 20,
        'price': 0.99,
        'price_cents': 99,
        'bonus': 0,
        'price_id_env': 'STRIPE_TOKEN_TASTING_PRICE_ID',
        'description': 'Try it out - perfect for getting started'
    },
    'starter': {
        'name': 'Starter Pack',
        'tokens': 110,
        'price': 4.99,
        'price_cents': 499,
        'bonus': 10,
        'price_id_env': 'STRIPE_TOKEN_STARTER_PRICE_ID',
        'description': 'Perfect for trying out our platform'
    },
    'popular': {
        'name': 'Popular Pack',
        'tokens': 220,
        'price': 9.99,
        'price_cents': 999,
        'bonus': 20,
        'price_id_env': 'STRIPE_TOKEN_POPULAR_PRICE_ID',
        'description': 'Most popular choice - 10% bonus!',
        'badge': 'MOST POPULAR'
    },
    'creator': {
        'name': 'Creator Pack',
        'tokens': 500,
        'price': 19.99,
        'price_cents': 1999,
        'bonus': 100,
        'price_id_env': 'STRIPE_TOKEN_PRO_PRICE_ID',
        'description': 'For power users - 25% bonus!'
    },
    'studio': {
        'name': 'Studio Pack',
        'tokens': 1400,
        'price': 49.99,
        'price_cents': 4999,
        'bonus': 400,
        'price_id_env': 'STRIPE_TOKEN_CREATOR_PRICE_ID',
        'description': 'Maximum value - 40% bonus!',
        'badge': 'BEST VALUE'
    }
}
