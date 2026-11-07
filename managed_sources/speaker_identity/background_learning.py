"""Bounded optional work; no command, identity, playback or storage authority."""
import asyncio

class BackgroundLearning:
    def __init__(self,infer,executor,collect,*,limit=2,timeout=8):
        self.infer=infer;self.executor=executor;self.collect=collect
        self.limit=limit;self.timeout=timeout;self.tasks=set();self.closed=False
        self._shutdown_task=None
        self.accepted=0;self.completed=0;self.dropped=0;self.failed=0;self.cancelled=0;self.last_error=None

    def submit(self,item,conversation):
        pcm=item.pop('learning_pcm',None)
        if not pcm:return False
        if self.closed or len(self.tasks)>=self.limit:
            self.dropped+=1;return False
        payload={key:item[key] for key in ('voiced','text','utterance','playback') if key in item}
        task=asyncio.create_task(self._run(pcm,payload,conversation))
        self.tasks.add(task);task.add_done_callback(self._finished);self.accepted+=1
        return True

    def _finished(self,task):
        self.tasks.discard(task)
        if task.cancelled():self.cancelled+=1

    async def _run(self,pcm,payload,conversation):
        try:
            # Only inference can be aborted by a deadline. Executor threads
            # cannot be cancelled: keep their slot and drain before release.
            async with asyncio.timeout(self.timeout):
                result=await self.infer(pcm)
            pcm=None
            job=asyncio.ensure_future(self.executor(self._collect,result,payload,conversation))
            try:
                await asyncio.shield(job)
            except asyncio.CancelledError:
                await asyncio.gather(job,return_exceptions=True)
                raise
            self.completed+=1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.failed+=1;self.last_error=type(exc).__name__

    async def shutdown(self):
        if self._shutdown_task is None:
            self.closed=True
            self._shutdown_task=asyncio.create_task(self._drain())
        await asyncio.shield(self._shutdown_task)

    def _collect(self,*args):
        if not self.closed:return self.collect(*args)

    async def _drain(self):
        tasks=list(self.tasks)
        for task in tasks:task.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)
        self.tasks.clear()

    def snapshot(self):
        return {'mode':'optional_background','pending':len(self.tasks),'limit':self.limit,
                'accepted':self.accepted,'completed':self.completed,'dropped':self.dropped,
                'failed':self.failed,'cancelled':self.cancelled,'last_error':self.last_error,
                'closed':self.closed,'drained':not self.tasks,'inference_timeout_s':self.timeout,
                'collector_lifecycle':'drained_before_release','raw_audio_saved':False}
