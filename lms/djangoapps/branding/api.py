"""EdX Branding API

Provides a way to retrieve "branded" parts of the site,
such as the site footer.

This information exposed to:
1) Templates in the LMS.
2) Consumers of the branding API.

This ensures that branded UI elements such as the footer
are consistent across the LMS and other sites (such as
the marketing site and blog).

"""
import logging
import urlparse

from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.staticfiles.storage import staticfiles_storage

from microsite_configuration import microsite
from edxmako.shortcuts import marketing_link
from branding.models import BrandingApiConfig


log = logging.getLogger("edx.footer")
EMPTY_URL = '#'


def is_enabled():
    """Check whether the branding API is enabled. """
    return BrandingApiConfig.current().enabled


def get_footer(is_secure=True):
    """Retrieve information used to render the footer.

    This will handle both the OpenEdX and EdX.org versions
    of the footer.  All user-facing text is internationalized.

    Currently, this does NOT support theming.

    Keyword Arguments:
        is_secure (bool): If True, use https:// in URLs.

    Returns: dict

    Example:
    >>> get_footer()
    {
        "copyright": "(c) 2015 EdX Inc",
        "logo_image": "http://www.example.com/logo.png",
        "social_links": [
            {
                "name": "facebook",
                "title": "Facebook",
                "url": "http://www.facebook.com/example",
                "icon-class": "fa-facebook-square",
                "action": "Sign up on Facebook!"
            },
            ...
        ],
        "navigation_links": [
            {
                "name": "about",
                "title": "About",
                "url": "http://www.example.com/about.html"
            },
            ...
        ],
        "mobile_links": [
            {
                "name": "apple",
                "title": "Apple",
                "url": "http://store.apple.com/example_app",
                "image": "http://example.com/static/apple_logo.png"
            },
            ...
        ],
        "legal_links": [
            {
                "url": "http://example.com/terms-of-service.html",
                "name": "terms_of_service",
                "title': "Terms of Service"
            },
            # ...
        ],
        "openedx_link": {
            "url": "http://open.edx.org",
            "title": "Powered by Open edX",
            "image": "http://example.com/openedx.png"
        }
    }

    """
    return {
        "copyright": _footer_copyright(),
        "logo_image": _footer_logo_img(is_secure),
        "social_links": _footer_social_links(),
        "navigation_links": _footer_navigation_links(),
        "mobile_links": _footer_mobile_links(is_secure),
        "legal_links": _footer_legal_links(),
        "openedx_link": _footer_openedx_link(),
    }


def _footer_copyright():
    """Return the copyright to display in the footer.

    Returns: unicode

    """
    org_name = (
        "edX Inc" if settings.FEATURES.get('IS_EDX_DOMAIN', False)
        else microsite.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
    )

    return _(
        # Translators: 'EdX', 'edX', and 'Open edX' are trademarks of 'edX Inc.'.
        # Please do not translate any of these trademarks and company names.
        u"\u00A9 {org_name}.  All rights reserved except where noted.  "
        u"EdX, Open edX and the edX and Open EdX logos are registered trademarks "
        u"or trademarks of edX Inc."
    ).format(org_name=org_name)


def _footer_openedx_link():
    """Return the image link for "powered by OpenEdX".

    Args:
        is_secure (bool): Whether the request is using TLS.

    Returns: dict

    """
    # Translators: 'Open edX' is a brand, please keep this untranslated.
    # See http://openedx.org for more information.
    title = _("Powered by Open edX")
    return {
        "url": settings.FOOTER_OPENEDX_URL,
        "title": title,
        "image": settings.FOOTER_OPENEDX_LOGO_IMAGE,
    }


def _footer_social_links():
    """Return the social media links to display in the footer.

    Returns: list

    """
    platform_name = microsite.get_value('platform_name', settings.PLATFORM_NAME)
    links = []

    for social_name in settings.SOCIAL_MEDIA_FOOTER_NAMES:
        display = settings.SOCIAL_MEDIA_FOOTER_DISPLAY.get(social_name, {})
        links.append(
            {
                "name": social_name,
                "title": unicode(display.get("title", "")),
                "url": settings.SOCIAL_MEDIA_FOOTER_URLS.get(social_name, "#"),
                "icon-class": display.get("icon", ""),
                "action": unicode(display.get("action", "")).format(platform_name=platform_name),
            }
        )
    return links


