# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
import unittest
from omsimod import __version__
from omsimod.ai_help import build_prompt, redact_paths


class PromptTests(unittest.TestCase):
    def test_private_paths_are_removed(self):
        paths = [r'C:\Users\Private Person\模型\人物.pmx',
                 'D:/Private Person/模型/人物.pmx',
                 r'\\private-server\Private Person\人物.pmx',
                 '/home/Private Person/模型/人物.pmx',
                 '/Users/Private Person/人物.pmx',
                 r'\\?\C:\Users\Private Person\人物.pmx',
                 r'C:\\Users\\Private Person\\人物.pmx',
                 '~/Private Person/人物.pmx', '../Private Person/人物.pmx',
                 'file:///C:/Users/Private%20Person/人物.pmx']
        for path in paths:
            for message in (f"Permission denied: '{path}'", f'失败：{path}', f'失败："{path}"'):
                with self.subTest(message=message):
                    result = redact_paths(message)
                    self.assertNotIn('Private', result)
                    self.assertNotIn('private-server', result)
                    self.assertNotIn('人物.pmx', result)
                    self.assertIn('[路径已隐藏]', result)

    def test_prompt_has_version_context_but_no_issue_number(self):
        prompt = build_prompt('检查模型与骨骼', 'left_thigh: D bone has a different rest position')
        self.assertIn(__version__, prompt)
        self.assertIn('left_thigh: D bone has a different rest position', prompt)
        self.assertIn('图形化编辑', prompt)
        self.assertNotIn('问题编号', prompt)
        self.assertNotIn('BONE-001', prompt)
        self.assertIn('9. 不得随意推荐具体参数值。', prompt)
        self.assertIn('10. 优先使用最短路径解决问题。', prompt)
        self.assertIn('11. 避免不必要的复杂格式或交互式问卷。', prompt)
        self.assertIn('https://github.com/splDANHENG/omsipmxtool', prompt)

    def test_empty_and_unknown_errors_do_not_invent_diagnosis(self):
        self.assertIn('尚未记录报错', build_prompt('尚未操作', ''))
        self.assertIn('不足以确定', build_prompt('转换', 'something unexpected'))

    def test_error_lines_and_quoted_path_suffix_survive(self):
        result = redact_paths("missing 'C:/Users/Private/file.png': unsupported\nleft_thigh: bone missing")
        self.assertIn('unsupported', result)
        self.assertIn('left_thigh: bone missing', result)

