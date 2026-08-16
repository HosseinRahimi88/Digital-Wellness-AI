Digital Wellness AI - ambient music tracks
==========================================

These five tracks are the app's built-in ambient music. They ship in a
separate archive because they are 27 MB of already-compressed audio -
larger than the app itself - and they are byte-identical in every
build. Download once, use with any version.

WHERE TO PUT THEM
-----------------
Copy the five .mp3 files into:

    Digital-Wellness-AI/frontend/assets/audio/

so you end up with:

    Digital-Wellness-AI/frontend/assets/audio/track1.mp3
    Digital-Wellness-AI/frontend/assets/audio/track2.mp3
    ... through track5.mp3

That is the whole installation. No configuration; refresh the page.

IF YOU SKIP THIS
----------------
The app works completely without them. The music widget notices the
files are missing and stays showing "paused" rather than pretending to
play. Nothing else depends on them - sound effects and the digital
guide's voice are separate systems and work either way.

YOUR OWN MUSIC
--------------
The upload button in the music widget accepts your own .mp3 and stores
it in your browser, so you can replace these without touching files.

Encoding
--------
80 kbps mono, 32 kHz. These are ambient background loops played under a
web app, not listening material - the sources were 120-190 kbps stereo,
which cost 27 MB for a difference nobody hears through the volume slider
this player ships at. Re-encoded, the whole project fits in one archive
instead of being split across several, which is worth more than the
bitrate. Durations are unchanged (verified by decode, not by header -
the original files carried wrong VBR headers and misreported their own
length).
