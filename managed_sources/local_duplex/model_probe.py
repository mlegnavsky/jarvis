"""Fixed, content-free timing comparison using the existing configured API client."""
import asyncio
import time

FIXED_PROMPT='Odpověz česky pouze jednou krátkou větou na pozdrav Ahoj. Neprováděj žádnou akci.'
CANDIDATES=('gpt-4.1-mini','gpt-4o-mini')

async def audit_models(client,configured,*,clock=time.monotonic):
 results=[]
 for model in dict.fromkeys((configured,*CANDIDATES)):
  if not isinstance(model,str) or not model or len(model)>80:continue
  fact={'model':model if model.startswith(('gpt-','o1','o3','o4')) else 'custom_model'}
  started=clock()
  try:
   key='max_completion_tokens' if model.lower().startswith(('gpt-5','gpt-4o','o1','o3','o4')) else 'max_tokens'
   async with asyncio.timeout(20):
    response=await client.chat.completions.create(model=model,
     messages=[{'role':'user','content':FIXED_PROMPT}],**{key:128})
   choice=response.choices[0];content=choice.message.content or ''
   fact.update(status='ok' if content.strip() and choice.finish_reason=='stop' else 'incomplete',
     output_chars=len(content),finish_reason=choice.finish_reason if choice.finish_reason in ('stop','length','content_filter','tool_calls') else 'other')
  except Exception as exc:
   fact.update(status='error',error=type(exc).__name__ if type(exc).__name__.isidentifier() else 'provider_error')
   code=getattr(exc,'status_code',None)
   if type(code) is int and 100<=code<=599:fact['status_code']=code
  fact['duration_ms']=round((clock()-started)*1000,1);results.append(fact)
 return results
