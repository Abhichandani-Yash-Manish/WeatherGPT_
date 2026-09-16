"""The route tables are enumerable, and every route points at a handler that exists.

The POST table used to live inside the request handler, so no test could enumerate it and a route could exist
without anything able to notice a handler that had been renamed. The table is module scope now; these checks pin
the inventory itself rather than one route at a time.
"""
import re
import unittest
from pathlib import Path

import test_answers as fixture
from weathergpt_data.product_api import PRODUCT_PATHS
from weathergpt_data.workspace import ROOT, Workspace, post_routes


def source_get_paths():
    """The GET paths the server names in its source: the products plus the explicitly known read routes."""
    server = (ROOT / 'weathergpt_data' / 'workspace.py').read_text(encoding='utf-8')
    return sorted(set(re.findall(r"path=='(/api/[a-z0-9/_-]+)'", server)))


class RouteInventoryTests(unittest.TestCase):
    publish = fixture.AnswerTests.publish
    add_place = fixture.AnswerTests.add_place

    def setUp(self):
        fixture.AnswerTests.setUp(self)
        self.app = Workspace(self.root / 'jobs.sqlite', self.root / 'raw', self.root / 'geography.sqlite')

    def test_every_post_route_resolves_to_a_callable_handler(self):
        routes = post_routes(self.app)
        self.assertTrue(routes, 'the route table is not empty')
        for path, handler in sorted(routes.items()):
            with self.subTest(path=path):
                self.assertTrue(path.startswith('/api/'), 'a route outside /api/ would bypass the token check')
                self.assertTrue(callable(handler), 'the handler for ' + path + ' is not callable')

    def test_the_route_table_has_no_duplicate_paths(self):
        routes = post_routes(self.app)
        self.assertEqual(len(routes), len(set(routes)), 'a duplicate path would silently drop a handler')

    def test_every_product_path_is_served_and_declares_itself_a_product(self):
        self.assertTrue(PRODUCT_PATHS, 'the product registry is not empty')
        for path in PRODUCT_PATHS:
            with self.subTest(path=path):
                self.assertTrue(path.startswith('/api/'))
                self.assertTrue(self.app.is_product(path), path + ' is declared but not served as a product route')

    def test_the_gated_get_list_is_small_and_under_api(self):
        # Product routes are served through the registry, so the literal paths in the source are the read routes
        # that are NOT product views. They are token-gated too, and the list is asserted to stay a short list of
        # named resources rather than growing into a second, unenumerated API.
        extras = {path for path in source_get_paths() if not self.app.is_product(path)}
        for path in sorted(extras):
            with self.subTest(path=path):
                self.assertTrue(path.startswith('/api/'), 'a known GET route must live under /api/')
        self.assertLessEqual(len(extras), 30, 'the gated GET list has grown beyond its purpose: ' + ', '.join(sorted(extras)))
        for expected in ['/api/health', '/api/languages', '/api/watch-health', '/api/outbox', '/api/briefs']:
            with self.subTest(path=expected):
                self.assertIn(expected, extras, 'the shell reads ' + expected + ' and it must stay enumerated')

    def test_a_post_route_is_not_a_product_route(self):
        overlap = sorted(set(post_routes(self.app)) & set(PRODUCT_PATHS))
        self.assertEqual(overlap, [], 'a path cannot be both a read view and a mutation: ' + ', '.join(overlap))


if __name__ == '__main__':
    unittest.main()
