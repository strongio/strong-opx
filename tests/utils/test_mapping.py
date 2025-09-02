from unittest import TestCase
from unittest.mock import Mock

from strong_opx.utils.mapping import CaseInsensitiveMultiTagDict, LazyDict


class LazyDictTests(TestCase):
    def test_len(self):
        mapping = LazyDict({"a": 1, "b": 2})
        self.assertEqual(len(mapping), 2)

        mapping["c"] = 3
        self.assertEqual(len(mapping), 3)

    def test_iter(self):
        mapping = LazyDict({"a": 1, "b": 2})
        mapping["c"] = 3

        self.assertSetEqual(set(mapping), {"a", "b", "c"})

    def test_items(self):
        mapping = LazyDict({"a": 1, "b": 2})
        mapping["c"] = 3

        self.assertSetEqual(set(mapping.items()), {("a", 1), ("b", 2), ("c", 3)})

    def test_set_lazy(self):
        mapping = LazyDict({"a": 1, "b": 2})
        mapping.set_lazy("c", lambda: 3)

        self.assertEqual(mapping["c"], 3)

    def test_repr(self):
        mapping = LazyDict({"a": 1, "b": 2})
        mapping["c"] = 3

        self.assertEqual(repr(mapping), "LazyDict({'a': 1, 'b': 2, 'c': 3})")

    def test_repr__lazy_object(self):
        lazy_resolver = Mock()

        mapping = LazyDict({"a": 1, "b": 2})
        mapping.set_lazy("c", lazy_resolver)

        self.assertEqual(repr(mapping), f"LazyDict({{'a': 1, 'b': 2, 'c': <LazyValue: {lazy_resolver}>}})")
        lazy_resolver.assert_not_called()


class CaseInsensitiveMultiTagDictTests(TestCase):
    def setUp(self):
        self.tags = CaseInsensitiveMultiTagDict(
            {"Environment": "Production", "Owner": "someone@example.com", "Project": "CloudMigration"}
        )

    def test_case_insensitive_lookup(self):
        self.assertEqual(self.tags["environment"], ["Production"])

    def test_case_insensitive_membership(self):
        self.assertIn("owner", self.tags)
        self.assertIn("ENVIRONMENT", self.tags)
        self.assertNotIn("team", self.tags)

    def test_update_and_get(self):
        self.tags["Team"] = "DevOps"
        self.assertEqual(self.tags["TEAM"], ["DevOps"])
        self.assertEqual(self.tags.get("team"), ["DevOps"])
        self.assertEqual(self.tags.get("cost-center"), [])

    def test_multi_tag_value(self):
        self.tags["environment"] = "Staging"
        self.assertEqual(self.tags["ENVIRONMENT"], ["Production", "Staging"])

    def test_delete_tag(self):
        del self.tags["Owner"]
        self.assertNotIn("owner", self.tags)
        with self.assertRaises(KeyError):
            _ = self.tags["owner"]
