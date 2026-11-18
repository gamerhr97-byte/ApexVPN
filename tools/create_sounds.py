"""Original quiet PCM cues, synthesized locally without external audio assets."""
import math,pathlib,struct,wave
root=pathlib.Path(__file__).resolve().parents[1]/'assets/sounds';root.mkdir(parents=True,exist_ok=True)
cues={'click':[(720,.045)],'connected':[(523.25,.11),(783.99,.16)],'disconnected':[(587.33,.11),(392,.14)],'error':[(220,.12),(196,.16)]}
for name,notes in cues.items():
 samples=[];rate=22050
 for frequency,duration in notes:
  length=int(rate*duration)
  for i in range(length):
   t=i/rate;envelope=min(1,t/.008)*max(0,1-i/length)**2
   tone=(math.sin(2*math.pi*frequency*t)+.15*math.sin(4*math.pi*frequency*t))*.13*envelope
   samples.append(int(32767*tone))
  samples.extend([0]*int(rate*.025))
 with wave.open(str(root/(name+'.wav')),'wb') as output:
  output.setparams((1,2,rate,0,'NONE','not compressed'));output.writeframes(struct.pack('<'+'h'*len(samples),*samples))
print('Four original short PCM cues created.')
