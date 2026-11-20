"""Short-lived complete WAV resources for generated speech, never microphone PCM."""
import asyncio
from contextlib import contextmanager
import os
from pathlib import Path
import re
import secrets
import stat
import threading
import time
from types import SimpleNamespace
import wave

NAME=re.compile(r'jarvis-[a-f0-9]{32}\.wav')


class SpeechFiles:
    def __init__(self,media_root,*,clock=time.time):
        self.media_root=Path(media_root);self.root=self.media_root/'jarvis_speech';self.clock=clock
        self.lock=threading.Lock()

    @contextmanager
    def directory(self):
        with self.lock:
            with self._directory() as directory:yield directory

    @contextmanager
    def _directory(self):
        try:
            parent=os.open(self.media_root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:
                try:os.mkdir('jarvis_speech',0o700,dir_fd=parent)
                except FileExistsError:pass
                directory=os.open('jarvis_speech',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
            finally:os.close(parent)
        except OSError:raise ValueError('private_speech_directory_unavailable') from None
        try:
            if stat.S_IMODE(os.fstat(directory).st_mode)&0o077:
                raise ValueError('private_speech_directory_required')
            yield directory
        finally:os.close(directory)

    def create(self,pcm):
        if not isinstance(pcm,bytes) or not 320<=len(pcm)<=32000*90 or len(pcm)%2:
            raise ValueError('invalid_speech_pcm')
        with self.directory() as directory:
            count=0;now=self.clock()
            for name in os.listdir(directory):
                if not NAME.fullmatch(name):continue
                info=os.stat(name,dir_fd=directory,follow_symlinks=False)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:continue
                if now-info.st_mtime>600:os.unlink(name,dir_fd=directory)
                else:count+=1
            if count>=4:raise ValueError('speech_resource_limit')
            name='jarvis-'+secrets.token_hex(16)+'.wav'
            handle=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
            try:
                with os.fdopen(handle,'wb') as stream:
                    with wave.open(stream,'wb') as audio:
                        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(pcm)
                os.utime(name,(now,now),dir_fd=directory,follow_symlinks=False)
            except BaseException:
                os.unlink(name,dir_fd=directory);raise
        return SimpleNamespace(name=name,path=self.root/name,
            media_id='media-source://media_source/local/jarvis_speech/'+name)

    def release(self,name):
        if not isinstance(name,str) or not NAME.fullmatch(name):raise ValueError('invalid_speech_resource')
        with self.directory() as directory:
            try:info=os.stat(name,dir_fd=directory,follow_symlinks=False)
            except FileNotFoundError:return
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise ValueError('unsafe_speech_resource')
            os.unlink(name,dir_fd=directory)


async def drain(future):
    """Finish owned file IO even if close and interruption cancel us together."""
    future=asyncio.ensure_future(future);cancelled=False
    while True:
        try:return await asyncio.shield(future),cancelled
        except asyncio.CancelledError:
            if future.cancelled():raise
            cancelled=True


async def create_owned_file(execute,store,pcm):
    item,cancelled=await drain(execute(store.create,pcm))
    async def release():
        _result,was_cancelled=await drain(execute(store.release,item.name))
        if was_cancelled:raise asyncio.CancelledError()
    if cancelled:
        await release();raise asyncio.CancelledError()
    return SimpleNamespace(media_id=item.media_id,release=release)


async def release_prepared(prepared):
    if (release:=getattr(prepared,'release',None)) is not None:
        _result,cancelled=await drain(release())
        if cancelled:raise asyncio.CancelledError()
