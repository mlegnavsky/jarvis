import unittest
from transport import read_limited
class ShortReads(unittest.IsolatedAsyncioTestCase):
 async def test_partial_network_reads_are_joined_to_eof(self):
  class Reader:
   chunks=iter([b'first',b'second',b''])
   async def read(self,n):return next(self.chunks)
  self.assertEqual(await read_limited(Reader(),20),b'firstsecond')
 async def test_oversized_download_is_rejected_before_parsing(self):
  class Reader:
   async def read(self,n):return bytes(16)
  with self.assertRaises(ValueError):await read_limited(Reader(),20)
