# BootChime
Py script to aid in setting up the boot chime in OpenCore.  It does so by helping you locate your `IOHDACodecDevice`s, `IOHDACodecAddress` values, current `SystemAudioVolume`, and by helping you calculate your VolumeAmplifier and MinimumVolume.

## Quick Start

* Clear any existing `SystemAudioVolume` value from both the local NVRAM, and the config.plist (in NVRAM -> Add and NVRAM -> Delete)
* Set your audio output device to your internal codec, turn the volume all the way up, and reboot
  * In *most* cases, this will save the max `SystemAudioVolume` value for your codec
  * In situations where this value is not properly saved, it may indicate an issue with your NVRAM, or codec - and this script isn't likely of use
* Open the BootChime script and select `S. Save current SystemAudioVolume as max` to retain this value, and auto-calculate the `VolumeAmplifier`
  * Copy the `VolumeAmplifier` integer value to your config.plist -> UEFI -> Audio -> VolumeAmplifier

This should yield a "sane" VolumeAmplifier value based off your max `SystemAudioVolume`.  After determining this value, you can further fine tune when the chime is muted by configuring a MinimumVolume level as follows:

* Set your system volume to the level where you'd like the chime to mute and reboot
* Open BootChime and check what it reports for the `Current SystemAudioVolume as MinimumVolume`
  * It lists a range of numbers up to 100 that can be used to mute the chime at the current volume
  * For example, my Dell 5580 reports the following at half volume: `--> 96 (use 97-100 to mute at this volume)`
* Copy the desired minimum value to your config.plist -> UEFI -> Audio -> MinimumVolume

## Pitfalls

You are still encouraged to work through [Dortania's Post-Install guide](https://dortania.github.io/OpenCore-Post-Install/cosmetic/gui.html#setting-up-boot-chime-with-audiodxe) to determing the proper values for your setup, though this script can make a number of them easier to find and calculate.

**Note:** Some codecs do not report a wide range of `SystemAudioVolume` values - so MinimumVolume may be difficult to fine-tune (if possible at all).  In playing with these settings, I found that my Dell 5580 used the same value from just over half volume all the way to max, while my HP Envy 15-j003cl had many more valid audio steps.  Your mileage may vary.

## Thanks

* Acidanthera for OpenCore and a myriad of other contributions
* Apple for macOS
* Dortania for their OpenCore guide
* Many others
