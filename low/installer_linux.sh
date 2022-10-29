#!/bin/bash
adsimulator_PATH="$HOME/.adsimulator"

if ! [ -f "$adsimulator_PATH/enable_root.cfg" ] && [ $(id -u) = 0 ] ; then
	echo "ERROR: This script must NOT be run as 'root'"
	exit 1
fi

if ! [ $(uname) == "Linux" ] ; then
    echo "ERROR: This installation script is only for systems running a Linux distribution"
    exit 1
fi

if ! [ -d "$adsimulator_PATH" ] ; then
    mkdir $adsimulator_PATH
fi

if ! [ -d "$adsimulator_PATH/adsimulator" ] ; then
    git clone https://github.com/nicolas-carolo/adsimulator $adsimulator_PATH/adsimulator
    cp -r $adsimulator_PATH/adsimulator/data $adsimulator_PATH
fi

cd $adsimulator_PATH/adsimulator
git_output=$(git pull)
if [ "$git_output" == "Already up to date." ]  ; then
    echo "adsimulator already up-to-date"
else
    touch $adsimulator_PATH/adsimulator_sw.lock
    echo "Latest version of adsimulator downloaded"
    echo "Run the following commands (be sure to use the Python 3 interpreter)"
    echo -e "\t$ pip install -r $adsimulator_PATH/adsimulator/requirements.txt"
    echo -e "\t$ cd $adsimulator_PATH/adsimulator"
    echo -e "\t$ python3 setup.py install"
    echo -e "\t$ rm $adsimulator_PATH/adsimulator_sw.lock"
    echo -e "\t$ adsimulator"
    if [ -d "$adsimulator_PATH/data" ] ; then
        rm -fr $adsimulator_PATH/data
    fi
    cp -r $adsimulator_PATH/adsimulator/data $adsimulator_PATH
fi
