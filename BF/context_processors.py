# BF/context_processors.py
"""
Context processor to detect which domain the user is visiting
and provide site-specific configuration to templates.
"""

from django.conf import settings


def site_info(request):
    host = request.get_host().lower()

    current_site = settings.DEFAULT_SITE

    if 'arthurflix' in host:
        current_site = 'arthurflix'
    elif 'bollyfun' in host:
        current_site = 'bollyfun'

    site_config = settings.SITE_DOMAINS.get(
        current_site,
        settings.SITE_DOMAINS[settings.DEFAULT_SITE]
    )

    return {
        'SITE_NAME': site_config.get('name', 'ArthurFlix'),
        'SITE_DOMAIN': site_config.get('domain', ''),
        'SITE_LOGO': site_config.get('logo', ''),
        'SITE_PRIMARY_COLOR': site_config.get('primary_color', '#000000'),
        'CURRENT_SITE_KEY': current_site,
    }
