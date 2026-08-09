# coding=utf-8
"""
Unit tests for ddns.util.comment module
@author: GitHub Copilot
"""
from __future__ import unicode_literals
from __init__ import unittest
from ddns.util.comment import remove_comment


class TestRemoveComment(unittest.TestCase):
    """Test cases for comment removal functionality"""

    def test_remove_comment_empty_string(self):
        """测试空字符串"""
        result = remove_comment("")
        self.assertEqual(result, "")

    def test_remove_comment_no_comments(self):
        """测试没有注释的内容"""
        content = '{"key": "value", "number": 123}'
        result = remove_comment(content)
        self.assertEqual(result, content)

    def test_remove_comment_hash_full_line(self):
        """测试整行 # 注释"""
        content = '# This is a comment\n{"key": "value"}'
        expected = '\n{"key": "value"}'
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_double_slash_full_line(self):
        """测试整行 // 注释"""
        content = '// This is a comment\n{"key": "value"}'
        expected = '\n{"key": "value"}'
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_hash_with_leading_whitespace(self):
        """测试带前导空白的 # 注释"""
        content = '   # This is a comment\n{"key": "value"}'
        expected = '\n{"key": "value"}'
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_double_slash_with_leading_whitespace(self):
        """测试带前导空白的 // 注释"""
        content = '  // This is a comment\n{"key": "value"}'
        expected = '\n{"key": "value"}'
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_hash_end_of_line(self):
        """测试行尾 # 注释"""
        content = '{"key": "value"} # this is a comment'
        expected = '{"key": "value"}'
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_double_slash_end_of_line(self):
        """测试行尾 // 注释"""
        content = '{"key": "value"} // this is a comment'
        expected = '{"key": "value"}'
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_hash_in_string_should_not_remove(self):
        """测试字符串内的 # 不应该被移除"""
        content = '{"url": "http://example.com#anchor"}'
        result = remove_comment(content)
        self.assertEqual(result, content)

    def test_remove_comment_double_slash_in_string_should_not_remove(self):
        """测试字符串内的 // 不应该被移除"""
        content = '{"url": "http://example.com/path"}'
        result = remove_comment(content)
        self.assertEqual(result, content)

    def test_remove_comment_single_quoted_string_with_hash(self):
        """测试单引号字符串内的 # 不应该被移除"""
        content = "{'url': 'http://example.com#anchor'}"
        result = remove_comment(content)
        self.assertEqual(result, content)

    def test_remove_comment_single_quoted_string_with_double_slash(self):
        """测试单引号字符串内的 // 不应该被移除"""
        content = "{'url': 'http://example.com/path'}"
        result = remove_comment(content)
        self.assertEqual(result, content)

    def test_remove_comment_escaped_quotes_in_string(self):
        """测试字符串内转义引号的处理"""
        content = '{"message": "He said \\"Hello#World\\""} # comment'
        expected = '{"message": "He said \\"Hello#World\\""}'
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_complex_json_with_comments(self):
        """测试复杂JSON配置与多种注释"""
        content = """{
    // Configuration file for DDNS
    "$schema": "https://ddns.newfuture.cc/schema/v4.0.json", // Schema validation
    "debug": false,  # false=disable, true=enable
    "dns": "dnspod_com",  // DNS provider
    "id": "1008666",      # ID or Email
    "token": "ae86$cbbcctv666666666666666",  // API Token or Key
    "ipv4": ["test.lorzl.ml"],  # IPv4 domains to update
    "ipv6": ["test.lorzl.ml"],  // IPv6 domains to update
    "index4": "public",     # IPv4 update method
    "index6": "url:https://iptest.com",  # IPv6 update method
    "proxy": null  // Proxy settings
}"""
        expected = """{

    "$schema": "https://ddns.newfuture.cc/schema/v4.0.json",
    "debug": false,
    "dns": "dnspod_com",
    "id": "1008666",
    "token": "ae86$cbbcctv666666666666666",
    "ipv4": ["test.lorzl.ml"],
    "ipv6": ["test.lorzl.ml"],
    "index4": "public",
    "index6": "url:https://iptest.com",
    "proxy": null
}"""
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_mixed_comment_styles(self):
        """测试混合注释风格"""
        content = """// Header comment
{
    # This is a hash comment
    "key1": "value1", // End of line comment
    "key2": "value2"  # Another end of line comment
}
# Footer comment"""
        expected = """
{

    "key1": "value1",
    "key2": "value2"
}
"""
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_comments_with_special_chars(self):
        """测试包含特殊字符的注释"""
        content = """// Comment with 中文字符 and émojis 🚀
{
    "test": "value" # Comment with symbols !@#$%^&*()
}"""
        expected = """
{
    "test": "value"
}"""
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_preserve_empty_lines(self):
        """测试保留空行"""
        content = """// Comment

{
    "key": "value"
}

// Another comment"""
        expected = """

{
    "key": "value"
}

"""
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_url_with_hash_and_comment(self):
        """测试URL中包含#，行尾有注释的情况"""
        content = '{"url": "https://example.com#section"} # This is a comment'
        expected = '{"url": "https://example.com#section"}'
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_json_array_with_comments(self):
        """测试JSON数组与注释"""
        content = """[
    // First item
    "item1", # Comment 1
    "item2", // Comment 2
    "item3"  # Last item
]"""
        expected = """[

    "item1",
    "item2",
    "item3"
]"""
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_nested_quotes(self):
        """测试嵌套引号的处理"""
        content = """{"message": "She said: \\"Don't use // or # here\\""} // comment"""
        expected = """{"message": "She said: \\"Don't use // or # here\\""} """
        result = remove_comment(content)
        # Note: we expect a trailing space where the comment was removed
        self.assertEqual(result, expected.rstrip())

    def test_remove_comment_multiple_slashes(self):
        """测试多个斜杠的情况"""
        content = '{"path": "C:\\\\Program Files\\\\App"} // Windows path'
        expected = '{"path": "C:\\\\Program Files\\\\App"}'
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_hash_after_double_slash_comment(self):
        """测试 // 注释中包含 # 的情况"""
        content = '{"key": "value"} // Comment with # symbol'
        expected = '{"key": "value"}'
        result = remove_comment(content)
        self.assertEqual(result, expected)

    def test_remove_comment_single_line_various_formats(self):
        """测试单行多种格式"""
        test_cases = [
            ('{"key": "value"}', '{"key": "value"}'),  # No comment
            ("# Full line comment", ""),  # Full line hash
            ("// Full line comment", ""),  # Full line double slash
            ("   # Indented comment", ""),  # Indented hash
            ("   // Indented comment", ""),  # Indented double slash
            ('{"a": "b"} # End comment', '{"a": "b"}'),  # End hash
            ('{"a": "b"} // End comment', '{"a": "b"}'),  # End double slash
        ]

        for input_content, expected in test_cases:
            with self.subTest(input_content=input_content):
                result = remove_comment(input_content)
                self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
