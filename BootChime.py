from Scripts import run, utils, plist, ioreg
import os, sys, json, binascii

class BootChime:
    def __init__(self, **kwargs):
        self.u = utils.Utils("Boot Chime")
        # Verify running os
        if not sys.platform.lower() == "darwin":
            self.u.head("Wrong OS!")
            print("")
            print("BootChime can only be run on macOS!")
            print("")
            self.u.grab("Press [enter] to exit...")
            exit()
        self.r = run.Run()
        self.i = ioreg.IOReg()
        self.codecs = []
        self.settings_file = "./Scripts/settings.json"
        cwd = os.getcwd()
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        if self.settings_file and os.path.exists(self.settings_file):
            self.settings = json.load(open(self.settings_file))
        else:
            self.settings = {}
        os.chdir(cwd)

    def save_settings(self):
        cwd = os.getcwd()
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        try:
            json.dump(self.settings,open(self.settings_file,"w"),indent=2)
        except Exception as e:
            print("Could not save settings:  {}".format(repr(e)))
        os.chdir(cwd)

    def get_codecs(self):
        if self.codecs: return self.codecs

        def get_pad(device):
            # Returns the number of chars before hitting +-o
            return len(device.split("+-o ")[0])

        def trim_devices(devices,device,append=True):
            # Helper to walk the passed devices list in reverse and remove any
            # whose padding is >= the passed device.
            # Returns the updated list with the new device optionally appeneded.
            pad = get_pad(device)
            while True:
                d_pad = get_pad(devices[-1]) if devices else -1
                if d_pad == -1 or d_pad < pad:
                    break # Bail out of the loop
                devices.pop(-1) # Remove the last element
            if append: devices.append(device)
            return devices

        # Let's walk the ioreg until we find our IOHDACodecDevice entries,
        # keeping track of nested devices by their indentation to retain
        # whichever the codec belongs to.
        devices = []
        codecs = []
        for line in self.i.get_ioreg():
            if any((x in line for x in ("  <class IOPCIDevice,","  <class IOACPIPlatformDevice,"))):
                # Got a PCI/ACPI device - compare it to our existing device list
                devices = trim_devices(devices,line)
            elif "  <class IOHDACodecDevice," in line and devices:
                # Got a codec - save some info.  Ensure we have only devices that
                # could be parents to this IOHDACodecDevice
                devices = trim_devices(devices,line,append=False)
                try:
                    codecs.append({
                        "line": line,
                        "info": self.i.get_device_info(line)[0]["parts"],
                        "device": devices[-1],
                        "device_name": devices[-1].split("+-o ")[1].split("@")[0],
                        "device_path": self.i.get_device_path(devices[-1])
                    })
                except:
                    pass
        return codecs

    def get_audio_volume(self, key = "SystemAudioVolume"):
        # Function to attempt to get SystemAudioVolume from NVRAM
        o = self.r.run({"args":["nvram","-x",key]})
        if o[2] != 0: return None
        # Got something - try to load it, and return the value
        try:
            p = plist.loads(o[0])
        except:
            return None
        data = plist.extract_data(p.get(key,None))
        return int(binascii.hexlify(data),16) if data is not None else None

    def get_audio_db(self):
        # Function to attempt to get SystemAudioVolumeDB from NVRAM
        sdb = self.get_audio_volume(key="SystemAudioVolumeDB")
        if sdb is None: return sdb
        # Convert to a signed 8-bit int
        sdb_signed = sdb-((sdb & 0x80) << 1) # Subtract 256 if bit 7 is set
        return (sdb_signed,sdb)

    def get_volume_amp(self,max_volume=0):
        if not isinstance(max_volume,(int,float)): return None
        vol_amp = (10000.)/float(max_volume)
        # Always round down per the OC docs
        return int(vol_amp)

    def clear_sav(self):
        self.u.head("Clearing SystemAudioVolume")
        print("")
        print("sudo nvram -d SystemAudioVolume")
        self.r.run({"args":["sudo","nvram","-d","SystemAudioVolume"],"sudo":True,"stream":True})
        print("")
        self.u.grab("Press [enter] to return...")

    def get_mask(self):
        bits = self.settings.get("audio_out_mask",0)
        if not isinstance(bits,int): bits = 0
        while True:
            self.u.head("AudioOutMask")
            print("")
            print("Note:  Requires OC 0.7.7 or newer!")
            print("")
            bin_str = "{0:b}".format(bits).rjust(32,"0")
            print("Binary:  {}".format(bin_str))
            print("Hex:     0x{}".format(hex(bits)[2:].upper()))
            print("Decimal: {}".format(bits))
            enabled_list = [str(i) for i,x in enumerate(bin_str[::-1]) if x != "0"]
            print("Enabled: {}".format(",".join(enabled_list) if enabled_list else "None"))
            print("")
            print("A. Enable All")
            print("N. Enable None")
            print("")
            print("M. Return to menu")
            print("Q. Quit")
            print("")
            print("To toggle outputs, pass them in a comma delimited list from 0-31 (eg: 1,2,3)")
            print("You can pass masks with the bin, hex, or dec prefix to decode them")
            print("eg: bin:0001010 or hex:0xABCD or dec:1234")
            print("")
            menu = self.u.grab("Please select an option:  ")
            if menu.lower() == "m": return
            elif menu.lower() == "q": self.u.custom_quit()
            elif menu.lower() == "a":
                bits = int("1"*32,2)
            elif menu.lower() == "n":
                bits = 0
            elif menu.lower().startswith("bin:"):
                # Binary - attempt to decode the value
                try:
                    temp_bits = int(menu.split(":")[-1],2)
                    assert 0 <= temp_bits < 32
                    bits = temp_bits
                except: pass # Bad value
            elif menu.lower().startswith("hex:"):
                # Hexadecimal - attempt to decode the value
                try:
                    temp_bits = int(menu.split(":")[-1].replace(" ","").strip("<>"),16)
                    assert 0 <= temp_bits < 32
                    bits = temp_bits
                except: pass # Bad value
            elif menu.lower().startswith("dec:"):
                # Decimal - attempt to decode the value
                try:
                    temp_bits = int(menu.split(":")[-1])
                    assert 0 <= temp_bits < 32
                    bits = temp_bits
                except: pass # Bad value
            else:
                num_list = [int(x) for x in menu.replace(" ","").split(",") if x.isdigit() and 0<=int(x)<32]
                if not num_list: continue # Nothing to do
                # Let's toggle bits!
                for num in num_list:
                    bits ^= 1 << num
            self.settings["audio_out_mask"] = bits
            self.save_settings()

    def main(self):
        self.codecs = self.get_codecs()
        self.u.head()
        print("")
        print("IOHDACodecDevices:")
        if not len(self.codecs):
            print("- None found!  Aborting...")
            print("")
            exit(1)
        for i,x in enumerate(self.codecs,start=1):
            print("- {}. {} - {}:".format(i,x["device_name"],x["device_path"]))
            if x["info"]:
                keys = ("IOHDACodecVendorID","IOHDACodecRevisionID","IOHDACodecAddress")
                pad  = len(max(keys,key=len))
                for y in keys:
                    val = x["info"].get(y,"MISSING VALUE!")
                    # Try to convert to hex
                    try: val = "0x"+hex(int(val))[2:].upper()
                    except: pass
                    print("  - {}: {}".format(y.rjust(pad),val))
            else:
                print("  - Missing information!")
        print("")
        sav = self.get_audio_volume()
        print("Current SystemAudioVolume:\n  --> {}{}".format(
            sav if sav is not None else "NOT SET",
            " (0x{})".format(hex(sav)[2:].upper()) if sav is not None else ""
        ))
        savdb = self.get_audio_db()
        print("Current SystemAudioVolumeDB (OC 0.7.7+):\n  --> {}{}".format(
            savdb[0] if savdb is not None else "NOT SET",
            " (0x{})".format(hex(savdb[1])[2:].upper()) if savdb is not None else ""
        ))
        volume_amp = None
        if "max_volume" in self.settings:
            volume_amp = self.get_volume_amp(self.settings["max_volume"])
            if volume_amp is not None:
                print("VolumeAmplifier (Calculated from max volume of {} - 0x{}):\n  --> {}".format(
                    self.settings["max_volume"],
                    hex(self.settings["max_volume"])[2:].upper(),
                    volume_amp
                ))
            if sav is not None:
                min_vol = int((float(sav) * float(volume_amp)) / 100.)
                print("Current SystemAudioVolume as MinimumVolume:\n  --> {}{}".format(
                    min_vol,
                    "" if min_vol >= 100 else " (use 100 to mute at this volume)" if min_vol == 99 else " (use {}-100 to mute at this volume)".format(min_vol+1)
                ))
        print("")
        if volume_amp is not None:
            print("M. Clear max SystemAudioVolume from settings")
        if sav is not None:
            print("C. Clear SystemAudioVolume value from NVRAM")
            print("S. Save current SystemAudioVolume as max")
        print("O. Setup AudioOutMask (OC 0.7.7+)")
        print("")
        print("Q. Quit")
        print("")
        menu = self.u.grab("Please select an option:  ").lower()
        if not len(menu): return
        if menu == "q": self.u.custom_quit()
        if sav is not None:
            if menu == "s":
                self.settings["max_volume"] = sav
                self.save_settings()
            elif menu == "c":
                self.clear_sav()
        if volume_amp is not None and menu == "m":
            self.settings.pop("max_volume",None)
            self.save_settings()
        if menu == "o":
            self.get_mask()

if __name__ == '__main__':
    if 2/3 == 0: input = raw_input
    b = BootChime()
    while True:
        try:
            b.main()
        except Exception as e:
            print("An error occurred: {}".format(repr(e)))
            input("Press [enter] to continue...")