def _footer_navigation_links():
    """Return the navigation links to display in the footer. """
    return [
        {
            "name": link_name,
            "title": link_title,
            "url": link_url,
        }
        for link_name, link_url, link_title in [
            ("about", marketing_link("ABOUT"), _("About")),
            ("blog", marketing_link("BLOG"), _("Blog")),
            ("news", marketing_link("NEWS"), _("News")),
            ("help-center", settings.SUPPORT_SITE_LINK, _("Help Center")),
            ("contact", marketing_link("CONTACT"), _("Contact")),
            ("careers", marketing_link("CAREERS"), _("Careers")),
            ("mobileapp", marketing_link("MOBILEAPP"), _("Mobile app")),
            ("sitemap", marketing_link("SITE_MAP"), _("Sitemap")),
        ]
        if link_url and link_url != "#"
    ]


def _footer_legal_links():
    """Return the legal footer links (e.g. terms of service). """

    links = [
        ("terms_of_service_and_honor_code", marketing_link("TOS_AND_HONOR"), _("Terms of Service & Honor Code")),
        ("privacy_policy", marketing_link("PRIVACY"), _("Privacy Policy")),
        ("accessibility_policy", marketing_link("ACCESSIBILITY"), _("Accessibility Policy")),
    ]

    # Backwards compatibility: If a combined "terms of service and honor code"
    # link isn't provided, add separate TOS and honor code links.
    tos_and_honor_link = marketing_link("TOS_AND_HONOR")
    if not (tos_and_honor_link and tos_and_honor_link != "#"):
        links.extend([
            ("terms_of_service", marketing_link("TOS"), _("Terms of Service")),
            ("honor_code", marketing_link("HONOR"), _("Honor Code")),
        ])

    return [
        {
            "name": link_name,
            "title": link_title,
            "url": link_url,
        }
        for link_name, link_url, link_title in links
        if link_url and link_url != "#"
    ]


def _footer_mobile_links(is_secure):
    """Return the mobile app store links.

    Args:
        is_secure (bool): Whether the request is using TLS.

    Returns: list

    """
    platform_name = microsite.get_value('platform_name', settings.PLATFORM_NAME)

    mobile_links = []
    if settings.FEATURES.get('ENABLE_FOOTER_MOBILE_APP_LINKS'):
        mobile_links = [
            {
                "name": "apple",
                "title": _(
                    "Download the {platform_name} mobile app from the Apple App Store"
                ).format(platform_name=platform_name),
                "url": settings.MOBILE_STORE_URLS.get('apple', '#'),
                "image": _absolute_url_staticfile(is_secure, 'images/app/app_store_badge_135x40.svg'),
            },
            {
                "name": "google",
                "title": _(
                    "Download the {platform_name} mobile app from Google Play"
                ).format(platform_name=platform_name),
                "url": settings.MOBILE_STORE_URLS.get('google', '#'),
                "image": _absolute_url_staticfile(is_secure, 'images/app/google_play_badge_45.png'),
            }
        ]
    return mobile_links


def _footer_logo_img(is_secure):
    """Return the logo used for footer about link

    Args:
        is_secure (bool): Whether the request is using TLS.

    Returns:
        Absolute url to logo
    """
    logo_name = microsite.get_value('FOOTER_ORGANIZATION_IMAGE', settings.FOOTER_ORGANIZATION_IMAGE)
    # `logo_name` is looked up from the microsite configuration,
    # which falls back on the Django settings, which loads it from
    # `lms.env.json`, which is created and managed by Ansible. Because of
    # this runaround, we lose a lot of the flexibility that Django's
    # staticfiles system provides, and we end up having to hardcode the path
    # to the footer logo rather than use the comprehensive theming system.
    # EdX needs the FOOTER_ORGANIZATION_IMAGE value to point to edX's
    # logo by default, so that it can display properly on edx.org -- both
    # within the LMS, and on the Drupal marketing site, which uses this API.
    try:
        return _absolute_url_staticfile(is_secure, logo_name)
    except ValueError:
        # However, if the edx.org comprehensive theme is not activated,
        # Django's staticfiles system will be unable to find this footer,
        # and will throw a ValueError. Since the edx.org comprehensive theme
        # is not activated by default, we will end up entering this block
        # of code on new Open edX installations, and on sandbox installations.
        # We can log when this happens:
        default_logo = "images/logo.png"
        log.info(
            "Failed to find footer logo at '%s', using '%s' instead",
            logo_name,
            default_logo,
        )
        # And we'll use the default logo path of "images/logo.png" instead.
        # There is a core asset that corresponds to this logo, so this should
        # always succeed.
        return staticfiles_storage.url(default_logo)


