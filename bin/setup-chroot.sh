#!/bin/bash
TOP=$(git rev-parse --show-toplevel)/chroot/
sudo mkdir -p ${TOP}/proc/ && 
sudo mount -t proc none ${TOP}/proc/ &&
sudo mkdir -p ${TOP}/dev/pts &&
sudo mount -t devpts devpts ${TOP}/dev/pts &&
sudo -i chroot ${TOP}/ /bin/bash; 
sudo umount ${TOP}/proc/
sudo umount ${TOP}/dev/pts

