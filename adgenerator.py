import argparse
import os
import sys
import fileinput

parser = argparse.ArgumentParser(description='Run the corresponding ADGenerator script from the security level provided.')

parser.add_argument('-seclev', default="low", help='Select security level low/medium/high')

args = parser.parse_args()
print(args.seclev)
if (args.seclev == "low"):
    os.chdir("/home/cathhuo/ADGenerator/low")
    os.system("pip install .")
    os.system("adsimulator")

elif (args.seclev == "medium"):
    os.chdir("/home/cathhuo/ADGenerator/medium_high")
    
    tempFile = open("adsimulator/DBCreator.py", 'r+' )
    for line in fileinput.input("adsimulator/DBCreator.py"):
        tempFile.write(line.replace("High", "Medium"))
    tempFile.close()

    os.system("pip install .")
    os.system("adsimulator")

elif (args.seclev == "high"):
    os.chdir("/home/cathhuo/ADGenerator/medium_high")

    tempFile = open("adsimulator/DBCreator.py", 'r+' )
    for line in fileinput.input("adsimulator/DBCreator.py"):
        tempFile.write(line.replace("Medium", "High"))
    tempFile.close()

    os.system("pip install .")
    os.system("adsimulator")

else:
    print("Please enter a security level: -seclev low/medium/high")