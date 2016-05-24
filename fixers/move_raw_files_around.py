#!/usr/bin/env python

import glob
import os

def main():
    """Main function"""
    root = os.path.join("/","Volumes", "LaCie", "Telemetry2", "ShaneAO")
    search = os.path.join(root, "*", "raw", "*.fits")
    print("Searching {0}".format(search))
    for filename in glob.iglob(search):
        datepart = filename.split(os.path.sep)[-3]
        destination = os.path.join(root, "raw", datepart, os.path.basename(filename))
        if not os.path.exists(os.path.dirname(destination)):
            os.makedirs(os.path.dirname(destination))
        os.rename(filename, destination)

if __name__ == '__main__':
    main()