def _absolute_url(is_secure, url_path):
    """Construct an absolute URL back to the site.

    Arguments:
        is_secure (bool): If true, use HTTPS as the protocol.
        url_path (unicode): The path of the URL.

    Returns:
        unicode

    """
    site_name = microsite.get_value('SITE_NAME', settings.SITE_NAME)
    parts = ("https" if is_secure else "http", site_name, url_path, '', '', '')
    return urlparse.urlunparse(parts)


def _absolute_url_staticfile(is_secure, name):
    """Construct an absolute URL to a static resource on the site.

    Arguments:
        is_secure (bool): If true, use HTTPS as the protocol.
        name (unicode): The name of the static resource to retrieve.

    Returns:
        unicode

    """
    url_path = staticfiles_storage.url(name)

    # In production, the static files URL will be an absolute
    # URL pointing to a CDN.  If this happens, we can just
    # return the URL.
    if urlparse.urlparse(url_path).netloc:
        return url_path

    # For local development, the returned URL will be relative,
    # so we need to make it absolute.
    return _absolute_url(is_secure, url_path)


def get_microsite_url(name):
    """
    Look up and return the value for given url name in microsite configuration.
    URLs are saved in "urls" dictionary inside Microsite Configuration.

    Return 'EMPTY_URL' if given url name is not defined in microsite configuration urls.
    """
    urls = microsite.get_value("urls", default={})
    return urls.get(name) or EMPTY_URL


def get_url(name):
    """
    Lookup and return page url, lookup is performed in the following order

    1. get microsite url, If microsite URL override exists, return it
    2. Otherwise return the marketing URL.

    :return: string containing page url.
    """
    # If a microsite URL override exists, return it.  Otherwise return the marketing URL.
    microsite_url = get_microsite_url(name)
    if microsite_url != EMPTY_URL:
        return microsite_url

    # get marketing link, if marketing is disabled then platform url will be used instead.
    url = marketing_link(name)

    return url or EMPTY_URL


def get_base_url(is_secure):
    """
    Return Base URL for site/microsite.
    Arguments:
        is_secure (bool): If true, use HTTPS as the protocol.
    """
    return _absolute_url(is_secure=is_secure, url_path="")


def get_logo_url():
    """
    Return the url for the branded logo image to be used
    """

    # if the MicrositeConfiguration has a value for the logo_image_url
    # let's use that
    image_url = microsite.get_value('logo_image_url')
    if image_url:
        return '{static_url}{image_url}'.format(
            static_url=settings.STATIC_URL,
            image_url=image_url
        )

    # otherwise, use the legacy means to configure this
    university = microsite.get_value('university')

    if university is None and settings.FEATURES.get('IS_EDX_DOMAIN', False):
        return staticfiles_storage.url('images/edx-theme/edx-logo-77x36.png')
    elif university:
        return staticfiles_storage.url('images/{uni}-on-edx-logo.png'.format(uni=university))
    else:
        return staticfiles_storage.url('images/logo.png')


def get_tos_and_honor_code_url():
    """
    Lookup and return terms of services page url
    """
    return get_url("TOS_AND_HONOR")


def get_privacy_url():
    """
    Lookup and return privacy policies page url
    """
    return get_url("PRIVACY")


def get_about_url():
    """
    Lookup and return About page url
    """
    return get_url("ABOUT")
