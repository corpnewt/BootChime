from Scripts import run, utils, plist
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
        # We haven't already gotten them - let's populate that list
        iohda = self.r.run({"args":["ioreg","-w0","-rxn","IOHDACodecDevice"]})[0].split("\n")
        ioreg = self.r.run({"args":["ioreg","-lw0"]})[0].split("\n")
        # First, we walk the iohda list, and find our codec info
        codecs = []
        current_codec = {}
        for x in iohda:
            if "<class IOHDACodecDevice," in x:
                current_codec["line"] = x
                current_codec["info"] = {}
            elif any((y in x for y in ("IOHDACodecVendorID","IOHDACodecRevisionID","IOHDACodecAddress"))):
                try:
                    current_codec["info"][x.split('"')[1]] = x.split(" = ")[-1]
                except:
                    pass
            elif x.replace("|","").strip() == "}": # Closing bracket
                # find the line in ioreg, then walk the path backwards to get the
                # device path
                if "line" in current_codec: # Only do this if we have the line
                    pad = found = None
                    path = []
                    for l in ioreg[::-1]:
                        if current_codec["line"] in l:
                            # Found it - gather pad, enable found
                            pad = len(l.split("+")[0])
                            found = True
                        if not found: continue # Don't care unless we're found
                        # Check for <class IOPCIDevice, and get pad if shorter
                        if any((y in l for y in ("<class IOPCIDevice,","<class IOACPIPlatformDevice,"))):
                            if pad is None or len(l.split("+")[0]) < pad:
                                # Set new pad - and retain the path dealio
                                pad = len(l.split("+")[0])
                                path.append(l.split("+-o ")[1].split("  <class")[0])
                    current_codec["path"] = path[::-1]
                    current_codec["device_name"] = path[0].split("@")[0]
                    dev_path = []
                    # Walk the path, and convert from ioreg devices to Device Path
                    for p in current_codec["path"]:
                        parts = p.split("@")[-1]
                        major = minor = "0"
                        try: major,minor = parts.split(",")
                        except: major = parts
                        if not dev_path:
                            dev_path.append("PciRoot(0x{})".format(major))
                        else:
                            dev_path.append("Pci(0x{},0x{})".format(major,minor))
                    current_codec["device_path"] = "/".join(dev_path)
                    codecs.append(current_codec)
                current_codec = {}
        return codecs

    def get_audio_volume(self):
        # Function to attempt to get SystemAudioVolume from NVRAM
        o = self.r.run({"args":["nvram","-x","SystemAudioVolume"]})
        if o[2] != 0: return None
        # Got something - try to load it, and return the value
        try:
            p = plist.loads(o[0])
        except:
            return None
        data = plist.extract_data(p.get("SystemAudioVolume",None))
        return int(binascii.hexlify(data),16) if data is not None else None

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
                for y in x["info"]:
                    print("  - {}: {}".format(y,x["info"][y]))
            else:
                print("  - Missing information!")
        print("")
        sav = self.get_audio_volume()
        print("Current SystemAudioVolume:\n  --> {}{}".format(
            sav if sav is not None else "NOT SET",
            " (0x{})".format(hex(sav)[2:].upper()) if sav is not None else ""
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
        if sav:
            print("S. Save current SystemAudioVolume as max")
            print("C. Clear SystemAudioVolume value from NVRAM")
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

if __name__ == '__main__':
    if 2/3 == 0: input = raw_input
    b = BootChime()
    while True:
        try:
            b.main()
        except Exception as e:
            print("An error occurred: {}".format(repr(e)))
            input("Press [enter] to continue...")
