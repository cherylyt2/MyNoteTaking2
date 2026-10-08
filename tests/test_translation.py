import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.main import app
from src.translator import llm_generate


class TranslationTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('src.routes.note.llm_generate', return_value='こんにちは')
    def test_translate_endpoint_returns_json(self, translate):
        response = self.client.post('/api/notes/translate', json={
            'content': 'Hello',
            'target_language': 'Japanese',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'translation': 'こんにちは',
            'target_language': 'Japanese',
        })
        translate.assert_called_once_with('Hello', 'Japanese')

    def test_translate_endpoint_rejects_empty_content(self):
        response = self.client.post('/api/notes/translate', json={
            'content': '   ',
            'target_language': 'Chinese',
        })

        self.assertEqual(response.status_code, 400)

    def test_llm_uses_prompt_template_and_returns_translation(self):
        mock_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='こんにちは'))]
        )
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            with patch('src.translator.OpenAI') as openai:
                openai.return_value.chat.completions.create.return_value = mock_response
                result = llm_generate('Hello', 'Japanese')

        messages = openai.return_value.chat.completions.create.call_args.kwargs['messages']
        self.assertEqual(result, 'こんにちは')
        self.assertIn('Japanese', messages[0]['content'])
        self.assertIn('Cantonese', messages[0]['content'])
        self.assertEqual(messages[1]['content'], 'Hello')

    def test_llm_retries_provider_response_without_choices(self):
        mock_response = SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason='stop',
                message=SimpleNamespace(content='こんにちは'),
            )]
        )
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            with patch('src.translator.OpenAI') as openai:
                openai.return_value.chat.completions.create.side_effect = [
                    SimpleNamespace(choices=None),
                    mock_response,
                ]
                with self.assertLogs('src.translator', level='INFO') as logs:
                    result = llm_generate('Hello', 'Japanese')

        self.assertEqual(result, 'こんにちは')
        self.assertEqual(openai.return_value.chat.completions.create.call_count, 2)
        self.assertIn('attempt 1 finish_reason=None', logs.output[0])
        self.assertIn('attempt 2 finish_reason=stop', logs.output[1])

    def test_llm_rejects_malformed_provider_output_after_retry(self):
        malformed_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='\ufffd'))]
        )
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            with patch('src.translator.OpenAI') as openai:
                openai.return_value.chat.completions.create.return_value = malformed_response
                with self.assertRaisesRegex(RuntimeError, 'no valid translation'):
                    llm_generate('Hello', 'Japanese')
        self.assertEqual(openai.return_value.chat.completions.create.call_count, 2)


if __name__ == '__main__':
    unittest.main()