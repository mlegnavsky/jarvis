"""Bounded body reads; a single aiohttp read(n) need not return a whole file."""
async def read_limited(stream,limit):
 chunks=[];size=0
 while True:
  chunk=await stream.read(16384)
  if not chunk:break
  size+=len(chunk)
  if size>limit:raise ValueError('download_size_limit')
  chunks.append(chunk)
 return b''.join(chunks)
