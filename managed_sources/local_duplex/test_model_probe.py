from types import SimpleNamespace as NS
import unittest

class ProbeTests(unittest.IsolatedAsyncioTestCase):
 async def test_benchmark_is_fixed_text_no_tools_and_no_response_text_saved(self):
  import model_probe as p
  requests=[]
  async def create(**kw):
   requests.append(kw)
   return NS(choices=[NS(finish_reason='stop',message=NS(content='Ahoj.'))],usage=NS(completion_tokens=3))
  client=NS(chat=NS(completions=NS(create=create)))
  result=await p.audit_models(client,'gpt-4.1-mini')
  self.assertEqual(len(requests),2)
  self.assertEqual({r['messages'][0]['content'] for r in requests},{p.FIXED_PROMPT})
  self.assertTrue(all('tools' not in r and 'functions' not in r for r in requests))
  self.assertNotIn('Ahoj.',str(result))
  self.assertTrue(all(x['status']=='ok' for x in result))
 async def test_provider_errors_are_sanitized(self):
  import model_probe as p
  async def create(**kw):raise ValueError('sk-PRIVATE secret URL')
  result=await p.audit_models(NS(chat=NS(completions=NS(create=create))),'gpt-4.1-mini')
  self.assertNotIn('PRIVATE',str(result))
  self.assertTrue(all(x['error']=='ValueError' for x in result))
