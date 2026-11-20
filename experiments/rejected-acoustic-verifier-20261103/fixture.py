"""Deterministic synthetic voices only; no microphone data."""
import numpy as np
RATE=16000

def speech_like(seconds, seed, rms=4200, f0_range=(105,205)):
    """Independent syllables; mostly voiced, formant-weighted harmonics + chirps.

    This intentionally does not rely on a broadband Gaussian excitation for AEC
    convergence. No sample or syllable repeats. F0, slope, vowel formants, duration,
    harmonic phase and gaps change with an independent RNG seed per voice.
    """
    rng=np.random.default_rng(seed)
    n=round(seconds*RATE)
    result=np.zeros(n,dtype=np.float64)
    vowels=((700,1200,2500),(400,1700,2600),(300,2200,3000),(550,900,2400),(450,1300,2800))
    cursor=0
    while cursor<n:
        count=min(n-cursor,int(rng.uniform(.12,.27)*RATE))
        t=np.arange(count)/RATE
        f0=rng.uniform(*f0_range)
        f0_end=f0*rng.uniform(.8,1.3)
        phase=2*np.pi*(f0*t+.5*(f0_end-f0)*t*t/max(t[-1],1/RATE))
        formants=np.asarray(vowels[int(rng.integers(len(vowels)))],float)*rng.uniform(.92,1.08)
        syllable=np.zeros(count)
        for harmonic in range(1,33):
            hz=harmonic*(f0+f0_end)/2
            if hz>=7400: break
            weight=(.08+sum(np.exp(-.5*((hz-formants)/np.array([110,160,230]))**2)))/harmonic**.55
            syllable += weight*np.sin(harmonic*phase+rng.uniform(-np.pi,np.pi))
        # Short voiced onset glide, not stochastic broadband content.
        glide_hz=rng.uniform(1800,3400)
        glide=np.sin(2*np.pi*(glide_hz*t+500*t*t/max(t[-1],1/RATE)))
        syllable += .08*glide*np.exp(-t/.035)
        fade=max(1,min(count//3,int(.025*RATE)))
        envelope=np.ones(count)
        envelope[:fade]=np.sin(np.linspace(0,np.pi/2,fade))**2
        envelope[-fade:]=np.sin(np.linspace(np.pi/2,0,fade))**2
        envelope*= .72+.28*np.sin(np.pi*np.arange(count)/count)
        syllable*=envelope*rng.uniform(.65,1.25)
        result[cursor:cursor+count]=syllable
        cursor+=count+int(rng.uniform(.008,.055)*RATE)
    result*=rms/max(np.sqrt(np.mean(result**2)),1e-12)
    # Inputs remain unclipped; output conversion below reports clipping too.
    return result

def pcm(x): return np.rint(np.clip(x,-32768,32767)).astype(np.int16)
