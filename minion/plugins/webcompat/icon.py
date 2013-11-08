# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from lxml.html import html5parser
from PIL import Image
from StringIO import StringIO

from minion.plugins.base import AbstractPlugin,BlockingPlugin,ExternalProcessPlugin
import minion.curly


def parse_icons_from_html(html):
    """Parsing an HTML document and return a list of rel icon links"""
    icons = []
    htmlparsed = html5parser.fromstring(html)
    html_links = htmlparsed.xpath('//h:link[@rel]',
        namespaces={'h': 'http://www.w3.org/1999/xhtml'})
    for html_link in html_links:
        attributes = html_link.attrib
        relvalues = attributes['rel'].lower()
        if relvalues in ('icon', 'apple-touch-icon', 'apple-touch-icon-precomposed'):
            icons.append(attributes)
    return icons


def is_apple_touch_icon(icon):
    return icon['rel'].startswith('apple-touch-icon')

def is_html5_icon(icon):
    return icon['rel'] == 'icon'

def is_shortcut_icon(icon):
    return icon['rel'] == 'shortcut icon'

def normalize_url(base, href):
    if not href.startswith("https://") and not href.startswith("http://"):
        if not href.startswith("/"):
            return base + "/" + href
        else:
            return base + href
    else:
        return href

class IconPlugin(BlockingPlugin):

    PLUGIN_NAME = "Alive"
    PLUGIN_WEIGHT = "light"

    FURTHER_INFO = [
        { "URL": "http://www.w3.org/TR/html5/links.html#rel-icon",
          "Title": "W3C - Link type 'icon' documentation" },
        { "URL": "How to Add a Favicon to your Site",
          "Title": "http://www.w3.org/2005/10/howto-favicon" }]

    REPORTS = {
        "only-touch-icons": {
            "Code": "ICON-0",
            "Summary": "The site only provides an iOS compatible icon",
            "Description": "The site only provides an iOS compatible icon",
            "Severity": "Low",
            "URLs": [],
            "FurtherInfo": FURTHER_INFO
        },
        "touch-icons-in-root": {
            "Code": "ICON-1",
            "Summary": "The site provides iOS compatible icons in the root but not with <link> tags.",
            "Description": "",
            "Severity": "Low",
            "URLs": [],
            "FurtherInfo": FURTHER_INFO
        },
        "no-icons": {
            "Code": "ICON-2",
            "Summary": "The site does not provide any icons through <link> tags",
            "Description": "The site does not provide any icons through <link> tags",
            "Severity": "Low",
            "URLs": [],
            "FurtherInfo": FURTHER_INFO
        },
        "bad-icon-type": {
            "Code": "ICON-3",
            "Summary": "The site is providing an icon with a type that is not recommended.",
            "Description": "The site is providing an an icon with type {icon_type}",
            "Severity": "Low",
            "URLs": [],
            "FurtherInfo": FURTHER_INFO
        },
        "icon-not-found": {
            "Code": "ICON-4",
            "Summary": "The site links to an icon that cannot be found",
            "Description": "The site links to an icon that cannot be found ({icon_url})",
            "Severity": "Low",
            "URLs": [],
            "FurtherInfo": FURTHER_INFO
        },
        "icon-type-mismatch": {
            "Code": "ICON-5",
            "Summary": "The site links to an icon that returns a different content type as specified",
            "Description": "The site links to an icon that returns a different content type as specified. The site specified {specified_type} but we got {actual_type}",
            "Severity": "Low",
            "URLs": [],
            "FurtherInfo": FURTHER_INFO
        },
        "icon-size-mismatch": {
            "Code": "ICON-6",
            "Summary": "The site links to an icon that has a different size as specified",
            "Description": "The site links to an icon that returns a different size as specified. The site specified {specified_size} but we got {actual_size}",
            "Severity": "Low",
            "URLs": [],
            "FurtherInfo": FURTHER_INFO
        },
    }

    DEFAULT_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'User-Agent': 'Mozilla/5.0 (Mobile; rv:25.0) Gecko/25.0 Firefox/25.0',
        'Accept-Encoding': 'gzip, deflate',
    }

    def do_run(self):

        r = minion.curly.get(self.configuration['target'], connect_timeout=5, timeout=15) # , headers=self.DEFAULT_HEADERS)
        r.raise_for_status()

        icons = parse_icons_from_html(r.body)

        #
        # First tests that we can do by just looking at the <link> elements
        #

        # 1.1 Check for no icons

        if len(icons) == 0:

            # 1.1.1 Check if the site has /apple-touch-icon.png in the root

            png1 = minion.curly.get(self.configuration['target'] + "/apple-touch-icon.png", headers=self.DEFAULT_HEADERS)
            png2 = minion.curly.get(self.configuration['target'] + "/apple-touch-icon-76x76.png", headers=self.DEFAULT_HEADERS)
            if png1.status == 200 or png2.status == 200:
                issue = self._format_report('touch-icons-in-root')
                self.report_issues([issue])

            issue = self._format_report('no-icons')
            self.report_issues([issue])
            return

        # 1.2 Check for only iOS icons

        apple_touch_icons = [icon for icon in icons if is_apple_touch_icon(icon)]
        html5_icons = [icon for icon in icons if is_html5_icon(icon)]

        if len(html5_icons) == 0 and len(apple_touch_icons) != 0:
            issue = self._format_report('only-touch-icons')
            self.report_issues([issue])
            return

        # 1.3 Check if any of the icons miss a type attribute or has an unsupported content type

        for icon in icons:
            if is_html5_icon(icon):
                icon_type = icon.get('type')
                if icon_type is None:
                    issue = self._format_report('missing-icon-type')
                    self.report_issues([issue])
                elif icon_type != 'image/png':
                    issue = self._format_report('bad-icon-type', description_formats={'icon_type': icon_type})
                    self.report_issues([issue])

        #
        # Now load the icons and make sure they exist
        #

        # 2.1 Check if the icons exist

        for icon in icons:
            if is_html5_icon(icon):

                # 2.1 Check if the icons exist

                url = normalize_url(self.configuration['target'], icon['href'])
                r = minion.curly.get(url, headers=self.DEFAULT_HEADERS)
                if r.status != 200:
                    issue = self._format_report('icon-not-found', description_formats=dict(icon_url=url))
                    self.report_issues([issue])
                    continue

                # 2.2 If the icon has a type attribute, check if the content type is correct

                icon_type = icon.get('type')
                if icon_type != r.headers['content-type']:
                    issue = self._format_report('icon-type-mismatch',
                                                description_formats=dict(specified_type=icon_type,
                                                                         actual_type=r.headers['content-type']))
                    self.report_issues([issue])

                # 2.3 Check if the size matches. We can only do this for png files.

                icon_size = icon.get('sizes')
                if icon_type == 'image/png' and icon_size is not None:
                    img = Image.open(StringIO(r.body))
                    actual_size = "%dx%d" % img.size
                    if actual_size != icon_size:
                        issue = self._format_report('icon-size-mismatch',
                                                    description_formats=dict(specified_size=icon_size,
                                                                             actual_size=actual_size))
                        self.report_issues([issue])
