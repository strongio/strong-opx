from unittest import TestCase

from strong_opx.template.lexer import LexerError, TemplateLexer, Token


class TemplateLexerTest(TestCase):
    maxDiff = None

    def test_simple_text(self):
        tokens = TemplateLexer("Hello world!").tokenize()
        self.assertListEqual(tokens, [Token("Hello world!", 0)])
        self.assertEqual(tokens[0].position, 0)

    def test_empty_string(self):
        tokens = TemplateLexer("").tokenize()
        self.assertListEqual(tokens, [])

    def test_simple_variable(self):
        tokens = TemplateLexer("Hello {{ name }}!").tokenize()
        self.assertListEqual(
            tokens,
            [
                Token("Hello ", 0),
                (Token("{{", 6), Token("name", 9), Token("}}", 14)),
                Token("!", 16),
            ],
        )

    def test_variable_without_spaces(self):
        tokens = TemplateLexer("{{name}}").tokenize()
        self.assertListEqual(
            tokens,
            [
                (Token("{{", 0), Token("name", 2), Token("}}", 6)),
            ],
        )

    def test_empty_variable(self):
        tokens = TemplateLexer("{{}}").tokenize()
        self.assertListEqual(tokens, [])

    def test_simple_block(self):
        tokens = TemplateLexer("{% if user %}Hello{% endif %}").tokenize()
        self.assertListEqual(
            tokens,
            [
                (Token("{%", 0), Token("if user", 3), Token("%}", 11)),
                Token("Hello", 13),
                (Token("{%", 18), Token("endif", 21), Token("%}", 27)),
            ],
        )

    def test_block_without_spaces(self):
        tokens = TemplateLexer("{%if user%}").tokenize()
        self.assertListEqual(
            tokens,
            [
                (Token("{%", 0), Token("if user", 2), Token("%}", 9)),
            ],
        )

    def test_empty_block(self):
        tokens = TemplateLexer("{%%}").tokenize()
        self.assertListEqual(tokens, [])

    def test_simple_comment(self):
        tokens = TemplateLexer("Before {# This is a comment #} After").tokenize()
        self.assertListEqual(
            tokens,
            [
                Token("Before ", 0),
                Token(" After", 30),
            ],
        )

    def test_comment_only(self):
        tokens = TemplateLexer("{# Just a comment #}").tokenize()
        self.assertListEqual(tokens, [])

    def test_comment_at_start(self):
        tokens = TemplateLexer("{# comment #}text").tokenize()
        self.assertListEqual(
            tokens,
            [
                Token("text", 13),
            ],
        )

    def test_comment_at_end(self):
        tokens = TemplateLexer("text{# comment #}").tokenize()
        self.assertListEqual(
            tokens,
            [
                Token("text", 0),
            ],
        )

    def test_multiple_comments(self):
        tokens = TemplateLexer("A{# comment1 #}B{# comment2 #}C").tokenize()
        self.assertListEqual(
            tokens,
            [
                Token("A", 0),
                Token("B", 15),
                Token("C", 30),
            ],
        )

    def test_nested_constructs_in_comment(self):
        tokens = TemplateLexer("Before {# {{ variable }} {% block %} #} After").tokenize()
        self.assertListEqual(
            tokens,
            [
                Token("Before ", 0),
                Token(" After", 39),
            ],
        )

    def test_unclosed_comment(self):
        with self.assertRaises(LexerError) as cm:
            TemplateLexer("text {# unclosed comment").tokenize()

        self.assertEqual(cm.exception.message, "Unclosed tag")
        self.assertEqual(cm.exception.start_pos, 5)
        self.assertEqual(cm.exception.end_pos, 7)

    def test_simple_raw_block(self):
        tokens = TemplateLexer("{% raw %}{{ not_parsed }}{% endraw %}").tokenize()
        self.assertListEqual(
            tokens,
            [
                (Token("{% raw %}", 0), Token("{{ not_parsed }}", 9), Token("{% endraw %}", 25)),
            ],
        )

    def test_raw_block_with_content(self):
        tokens = TemplateLexer("Before {% raw %}{{ var }} {# comment #} {% block %}{% endraw %} After").tokenize()
        self.assertListEqual(
            tokens,
            [
                Token("Before ", 0),
                (Token("{% raw %}", 7), Token("{{ var }} {# comment #} {% block %}", 16), Token("{% endraw %}", 51)),
                Token(" After", 63),
            ],
        )

    def test_raw_block_flexible_whitespace(self):
        test_cases = [
            "{% raw %}content{% endraw %}",
            "{%raw%}content{%endraw%}",
            "{%  raw  %}content{%  endraw  %}",
            "{% raw%}content{%endraw %}",
            "{%raw %}content{% endraw%}",
        ]

        for template in test_cases:
            with self.subTest(template=template):
                tokens = TemplateLexer(template).tokenize()
                self.assertEqual(len(tokens), 1)
                self.assertEqual(len(tokens[0]), 3)
                self.assertEqual(tokens[0][1].value, "content")

    def test_empty_raw_block(self):
        tokens = TemplateLexer("{% raw %}{% endraw %}").tokenize()
        self.assertListEqual(tokens, [])

    def test_unclosed_raw_block(self):
        with self.assertRaises(LexerError) as cm:
            TemplateLexer("{% raw %}content").tokenize()

        self.assertEqual(cm.exception.message, "Unclosed tag")
        self.assertEqual(cm.exception.start_pos, 0)
        self.assertEqual(cm.exception.end_pos, 9)

    def test_mixed_constructs(self):
        tokens = TemplateLexer(
            "Hello {{ name }}! {% if logged_in %}{# user comment #}Welcome back!{% endif %}"
        ).tokenize()
        self.assertListEqual(
            tokens,
            [
                Token("Hello ", 0),
                (Token("{{", 6), Token("name", 9), Token("}}", 14)),
                Token("! ", 16),
                (Token("{%", 18), Token("if logged_in", 21), Token("%}", 34)),
                Token("Welcome back!", 54),
                (Token("{%", 67), Token("endif", 70), Token("%}", 76)),
            ],
        )

    def test_complex_template(self):
        template = (
            "{# Header comment #}\n"
            "<h1>{{ page_title }}</h1>\n"
            "{% for item in items %}\n"
            "    <p>{{ item.name }}: $ {{ item.price }}</p>\n"
            "{% endfor %}\n"
            "{% raw %}\n"
            "<script>\n"
            "    var data = {{ json_data }};\n"
            "    // This won't be parsed\n"
            "</script>\n"
            "{% endraw %}\n"
            "{# Footer comment #}"
        )

        tokens = TemplateLexer(template).tokenize()

        self.assertListEqual(
            tokens,
            [
                Token("\n<h1>", 20),
                (Token("{{", 25), Token("page_title", 28), Token("}}", 39)),
                Token("</h1>\n", 41),
                (Token("{%", 47), Token("for item in items", 50), Token("%}", 68)),
                Token("\n    <p>", 70),
                (Token("{{", 78), Token("item.name", 81), Token("}}", 91)),
                Token(": $ ", 93),
                (Token("{{", 97), Token("item.price", 100), Token("}}", 111)),
                Token(value="</p>\n", position=113),
                (Token("{%", 118), Token("endfor", 121), Token("%}", 128)),
                Token("\n", 130),
                (
                    Token("{% raw %}", 131),
                    Token(
                        "\n<script>\n    var data = {{ json_data }};\n    // This won't be parsed\n</script>\n",
                        140,
                    ),
                    Token("{% endraw %}", 220),
                ),
                Token("\n", 232),
            ],
        )

    def test_unclosed_variable(self):
        with self.assertRaises(LexerError) as cm:
            TemplateLexer("{{ unclosed variable").tokenize()

        self.assertEqual(cm.exception.message, "Unclosed tag")
        self.assertEqual(cm.exception.start_pos, 0)
        self.assertEqual(cm.exception.end_pos, 2)

    def test_unclosed_block(self):
        with self.assertRaises(LexerError) as cm:
            TemplateLexer("{% unclosed block").tokenize()

        self.assertEqual(cm.exception.message, "Unclosed tag")
        self.assertEqual(cm.exception.start_pos, 0)
        self.assertEqual(cm.exception.end_pos, 2)

    def test_malformed_delimiters(self):
        tokens = TemplateLexer("{ { not_a_variable } } { # not_a_comment").tokenize()
        self.assertListEqual(
            tokens,
            [
                Token("{ { not_a_variable } } { # not_a_comment", 0),
            ],
        )

    def test_consecutive_constructs(self):
        tokens = TemplateLexer("{{var1}}{{var2}}{%block%}").tokenize()
        self.assertListEqual(
            tokens,
            [
                (Token("{{", 0), Token("var1", 2), Token("}}", 6)),
                (Token("{{", 8), Token("var2", 10), Token("}}", 14)),
                (Token("{%", 16), Token("block", 18), Token("%}", 23)),
            ],
        )

    def test_single_character_constructs(self):
        tokens = TemplateLexer("{ } % # ").tokenize()
        self.assertListEqual(
            tokens,
            [
                Token("{ } % # ", 0),
            ],
        )
