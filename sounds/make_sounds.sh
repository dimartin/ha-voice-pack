#!/bin/sh
# Generate the alarm tones with ffmpeg (synthesized, so no licensing questions).
# Usage: make_sounds.sh OUTDIR   -> OUTDIR/alarm_{classic,chimes,pulse,gentle}.mp3
# Each file is one short cycle; the alarm automation repeats it until cancelled.
set -eu
out=${1:?usage: make_sounds.sh OUTDIR}
mkdir -p "$out"

tone() {  # name seconds expression
  ffmpeg -loglevel error -y -f lavfi -i "aevalsrc=exprs='$3':s=44100:d=$2" \
    -ac 1 -codec:a libmp3lame -b:a 96k "$out/alarm_$1.mp3"
}

# classic: four quick 1 kHz beeps, a pause, three times (digital clock).
tone classic 3.3 \
  '0.5*lt(mod(t,1.1),0.6)*lt(mod(mod(t,1.1),0.15),0.08)*(sin(2*PI*1000*t)+0.3*sin(2*PI*3000*t))'

# chimes: rising C-E-G-C with a bell decay.
tone chimes 3.4 \
  '0.3*(gte(t,0)*exp(-3*t)*sin(2*PI*523.25*t)+gte(t,0.4)*exp(-3*(t-0.4))*sin(2*PI*659.25*(t-0.4))+gte(t,0.8)*exp(-3*(t-0.8))*sin(2*PI*783.99*(t-0.8))+gte(t,1.2)*exp(-2*(t-1.2))*sin(2*PI*1046.5*(t-1.2)))'

# pulse: rising 600-1200 Hz sweeps, four times.
tone pulse 3 \
  '0.45*lt(mod(t,0.75),0.5)*sin(2*PI*(600*mod(t,0.75)+600*mod(t,0.75)*mod(t,0.75)))'

# gentle: soft alternating A4/E5 notes.
tone gentle 3.6 \
  '0.3*exp(-5*mod(t,0.6))*sin(2*PI*if(lt(mod(t,1.2),0.6),440,659.25)*mod(t,0.6))'

ls -l "$out"
